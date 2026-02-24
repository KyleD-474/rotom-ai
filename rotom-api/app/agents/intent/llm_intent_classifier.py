import json
from app.agents.intent.base_intent_classifier import BaseIntentClassifier
from app.agents.llm.base_llm_client import BaseLLMClient


class LLMIntentClassifier(BaseIntentClassifier):
    """
    LLM-backed intent classifier.

    Responsibilities:
    - Build classification prompt
    - Invoke LLM client
    - Enforce strict structured JSON contract
    - Validate capability against registry list
    - Return structured invocation data

    This class:
    - Does NOT resolve capabilities
    - Does NOT execute capabilities
    - Does NOT access session state
    - Does NOT construct dependencies
    """

    def __init__(self, llm_client: BaseLLMClient, available_capabilities: list[str]):
        self.llm_client = llm_client
        self.available_capabilities = available_capabilities


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

        raw_output = self.llm_client.generate(prompt)

        try:
            # --- Parse LLM response --- 
            parsed = json.loads(raw_output)

            # --- Validate capability field ---
            capability = parsed.get("capability")

            if not isinstance(capability, str) or not capability.strip():
                raise ValueError("'capability' must be a non-empty string")
            
            capability = capability.strip()
            
            if capability not in self.available_capabilities:
                raise ValueError(f"Invalid capability returned by LLM: {capability}")
            
            # --- Validate arguments field ---
            arguments = parsed.get("arguments", {})

            # Arguments must always be an object
            if not isinstance(arguments, dict):
                raise ValueError("'arguments' must be a JSON object")
            
            # Return structured invocation payload
            return {
                "capability": capability,
                "arguments": arguments,
            }

        except Exception as e:
            # Keep failure centralized and structured
            raise ValueError(f"Failed to parse LLM intent response: {e}")

    def _build_prompt(self, user_input: str) -> str:
        """
        Builds the intent classification prompt.

        We now enforce a stricter JSON format that includes arguments.
        """

        return f"""
You are an intent classifier.

Available capabilities:
{self.available_capabilities}

Given the user input, respond ONLY with valid JSON in this exact format:

{{
  "capability": "<capability_name>",
  "arguments": {{ }}
}}

Rules:
- "capability" must match one of the available capabilities.
- "arguments" must always be a JSON object.
- Do NOT include explanations.
- Do NOT include markdown.
- Output JSON only.

User input:
{user_input}
"""