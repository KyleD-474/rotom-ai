import json
from app.agents.intent.base_intent_classifier import BaseIntentClassifier
from app.agents.llm.base_llm_client import BaseLLMClient


class LLMIntentClassifier(BaseIntentClassifier):

    def __init__(self, llm_client: BaseLLMClient, available_capabilities: list[str]):
        self.llm_client = llm_client
        self.available_capabilities = available_capabilities

    def classify(self, user_input: str) -> str:
        prompt = self._build_prompt(user_input)

        raw_output = self.llm_client.generate(prompt)

        try:
            parsed = json.loads(raw_output)
            capability = parsed.get("capability")

            if capability not in self.available_capabilities:
                raise ValueError("Invalid capability returned by LLM")

            return capability

        except Exception as e:
            raise ValueError(f"Failed to parse LLM intent response: {e}")

    def _build_prompt(self, user_input: str) -> str:
        return f"""
You are an intent classifier.

Available capabilities:
{self.available_capabilities}

Given the user input, respond ONLY with valid JSON in this format:

{{ "capability": "<capability_name>" }}

User input:
{user_input}
"""