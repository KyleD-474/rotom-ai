"""
continuation — Phase 7: Tool result injection (structured reasoning continuation)

This package provides the abstraction and implementations for the "continuation"
step: after a capability runs, we can pass its result to a decider that returns
a structured decision (done? next step? optional final_output). The service
layer imports from here to inject into RotomCore.

Why __init__.py?
----------------
In Python, a directory is only treated as a "package" (importable with
`from app.agents.continuation import NoOpContinuationDecider`) if it contains
an __init__.py file. This file can be empty or can run code when the package
is imported. We use it to re-export the public types (BaseContinuationDecider,
NoOpContinuationDecider, LLMContinuationDecider) so that other modules can
write:

  from app.agents.continuation import NoOpContinuationDecider

instead of:

  from app.agents.continuation.no_op_decider import NoOpContinuationDecider

That keeps imports shorter and hides the internal file layout. Without
__init__.py, the directory would not be a package and we could not
`import app.agents.continuation` at all.
"""

from app.agents.continuation.base_continuation_decider import BaseContinuationDecider
from app.agents.continuation.no_op_decider import NoOpContinuationDecider
from app.agents.continuation.llm_decider import LLMContinuationDecider

__all__ = ["BaseContinuationDecider", "NoOpContinuationDecider", "LLMContinuationDecider"]
