"""
word_count.py — Word-count capability for testing multi-step flows

Returns the number of words in the given text. Deterministic and fast, so
continuation tests can chain echo → word_count (or similar) without calling
an LLM inside a capability. Keeps tests predictable and quick.
"""

from app.capabilities.base_capability import BaseCapability
from app.models.capability_result import CapabilityResult
from app.core.logger import get_logger

logger = get_logger(__name__, layer="capability", component="word_count")


class WordCountCapability(BaseCapability):
    name = "word_count"
    description = "Count the number of words in the provided text."
    argument_schema = {"text": "string - The text to count words in."}

    def execute(self, arguments: dict) -> CapabilityResult:
        text = arguments.get("text", "")
        logger.debug("Word count execution started")
        count = len(text.split()) if isinstance(text, str) else 0
        logger.debug("Word count execution completed")
        return CapabilityResult(
            capability=self.name,
            output=str(count),
            success=True,
            metadata={"word_count": count},
        )
