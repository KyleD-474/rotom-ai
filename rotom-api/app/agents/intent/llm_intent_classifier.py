"""
LLM-backed intent classifier. Uses an LLM to turn user text into a
structured capability + arguments. Phase 5: accepts optional context so
the LLM can see recent conversation when classifying (e.g. "echo that again").
"""
import json
from app.agents.intent.base_intent_classifier import BaseIntentClassifier
from app.agents.llm.base_llm_client import BaseLLMClient
from app.core.logger import get_logger


logger = get_logger(__name__, layer="intent", component="llm_intent_classifier")


class LLMIntentClassifier(BaseIntentClassifier):
    """
    Asks the LLM: "Given the user input (and optional recent context), which
    tool should run and with what arguments?" The LLM returns JSON; we parse
    and validate it. This class does NOT run capabilities or touch session
    state—it only produces the routing decision.
    """

    def __init__(self, llm_client: BaseLLMClient, tool_metadata: list[dict]):
        self.llm_client = llm_client
        # List of {name, description, arguments} for each capability (from registry).
        self.tool_metadata = tool_metadata

    def classify(self, user_input: str, context: str | None = None) -> dict:
        """
        Build a prompt (including context if provided), call the LLM, then
        parse and validate the JSON response. Returns {"capability": str, "arguments": dict}.
        """
        prompt = self._build_prompt(user_input, context=context)

        logger.info(f"prompt: {prompt}")

        raw_output = self.llm_client.generate(prompt)

        logger.info(f"raw_output: {raw_output}")

        try:
            parsed = json.loads(raw_output)
            capability = parsed.get("capability")

            if not isinstance(capability, str) or not capability.strip():
                raise ValueError("'capability' must be a non-empty string")

            capability = capability.strip()
            valid_names = [tool["name"] for tool in self.tool_metadata]
            if capability not in valid_names:
                raise ValueError(f"Invalid capability returned by LLM: {capability}")

            arguments = parsed.get("arguments", {})
            if not isinstance(arguments, dict):
                raise ValueError("'arguments' must be a JSON object")

            return {"capability": capability, "arguments": arguments}

        except Exception as e:
            raise ValueError(f"Failed to parse LLM intent response: {e}")

    def _build_prompt(self, user_input: str, context: str | None = None) -> str:
        """
        Assemble the prompt: list of tools (name, description, args), JSON
        format instructions, then optionally a "Recent context" block (Phase 5),
        then the current user input. The LLM never sees raw session state—only
        this formatted context string.
        """
        tools_section = ""

        for tool in self.tool_metadata:
            tools_section += f"\nTool: {tool['name']}\n"
            tools_section += f"Description: {tool['description']}\n"
            tools_section += "Arguments:\n"

            for arg_name, arg_desc in tool["arguments"].items():
                tools_section += f"  - {arg_name}: {arg_desc}\n"

        # Phase 5: When context is present, we add it and one general principle:
        # resolve references using context. We do NOT enumerate phrases ("that", "it", ...)—
        # that doesn't scale. A scalable alternative (future) is a separate "resolve then classify"
        # step: one call rewrites the user message to be unambiguous, then we classify the rewrite.
        context_block = ""
        context_rule = ""
        if context and context.strip():
            context_block = f"""
Recent context (for reference):
{context.strip()}

"""
            context_rule = "\n- If the current input refers to something in the recent context, fill argument values from that context (e.g. the prior message or result), not the literal wording of the input.\n"

        return f"""
You are an intent classifier.

Available tools:
{tools_section}

Given the user input, respond ONLY with valid JSON in this exact format:

{{
  "capability": "<tool_name>",
  "arguments": {{
      "<argument_name>": <value>
  }}
}}

Rules:
- "capability" must match one of the listed tools.
- "arguments" must match the defined argument schema for that tool.
- Do NOT invent argument names.
- Do NOT include explanations.
- Do NOT include markdown.
- Output JSON only.{context_rule}
{context_block}
User input:
{user_input}
"""