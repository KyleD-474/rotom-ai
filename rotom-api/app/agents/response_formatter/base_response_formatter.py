"""
base_response_formatter.py — Phase 8.5: Abstract interface for formatting the final response

When all goals are satisfied, the response formatter turns the accumulated
output_data (and user_input, goals) into a single user-facing response string.
RotomCore uses this as the output of the final CapabilityResult (with synthesized=True).
"""

from abc import ABC, abstractmethod
from app.models.plan import Plan


class BaseResponseFormatter(ABC):
    """Implementations take (user_input, output_data, goals) and return a single response string."""

    @abstractmethod
    def format_response(
        self,
        user_input: str,
        output_data: list,
        goals: Plan,
    ) -> str:
        """
        Produce the final user-facing response from the collected data.

        Args:
            user_input: The original user message.
            output_data: List of step results (e.g. [{"goal": "...", "capability": "...", "output": "..."}]).
            goals: The plan (list of goal strings) that was executed.

        Returns:
            A single string to return as the CapabilityResult output (synthesized).
        """
        pass
