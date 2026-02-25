"""
capability_result.py — Standard result shape for every capability

Every capability returns a CapabilityResult (not a raw string). That way we can
attach metadata (e.g. execution time), signal success or failure, and keep the
API response consistent. RotomCore adds fields like execution_time_ms and
session_id before passing the result up to the service and API. This model is
internal (used by RotomCore and capabilities); the HTTP response uses the
RunResponse schema which mirrors these fields.
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional


class CapabilityResult(BaseModel):
    """What a capability returns: which capability ran, the output text, success flag, and optional metadata."""

    capability: str
    output: str
    success: bool
    metadata: Dict[str, Any] = {}
    session_id: Optional[str] = None