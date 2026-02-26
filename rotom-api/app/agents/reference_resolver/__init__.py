"""
reference_resolver — Phase 6: Resolve-then-classify preprocessing

This package provides the abstraction and implementation for rewriting user
messages so that references ("that", "it", "again") are resolved from session
context before intent classification. The service layer imports from here to
inject into RotomCore.
"""

from app.agents.reference_resolver.base import BaseReferenceResolver
from app.agents.reference_resolver.llm_resolver import LLMReferenceResolver

__all__ = ["BaseReferenceResolver", "LLMReferenceResolver"]
