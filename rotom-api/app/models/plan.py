"""
plan.py — Phase 8.5: Structured plan (list of goals)

The plan builder returns a Plan: an ordered list of steps. Each step has a goal
description and optionally store_output_as / use_from_memory for the artifact store.
RotomCore uses this list to drive the goals-based loop; we do not advance to the
next goal until the goal checker says the current one is satisfied.
"""

from typing import List, TypedDict, Union


class _PlanStepOptional(TypedDict, total=False):
    store_output_as: str
    use_from_memory: Union[str, List[str]]


class PlanStep(_PlanStepOptional, TypedDict):
    """One step in a Plan. goal is required; store_output_as and use_from_memory are optional."""
    goal: str


# Plan is an ordered list of steps (each step has at least "goal").
Plan = List[PlanStep]


def plan_goal_strings(plan: Plan) -> List[str]:
    """
    Return the list of goal description strings for display (e.g. response formatter, metadata).
    Use this when callers expect a list of strings rather than full step objects.
    """
    return [s["goal"] for s in plan]
