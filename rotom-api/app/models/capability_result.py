"""
capability_result.py

Defines the standardized result returned by all capabilities.

Why this exists:

Previously, capabilities returned raw strings.
That made it impossible to:

- Attach metadata
- Signal execution success/failure cleanly
- Extend response structure later
- Support multi-step execution pipelines

This model becomes the execution contract between:
Capability → RotomCore → Service → API
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional


class CapabilityResult(BaseModel):
    """
    Standardized capability execution result.
    """

    capability: str
    output: str
    success: bool
    metadata: Dict[str, Any] = {}
    session_id: Optional[str] = None