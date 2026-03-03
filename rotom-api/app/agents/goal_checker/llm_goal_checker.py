"""
llm_goal_checker.py — Phase 8.5: LLM-backed goal checker

Lightweight LLM call: goal + capability that ran + result → JSON with
satisfied (bool) and optional output_snippet. Only answers "is this goal satisfied?"
"""

import json
from app.agents.goal_checker.base_goal_checker import BaseGoalChecker
from app.agents.llm.base_llm_client import BaseLLMClient
from app.models.capability_result import CapabilityResult
from app.models.goal_checker_result import GoalCheckerResult
from app.core.logger import get_logger

logger = get_logger(__name__, layer="agent", component="goal_checker")

RESULT_SUMMARY_MAX_LEN = 500


class LLMGoalChecker(BaseGoalChecker):
    """Calls the LLM to decide if the current goal is satisfied after a capability run."""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    def check(
        self,
        goal: str,
        capability_name: str,
        result: CapabilityResult,
    ) -> GoalCheckerResult:
        """Build prompt, call LLM, parse satisfied (and optional output_snippet)."""
        logger.debug(f"Building prompt for llm goal checker.\nGoal:\n{goal}\nCapability name:\n{capability_name}\nResult:\n{result}")
        prompt = self._build_prompt(goal, capability_name, result)
        logger.debug(f"Prompt for llm goal checker:\n{prompt}")
        raw = self.llm_client.generate(prompt)
        logger.debug(f"Raw output (response) from llm goal checker:\n{raw}")
        parsed = self._parse_response(raw)
        logger.debug(f"Parsed output (response) from llm goal checker:\n{parsed}")
        return parsed

    def _build_prompt(
        self,
        goal: str,
        capability_name: str,
        result: CapabilityResult,
    ) -> str:
        """Ask for JSON: satisfied (bool), optional output_snippet (string)."""
        output_summary = (result.output or "")[:RESULT_SUMMARY_MAX_LEN]
        return f"""You are a goal checker. Given the current goal and what was just done, answer ONLY with valid JSON.

JSON shape:
{{
  "satisfied": true or false,
  "output_snippet": null or "<short string to record for this goal, if any>"
}}

Rules:
- "satisfied": true only if the goal has been fully accomplished with the capability that ran and its result. false if more steps are needed for this goal.
- "output_snippet": optional; use if you want to record a short label or value for this goal (e.g. "word_count_original: 146"). Otherwise null.

Current goal: {goal}
Capability that just ran: {capability_name}
Success: {result.success}
Result output: {output_summary}

JSON only:"""

    def _parse_response(self, raw: str) -> GoalCheckerResult:
        """Parse JSON; default to satisfied=True on parse failure to avoid infinite loop."""
        raw = (raw or "").strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("Goal checker returned invalid JSON; defaulting to satisfied=True", extra={"error": str(e)})
            return GoalCheckerResult(satisfied=True)
        satisfied = data.get("satisfied", True)
        if not isinstance(satisfied, bool):
            satisfied = True
        snippet = data.get("output_snippet")
        if snippet is not None and not isinstance(snippet, str):
            snippet = None
        return GoalCheckerResult(satisfied=satisfied, output_snippet=snippet)
