"""
Rule-based intent classifier: no LLM, just keyword matching. Useful for
tests and offline dev. Implements the same classify(user_input, context=...)
signature as LLMIntentClassifier; we simply ignore context so the interface
stays consistent.
"""
from app.agents.intent.base_intent_classifier import BaseIntentClassifier
from app.core.logger import get_logger

logger = get_logger(__name__, layer="agent", component="intent_classifier")


class RuleBasedIntentClassifier(BaseIntentClassifier):
    """
    Picks capability by looking for keywords in user_input (e.g. "echo" → echo,
    "summarize" → summarizer_stub). Does not use context—each message is
    classified in isolation.
    """

    def classify(self, user_input: str, context: str | None = None) -> dict:
        # context is part of the interface but we don't use it here.
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