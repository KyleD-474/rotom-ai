"""
base_plan_builder.py — Phase 8.5: Abstract interface for building a plan from user input

The plan builder turns the full user message into an ordered list of steps (Plan).
Each step has at least a goal description; optionally store_output_as and use_from_memory
for the artifact store. RotomCore calls this once at the start of the Phase 8.5 path.
"""

from abc import ABC, abstractmethod
from app.models.plan import Plan


class BasePlanBuilder(ABC):
    """Implementations take user_input and return a Plan (list of PlanStep)."""

    @abstractmethod
    def build_plan(self, user_input: str) -> Plan:
        """
        Produce an ordered list of steps from the user's message.

        Args:
            user_input: The full user message.

        Returns:
            A Plan: list of PlanStep (each has "goal"; optionally "store_output_as", "use_from_memory").
        """
        pass
