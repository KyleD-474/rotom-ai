"""
base_intent_classifier.py

Defines the interface for intent classifiers.

An IntentClassifier's job is simple:
Given a user_input string,
return the name of the capability that should handle it.

This keeps routing logic separate from RotomCore.
"""

from abc import ABC, abstractmethod


class BaseIntentClassifier(ABC):
    """
    All intent classifiers must implement classify().
    """

    @abstractmethod
    def classify(self, user_input: str) -> str:
        """
        Determine which capability should handle the input.

        Returns:
            str: capability name
        """
        pass