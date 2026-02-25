"""
run_response.py — Response schema for POST /run

The HTTP response shape is defined here so the API contract is explicit and
stable. It matches the internal CapabilityResult (capability name, output,
success, metadata, session_id) but we keep it as a separate schema so that
internal models can evolve without forcing breaking API changes.
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional


class RunResponse(BaseModel):
    """What the client gets back: which capability ran, its output, success flag, optional metadata, and session_id if provided."""

    capability: str
    output: str
    success: bool
    metadata: Dict[str, Any]
    session_id: Optional[str] = None