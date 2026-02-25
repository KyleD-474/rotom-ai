"""
base_agent.py — Abstract interface for agents

Agents are the layer that process user input and return a result. RotomCore
is the main (and currently only) agent: it implements handle(user_input, ...).
This base class exists so we can type or document the contract (e.g. "anything
that implements handle") as the system grows. Subclasses may accept additional
parameters (e.g. session_id) but the core is: handle(user_input) → result.
"""

from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Subclasses must implement handle: take user input and return a result (e.g. CapabilityResult)."""

    @abstractmethod
    def handle(self, user_input: str):
        pass