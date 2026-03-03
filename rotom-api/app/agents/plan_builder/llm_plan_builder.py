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
from app.agents.plan_builder.base_plan_builder import BasePlanBuilder
from app.agents.llm.base_llm_client import BaseLLMClient
from app.models.plan import Plan
from app.core.logger import get_logger

logger = get_logger(__name__, layer="agent", component="plan_builder")

USER_INPUT_TRUNCATE_LEN = 8000


class LLMPlanBuilder(BasePlanBuilder):
    """Calls the LLM to decompose user_input into an ordered list of goals."""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    def build_plan(self, user_input: str) -> Plan:
        """Ask the LLM for a list of goals; parse and return. Fallback to single goal on error."""
        logger.debug(f"Building prompt for llm plan builder.\nUser input:\n{user_input}")
        prompt = self._build_prompt(user_input)
        logger.debug(f"Prompt for llm plan builder:\n{prompt}")
        raw = self.llm_client.generate(prompt)
        logger.debug(f"Raw output (response) from llm plan builder:\n{raw}")
        parsed = self._parse_response(raw, user_input)
        logger.debug(f"Parsed output (response) from llm plan builder:\n{json.dumps(parsed, indent=2)}")
        return parsed

    def _build_prompt(self, user_input: str) -> str:
        """Ask for a JSON array of logical, descriptive goals. Each goal will be fed one at a time to another LLM to resolve (pick a tool + arguments)."""
        text = (user_input or "").strip()
        if len(text) > USER_INPUT_TRUNCATE_LEN:
            text = text[:USER_INPUT_TRUNCATE_LEN] + "\n..."
        return f"""You create a short list of logical, descriptive goals. Each goal will be sent to another LLM one at a time to be resolved (that LLM will choose a tool and arguments). So each goal must be clear and self-contained: what to do, and what to use (e.g. "original text", "summarized text").

Output ONLY a valid JSON array of goal strings. No explanations, no markdown.

Good style (descriptive, one-at-a-time resolvable):
["get word count of original text and output it", "summarize original text and output it", "get word count of summarized text and output it"]

User message:
{text}

JSON array of goals only:"""

    def _parse_response(self, raw: str, user_input: str) -> Plan:
        """Parse JSON array of goal strings. On failure, return single goal = user_input."""
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
            return [user_input.strip() or "Complete the user request"]
        if not isinstance(data, list):
            logger.warning("Plan builder did not return a list; using single goal")
            return [user_input.strip() or "Complete the user request"]
        goals = []
        for i, item in enumerate(data):
            if isinstance(item, str) and item.strip():
                goals.append(item.strip())
            elif isinstance(item, dict) and item.get("description"):
                goals.append(str(item["description"]).strip())
        if not goals:
            logger.warning("Plan builder returned empty goals; using single goal")
            return [user_input.strip() or "Complete the user request"]
        return goals
