# patch_warmup.py  -- run from the repo root
import sys

# ---------------- 1. load the model once, with a lock ----------------
path = "backend/app/privacy/detectors/pii_model.py"
with open(path, "r", encoding="utf-8") as f:
    data = f.read()

if "_lock = threading.Lock()" not in data:
    old_import = "from functools import lru_cache"
    old_def = "@lru_cache(maxsize=1)\ndef get_model():"

    if old_import not in data or old_def not in data:
        sys.exit("pii_model.py has unexpected content; patch it manually.")

    data = data.replace(old_import, "import threading\nfrom functools import lru_cache", 1)

    data = data.replace(
        old_def,
        '''_lock = threading.Lock()
_model = None


def get_model():
    global _model

    # Only one request loads the model. Others wait for it.
    with _lock:
        if _model is None:
            _model = _load_model()

        return _model


def _load_model():''',
        1,
    )

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
    print("patched", path)

# ---------------- 2. warm up in the background at startup ----------------
path = "backend/app/main.py"
with open(path, "r", encoding="utf-8") as f:
    data = f.read()

if "def _warm_up" not in data:
    old = "app = FastAPI(\n"

    if old not in data:
        sys.exit("main.py has unexpected content; patch it manually.")

    helper = '''import threading
from contextlib import asynccontextmanager


def _warm_up():
    try:
        from app.privacy.detectors.pii_model import get_model
        from app.privacy.image.ocr import get_engine

        get_model()
        get_engine()
        print("[OBSCURA] Models ready.")
    except Exception as error:
        print(f"[OBSCURA] Warm-up skipped: {type(error).__name__}: {error}")


@asynccontextmanager
async def lifespan(app):
    # Background thread: the server starts immediately.
    threading.Thread(target=_warm_up, daemon=True).start()
    yield


'''

    data = data.replace(old, helper + "app = FastAPI(\n    lifespan=lifespan,\n", 1)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
    print("patched", path)

print("Done.")