
"""
rule_based_classifier.py

Simple rule-based intent classifier.

This is intentionally basic:
It checks for keywords and returns capability names.

Later we can replace this with an LLM-backed classifier
without changing RotomCore.
"""

from app.agents.intent.base_intent_classifier import BaseIntentClassifier
from app.core.logger import get_logger

logger = get_logger(__name__, layer="agent", component="intent_classifier")

class RuleBasedIntentClassifier(BaseIntentClassifier):
    """
    Naive keyword-based classifier.
    """

    def classify(self, user_input: str) -> str:
        """
        Determine capability based on keyword presence.
        """

        text = user_input.lower()

        if "echo" in text:
            capability = "echo"

        if "summarize" in text:
            capability = "summarizer_stub"
        else:
            capability = "echo"  # default fallback
        
        # Only log the final routing decision
        logger.info(f"Routing to capability: {capability}")

        return capability