"""
models.py — Session state shape

A session is identified by session_id and can hold arbitrary key-value data in
data. RotomCore uses the session store to ensure a session exists when
session_id is provided; the actual conversation context for the LLM is stored
in the memory layer (app.core.memory), not in SessionState.data. This dataclass
is the minimal "session exists" record.
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class SessionState:
    session_id: str
    data: Dict[str, Any] = field(default_factory=dict)