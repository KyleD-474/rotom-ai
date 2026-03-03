"""
plan.py — Phase 8.5: Structured plan (list of goals)

The plan builder returns a Plan: an ordered list of goal descriptions. Each goal
is a short string (e.g. "Summarize the original text"). RotomCore uses this list
to drive the goals-based loop; we do not advance to the next goal until the
goal checker says the current one is satisfied.
"""

from typing import List

# Plan is an ordered list of goal description strings.
Plan = List[str]
