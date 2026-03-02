"""
registry.py — Central registry of capabilities

RotomCore does not create capabilities itself. It asks the registry "give me
the capability named X" and the registry returns the instance. That keeps
orchestration decoupled from capability construction and makes it easy to add
or swap capabilities in one place. The intent classifier (LLM) gets its list
of "available tools" from list_metadata(), so the prompt always matches what
the registry actually has.

The registry does not create capabilities in production: the service layer
builds the list (e.g. SummarizerStubCapability(llm_client=llm_client)) and
passes it in. When capabilities is omitted (e.g. tests calling CapabilityRegistry()),
_default_capabilities() is used — summarizer then has no LLM (stub-only behavior).
"""

from app.capabilities.echo import EchoCapability
from app.capabilities.summarizer_stub import SummarizerStubCapability
from app.capabilities.word_count import WordCountCapability
from app.core.logger import get_logger

logger = get_logger(__name__, layer="capability", component="registry")


def _default_capabilities():
    """Default capability list: no injected LLM, for tests and backward compatibility."""
    return [EchoCapability(), SummarizerStubCapability(), WordCountCapability()]


class CapabilityRegistry:
    """
    Holds capability instances by name. Built at startup with the current set of capabilities.
    Pass capabilities to inject service-built instances (e.g. summarizer with llm_client).
    """

    def __init__(self, capabilities=None):
        logger.debug("Capability Registry initialized")
        if capabilities is not None:
            cap_list = capabilities
        else:
            cap_list = _default_capabilities()
        self._capabilities = {capability.name: capability for capability in cap_list}

    def get(self, name: str):
        """Return the capability with this name, or None if not found. RotomCore uses this to execute."""
        capability = self._capabilities.get(name)
        if capability:
            logger.debug(
                "capability_retrieved",
                extra={"event": "capability_lookup_success", "capability": name},
            )
        else:
            logger.warning(
                "capability_lookup_failed",
                extra={"event": "capability_lookup_failed", "capability": name},
            )
        return capability

    def list_capabilities(self) -> list[str]:
        """Return the list of capability names. Useful for checks or debugging."""
        return list(self._capabilities.keys())

    def list_metadata(self) -> list[dict]:
        """Return name, description, and argument_schema for each capability. Used by the intent classifier to build the LLM prompt."""
        return [
            {"name": cap.name, "description": cap.description, "arguments": cap.argument_schema}
            for cap in self._capabilities.values()
        ]