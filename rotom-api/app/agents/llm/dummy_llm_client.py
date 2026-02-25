"""
dummy_llm_client.py — Stub LLM that always returns a fixed JSON response

Use this when you want to test the pipeline without calling the real OpenAI API
(e.g. in unit tests or when offline). It ignores the prompt and returns a
valid capability invocation so the rest of the flow (validation, registry,
execute) still runs. You can swap it in via AgentService by constructing
DummyLLMClient() instead of OpenAIClient().
"""

from app.agents.llm.base_llm_client import BaseLLMClient


class DummyLLMClient(BaseLLMClient):
    """Always returns the same JSON. Handy for tests and offline development."""

    def generate(self, prompt: str) -> str:
        return '{ "capability": "echo", "arguments": { "message": "dummy" } }'