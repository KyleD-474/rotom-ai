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

# Returns input string unchanged.
class EchoCapability(BaseCapability):

    def execute(self, user_input: str) -> CapabilityResult:
        logger.debug("Echo execution started")

        result = user_input
        
        # Inserted failure to test error-handling in rotom_core.py:
        # raise ValueError("Echo exploded")
        
        logger.debug("Echo execution comlpeted")

        return CapabilityResult(
            capability="echo",
            output=result,
            success=True,
            metadata={}
        )