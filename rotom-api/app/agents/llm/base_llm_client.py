"""
base_llm_client.py — Abstract interface for LLM providers

RotomCore does not call an LLM directly. The intent classifier receives an
LLM client (this interface) and calls generate(prompt) to get a string
response. That way we can swap OpenAI for another provider or a dummy in tests
without changing the classifier or RotomCore.
"""

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Implementations must return raw string output (e.g. JSON text from the model)."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send the prompt to the LLM and return the raw response text."""
        pass