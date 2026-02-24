"""
registry.py

Central registry of available capabilities.

Purpose:
- Decouple RotomCore from direct capability instantiation
- Allow dynamic capability registration in future
- Enable plugin architecture later
"""

from app.capabilities.echo import EchoCapability
from app.capabilities.summarizer_stub import SummarizerStubCapability
from app.core.logger import get_logger

logger = get_logger(__name__, layer="capability", component="registry")


# Stores and retrieves capability instances.
class CapabilityRegistry:

    def __init__(self):
        logger.debug(
            "capability_registry_initialized",
            extra={"event": "registry_initialized"}
        )

        self._capabilities = {
            "echo": EchoCapability(),
            "summarizer_stub": SummarizerStubCapability(),
        }

    # Retrieve capability by name.
    def get(self, name: str):
        capability = self._capabilities.get(name)

        if capability:
            logger.debug(
                "capability_retrieved",
                extra={
                    "event": "capability_lookup_success",
                    "capability": name
                }
            )
        else:
            logger.warning(
                "capability_lookup_failed",
                extra={
                    "event": "capability_lookup_failed",
                    "capability": name
                }
            )

        return capability