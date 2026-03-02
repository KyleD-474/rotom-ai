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
ContinuationResult (done, next_capability, etc.). Phase 8 uses that to loop.

Phase 8: We loop until the decider returns done=True or we hit
MAX_CONTINUATION_ITERATIONS. When done=False with next_capability/arguments,
we run that capability and repeat. Optional final_output replaces the last
result's output when set.
"""
import json
import time
from app.core.logger import get_logger
from app.models.capability_result import CapabilityResult

logger = get_logger(__name__, layer="agent", component="rotom_core")

# When we store the capability result in memory we truncate output to avoid huge prompts.
OUTPUT_SUMMARY_MAX_LEN = 200

# Phase 8: Max capability runs per request; prevents unbounded loops when continuation says "not done".
MAX_CONTINUATION_ITERATIONS = 5


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
        logger.debug(f"Beginning handle() method.\nInput received: {user_input}")

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
            logger.error(f"IntentClassifier returned invalid invocation structure.\nIntent data:\n{json.dumps(intent_data, indent=4)}")
            raise ValueError("IntentClassifier returned invalid invocation structure")
            
        # Convert structured intent into internal invocation model.
        capability_name = intent_data["capability"]
        arguments = intent_data["arguments"]

        # Phase 8: Loop: run capability → continuation → append memory; repeat until done or max iterations.
        result = None
        iteration = 0
        while iteration < MAX_CONTINUATION_ITERATIONS:
            iteration += 1
            
            logger.debug(
                f"Continuation iteration start:\n"+
                f"iteration: {iteration}\n"+
                f"capability: {capability_name}\n"+
                f"arguments: \n{json.dumps(arguments, indent=4)}\n"
            )

            capability = self.registry.get(capability_name)
            if not capability:
                logger.error(f"Capability not found.\nCapability name: {capability_name}")
                raise ValueError(f"Capability '{capability_name}' not found")

            self._validate_arguments(capability_name, capability, arguments)
            logger.debug(f"Arguments validated successfully.\nCapability name: {capability_name}\nArguments:\n{json.dumps(arguments, indent=4)}")

            start_time = time.perf_counter()
            try:
                result = capability.execute(arguments)
            except Exception as e:
                logger.error(f"Capability execution failed.\nCapability name: {capability_name}\nError: {str(e)}")
                result = CapabilityResult(
                    capability=capability_name,
                    output="",
                    success=False,
                    metadata={"error": str(e)},
                )
            end_time = time.perf_counter()
            result.metadata["execution_time_ms"] = round((end_time - start_time) * 1000, 2)
            result.session_id = session_id
            # Phase 8: Observability — which iteration this step was, and total so far (updated each iteration).
            result.metadata["continuation_iteration"] = iteration
            result.metadata["continuation_total_iterations"] = iteration

            # Phase 7/8: Continuation decider; when present we use its return to loop or apply final_output.
            cont = None
            if self.continuation_decider is not None:
                cont = self.continuation_decider.continue_(user_input, capability_name, result)
                logger.debug(
                    f"Continuation decision from llm continuation decider:\n"+
                    f"iteration: {iteration}\n"+
                    f"done: {bool(cont.done)}\n"+
                    f"next_capability: {getattr(cont, "next_capability", None)}\n"+
                    f"has_final_output: {bool(getattr(cont, "final_output", None) and (cont.final_output or "").strip() != "")}\n",
                )
            # Phase 5: Append this step to memory. First iteration: user message + assistant; later: assistant only.
            if session_id:
                if iteration == 1:
                    self.session_memory.append(
                        session_id, {"role": "user", "content": user_input}
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

            # No decider => single-step (Phase 7 default); we're done.
            if cont is None:
                return result
            # Decider says done: optionally surface final_output, then return.
            if cont.done:
                if cont.final_output is not None and cont.final_output.strip() != "":
                    result = CapabilityResult(
                        capability=result.capability,
                        output=cont.final_output,
                        success=result.success,
                        metadata={**result.metadata, "synthesized": True},
                        session_id=result.session_id,
                    )
                return result
            # Hit max iterations: return last result.
            if iteration >= MAX_CONTINUATION_ITERATIONS:
                logger.warning(
                    "continuation_max_iterations_reached",
                    extra={
                        "event": "continuation_max_iterations_reached",
                        "iteration": iteration,
                        "max_iterations": MAX_CONTINUATION_ITERATIONS,
                        "capability": result.capability,
                    },
                )
                return result
            # Continuation said not done but next step invalid: stop and return last result.
            if not cont.next_capability or not isinstance(cont.arguments, dict):
                logger.warning(
                    "Continuation returned done=False but missing next_capability or arguments; stopping.",
                    extra={
                        "event": "continuation_invalid_next",
                        "iteration": iteration,
                        "capability": result.capability,
                    },
                )
                return result
            next_cap = self.registry.get(cont.next_capability)
            if not next_cap:
                logger.warning(
                    "Continuation next_capability not in registry; stopping.",
                    extra={
                        "event": "continuation_unknown_capability",
                        "iteration": iteration,
                        "next_capability": cont.next_capability,
                        "capability": result.capability,
                    },
                )
                return result
            try:
                self._validate_arguments(
                    cont.next_capability, next_cap, cont.arguments
                )
            except ValueError:
                logger.warning(
                    "Continuation arguments invalid for next capability; stopping.",
                    extra={
                        "event": "continuation_invalid_arguments",
                        "iteration": iteration,
                        "next_capability": cont.next_capability,
                        "capability": result.capability,
                    },
                )
                return result
            capability_name = cont.next_capability
            arguments = cont.arguments

        return result


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