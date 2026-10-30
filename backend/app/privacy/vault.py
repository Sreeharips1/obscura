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


# Temporary in-memory storage for the prototype.
_SESSIONS: dict[str, VaultSession] = {}

# Automatically remove old mappings.
TTL_SECONDS = 15 * 60


def create_session(
    original_text: str,
    sanitized_text: str,
    aliases: list[Any],
) -> str:

    session_id = str(uuid.uuid4())

    _SESSIONS[session_id] = VaultSession(
        original_text=original_text,
        sanitized_text=sanitized_text,
        aliases=aliases,
        created_at=time.time(),
    )

    return session_id


def get_session(session_id: str):

    cleanup()

    return _SESSIONS.get(session_id)


def delete_session(session_id: str):

    _SESSIONS.pop(session_id, None)


def cleanup():

    current_time = time.time()

    expired_sessions = [
        session_id
        for session_id, session in _SESSIONS.items()
        if current_time - session.created_at > TTL_SECONDS
    ]

    for session_id in expired_sessions:
        _SESSIONS.pop(session_id, None)