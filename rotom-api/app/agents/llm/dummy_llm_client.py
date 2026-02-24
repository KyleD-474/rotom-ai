from app.agents.llm.base_llm_client import BaseLLMClient


class DummyLLMClient(BaseLLMClient):
    """
    Temporary stub for development.
    """

    def generate(self, prompt: str) -> str:
        # Hardcoded for now
        return '{ "capability": "echo" }'