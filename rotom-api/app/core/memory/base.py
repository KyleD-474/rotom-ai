"""
base.py — Phase 5: Session memory interface

This module defines the *contract* for session memory. We use an abstract
interface (not a concrete class) so that:

  - RotomCore and the intent classifier depend only on "something that can
    get context and append entries," not on in-memory lists or a database.
  - We can swap in a different implementation later (e.g. persistent DB or
    vector store) without changing RotomCore or the classifier.
  - Tests can inject a fake memory that returns fixed context or does nothing.

Capabilities never touch memory; only the orchestration layer (RotomCore) does.
"""

from abc import ABC, abstractmethod


class BaseSessionMemory(ABC):
    """
    Abstract interface for session-scoped memory.

    A "session" is identified by session_id (e.g. from the API request).
    For each session we store a sequence of "turn" entries (user said X,
    assistant ran capability Y with result Z). This class does not say
    *where* that data is stored—only that we can:
      - get_context(session_id) → human-readable string for the LLM prompt
      - append(session_id, entry) → record one piece of a turn
    """

    @abstractmethod
    def get_context(self, session_id: str, max_turns: int = 5) -> str:
        """
        Return a string summarizing recent turns for this session.

        This string is injected into the intent-classification prompt so the
        LLM can see "what happened recently" (e.g. "User: hello" / "Assistant
        ran echo; result: hello"). That way, follow-up messages like "echo that
        again" can be classified correctly.

        Returns empty string if the session has no history or doesn't exist.

        Args:
            session_id: Which conversation/session to read from.
            max_turns: How many recent turns to include (one turn = user + assistant).
        """
        pass

    @abstractmethod
    def append(self, session_id: str, entry: dict) -> None:
        """
        Append one turn entry for this session.

        RotomCore calls this twice per request (when session_id is set): once
        with the user's message, once with a short summary of what capability
        ran and what it returned. The exact keys in `entry` are up to the
        implementation; typical ones: role ("user" | "assistant"), content,
        capability, output_summary.
        """
        pass
