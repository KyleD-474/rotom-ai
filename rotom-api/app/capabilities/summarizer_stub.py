"""
summarizer_stub.py

Placeholder summarization capability.

Future:
- Replace with LLM-backed summarizer
"""

from app.capabilities.base_capability import BaseCapability
from app.models.capability_result import CapabilityResult
from app.core.logger import get_logger

logger = get_logger(__name__, layer="capability", component="summarizer_stub")


class SummarizerStubCapability(BaseCapability):
    """
    Returns placeholder summary.
    """

    def execute(self, arguments: dict) -> CapabilityResult:
        logger.debug("Summarizer Stub execution started")

        text = arguments.get("text", "")

        summary = f"[SUMMARY PLACEHOLDER]: {text[:50]}"

        logger.debug("Summarizer Stub execution completed")

        return CapabilityResult(
            capability="summarizer_stub",
            output=summary,
            success=True,
            metadata={
                "original_length": len(text)
            }
        )