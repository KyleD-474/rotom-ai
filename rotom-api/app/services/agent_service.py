"""
agent_service.py — Service layer: wires dependencies, exposes run()

The API layer (FastAPI routes) calls AgentService.run(user_input, session_id).
This class is responsible for *building* all the pieces RotomCore needs—session
store, session memory (Phase 5), capability registry, LLM client, intent
classifier, reference resolver (Phase 6), and the goals-based path (plan_builder,
goal_checker, response_formatter)—and injecting them into RotomCore. RotomCore
always uses the goals-based flow. RotomCore itself creates nothing; it only
receives dependencies.
"""

from app.agents.rotom_core import RotomCore
from app.core.logger import get_logger
from app.core.memory import InMemorySessionMemory
from app.core.session.store import InMemorySessionStore
from app.capabilities.registry import CapabilityRegistry
from app.capabilities.echo import EchoCapability
from app.capabilities.summarizer_stub import SummarizerStubCapability
from app.capabilities.word_count import WordCountCapability

# from app.agents.llm.dummy_llm_client import DummyLLMClient
from app.agents.llm.openai_client import OpenAIClient
from app.agents.intent_classifier import LLMIntentClassifier
from app.agents.reference_resolver import LLMReferenceResolver
from app.agents.plan_builder import LLMPlanBuilder
from app.agents.goal_checker import LLMGoalChecker
from app.agents.response_formatter import LLMResponseFormatter

logger = get_logger(__name__, layer="service", component="agent_service")


class AgentService:
    """
    Constructs RotomCore and its dependencies. The only public method is
    run(user_input, session_id=None), which delegates to rotom_core.handle(...).
    """

    def __init__(self):
        logger.debug("Agent service initialized")

        # Where we store session identity (and optionally other session data).
        session_store = InMemorySessionStore()

        # Phase 5: Where we store recent conversation per session for the LLM context.
        session_memory = InMemorySessionMemory()

        llm_client = OpenAIClient()
        
        # We build capabilities here (not in the registry) so we can inject llm_client into the summarizer.
        # The registry only holds what we pass; it does not create capabilities in this path.
        # Summarizer always gets llm_client so production does real summarization.
        capabilities = [
            EchoCapability(),
            SummarizerStubCapability(llm_client=llm_client),
            WordCountCapability(),
        ]
        registry = CapabilityRegistry(capabilities=capabilities)
        tool_metadata = registry.list_metadata()


        intent_classifier = LLMIntentClassifier(
            llm_client=llm_client,
            tool_metadata=tool_metadata,
        )
        # Phase 6: Resolver rewrites user message from context before building plan.
        reference_resolver = LLMReferenceResolver(llm_client=llm_client)

        # Goals-based path: always wired so RotomCore uses plan → goals → goal_checker → response_formatter.
        plan_builder = LLMPlanBuilder(llm_client=llm_client)
        goal_checker = LLMGoalChecker(llm_client=llm_client)
        response_formatter = LLMResponseFormatter(llm_client=llm_client)

        # RotomCore gets everything via constructor—no hidden dependencies.
        self.rotom_core = RotomCore(
            intent_classifier=intent_classifier,
            registry=registry,
            session_store=session_store,
            session_memory=session_memory,
            plan_builder=plan_builder,
            goal_checker=goal_checker,
            response_formatter=response_formatter,
            reference_resolver=reference_resolver,
        )

    def run(self, user_input: str, session_id: str | None = None):
        """Process one user message; optional session_id enables Phase 5 context/memory for that session."""
        logger.debug("Agent service dispatching to agent (rotom_core)")
        result = self.rotom_core.handle(user_input, session_id=session_id)
        logger.debug("Agent service execution completed")
        return result