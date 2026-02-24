from typing import Dict
from .models import SessionState


class InMemorySessionStore:
    """
    Process-local, in-memory session store.
    Not persistent.
    Not distributed.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)