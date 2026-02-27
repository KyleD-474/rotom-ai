"""
rotom_core.py — The main orchestrator

RotomCore is the "brain" that: (1) asks the intent classifier which capability
to run and with what arguments, (2) looks up that capability in the registry,
(3) validates arguments, (4) runs the capability, (5) handles errors and
timing. It does NOT construct any of its dependencies—those are injected
by the service layer.

Phase 5: When a session_id is present, we read recent conversation from
session_memory and pass it to the classifier (so it can understand "echo that
again"). After execution we append this turn (user message + what we ran +
short result summary) to session_memory for the next request. Capabilities
never see session or memory—only RotomCore talks to memory.

Phase 6: When session_id and context exist and a reference_resolver is injected,
we first rewrite the user message (resolve "that", "it", "again" from context),
then run intent classification on the rewritten message only. We still append
the original user_input to memory so the stored conversation reflects what the
user actually said.

Phase 7: After a capability runs, we call the continuation_decider (if present)
with the user message, capability name, and result. It returns a structured
ContinuationResult (done, next_capability, etc.). In Phase 7 we do not use
that to change the response—we still return the capability output. The call
establishes the contract for Phase 8 to loop or use a synthesized reply.
"""
import time
from app.core.logger import get_logger
from app.models.capability_result import CapabilityResult
from app.models.capability_invocation import CapabilityInvocation

logger = get_logger(__name__, layer="agent", component="rotom_core")

# When we store the capability result in memory we truncate output to avoid huge prompts.
OUTPUT_SUMMARY_MAX_LEN = 200


class RotomCore:
    """
    Single entry point for "handle this user message": classify intent,
    resolve capability, validate args, execute, then record the turn in
    memory if we have a session_id.
    """

    def __init__(
        self,
        intent_classifier,
        registry,
        session_store,
        session_memory,
        reference_resolver=None,
        continuation_decider=None,
    ):
        logger.info("Rotom Core initialized")
        self.registry = registry
        self.intent_classifier = intent_classifier
        self.session_store = session_store
        self.session_memory = session_memory
        # Phase 6: Optional. When set, we rewrite user message from context before classifying.
        self.reference_resolver = reference_resolver
        # Phase 7: Optional. When set, we call it after every capability run; it returns a structured continuation. We don't use the return to change the response yet.
        self.continuation_decider = continuation_decider

    def handle(self, user_input: str, session_id: str | None = None):
        """
        Process one user message: get context from memory (if session), optionally
        rewrite references (Phase 6), classify intent, run the chosen capability,
        then write this turn back to memory. Memory always stores the original
        user_input, not the rewritten message.
        """
        logger.debug("Input received")

        if session_id:
            self.session_store.get(session_id)  # ensure session exists

        # Phase 5: Pull recent conversation for this session.
        context = ""
        if session_id:
            context = self.session_memory.get_context(session_id, max_turns=5) or ""

        # Phase 6: Resolve-then-classify. When we have context and a resolver,
        # rewrite the message first so the classifier sees an explicit message only.
        message_for_classifier = user_input
        used_resolver = False
        if session_id and context.strip() and self.reference_resolver is not None:
            message_for_classifier = self.reference_resolver.resolve(user_input, context)
            used_resolver = True

        # Ask classifier: which capability + arguments? When we rewrote, pass
        # context=None so the classifier prompt stays simple (no reference-resolution rules).
        classifier_context = None if used_resolver else (context or None)
        intent_data = self.intent_classifier.classify(
            message_for_classifier, context=classifier_context
        )
       
        # Defensive contract enforcement
        if not self._validate_intent_data(intent_data):
            raise ValueError("IntentClassifier returned invalid invocation structure")
            
        # Convert structured intent into internal invocation model
        invocation = CapabilityInvocation(
            capability_name=intent_data["capability"],
            arguments=intent_data["arguments"],
        )

        # Extract capabilty name from internal invocation model 
        capability_name = invocation.capability_name

        logger.debug(f"Routing decision: {capability_name}")

        # Find capability in registry
        capability = self.registry.get(capability_name)

        if not capability:
            logger.error(
                "Capability not found.",
                extra={
                    "event": "capability_error",
                    "capability": capability_name
                }
            )
            raise ValueError(f"Capability '{capability_name}' not found")

        # --- Phase 4: Argument validation (before execution) ---
        self._validate_arguments(capability_name, capability, invocation.arguments)

        logger.debug(f"Execution started: {capability_name}")

        start_time = time.perf_counter() # Measure execution time
        
        try:
            # --- Phase 2: Execute with structured arguments ---
            result = capability.execute(invocation.arguments)
            error_message = None

        except Exception as e:
            # Catch any unhandled exception from capability
            error_message = str(e)

            # Log the error with structured context
            self._log_failure(capability_name, error_message)
            
            # Create a fallback CapabilityResult
            result = CapabilityResult(
                capability=capability_name,
                output="",
                success=False,
                metadata={
                    "error": error_message
                }
            )

        
        end_time = time.perf_counter() # Capture execution timing
        execution_time_ms = (end_time - start_time) * 1000

        # Inject execution timing into metadata
        result.metadata["execution_time_ms"] = round(execution_time_ms, 2)
        
        # Session injection remains centralized in RotomCore.
        # Keep session visible internally.
        result.session_id = session_id

        # Phase 7: Continuation step. If a decider is injected, call it with the result.
        # We do not use the return value to change the response in Phase 7—we still return result.
        if self.continuation_decider is not None:
            self.continuation_decider.continue_(user_input, capability_name, result)

        # Phase 5: Save this turn to memory so the *next* request in this
        # session can see "user said X, we ran Y, result Z." We append two
        # entries: one for the user message, one for what we did.
        if session_id:
            self.session_memory.append(
                session_id,
                {"role": "user", "content": user_input},
            )
            output_summary = (result.output or "")[:OUTPUT_SUMMARY_MAX_LEN]
            self.session_memory.append(
                session_id,
                {
                    "role": "assistant",
                    "capability": capability_name,
                    "success": result.success,
                    "output_summary": output_summary,
                },
            )
        
        logger.debug(f"Execution finished: {capability_name}")

        return result
    


    def _log_failure(self, capability_name: str, error_message: str):
        """
        Centralized failure logging for capability execution.
        """
        logger.error(
            f"Capability execution failed: {capability_name}",
            extra={
                "error": error_message,
                "capability": capability_name
            }
        )


    def _validate_intent_data(self, intent_data) -> bool:
        """
        Ensures the IntentClassifier returned a structurally valid invocation contract.

        This protects RotomCore from contract drift or misbehaving classifier implementations.
        """
        return (
            isinstance(intent_data, dict)
            and "capability" in intent_data
            and isinstance(intent_data["capability"], str)
            and intent_data["capability"].strip() != ""
            and "arguments" in intent_data
            and isinstance(intent_data["arguments"], dict)
        )

    def _validate_arguments(
        self, capability_name: str, capability, arguments: dict
    ) -> None:
        """
        Validates arguments against the capability's argument_schema before execution.

        Phase 4: Argument validation layer.
        - Every key in argument_schema must be present in arguments (required keys).
        - Arguments may only contain keys defined in argument_schema (no extra keys).

        Raises ValueError with a clear message if validation fails.
        """
        schema = getattr(capability, "argument_schema", None) or {}
        if not isinstance(schema, dict):
            raise ValueError(
                f"Capability '{capability_name}' has invalid argument_schema"
            )

        # Required: all schema keys must be present
        missing = [k for k in schema if k not in arguments]
        if missing:
            raise ValueError(
                f"Capability '{capability_name}' missing required arguments: {missing}"
            )

        # Strict: no extra keys beyond schema
        extra = [k for k in arguments if k not in schema]
        if extra:
            raise ValueError(
                f"Capability '{capability_name}' received unknown arguments: {extra}"
            )