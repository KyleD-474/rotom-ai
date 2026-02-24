from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """
    Abstract interface for LLM providers.
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate a response from the LLM.
        Must return raw string output.
        """
        pass