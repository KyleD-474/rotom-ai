"""
base_intent_classifier.py

Defines the interface for intent classifiers.

An IntentClassifier's job:

Given a user_input string,
return a structured invocation contract:

{
    "capability": "<string>",
    "arguments": { ... }
}

This keeps routing logic separate from RotomCore.
"""

from abc import ABC, abstractmethod


class BaseIntentClassifier(ABC):
    """
    All intent classifiers must implement classify().
    """

    @abstractmethod
    def classify(self, user_input: str) -> dict:
        """
        Determine which capability should handle the input.

        Returns:
            dict: {
                "capability": str,
                "arguments": dict
            }
        """
        pass