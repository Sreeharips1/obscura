import time
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class VaultSession:
    original_text: str
    sanitized_text: str
    aliases: list[Any]
    created_at: float
    image_bytes: bytes | None = None


# Temporary in-memory storage for the prototype.
_SESSIONS: dict[str, VaultSession] = {}

TTL_SECONDS = 15 * 60


def create_session(
    original_text: str,
    sanitized_text: str,
    aliases: list[Any],
    image_bytes: bytes | None = None,
) -> str:

    session_id = str(uuid.uuid4())

    _SESSIONS[session_id] = VaultSession(
        original_text=original_text,
        sanitized_text=sanitized_text,
        aliases=aliases,
        created_at=time.time(),
        image_bytes=image_bytes,
    )

    return session_id


def get_session(session_id: str):

    cleanup()

    return _SESSIONS.get(session_id)


def delete_session(session_id: str):

    _SESSIONS.pop(session_id, None)


def cleanup():

    now = time.time()

    expired = [
        sid for sid, s in _SESSIONS.items()
        if now - s.created_at > TTL_SECONDS
    ]

    for sid in expired:
        _SESSIONS.pop(sid, None)
