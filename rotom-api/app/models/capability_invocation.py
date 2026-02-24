class CapabilityInvocation:
    """
    Internal execution contract between intent classification
    and capability execution.

    This model is framework-agnostic and does not expose
    raw LLM payloads to the rest of the system.
    """

    def __init__(self, capability_name: str, arguments: dict | None = None):
        self.capability_name = capability_name
        self.arguments = arguments or {}