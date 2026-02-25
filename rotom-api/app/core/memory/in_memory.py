"""
in_memory.py — Phase 5: In-memory implementation of session memory

This is the concrete implementation of BaseSessionMemory used in production
(by default). It keeps everything in a Python dict in process memory—so when
the process restarts, all conversation history is lost. That's intentional for
Phase 5; a future phase could add a persistent implementation behind the same
interface.
"""

from typing import Dict, List

from app.core.memory.base import BaseSessionMemory


# Limit how many entries we keep per session so memory doesn't grow forever.
# 20 entries ≈ 10 user+assistant pairs (one "turn" = user message + assistant response).
MAX_ENTRIES_PER_SESSION = 20


class InMemorySessionMemory(BaseSessionMemory):
    """
    Session memory stored in RAM. One list of entries per session_id.

    - get_context(): take the last N entries, format them as "User: ..." and
      "Assistant ran X; result: ..." so the LLM gets a readable summary.
    - append(): add one entry to the session's list, then trim the list if it
      exceeds MAX_ENTRIES_PER_SESSION so we don't leak memory.
    """

    def __init__(self, max_entries_per_session: int = MAX_ENTRIES_PER_SESSION) -> None:
        self._max_entries = max_entries_per_session
        # session_id -> list of dicts (each dict is one "entry": user or assistant)
        self._sessions: Dict[str, List[dict]] = {}

    def get_context(self, session_id: str, max_turns: int = 5) -> str:
        entries = self._sessions.get(session_id)
        if not entries:
            return ""

        # One "turn" = user message + assistant response = 2 entries. So max_turns=5 → last 10 entries.
        n = max(0, max_turns * 2) if max_turns else len(entries)
        recent = entries[-n:] if n else entries
        lines = []
        for e in recent:
            role = e.get("role", "unknown")
            if role == "user":
                content = e.get("content", "")
                lines.append(f"User: {content}")
            elif role == "assistant":
                cap = e.get("capability", "")
                summary = e.get("output_summary", e.get("summary", ""))
                lines.append(f"Assistant ran {cap}; result: {summary}")
            else:
                lines.append(str(e))
        return "\n".join(lines) if lines else ""

    def append(self, session_id: str, entry: dict) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        store = self._sessions[session_id]
        store.append(entry)
        # Keep only the most recent entries; drop older ones to cap memory use.
        if len(store) > self._max_entries:
            self._sessions[session_id] = store[-self._max_entries:]
