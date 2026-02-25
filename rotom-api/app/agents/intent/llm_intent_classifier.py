import json
from app.agents.intent.base_intent_classifier import BaseIntentClassifier
from app.agents.llm.base_llm_client import BaseLLMClient
from app.core.logger import get_logger


logger = get_logger(__name__, layer="intent", component="llm_intent_classifier")


class LLMIntentClassifier(BaseIntentClassifier):
    """
    LLM-backed intent classifier.

    Responsibilities:
    - Build classification prompt
    - Invoke LLM client
    - Enforce strict structured JSON contract
    - Validate capability against registry metadata
    - Return structured invocation data

    This class:
    - Does NOT resolve capabilities
    - Does NOT execute capabilities
    - Does NOT access session state
    - Does NOT construct dependencies
    """

    def __init__(self, llm_client: BaseLLMClient, tool_metadata: list[dict]):
        self.llm_client = llm_client
        self.tool_metadata = tool_metadata


    def classify(self, user_input: str) -> dict:
        """
        Classifies user input into a structured capability invocation.

        Returns:
            {
                "capability": "<string>",
                "arguments": { ... }
            }

        Raises:
            ValueError if JSON is invalid or structure is incorrect.
        """
        prompt = self._build_prompt(user_input)
        
        logger.info(f"prompt: {prompt}")
        
        raw_output = self.llm_client.generate(prompt)

        logger.info(f"raw_output: {raw_output}")

        try:
            # --- Parse LLM response ---
            parsed = json.loads(raw_output)

            # --- Validate capability field ---
            capability = parsed.get("capability")

            if not isinstance(capability, str) or not capability.strip():
                raise ValueError("'capability' must be a non-empty string")

            capability = capability.strip()

            valid_names = [tool["name"] for tool in self.tool_metadata]

            if capability not in valid_names:
                raise ValueError(f"Invalid capability returned by LLM: {capability}")

            # --- Validate arguments field ---
            arguments = parsed.get("arguments", {})

            # Arguments must always be an object
            if not isinstance(arguments, dict):
                raise ValueError("'arguments' must be a JSON object")

            return {
                "capability": capability,
                "arguments": arguments,
            }

        except Exception as e:
            raise ValueError(f"Failed to parse LLM intent response: {e}")


    def _build_prompt(self, user_input: str) -> str:
        """
        Builds the intent classification prompt.

        Tool metadata is dynamically injected from the registry.
        """

        tools_section = ""

        for tool in self.tool_metadata:
            tools_section += f"\nTool: {tool['name']}\n"
            tools_section += f"Description: {tool['description']}\n"
            tools_section += "Arguments:\n"

            for arg_name, arg_desc in tool["arguments"].items():
                tools_section += f"  - {arg_name}: {arg_desc}\n"

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
- Output JSON only.

User input:
{user_input}
"""