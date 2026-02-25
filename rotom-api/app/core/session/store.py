"""
store.py — In-memory session store

This is where we keep "session identity": given a session_id from the API, we
return (or create) a SessionState for it. We do not store conversation history
here—that lives in the memory layer (app.core.memory). This store is
process-local and not persistent; when the process restarts, all sessions are
gone. A future implementation could use Redis or a DB behind the same interface.
"""

from typing import Dict
from .models import SessionState


class InMemorySessionStore:
    """Maps session_id to SessionState. get() creates the session if it doesn't exist; clear() removes it."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        """Return the session for this id, creating a new SessionState if needed."""
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    def clear(self, session_id: str) -> None:
        """Remove the session (e.g. on logout or explicit reset)."""
        self._sessions.pop(session_id, None)