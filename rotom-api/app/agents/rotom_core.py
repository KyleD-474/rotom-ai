"""
rotom_core.py

RotomCore is the executive orchestrator.

Responsibilities:
- Interpret user input
- Determine appropriate capability
- Execute capability
- Return result

Future:
- IntentClassifier abstraction
- LLM integration
- Memory/session integration
"""
import time
from app.core.logger import get_logger
from app.models.capability_result import CapabilityResult
from app.models.capability_invocation import CapabilityInvocation

logger = get_logger(__name__, layer="agent", component="rotom_core")


class RotomCore:
    """
    Executive agent responsible for routing.
    """
    
    def __init__(
        self,
        intent_classifier,
        registry,
        session_store
    ):
        logger.info("Rotom Core initialized")

        self.registry = registry
        self.intent_classifier = intent_classifier
        self.session_store = session_store

    def handle(self, user_input: str, session_id: str | None = None):
        """ 
        Primary execution entry point.
        """

        logger.debug("Input received")

        # Ensure session exists if provided
        session = None
        if session_id:
            session = self.session_store.get(session_id)

        # --- Phase 2: Structured Intent Classification ---
        # Classifier now returns structured data:
        # { "capability": str, "arguments": dict }
        intent_data = self.intent_classifier.classify(user_input)
       
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