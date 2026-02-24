"""
agent_service.py

Service layer between API and Agent.

Responsibilities:
- Provide a clean abstraction between HTTP layer and agent logic
- Handle orchestration-level concerns
- Remain transport-agnostic

This layer allows us to:
- Replace FastAPI later
- Add background jobs
- Introduce session state
"""

from app.agents.rotom_core import RotomCore
from app.core.logger import get_logger

from app.core.session.store import InMemorySessionStore
from app.capabilities.registry import CapabilityRegistry

# from app.agents.llm.dummy_llm_client import DummyLLMClient
from app.agents.llm.openai_client import OpenAIClient
from app.agents.intent.llm_intent_classifier import LLMIntentClassifier

logger = get_logger(__name__, layer="service", component="agent_service")


# Thin orchestration layer wrapping RotomCore.
class AgentService:
    def __init__(self):
        logger.debug("Agent service initialized")

        # Core infrastructure
        session_store = InMemorySessionStore()
        registry = CapabilityRegistry()

        # LLM infrastructure
        # llm_client = DummyLLMClient()
        llm_client = OpenAIClient()
        available_capabilities = registry.list_capabilities()

        intent_classifier = LLMIntentClassifier(
            llm_client=llm_client,
            available_capabilities=available_capabilities
        )

        self.rotom_core = RotomCore(
            intent_classifier=intent_classifier,
            registry=registry,
            session_store=session_store
        )

    # Entry point from API layer.
    # Logs lifecycle events and delegates to RotomCore.
    def run(self, user_input: str, session_id: str | None = None):
        logger.debug("Agent service dispatching to agent")
        result = self.rotom_core.handle(user_input, session_id=session_id)
        logger.debug("Agent service execution completed")

        return result