"""
echo.py — Echo capability: returns the given message unchanged

This is the simplest capability: it takes a "message" argument and returns
it as the output. We use it to test the full pipeline (API → service → RotomCore
→ classifier → registry → capability) and to validate that argument validation
and session memory work without needing a real LLM or external service.
"""

from app.capabilities.base_capability import BaseCapability
from app.models.capability_result import CapabilityResult
from app.core.logger import get_logger

logger = get_logger(__name__, layer="capability", component="echo")


class EchoCapability(BaseCapability):
    name = "echo"
    description = "Repeat the provided message verbatim."
    argument_schema = {"message": "string - The message to repeat."}

    def execute(self, arguments: dict) -> CapabilityResult:
        message = arguments.get("message", "")
        logger.debug("Echo execution started")
        logger.debug("Echo execution completed")
        return CapabilityResult(capability="echo", output=message, success=True, metadata={})