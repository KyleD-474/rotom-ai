"""
base_plan_builder.py — Phase 8.5: Abstract interface for building a plan from user input

The plan builder turns the full user message into an ordered list of goals
(user-level steps). RotomCore calls this once at the start of the Phase 8.5 path.
"""

from abc import ABC, abstractmethod
from app.models.plan import Plan


class BasePlanBuilder(ABC):
    """Implementations take user_input and return a Plan (list of goal description strings)."""

    @abstractmethod
    def build_plan(self, user_input: str) -> Plan:
        """
        Produce an ordered list of goals from the user's message.

        Args:
            user_input: The full user message.

        Returns:
            A Plan: list of goal description strings (e.g. ["Capture original text", "Summarize the text"]).
        """
        pass
