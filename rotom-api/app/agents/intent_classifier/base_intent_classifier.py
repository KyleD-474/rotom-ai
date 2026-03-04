"""
base_intent_classifier.py — Interface for intent classifiers

An intent classifier answers: "Given what the user said, which capability
should run and with what arguments?" It returns a structured contract:

  { "capability": "<name>", "arguments": { ... } }

RotomCore uses this to pick a capability from the registry and call
execute(arguments). Keeping this in a separate abstraction lets us swap
implementations (e.g. rule-based vs LLM-based) without changing RotomCore.

Phase 5: We added an optional `context` parameter. When the same session
sends a second message, the classifier can receive a short summary of the
previous turn (e.g. "User said X, we ran echo, result was Y") so it can
handle follow-ups like "echo that again" or "run it again."
"""

from abc import ABC, abstractmethod


class BaseIntentClassifier(ABC):
    """
    All intent classifiers must implement classify(user_input, context=None).
    The classifier does not know where context comes from—RotomCore passes it.
    """

    @abstractmethod
    def classify(self, user_input: str, context: str | None = None) -> dict:
        """
        Decide which capability handles this input and with what arguments.

        context: Optional. When present, it's a string summarizing recent
        conversation (e.g. previous user message and what the assistant did).
        Used so the LLM can interpret "that" or "it" in the current message.
        """
        pass