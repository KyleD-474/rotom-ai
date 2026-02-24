"""
echo.py

Simple echo capability.

Used for:
- Testing routing
- Validating capability system
"""

from app.capabilities.base_capability import BaseCapability
from app.models.capability_result import CapabilityResult
from app.core.logger import get_logger

logger = get_logger(__name__, layer="capability", component="echo")


class EchoCapability(BaseCapability):

    def execute(self, arguments: dict) -> CapabilityResult:
        logger.debug("Echo execution started")

        # Phase 2: Structured arguments
        message = arguments.get("message", "")

        # raise ValueError("Echo exploded")  # Testing failure path

        logger.debug("Echo execution completed")

        return CapabilityResult(
            capability="echo",
            output=message,
            success=True,
            metadata={}
        )