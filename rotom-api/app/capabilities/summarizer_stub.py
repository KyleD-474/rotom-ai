"""
summarizer_stub.py — Placeholder summarization capability

This capability exists so the intent classifier has a second tool to choose from
(e.g. "summarize this" can route here). It does not call an LLM; it just
truncates the input and labels it as a placeholder. Later it can be replaced
with a real summarizer that uses the injected LLM client or an external API.
"""

from app.capabilities.base_capability import BaseCapability
from app.models.capability_result import CapabilityResult
from app.core.logger import get_logger

logger = get_logger(__name__, layer="capability", component="summarizer_stub")


class SummarizerStubCapability(BaseCapability):
    name = "summarizer_stub"
    description = "Summarize the provided text."
    argument_schema = {"text": "string - The text to summarize."}

    def execute(self, arguments: dict) -> CapabilityResult:
        text = arguments.get("text", "")
        logger.debug("Summarizer Stub execution started")
        summary = f"[SUMMARY PLACEHOLDER]: {text[:50]}"
        logger.debug("Summarizer Stub execution completed")
        return CapabilityResult(
            capability="summarizer_stub",
            output=summary,
            success=True,
            metadata={"original_length": len(text)},
        )