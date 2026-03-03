"""
base_goal_checker.py — Phase 8.5: Abstract interface for "is this goal satisfied?"

The goal checker answers only: given the current goal, what we just ran, and the
result, is the goal satisfied? It does not suggest the next capability—the
intent classifier does that. RotomCore calls this after each capability run
within a goal.
"""

from abc import ABC, abstractmethod
from app.models.capability_result import CapabilityResult
from app.models.goal_checker_result import GoalCheckerResult


class BaseGoalChecker(ABC):
    """Implementations take (goal, capability_name, result) and return GoalCheckerResult(satisfied, optional snippet)."""

    @abstractmethod
    def check(
        self,
        goal: str,
        capability_name: str,
        result: CapabilityResult,
    ) -> GoalCheckerResult:
        """
        Decide whether the current goal is satisfied after running the given capability.

        Args:
            goal: The current goal description.
            capability_name: Name of the capability that just ran.
            result: The CapabilityResult from that run.

        Returns:
            GoalCheckerResult(satisfied=True/False, optional output_snippet to append to output_data).
        """
        pass
