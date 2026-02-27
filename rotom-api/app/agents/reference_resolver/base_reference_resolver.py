"""
base_reference_resolver.py — Phase 6: Abstract interface for reference resolution

A reference resolver has one job: given the user's raw message and recent
conversation context, return a single rewritten message where pronouns and
references ("that", "it", "again", etc.) are resolved from context. It does
not know about capabilities, session storage, or intent—only "text in,
rewritten text out." RotomCore calls this optionally before intent classification
so the classifier sees an explicit message (e.g. "echo hello") instead of
"do that again," keeping the classifier simple and scalable.
"""

from abc import ABC, abstractmethod


class BaseReferenceResolver(ABC):
    """
    Implementations take (user_input, context) and return a rewritten string
    with references resolved. No capability or session logic—pure preprocessing.
    """

    @abstractmethod
    def resolve(self, user_input: str, context: str) -> str:
        """
        Rewrite the user's message so that references to prior context are
        made explicit.

        Args:
            user_input: The raw message from the user (e.g. "do that again").
            context: A string summarizing recent conversation for this session.

        Returns:
            A single string: the rewritten message (e.g. "echo hello") with
            references resolved. No JSON, no explanation—just the new message.
        """
        pass
