"""
run_response.py

Defines the API response schema for the /run endpoint.

This is the formal API contract exposed externally.
It mirrors CapabilityResult but exists separately
to maintain a clean separation between internal models
and external API schemas.
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional


class RunResponse(BaseModel):
    """
    Structured response returned by /run endpoint.
    """

    capability: str
    output: str
    success: bool
    metadata: Dict[str, Any]
    session_id: Optional[str] = None