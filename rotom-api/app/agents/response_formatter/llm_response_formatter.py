"""
llm_response_formatter.py — Phase 8.5: LLM-backed response formatter

When all goals are satisfied, one LLM call: user_input + output_data + goals →
a single user-facing response string. RotomCore uses this as the final
CapabilityResult output (synthesized).
"""

from app.agents.response_formatter.base_response_formatter import BaseResponseFormatter
from app.agents.llm.base_llm_client import BaseLLMClient
from app.models.plan import Plan
from app.core.logger import get_logger
import json

logger = get_logger(__name__, layer="agent", component="response_formatter")

OUTPUT_DATA_TRUNCATE = 3000


class LLMResponseFormatter(BaseResponseFormatter):
    """Calls the LLM to produce a final narrative from the collected output_data and goals."""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    def format_response(
        self,
        user_input: str,
        output_data: list,
        goals: Plan,
    ) -> str:
        """Build prompt with user_input, output_data, goals; return LLM response as the final output."""
        logger.debug(f"Building prompt for llm response formatter.\nUser input:\n{user_input}\nOutput data:\n{json.dumps(output_data, indent=2)}\nGoals:\n{json.dumps(goals, indent=2)}")
        
        prompt = self._build_prompt(user_input, output_data, goals)
        logger.debug(f"Prompt for llm response formatter:\n{prompt}")
        
        raw = self.llm_client.generate(prompt)
        logger.debug(f"Raw output (response) from llm response formatter:\n{raw}")
        
        formatted_response = (raw or "").strip() or "No response generated."
        logger.debug(f"Formatted response from llm response formatter:\n{formatted_response}")
        return formatted_response

    def _build_prompt(self, user_input: str, output_data: list, goals: Plan) -> str:
        """Ask the LLM to produce a clear, user-facing response from the data."""
        data_str = json.dumps(output_data, indent=2)
        if len(data_str) > OUTPUT_DATA_TRUNCATE:
            data_str = data_str[:OUTPUT_DATA_TRUNCATE] + "\n..."
        goals_str = "\n".join(f"{i+1}. {g}" for i, g in enumerate(goals))
        user_short = (user_input or "").strip()
        if len(user_short) > 1500:
            user_short = user_short[:1500] + "..."
        return f"""You are a response formatter. The user made a request, and the system has collected results for each goal. Produce a single, clear response for the user that summarizes what was done and presents the key results. Write in a helpful, concise way. Do not repeat the raw JSON; turn it into readable narrative or structured summary.

User's original request:
{user_short}

Goals that were executed:
{goals_str}

Collected output data (from each step):
{data_str}

Write the final response to the user:"""
