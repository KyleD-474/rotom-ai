from app.agents.intent.base_intent_classifier import BaseIntentClassifier
from app.core.logger import get_logger

logger = get_logger(__name__, layer="agent", component="intent_classifier")


class RuleBasedIntentClassifier(BaseIntentClassifier):
    """
    Naive keyword-based classifier.

    Useful for:
    - Local testing
    - Deterministic behavior
    - Offline development
    """

    def classify(self, user_input: str) -> dict:
        """
        Determine capability and construct structured invocation.
        """

        text = user_input.lower()

        if "summarize" in text:
            capability = "summarizer_stub"
            arguments = {"text": user_input}

        elif "echo" in text:
            capability = "echo"
            arguments = {"message": user_input}

        else:
            capability = "echo"
            arguments = {"message": user_input}

        logger.info(f"Routing to capability: {capability}")

        return {
            "capability": capability,
            "arguments": arguments
        }