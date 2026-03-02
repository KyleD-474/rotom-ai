"""
agent_service.py — Service layer: wires dependencies, exposes run()

The API layer (FastAPI routes) calls AgentService.run(user_input, session_id).
This class is responsible for *building* all the pieces RotomCore needs—session
store, session memory (Phase 5), capability registry, LLM client, intent
classifier, and reference resolver (Phase 6)—and injecting them into RotomCore.
RotomCore itself creates nothing; it only receives dependencies. That way we
can test RotomCore with mocks and swap implementations (e.g. different memory
backend) in one place.

Phase 8: Continuation decider is chosen via ROTOM_CONTINUATION_MODE (env):
  - "noop" (default): NoOpContinuationDecider — single-step, no extra LLM call.
  - "llm": LLMContinuationDecider — multi-step reasoning via structured continuation.
"""

import os

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
from app.agents.intent.llm_intent_classifier import LLMIntentClassifier
from app.agents.reference_resolver import LLMReferenceResolver
from app.agents.continuation import NoOpContinuationDecider, LLMContinuationDecider

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
        # Phase 6: Resolver rewrites user message from context before classification.
        # We reuse the same llm_client so one provider serves both resolver and classifier.
        reference_resolver = LLMReferenceResolver(llm_client=llm_client)
        
        # Phase 7/8: Continuation decider — noop (single-step) or LLM (multi-step). Env switch for gradual rollout.
        continuation_mode = os.getenv("ROTOM_CONTINUATION_MODE", "noop").lower()
        if continuation_mode == "llm":
            continuation_decider = LLMContinuationDecider(
                llm_client=llm_client,
                tool_metadata=tool_metadata,
            )
            logger.debug("Continuation decider: LLM (multi-step enabled)")
        else:
            continuation_decider = NoOpContinuationDecider()
            if continuation_mode != "noop":
                logger.warning(
                    "Unknown ROTOM_CONTINUATION_MODE; using noop",
                    extra={"event": "continuation_mode_unknown", "mode": continuation_mode},
                )

        # RotomCore gets everything via constructor—no hidden dependencies.
        self.rotom_core = RotomCore(
            intent_classifier=intent_classifier,
            registry=registry,
            session_store=session_store,
            session_memory=session_memory,
            reference_resolver=reference_resolver,
            continuation_decider=continuation_decider,
        )

    def run(self, user_input: str, session_id: str | None = None):
        """Process one user message; optional session_id enables Phase 5 context/memory for that session."""
        logger.debug("Agent service dispatching to agent")
        result = self.rotom_core.handle(user_input, session_id=session_id)
        logger.debug("Agent service execution completed")
        return result