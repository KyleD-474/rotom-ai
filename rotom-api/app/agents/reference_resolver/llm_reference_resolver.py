"""
llm_reference_resolver.py — Phase 6: LLM-backed reference resolver

Given (user_input, context), this implementation asks the LLM to rewrite the
user message so that references like "that", "it", "again" are resolved from
the recent context only when they clearly refer to the prior conversation—not
when they refer to something in the same message. It uses the same BaseLLMClient
abstraction as the intent classifier so we can test with a mock and swap providers.
"""

from app.agents.reference_resolver.base_reference_resolver import BaseReferenceResolver
from app.agents.llm.base_llm_client import BaseLLMClient
from app.core.logger import get_logger

logger = get_logger(__name__, layer="agent", component="reference_resolver")


class LLMReferenceResolver(BaseReferenceResolver):
    """
    Calls the LLM with a short prompt: context + user message, instruct it to
    output only the rewritten message (no explanation, no JSON). Strip and return.
    """

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    def resolve(self, user_input: str, context: str) -> str:
        """
        If context is empty or whitespace, return user_input unchanged (defensive—
        RotomCore normally only calls us when context exists, but this avoids LLM
        calls with empty context). Otherwise build a prompt, call the LLM, and
        return the stripped reply (the rewritten message only, no JSON or explanation).
        """
        if not context or not context.strip():
            return user_input.strip() if user_input else user_input

        prompt = self._build_prompt(user_input, context.strip())
        raw = self.llm_client.generate(prompt)
        return raw.strip() if raw else user_input

    def _build_prompt(self, user_input: str, context: str) -> str:
        """
        Build a prompt that asks the LLM to resolve references only when they
        clearly refer to the prior conversation; leave same-message referents unchanged.
        Output only the resolved message as the user would have typed it.
        """
        return f"""You are a reference resolver. Your job is to rewrite the user's message ONLY when "that", "it", "again", etc. clearly refer to something in the RECENT CONTEXT (prior conversation). Do NOT replace references when they clearly refer to something IN THE USER'S OWN MESSAGE (e.g. a quoted phrase, "the above", or the result of the first part of their sentence).

RULES:
- Resolve from context only when the user clearly refers to the prior conversation (e.g. "do that again", "summarize the last message").
- When the user's message is self-contained and "that"/"it" refer to something in the same message (e.g. quoted text, or "repeat that twice" where "that" is the phrase they just gave), output the message UNCHANGED.
- When in doubt, do NOT substitute from context—leave the message as-is so you do not overwrite same-message referents.
- Output ONLY the resolved message as the user would have typed it. No JSON, no explanation.

Example 1 (resolve from context): User says "do that again"; context shows prior user message "echo hello". Output: echo hello

Example 2 (do not resolve from context): User says "Count the words in 'The cow jumped over the moon' and repeat that twice." Here "that" refers to the phrase or the count in the same message. Output the message unchanged.

Recent context:
{context}

User message:
{user_input}

Resolved message (exactly what the user would have typed, nothing else):"""
