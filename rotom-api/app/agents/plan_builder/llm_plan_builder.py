"""
llm_plan_builder.py — Phase 8.5: LLM-backed plan builder

Produces logical, descriptive goals that are fed one at a time to the intent
classifier (another LLM) to resolve. Each goal should be self-contained so the
classifier can pick the right capability and arguments (e.g. "get word count of
original text and output it", "summarize original text and output it", "get word
count of summarized text and output it"). One LLM call: user_input → JSON array
of goal strings; on parse failure or empty list we fall back to a single goal.
"""

import json
from typing import List, Optional

from app.agents.plan_builder.base_plan_builder import BasePlanBuilder
from app.agents.llm.base_llm_client import BaseLLMClient
from app.models.plan import Plan, PlanStep
from app.core.logger import get_logger

logger = get_logger(__name__, layer="agent", component="plan_builder")

USER_INPUT_TRUNCATE_LEN = 8000


class LLMPlanBuilder(BasePlanBuilder):
    """Calls the LLM to decompose user_input into an ordered list of goals."""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    def build_plan(self, user_input: str) -> Plan:
        """Ask the LLM for a list of goals; parse and return. Fallback to single goal on error."""
        logger.debug(f"Building plan.")
        prompt = self._build_prompt(user_input)
        logger.debug(f"Plan builder prompt:\n{prompt}")
        raw = self.llm_client.generate(prompt)
        parsed = self._parse_response(raw, user_input)
        logger.debug(f"Plan builder result:\n{parsed}")
        return parsed

    def _build_prompt(self, user_input: str) -> str:
        """Ask for a JSON array of goals (strings or objects). Objects may include store_output_as and use_from_memory for artifact passing."""
        text = (user_input or "").strip()
        if len(text) > USER_INPUT_TRUNCATE_LEN:
            text = text[:USER_INPUT_TRUNCATE_LEN] + "\n..."
        return f"""You create a short list of logical, descriptive goals. Each goal will be sent to another LLM one at a time to be resolved (that LLM will choose a tool and arguments). So each goal must be clear and self-contained: what to do, and what to use (e.g. "original text", "summarized text").

When a step produces an output that a LATER step will need (e.g. a summary, an extracted value), add "store_output_as": "short_key" to that step. When a step needs an output from an earlier step, add "use_from_memory": "short_key" to that step. Use the same key name for the producer and consumer.

Output ONLY a valid JSON array. Each element may be:
- A goal string (plain string), or
- An object with "goal" (string) and optionally "store_output_as" (string key) and/or "use_from_memory" (string or array of strings).
A plain array of goal strings is still valid if you need no artifact passing.

Example (word count original, summarize and store, echo, word count of summary):
["get word count of original text and output it", {{ "goal": "summarize original text and output it", "store_output_as": "summarized_text" }}, "print 'Hello World!!!'", {{ "goal": "get word count of summarized text and output it", "use_from_memory": "summarized_text" }}]

User message:
{text}

JSON array only:"""

    def _parse_response(self, raw: str, user_input: str) -> Plan:
        """Parse JSON array into a list of PlanStep. Accepts goal strings or objects with goal/store_output_as/use_from_memory."""
        fallback_goal = (user_input or "").strip() or "Complete the user request"
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
            logger.warning("Plan builder returned invalid JSON; using single goal", extra={"error": str(e)})
            return [{"goal": fallback_goal}]
        if not isinstance(data, list):
            logger.warning("Plan builder did not return a list; using single goal")
            return [{"goal": fallback_goal}]
        steps: List[PlanStep] = []
        for item in data:
            step = self._normalize_item_to_step(item)
            if step:
                steps.append(step)
        if not steps:
            logger.warning("Plan builder returned no valid goals; using single goal")
            return [{"goal": fallback_goal}]
        return steps

    def _normalize_item_to_step(self, item) -> Optional[PlanStep]:
        """Turn one array element (string or dict) into a PlanStep, or None if invalid."""
        if isinstance(item, str) and (s := (item or "").strip()):
            return {"goal": s}
        if isinstance(item, dict):
            goal = (item.get("goal") or item.get("description") or "").strip()
            if goal:
                step: PlanStep = {"goal": goal}
                if item.get("store_output_as"):
                    step["store_output_as"] = str(item["store_output_as"]).strip()
                if item.get("use_from_memory") is not None:
                    step["use_from_memory"] = item["use_from_memory"]
                return step
        return None
