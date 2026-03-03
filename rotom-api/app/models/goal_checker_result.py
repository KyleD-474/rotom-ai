"""
goal_checker_result.py — Phase 8.5: Result of asking "is this goal satisfied?"

The goal checker returns satisfied (bool) and optionally output_snippet (string
to append to output_data for this goal). RotomCore does not advance to the next
goal until satisfied is True.
"""

from typing import Optional


class GoalCheckerResult:
    """Result of goal checker: is the current goal satisfied? Optional snippet for output_data."""

    def __init__(self, satisfied: bool, output_snippet: Optional[str] = None):
        self.satisfied = satisfied
        self.output_snippet = output_snippet if output_snippet and str(output_snippet).strip() else None
