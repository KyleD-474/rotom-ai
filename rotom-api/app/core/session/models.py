from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class SessionState:
    session_id: str
    data: Dict[str, Any] = field(default_factory=dict)