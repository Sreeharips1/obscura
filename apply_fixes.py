# apply_fixes.py  -- run from the repo root
import os, sys

if not (os.path.isdir("backend/app") and os.path.isdir("frontend/src")):
    sys.exit("Run this from the repo root (the folder containing backend/ and frontend/).")

FILES = {}

# ----------------------------------------------------------------------
FILES["backend/app/debug.py"] = r'''import os


def debug(*args, **kwargs):
    # Only prints when OBSCURA_DEBUG=1. Never leave this on in production,
    # because debug output can contain private values.
    if os.getenv("OBSCURA_DEBUG", "0") == "1":
        print(*args, **kwargs)
'''

# ----------------------------------------------------------------------
FILES["backend/app/routes/privacy.py"] = r'''from fastapi import APIRouter

from app.debug import debug
from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    PrepareRequest,
    PrepareResponse,
    AliasPreview,
    ClearRequest,
)
from app.privacy.service import analyze, sanitize
from app.privacy.vault import create_session, delete_session


router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_text(request: AnalyzeRequest):

    detections = analyze(request.text)

    return AnalyzeResponse(
        text=request.text,
        detections=detections,
    )


@router.post("/prepare", response_model=PrepareResponse)
def prepare_text(request: PrepareRequest):

    detections = analyze(request.text)

    # --------------------------------------------------------
    # BLOCK SECRETS
    #
    # IMPORTANT: check ALL detections, not only the selected
    # ones. The UI never lets the user select BLOCK items, so
    # checking only the selection would let secrets through.
    # --------------------------------------------------------

    blocked = [
        detection
        for detection in detections
        if detection.recommended_action == "BLOCK"
    ]

    if blocked:
        return PrepareResponse(
            session_id="",
            original_text=request.text,
            sanitized_text="",
            aliases=[],
            blocked=True,
            warning=(
                "A credential or secret was detected. "
                "Remove it before sending this request "
                "to an external AI."
            ),
        )

    # --------------------------------------------------------
    # Only keep selected IDs that really exist.
    # --------------------------------------------------------

    known_ids = {detection.id for detection in detections}

    selected_ids = [
        detection_id
        for detection_id in request.selected_detection_ids
        if detection_id in known_ids
    ]

    ignored = len(request.selected_detection_ids) - len(selected_ids)

    if ignored:
        debug(f"[OBSCURA] {ignored} selected detection IDs were not found.")

    # --------------------------------------------------------
    # SANITIZE
    # --------------------------------------------------------

    sanitized_text, aliases = sanitize(
        request.text,
        detections,
        selected_ids,
    )

    debug(
        "[OBSCURA] prepare:",
        f"{len(detections)} detections,",
        f"{len(aliases)} aliases",
    )

    # --------------------------------------------------------
    # CREATE PRIVACY VAULT SESSION
    # --------------------------------------------------------

    session_id = create_session(
        original_text=request.text,
        sanitized_text=sanitized_text,
        aliases=aliases,
    )

    previews = [
        AliasPreview(
            type=alias.type,
            original=alias.original,
            alias=alias.alias,
        )
        for alias in aliases
    ]

    return PrepareResponse(
        session_id=session_id,
        original_text=request.text,
        sanitized_text=sanitized_text,
        aliases=previews,
    )


@router.post("/clear")
def clear_session(request: ClearRequest):

    delete_session(request.session_id)

    return {"cleared": True}
'''

# ----------------------------------------------------------------------
FILES["backend/app/routes/chat.py"] = r'''from fastapi import APIRouter, HTTPException

from app.ai.gemini import generate_text
from app.debug import debug
from app.models import SendRequest, SendResponse
from app.privacy.pseudonymizer import restore_text
from app.privacy.response_guard import verify_response
from app.privacy.vault import get_session, delete_session


router = APIRouter()


@router.post("/send", response_model=SendResponse)
def send_to_ai(request: SendRequest):

    session = get_session(request.session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=(
                "Privacy session expired or does not exist. "
                "Please create the protected preview again."
            ),
        )

    # Only visible when OBSCURA_DEBUG=1. This is the sanitized
    # text, which is what Gemini receives.
    debug("\n========== OBSCURA -> AI ==========")
    debug(session.sanitized_text)
    debug("===================================\n")

    try:

        ai_response = generate_text(session.sanitized_text)

        # ----------------------------------------------------
        # RESPONSE PRIVACY CHECK
        # ----------------------------------------------------

        guard_result = verify_response(ai_response, session.aliases)

        if not guard_result["safe"]:

            leaked_types = [
                leak["type"] for leak in guard_result["potential_leaks"]
            ]

            # Log only the TYPES, never the original values.
            print(
                "[OBSCURA SECURITY] Potential private-data leak "
                f"detected in AI response. Types: {leaked_types}"
            )

            delete_session(request.session_id)

            raise HTTPException(
                status_code=502,
                detail=(
                    "The AI response appeared to contain original "
                    "private information. OBSCURA blocked the response."
                ),
            )

        # ----------------------------------------------------
        # RESTORE ORIGINAL VALUES
        # ----------------------------------------------------

        restored_response = restore_text(ai_response, session.aliases)

        delete_session(request.session_id)

        return SendResponse(response=restored_response)

    except HTTPException:
        raise

    except Exception as error:

        print(f"[OBSCURA] Gemini request failed: {type(error).__name__}")
        debug(repr(error))

        raise HTTPException(
            status_code=502,
            detail=f"Gemini request failed: {error}",
        )
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/detector.py"] = r'''from app.debug import debug
from app.models import Detection

from app.privacy.detectors.patterns import detect_patterns
from app.privacy.detectors.secrets import detect_secrets
from app.privacy.detectors.context import detect_context
from app.privacy.detectors.contextual import detect_contextual
from app.privacy.detectors.ner import detect_ner
from app.privacy.detectors.pii_model import detect_pii

from app.privacy.entity_fusion import fuse_detections
from app.privacy.overlap_resolver import resolve_overlaps


def _run(name: str, function, text: str) -> list[Detection]:
    # One broken optional detector (for example a missing model)
    # must not take the whole pipeline down. The warning is always
    # printed so you notice that protection is reduced.
    try:
        return function(text)
    except Exception as error:
        print(
            f"[OBSCURA WARNING] {name} detector failed "
            f"({type(error).__name__}). Continuing without it."
        )
        debug(repr(error))
        return []


def _dump(title: str, detections: list[Detection]) -> None:
    # Values are intentionally NOT printed.
    debug(f"\n========== {title} ==========")
    for d in detections:
        debug(
            f"{d.type:20} | {d.source:15} | "
            f"{d.confidence:.2f} | {d.start}:{d.end}"
        )
    debug("===================================\n")


def detect_text(text: str) -> list[Detection]:

    detections: list[Detection] = []

    detections.extend(_run("pattern", detect_patterns, text))
    detections.extend(_run("secret", detect_secrets, text))
    detections.extend(_run("confidential-context", detect_context, text))
    detections.extend(_run("contextual", detect_contextual, text))
    detections.extend(_run("ner", detect_ner, text))
    detections.extend(_run("pii-model", detect_pii, text))

    _dump("BEFORE FUSION", detections)

    detections = fuse_detections(detections)

    _dump("AFTER FUSION", detections)

    detections = resolve_overlaps(detections)

    return detections
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/entity_fusion.py"] = r'''from app.models import Detection


# ============================================================
# WEIGHTS
# ============================================================

SOURCE_WEIGHT = {
    "PATTERN": 1.00,
    "SECRET": 1.00,
    "CONTEXT": 0.92,
    "NER": 0.82,
    "PII_MODEL": 0.78,
    "UNKNOWN": 0.50,
}

RISK_WEIGHT = {
    "CRITICAL": 1.00,
    "HIGH": 0.85,
    "MEDIUM": 0.65,
    "LOW": 0.40,
}

TYPE_PRIORITY = {
    "PASSWORD": 110,
    "API_KEY_OR_TOKEN": 110,
    "PRIVATE_KEY": 110,
    "JWT_TOKEN": 109,

    "AADHAAR_LIKE": 105,
    "PAN_LIKE": 105,
    "CARD_NUMBER_LIKE": 104,
    "BANK_ACCOUNT": 103,

    "EMAIL": 100,
    "PHONE": 99,

    "IMEI": 95,
    "MAC_ADDRESS": 94,
    "IFSC_CODE": 93,
    "UPI_ID": 92,
    "IP_ADDRESS": 91,

    "SENSITIVE_URL": 90,

    "ADDRESS": 85,
    "LOCATION": 84,
    "PERSON_NAME": 83,
    "ORGANIZATION": 82,
    "EMPLOYER": 80,
    "PROJECT_NAME": 79,

    "CONFIDENTIAL_CONTEXT": 40,
}

CONTEXT_TYPE_PREFERENCE = {
    "ORGANIZATION": 4,
    "EMPLOYER": 3,
    "PERSON_NAME": 3,
    "ADDRESS": 3,
    "LOCATION": 2,
    "PROJECT_NAME": 2,
}


# ============================================================
# HELPERS
# ============================================================

def overlaps(first: Detection, second: Detection) -> bool:
    return first.start < second.end and second.start < first.end


def normalized_value(detection: Detection) -> str:
    return detection.value.strip().lower()


def same_entity(first: Detection, second: Detection) -> bool:
    # ------------------------------------------------------------
    # Two detections are the "same candidate" ONLY when they are
    # about the same piece of text.
    #
    # The old rule "same type + same value anywhere in the text"
    # was removed on purpose: it merged every occurrence of a
    # repeated value (e.g. "Sreehari" twice) into ONE detection,
    # so only one span was kept and the others stayed in plaintext.
    # Repeated occurrences must stay separate detections; the
    # pseudonymizer gives them the same alias.
    # ------------------------------------------------------------

    # Exact same span (even if detectors disagree about the type).
    if first.start == second.start and first.end == second.end:
        return True

    # Same value AND overlapping span.
    if normalized_value(first) == normalized_value(second) and overlaps(first, second):
        return True

    return False


def source_score(detection: Detection) -> float:
    sources = detection.evidence or [detection.source]

    if not sources:
        return SOURCE_WEIGHT["UNKNOWN"]

    return max(
        SOURCE_WEIGHT.get(source, SOURCE_WEIGHT["UNKNOWN"])
        for source in sources
    )


def choose_best(detections: list[Detection]) -> Detection:

    def score(detection: Detection):

        base_type = TYPE_PRIORITY.get(detection.type, 0)

        has_context = (
            detection.source == "CONTEXT"
            or "CONTEXT" in (detection.evidence or [])
        )

        context_bonus = 0

        if has_context:
            context_bonus = CONTEXT_TYPE_PREFERENCE.get(detection.type, 0)

        if detection.type == "PERSON_NAME" and has_context:
            base_type += 10

        if detection.type == "ORGANIZATION" and has_context:
            base_type += 8

        return (
            base_type,
            context_bonus,
            source_score(detection),
            detection.confidence,
            RISK_WEIGHT.get(detection.risk, 0.0),
            detection.end - detection.start,
        )

    return max(detections, key=score)


def calculate_confidence(detections: list[Detection]) -> float:

    if not detections:
        return 0.0

    probability_not_detected = 1.0

    for detection in detections:

        base = max(0.0, min(detection.confidence, 1.0))

        effective = max(0.0, min(base * source_score(detection), 0.99))

        probability_not_detected *= 1.0 - effective

    combined = 1.0 - probability_not_detected

    return round(min(combined, 0.99), 2)


# ============================================================
# FUSE
# ============================================================

def fuse_detections(detections: list[Detection]) -> list[Detection]:

    if not detections:
        return []

    ordered = sorted(detections, key=lambda d: (d.start, d.end))

    groups: list[list[Detection]] = []

    for detection in ordered:

        matched_group = None

        for group in groups:
            if any(same_entity(detection, existing) for existing in group):
                matched_group = group
                break

        if matched_group is not None:
            matched_group.append(detection)
        else:
            groups.append([detection])

    fused = []

    for group in groups:

        best = choose_best(group)

        evidence = []

        for detection in group:
            for source in (detection.evidence or [detection.source]):
                if source not in evidence:
                    evidence.append(source)

        confidence = calculate_confidence(group)

        if len(group) == 1:
            reason = best.reason
        else:
            reason = (
                f"{best.reason} "
                "Multiple detection methods supported this finding."
            )

        fused.append(
            best.model_copy(
                update={
                    "confidence": confidence,
                    "source": "+".join(evidence),
                    "evidence": evidence,
                    "reason": reason,
                }
            )
        )

    fused.sort(key=lambda d: (d.start, d.end))

    return fused
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/pseudonymizer.py"] = r'''from collections import defaultdict

from app.models import Detection, AliasItem


# ============================================================
# TOKEN PREFIXES
# ============================================================

TOKEN_PREFIXES = {
    "EMAIL": "OBSCURA_EMAIL",
    "PHONE": "OBSCURA_PHONE",
    "PERSON_NAME": "OBSCURA_NAME",
    "ORGANIZATION": "OBSCURA_ORG",
    "EMPLOYER": "OBSCURA_EMPLOYER",
    "ADDRESS": "OBSCURA_ADDRESS",
    "LOCATION": "OBSCURA_LOCATION",
    "PROJECT_NAME": "OBSCURA_PROJECT",

    "AADHAAR_LIKE": "OBSCURA_GOV_ID",
    "PAN_LIKE": "OBSCURA_GOV_ID",

    "IFSC_CODE": "OBSCURA_BANK_CODE",
    "UPI_ID": "OBSCURA_UPI",
    "CARD_NUMBER_LIKE": "OBSCURA_CARD",

    "IP_ADDRESS": "OBSCURA_IP",
    "MAC_ADDRESS": "OBSCURA_MAC",
    "IMEI": "OBSCURA_IMEI",

    "SENSITIVE_URL": "OBSCURA_URL",

    "USERNAME": "OBSCURA_USERNAME",
    "PASSWORD": "OBSCURA_PASSWORD",

    "BANK_ACCOUNT": "OBSCURA_BANK_ACCOUNT",
    "PASSPORT_NUMBER": "OBSCURA_PASSPORT",
    "DRIVER_LICENSE": "OBSCURA_LICENSE",

    "CONFIDENTIAL_CONTEXT": "OBSCURA_CONFIDENTIAL",
}


def generate_token(detection_type: str, number: int) -> str:

    prefix = TOKEN_PREFIXES.get(detection_type, "OBSCURA_PRIVATE")

    return f"<{prefix}_{number:03d}>"


def normalize_entity_value(value: str) -> str:

    return " ".join(value.strip().lower().split())


def _entity_key(detection: Detection) -> tuple[str, str]:

    return (detection.type, normalize_entity_value(detection.value))


# ============================================================
# EXPAND SELECTION
# ============================================================
#
# If the user protects ONE occurrence of a value (e.g. "Sreehari"),
# every other occurrence of the same type + value is protected too.
# Otherwise the name would still leak from the other occurrences.
# BLOCK items are never included here.
# ============================================================

def expand_selection(
    detections: list[Detection],
    selected_ids: list[str],
) -> list[str]:

    selected = set(selected_ids)

    chosen_entities = {
        _entity_key(detection)
        for detection in detections
        if detection.id in selected
        and detection.recommended_action != "BLOCK"
    }

    return [
        detection.id
        for detection in detections
        if detection.recommended_action != "BLOCK"
        and (
            detection.id in selected
            or _entity_key(detection) in chosen_entities
        )
    ]


# ============================================================
# BUILD ALIAS MAP
# ============================================================

def build_aliases(
    detections: list[Detection],
    selected_ids: list[str],
) -> list[AliasItem]:

    aliases = []
    counters = defaultdict(int)
    entity_aliases = {}

    selected = set(selected_ids)

    selected_detections = sorted(
        (
            detection
            for detection in detections
            if detection.id in selected
            and detection.recommended_action != "BLOCK"
        ),
        key=lambda detection: (detection.start, detection.end),
    )

    for detection in selected_detections:

        key = _entity_key(detection)

        if key in entity_aliases:
            continue

        counters[detection.type] += 1

        alias = AliasItem(
            detection_id=detection.id,
            original=detection.value,
            alias=generate_token(detection.type, counters[detection.type]),
            type=detection.type,
        )

        aliases.append(alias)
        entity_aliases[key] = alias

    return aliases


# ============================================================
# SANITIZE TEXT
# ============================================================

def sanitize_text(
    text: str,
    detections: list[Detection],
    selected_ids: list[str],
):

    selected_ids = expand_selection(detections, selected_ids)

    aliases = build_aliases(detections, selected_ids)

    alias_by_entity = {
        (alias.type, normalize_entity_value(alias.original)): alias
        for alias in aliases
    }

    selected = set(selected_ids)

    replacements = []

    for detection in detections:

        if detection.id not in selected:
            continue

        alias = alias_by_entity.get(_entity_key(detection))

        if alias is None:
            continue

        replacements.append((detection.start, detection.end, alias.alias))

    # Right -> left keeps earlier character positions valid.
    replacements.sort(key=lambda item: item[0], reverse=True)

    sanitized = text

    for start, end, replacement in replacements:
        sanitized = sanitized[:start] + replacement + sanitized[end:]

    return sanitized, aliases


# ============================================================
# RESTORE AI RESPONSE
# ============================================================

def restore_text(text: str, aliases: list[AliasItem]) -> str:

    restored = text

    for alias in sorted(aliases, key=lambda a: len(a.alias), reverse=True):
        restored = restored.replace(alias.alias, alias.original)

    return restored
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/detectors/context.py"] = r'''import re

from app.models import Detection
from app.privacy.detectors.patterns import make_detection


# ============================================================
# CONFIDENTIAL CONTEXT PATTERNS
# ============================================================

CONFIDENTIAL_PATTERNS = [
    r"\bconfidential\b",
    r"\binternal\s+use\s+only\b",
    r"\bnot\s+for\s+distribution\b",
    r"\bdo\s+not\s+share\b",
    r"\bprivate\s+information\b",
    r"\bsecret\s+project\b",
    r"\bunreleased\s+product\b",
    r"\btrade\s+secret\b",
]


def detect_context(text: str) -> list[Detection]:

    detections = []

    for pattern in CONFIDENTIAL_PATTERNS:

        for match in re.finditer(pattern, text, re.IGNORECASE):

            detections.append(
                make_detection(
                    kind="CONFIDENTIAL_CONTEXT",
                    value=match.group(),
                    category="CONFIDENTIAL_INFORMATION",
                    confidence=0.72,
                    risk="HIGH",
                    reason=(
                        "The surrounding language suggests "
                        "that this information may be confidential."
                    ),
                    start=match.start(),
                    end=match.end(),
                    action="ASK_USER",
                    source="CONTEXT",
                )
            )

    return detections
'''

# ----------------------------------------------------------------------
FILES["backend/app/privacy/image/detector.py"] = r'''import cv2
import hashlib

from app.privacy.image.models import ImageRegion, ImageDetectionResult


def generate_region_id(region_type: str, x: int, y: int, width: int, height: int) -> str:

    raw = f"{region_type}:{x}:{y}:{width}:{height}"

    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def _polygons_to_regions(points, region_type, label, confidence) -> list[ImageRegion]:

    regions = []

    if points is None or len(points) == 0:
        return regions

    for polygon in points:

        if polygon is None:
            continue

        polygon = polygon.astype(int).reshape(-1, 2)

        x = int(polygon[:, 0].min())
        y = int(polygon[:, 1].min())
        width = int(polygon[:, 0].max()) - x
        height = int(polygon[:, 1].max()) - y

        if width <= 0 or height <= 0:
            continue

        regions.append(
            ImageRegion(
                id=generate_region_id(region_type, x, y, width, height),
                type=region_type,
                label=label,
                confidence=confidence,
                x=x,
                y=y,
                width=width,
                height=height,
                source="OPENCV",
                recommended_action="BLUR",
            )
        )

    return regions


# ============================================================
# QR CODE DETECTION
# ============================================================

def detect_qr_codes(image) -> list[ImageRegion]:

    try:
        detector = cv2.QRCodeDetector()

        # detectMulti only LOCATES codes. It does not need to decode
        # them, so unreadable/partial QR codes are still found.
        ok, points = detector.detectMulti(image)

        if not ok:
            return []

        return _polygons_to_regions(points, "QR_CODE", "QR code", 0.98)

    except Exception as error:
        print(f"[OBSCURA IMAGE] QR detection error: {error}")
        return []


# ============================================================
# BARCODE DETECTION
# ============================================================

def _make_barcode_detector():

    # Newer OpenCV (needs opencv-contrib): cv2.barcode.BarcodeDetector
    barcode_module = getattr(cv2, "barcode", None)

    if barcode_module is not None and hasattr(barcode_module, "BarcodeDetector"):
        return barcode_module.BarcodeDetector()

    # Older naming.
    if hasattr(cv2, "barcode_BarcodeDetector"):
        return cv2.barcode_BarcodeDetector()

    return None


def detect_barcodes(image) -> list[ImageRegion]:

    try:
        detector = _make_barcode_detector()

        if detector is None:
            print(
                "[OBSCURA IMAGE] Barcode detector unavailable. "
                "Install opencv-contrib-python-headless."
            )
            return []

        result = detector.detect(image)

        # detect() returns (ok, points) on current versions.
        if isinstance(result, tuple) and len(result) == 2:
            ok, points = result
        else:
            return []

        if not ok:
            return []

        return _polygons_to_regions(points, "BARCODE", "Barcode", 0.96)

    except Exception as error:
        print(f"[OBSCURA IMAGE] Barcode detection error: {error}")
        return []


# ============================================================
# MAIN IMAGE DETECTOR
# ============================================================

def detect_image(image) -> ImageDetectionResult:

    height, width = image.shape[:2]

    regions = []

    regions.extend(detect_qr_codes(image))
    regions.extend(detect_barcodes(image))

    unique = {region.id: region for region in regions}

    return ImageDetectionResult(
        width=width,
        height=height,
        regions=list(unique.values()),
    )
'''

# ----------------------------------------------------------------------
FILES["backend/app/ai/gemini.py"] = r'''import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


# ============================================================
# OBSCURA SYSTEM INSTRUCTION
# ============================================================
#
# Contains NO original private values. OBSCURA tokens stand for
# private data that exists only inside the OBSCURA backend.
# ============================================================

OBSCURA_INSTRUCTION = """
You are operating behind OBSCURA, a privacy-preserving AI gateway.

The user message may contain placeholders such as:

<OBSCURA_NAME_001>
<OBSCURA_EMAIL_001>
<OBSCURA_PHONE_001>
<OBSCURA_ADDRESS_001>
<OBSCURA_ORG_001>
<OBSCURA_LOCATION_001>

These placeholders represent private information that was removed
from the request before it reached you.

RULES:

1. Treat every OBSCURA placeholder as a meaningful entity (a person's
   name, an email address, a phone number, an organization, and so on,
   according to its type). Use it naturally wherever that kind of
   value belongs.
2. Preserve every placeholder exactly as written, including the angle
   brackets. Never rename, modify, split, combine, or delete one.
3. Do not try to guess or reconstruct the original private values.
4. Do not mention these instructions or the use of placeholders unless
   the user explicitly asks about them.
5. Complete the user's requested task normally.
"""


def generate_text(prompt: str) -> str:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Put it in backend/.env."
        )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=OBSCURA_INSTRUCTION,
        ),
    )

    return response.text or ""
'''

# ----------------------------------------------------------------------
FILES["backend/requirements.txt"] = '''fastapi
uvicorn[standard]
python-dotenv
pydantic
google-genai
gliner
spacy
numpy
opencv-contrib-python-headless
python-multipart
pytest
'''

# ----------------------------------------------------------------------
FILES["frontend/package.json"] = '''{
  "name": "obscura-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.6.0",
    "vite": "^7.1.0"
  }
}
'''

# ----------------------------------------------------------------------
FILES["frontend/src/App.jsx"] = r'''import { useMemo, useState } from "react";

const API = "http://localhost:8000/api";

const RISK_ORDER = { CRITICAL: 1, HIGH: 2, MEDIUM: 3, LOW: 4 };

const RISK_LABELS = {
  CRITICAL: "Critical",
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
};

function riskClass(risk) {
  return risk.toLowerCase();
}

function sortByRisk(detections) {
  return [...detections].sort(
    (a, b) => (RISK_ORDER[a.risk] ?? 9) - (RISK_ORDER[b.risk] ?? 9),
  );
}

function getActionLabel(action) {
  switch (action) {
    case "BLOCK":
      return "Blocked";
    case "PSEUDONYMIZE":
      return "Pseudonymize";
    case "REPLACE":
      return "Replace";
    case "ASK_USER":
      return "Review";
    default:
      return action;
  }
}

export default function App() {
  const [text, setText] = useState("");

  const [analyzed, setAnalyzed] = useState(false);
  const [detections, setDetections] = useState([]);
  const [selected, setSelected] = useState(new Set());

  const [sanitized, setSanitized] = useState("");
  const [aliases, setAliases] = useState([]);
  const [sessionId, setSessionId] = useState("");

  const [aiResponse, setAiResponse] = useState("");

  const [status, setStatus] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isPreparing, setIsPreparing] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const hasDetections = detections.length > 0;
  const hasBlocked = detections.some(
    (detection) => detection.recommended_action === "BLOCK",
  );
  const orderedDetections = sortByRisk(detections);
  const selectedCount = selected.size;

  const recommendedIds = useMemo(
    () =>
      detections
        .filter((detection) => detection.recommended_action !== "BLOCK")
        .map((detection) => detection.id),
    [detections],
  );

  // Forget everything derived from the old text.
  // Detection IDs depend on the exact text, so they go stale on any edit.
  function resetResults() {
    setAnalyzed(false);
    setDetections([]);
    setSelected(new Set());
    setSanitized("");
    setAliases([]);
    setSessionId("");
    setAiResponse("");
  }

  function handleTextChange(event) {
    setText(event.target.value);

    if (analyzed || sanitized || aiResponse) {
      resetResults();
      setStatus("");
    }
  }

  // ==========================================================
  // ANALYZE
  // ==========================================================

  async function analyze() {
    if (!text.trim()) return;

    try {
      setIsAnalyzing(true);
      setStatus("Checking for potentially sensitive information...");
      resetResults();

      const response = await fetch(`${API}/privacy/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        throw new Error("Privacy analysis failed.");
      }

      const data = await response.json();
      const found = data.detections || [];

      setDetections(found);
      setAnalyzed(true);

      // Select everything except BLOCK items by default.
      setSelected(
        new Set(
          found
            .filter((detection) => detection.recommended_action !== "BLOCK")
            .map((detection) => detection.id),
        ),
      );

      if (found.some((d) => d.recommended_action === "BLOCK")) {
        setStatus(
          "A secret or credential was found. Remove it from your text before continuing.",
        );
      } else if (found.length) {
        setStatus(
          `${found.length} potentially sensitive item${
            found.length === 1 ? "" : "s"
          } detected.`,
        );
      } else {
        setStatus(
          "No supported sensitive patterns were detected. You can continue.",
        );
      }
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Unable to analyze the text.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  function toggle(id) {
    const detection = detections.find((item) => item.id === id);

    if (detection?.recommended_action === "BLOCK") return;

    setSelected((old) => {
      const next = new Set(old);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectRecommended() {
    setSelected(new Set(recommendedIds));
    setStatus("Recommended privacy protections selected.");
  }

  function clearAll() {
    setSelected(new Set());
    setStatus("All optional privacy protections cleared.");
  }

  // ==========================================================
  // CREATE PROTECTED PREVIEW
  // ==========================================================

  async function createPreview() {
    if (hasBlocked) {
      setStatus("Remove the secret or credential before continuing.");
      return;
    }

    try {
      setIsPreparing(true);
      setStatus("Creating protected AI input...");

      const response = await fetch(`${API}/privacy/prepare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          selected_detection_ids: [...selected],
        }),
      });

      if (!response.ok) {
        throw new Error("Unable to create the protected preview.");
      }

      const data = await response.json();

      if (data.blocked) {
        setSanitized("");
        setAliases([]);
        setSessionId("");
        setStatus(data.warning || "This request cannot be sent.");
        return;
      }

      setSessionId(data.session_id);
      setSanitized(data.sanitized_text);
      setAliases(data.aliases || []);

      setStatus(
        "Protected preview ready. Review exactly what Gemini will receive.",
      );
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Unable to create protected preview.");
    } finally {
      setIsPreparing(false);
    }
  }

  // ==========================================================
  // SEND TO GEMINI
  // ==========================================================

  async function sendToAI() {
    if (!sessionId) {
      setStatus("Create a protected preview first.");
      return;
    }

    try {
      setIsSending(true);
      setStatus("Sending only protected data to Gemini...");

      const response = await fetch(`${API}/chat/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "AI request failed.");
      }

      // Restoration happens in the trusted backend, never here.
      setAiResponse(data.response);
      setSessionId("");

      setStatus(
        "Response received. Original private values were restored inside the trusted backend.",
      );
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Unable to communicate with Gemini.");
    } finally {
      setIsSending(false);
    }
  }

  async function clearPrivacySession() {
    if (sessionId) {
      try {
        await fetch(`${API}/privacy/clear`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
        });
      } catch (error) {
        console.error("Unable to clear session:", error);
      }
    }

    setSessionId("");
    setSanitized("");
    setAliases([]);
    setStatus("Temporary privacy data cleared.");
  }

  async function copyProtectedText() {
    if (!sanitized) return;

    try {
      await navigator.clipboard.writeText(sanitized);
      setStatus("Protected text copied to clipboard.");
    } catch (error) {
      console.error(error);
      setStatus("Unable to copy protected text.");
    }
  }

  // ==========================================================
  // UI
  // ==========================================================

  return (
    <div className="app">
      <header className="header">
        <div>
          <div className="brand">OBSCURA</div>
          <div className="subtitle">Privacy-Preserving AI Gateway</div>
        </div>

        <select className="model" defaultValue="Gemini">
          <option>Gemini</option>
        </select>
      </header>

      <main className="main">
        <section className="hero">
          <h1>
            Chat with AI without unnecessarily exposing your private data.
          </h1>

          <p>
            OBSCURA checks your input before it reaches the external AI, lets
            you choose what to protect, and shows you the exact protected
            request before transmission.
          </p>
        </section>

        <section className="composer card">
          <textarea
            value={text}
            onChange={handleTextChange}
            placeholder={
              "Try: My name is Sreehari, phone is " +
              "9876543210 and email is example@gmail.com. " +
              "Write a job application email."
            }
          />

          <div className="composerFooter">
            <span className="hint">
              Your raw text is analyzed before external AI transmission.
            </span>

            <button disabled={!text.trim() || isAnalyzing} onClick={analyze}>
              {isAnalyzing ? "Checking..." : "Check Privacy"}
            </button>
          </div>
        </section>

        {status && <div className="status">{status}</div>}

        {/* ===================================================
            PRIVACY REVIEW (always shown after analysis)
        =================================================== */}

        {analyzed && (
          <section className="card">
            <div className="sectionTitle">
              <div>
                <h2>Privacy Review</h2>

                <p>
                  {hasDetections
                    ? "We found potentially sensitive information in your request. Choose what should be hidden from the external AI."
                    : "No sensitive items were detected. Detection is rule and model based, so please still review your text yourself."}
                </p>
              </div>

              {hasDetections && (
                <span className="count">
                  {selectedCount} / {detections.length} selected
                </span>
              )}
            </div>

            {hasBlocked && (
              <div className="blockedMessage">
                🔒 A secret or credential was detected. Remove it from your
                text and run the check again. This request cannot be sent while
                it is present.
              </div>
            )}

            {hasDetections && (
              <>
                <div className="privacyActions">
                  <button className="secondary" onClick={selectRecommended}>
                    Select Recommended
                  </button>

                  <button className="secondary" onClick={clearAll}>
                    Clear All
                  </button>
                </div>

                <div className="detections">
                  {orderedDetections.map((detection) => {
                    const isBlocked =
                      detection.recommended_action === "BLOCK";
                    const isSelected = selected.has(detection.id);

                    return (
                      <label
                        className={`detection ${riskClass(detection.risk)} ${
                          isBlocked ? "blockedDetection" : ""
                        }`}
                        key={detection.id}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          disabled={isBlocked}
                          onChange={() => toggle(detection.id)}
                        />

                        <div className="detectionBody">
                          <div className="detectionTop">
                            <strong>{detection.value}</strong>

                            <span
                              className={`risk ${riskClass(detection.risk)}`}
                            >
                              {RISK_LABELS[detection.risk] || detection.risk}
                            </span>
                          </div>

                          <div className="meta">
                            {detection.type} {" · "} {detection.category}
                          </div>

                          <div className="reason">{detection.reason}</div>

                          <div className="action">
                            Action:{" "}
                            <strong>
                              {getActionLabel(detection.recommended_action)}
                            </strong>
                          </div>

                          {isBlocked && (
                            <div className="blockedMessage">
                              🔒 This item cannot be sent to the external AI.
                            </div>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              </>
            )}

            <button onClick={createPreview} disabled={hasBlocked || isPreparing}>
              {isPreparing
                ? "Preparing..."
                : selectedCount === 0
                  ? "Continue Without Protection"
                  : "Create Protected Preview"}
            </button>
          </section>
        )}

        {/* ===================================================
            AI INPUT PREVIEW
        =================================================== */}

        {sanitized && (
          <section className="card preview">
            <div className="sectionTitle">
              <div>
                <h2>AI Input Preview</h2>

                <p>
                  Review the exact text that will cross the AI privacy boundary.
                </p>
              </div>
            </div>

            <div className="compare">
              <div>
                <div className="label">ORIGINAL</div>
                <pre>{text}</pre>
              </div>

              <div>
                <div className="label">AI WILL RECEIVE</div>
                <pre>{sanitized}</pre>
              </div>
            </div>

            {aliases.length > 0 && (
              <div className="aliasSection">
                <div className="label">PROTECTED VALUES</div>

                <div className="aliasList">
                  {aliases.map((alias, index) => (
                    <div className="alias" key={`${alias.original}-${index}`}>
                      <span>{alias.original}</span>
                      <span>→</span>
                      <strong>{alias.alias}</strong>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="previewNotice">
              🔐 Gemini will receive only the protected version shown above.
              <br />
              The original-to-alias mapping remains inside the OBSCURA backend.
            </div>

            <div className="actions">
              <button className="secondary" onClick={copyProtectedText}>
                Copy Protected Text
              </button>

              <button className="secondary" onClick={clearPrivacySession}>
                Clear Privacy Data
              </button>

              <button onClick={sendToAI} disabled={!sessionId || isSending}>
                {isSending ? "Sending..." : "Confirm & Send to Gemini"}
              </button>
            </div>
          </section>
        )}

        {aiResponse && (
          <section className="card response">
            <div className="label">AI RESPONSE</div>

            <div className="responseText">{aiResponse}</div>

            <div className="responseNotice">
              ✓ Private values were restored by the OBSCURA backend.
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
'''

# ----------------------------------------------------------------------
# WRITE EVERYTHING
# ----------------------------------------------------------------------
for path, content in FILES.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("wrote", path)

# README: add the spaCy model step
readme = "README.md"
if os.path.exists(readme):
    with open(readme, "r", encoding="utf-8") as f:
        data = f.read()
    marker = "pip install -r requirements.txt\n"
    extra = "python -m spacy download en_core_web_sm\n"
    if marker in data and extra not in data:
        data = data.replace(marker, marker + "\n# Required for the NER detector\n" + extra, 1)
        with open(readme, "w", encoding="utf-8", newline="\n") as f:
            f.write(data)
        print("updated README.md")

print("\nDone. Next steps are in the chat message.")