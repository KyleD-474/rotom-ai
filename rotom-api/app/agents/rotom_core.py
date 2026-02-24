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

        # Idenitfy intended capbility based off of user input
        capability_name = self.intent_classifier.classify(user_input)

        logger.debug(f"Routing decision: {capability_name}")

        # Find capability to execute from capbility_registry
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

        logger.debug(f"Execution started: {capability_name}")

        # Measure execution time
        start_time = time.perf_counter()

        # Execute the capability with user_input
        try:
            result = capability.execute(user_input)
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

        # Capture execution timing
        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000

        # Inject execution timing into metadata
        result.metadata["execution_time_ms"] = round(execution_time_ms, 2)
        
        # Keep session visible internally & inject it into result metadata
        result.session_id = session_id
        if session_id:
            result.metadata["session_id"] = session_id
        
        logger.debug(f"Execution finished: {capability_name}")

        return result
    


    def _log_failure(self, capability_name: str, error_message: str):
        """
        Centralized failure logging for capability execution.

        Keeps error logging consistent and avoids clutter
        inside the main execution flow.
        """
        logger.error(
            f"Capability execution failed: {capability_name}",
            extra={
                "error": error_message,
                "capability": capability_name
            }
        )