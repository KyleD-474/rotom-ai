"""
summarizer_stub.py — Summarization capability (stub or LLM-backed)

When llm_client is None (e.g. in tests or default registry), this capability
behaves as a deterministic stub: truncates input and prefixes a placeholder.
When llm_client is injected (e.g. by the service layer), it calls the LLM
to produce a short summary so multi-step flows like "draft → summarize" work
for real. Capabilities may use injected services per architecture; they do
not construct dependencies.
"""

from app.capabilities.base_capability import BaseCapability
from app.models.capability_result import CapabilityResult
from app.core.logger import get_logger

logger = get_logger(__name__, layer="capability", component="summarizer_stub")

# Max chars sent to LLM for summarization to keep prompts bounded.
SUMMARY_INPUT_MAX_LEN = 4000


class SummarizerStubCapability(BaseCapability):
    name = "summarizer_stub"
    description = "Summarize the provided text in one or two sentences."
    argument_schema = {"text": "string - The text to summarize."}

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: Optional LLM client. When None, stub behavior (deterministic).
                When set, summarize via llm_client.generate() for real summaries.
        """
        self.llm_client = llm_client

    def execute(self, arguments: dict) -> CapabilityResult:
        text = (arguments.get("text") or "").strip()
        logger.debug("Summarizer execution started")

        if self.llm_client is not None:
            # Real summarization: bounded prompt, structured instruction.
            truncated = text[:SUMMARY_INPUT_MAX_LEN]
            if len(text) > SUMMARY_INPUT_MAX_LEN:
                truncated += "..."
            prompt = f"""Summarize the following in one or two concise sentences. Output only the summary, no preamble.

Text:
{truncated}

Summary:"""
            try:
                summary = (self.llm_client.generate(prompt) or "").strip()
                if not summary:
                    summary = "[No summary produced]"
            except Exception as e:
                logger.warning(
                    "Summarizer LLM call failed; falling back to stub",
                    extra={"event": "summarizer_llm_error", "error": str(e)},
                )
                summary = f"[SUMMARY]: {text[:80]}{'...' if len(text) > 80 else ''}"
            output = summary
        else:
            # Stub: deterministic for tests and when no LLM is wired.
            output = f"[SUMMARY PLACEHOLDER]: {text[:50]}{'...' if len(text) > 50 else ''}"

        logger.debug("Summarizer execution completed")
        return CapabilityResult(
            capability=self.name,
            output=output,
            success=True,
            metadata={"original_length": len(text)},
        )
