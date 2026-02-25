"""
capability_invocation.py — Internal "what to run" object

After the intent classifier returns {"capability": "echo", "arguments": {...}},
RotomCore turns that into a CapabilityInvocation and uses it to look up the
capability and call execute(arguments). This is a plain internal model—not an
API schema—so we don't leak raw LLM output or framework details into the rest
of the system.
"""


class CapabilityInvocation:
    """Holds the capability name and arguments that RotomCore will pass to capability.execute(arguments)."""

    def __init__(self, capability_name: str, arguments: dict | None = None):
        self.capability_name = capability_name
        self.arguments = arguments or {}