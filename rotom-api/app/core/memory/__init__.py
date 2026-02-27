"""
Session memory (Phase 5).

Import from here when you need the memory abstraction or the default
in-memory implementation:

  - BaseSessionMemory: abstract interface (get_context, append). Use this
    type for parameters so callers can pass a mock in tests.
  - InMemorySessionMemory: concrete implementation that stores entries in
    a dict in process memory. Used by AgentService to wire RotomCore.
"""

from app.core.memory.base_session_memory import BaseSessionMemory
from app.core.memory.in_memory import InMemorySessionMemory

__all__ = ["BaseSessionMemory", "InMemorySessionMemory"]
