# Rotom AI Orchestration System
## Architecture Constitution (v1.6)

This document defines the structural, behavioral, and dependency rules of the Rotom system.
All development must adhere to these constraints unless this document is explicitly revised.

Architecture leads code.

---

# 1. System Identity

Rotom is a **bounded AI orchestration kernel**: the control layer for a persistent, personal AI system (e.g. a "Jarvis"-style assistant on your Linux PC) with access to files, the internet, and LLM when needed — capable of planning, tool execution, memory use, and hybrid reasoning, **without losing control**.

Rotom is responsible for:

- Interpreting user input
- Classifying intent (LLM-based as of v1.1)
- Routing to capabilities
- Managing execution lifecycle
- Handling structured failure
- Managing session state
- Returning structured results
- Enforcing iteration limits and execution boundaries (as the roadmap advances)

Rotom is NOT:

- A monolithic AI agent
- A thin LLM wrapper or chatbot
- A persistence-first system
- A tightly coupled framework
- An uncontrolled agent

Rotom is an orchestration core. The LLM cannot access systems unless a capability exists; capabilities are the explicit gatekeeper.

For intended use cases (trip planning, research, developer automation, browser automation, workflows, etc.), see **USECASES.md**.

LLM-based intent classification was introduced in v1.1.
Structured invocation (capability + arguments) was introduced in v1.2.
Metadata-driven prompt construction was introduced in v1.3.
Argument validation before execution was introduced in v1.4. Session memory (context injection and turn storage) was introduced in v1.5. Reference resolution (resolve-then-classify) was introduced in v1.6. Tool result injection (continuation contract) was introduced in Phase 7. A bounded iterative reasoning loop (multi-step within one request) was introduced in Phase 8.

Execution is now **single-request, bounded multi-step** and deterministic; bounded loops and iteration limits are enforced inside RotomCore.

Orchestration-level AI determines routing decisions.
Execution remains bounded and controlled by RotomCore.

---

# 2. Layered Architecture

Strict downward dependency flow:

API → Service → Agents → Capabilities

No upward or lateral dependency violations allowed.

---

## 2.1 API Layer (`app/api`)

Responsibilities:
- FastAPI route definitions
- Request validation via API schemas
- Response serialization
- Logging entry/exit

Must NOT:
- Contain orchestration logic
- Contain capability logic
- Import core domain models

API schemas are strictly boundary objects.

---

## 2.2 Service Layer (`app/services`)

Responsibilities:
- Construct RotomCore
- Own dependency wiring
- Serve as application boundary

Constructs:
- SessionStore implementation
- CapabilityRegistry
- IntentClassifier implementation (LLM-backed)
- LLMClient implementation (OpenAIClient currently)
- ReferenceResolver implementation (LLMReferenceResolver, Phase 6)
- RotomCore

Must NOT:
- Contain routing logic
- Contain capability logic
- Contain business rules

---

## 2.3 Agent Layer (`app/agents`)

Contains:
- RotomCore
- Intent classification abstractions (base_intent_classifier.py)
- LLM client abstractions (base_llm_client.py)
- Reference resolver abstractions (base_reference_resolver.py, Phase 6)
- Continuation decider abstractions (base_continuation_decider.py, Phase 7)

Responsibilities of RotomCore:
- Orchestration
- Session lifecycle ownership
- Structured failure handling
- Execution timing injection
- Capability resolution
- Defensive invocation validation

RotomCore must:
- Construct nothing
- Receive all dependencies via injection
- Remain framework-agnostic

---

## 2.4 Capability Layer (`app/capabilities`)

Capabilities are pure execution units.

Rules:
- Stateless
- No session awareness
- No orchestration awareness
- No persistence awareness
- Dependencies must be injected
- Execution must remain bounded and atomic

Capabilities define declarative metadata:

- name
- description
- argument_schema (dict[str, str])

Capabilities MAY internally use injected services (including an LLM client) provided:

- They do not construct dependencies
- They do not orchestrate other capabilities
- They do not access session state
- They remain bounded from RotomCore’s perspective

Failure policy is NOT owned by capabilities.

---

## 2.5 Core Utilities (`app/core`)

Contains:
- Logging configuration
- Context utilities
- Session store implementations
- Session memory interface (base_session_memory.py: BaseSessionMemory)

Must NOT:
- Contain orchestration logic
- Contain capability logic

---

## 2.6 Models (`app/models`)

Internal domain models only.

Examples:
- CapabilityResult
- CapabilityInvocation

Must NOT:
- Be API schemas
- Be tied to FastAPI

CapabilityInvocation serves as the internal transport object between
intent classification and capability execution.

---

## 2.7 Schemas (`app/schemas`)

Strictly API boundary models.

Rules:
- Used only in routes
- Must not enter core logic
- Must not be imported into RotomCore

---

# 3. Dependency Ownership

Construction Flow:

FastAPI → AgentService → RotomCore

AgentService constructs:
- SessionStore implementation
- CapabilityRegistry
- IntentClassifier implementation (LLM-backed)
- LLMClient implementation
- ReferenceResolver implementation (Phase 6)
- RotomCore

RotomCore constructs nothing.

All dependencies are injected.

---

# 4. Session Architecture

Session lifecycle is owned by RotomCore.

Capabilities:
- Must not access session state.
- Must not receive session state.

SessionStore:
- Is an abstraction boundary.
- Currently implemented as InMemorySessionStore.
- Future persistence must implement the same interface.

Session persistence must never leak into capabilities.

---

# 5. Execution Contract (v1.7)

Invocation contract:

    {
      "capability": "<string>",
      "arguments": { ... }
    }

Execution flow (single request, possibly multi-step, always bounded):

1. Receive input.
2. If `session_id` is present, ensure the session exists via `SessionStore`.
3. Load recent context from `SessionMemory` for this session (Phase 5).
4. (Phase 6, when session and context and resolver) Optionally rewrite user message via reference resolver; classifier then receives the **rewritten** message only.
5. LLM classifies intent via metadata-driven structured JSON → `{capability, arguments}` for the **first** step.
6. Enter a bounded loop inside RotomCore (Phase 8):
   - 6.1 Resolve capability against registry.
   - 6.2 Construct `CapabilityInvocation` and validate arguments against `argument_schema` (Phase 4).
   - 6.3 Execute capability with structured arguments; catch unhandled exceptions and wrap in `CapabilityResult`.
   - 6.4 Inject execution timing into metadata and attach `session_id`.
   - 6.5 If a continuation decider is configured (Phase 7), call `continue_(user_input, capability_name, result)` and receive `ContinuationResult(done, next_capability, arguments, final_output)`.
   - 6.6 Append this step to `SessionMemory` (user turn once on first iteration, assistant summary per iteration).
   - 6.7 If there is **no** decider, or `done=True`, or max-iteration guard reached, or the next step is invalid (missing/unknown `next_capability` or invalid `arguments`) → exit loop.
   - 6.8 Otherwise, set `capability = next_capability` and `arguments = arguments` from `ContinuationResult` and repeat from 6.1.
7. If the final `ContinuationResult` provides a non-empty `final_output`, surface that as the returned `CapabilityResult.output` and mark metadata with `synthesized=True`; otherwise, return the last capability's own output.

Execution remains synchronous and deterministic; multi-step behavior is explicit, structured, and guarded by a max-iteration limit.

---

# 6. Logging Policy

- Debug logging allowed in all layers.
- Structured error logging centralized in RotomCore.
- Capabilities do not enforce failure policy.

---

# 7. Async Policy

System is currently synchronous.

Async may only be introduced when:
- Multi-step LLM reasoning loops are added
- External APIs require concurrency
- Persistence requires it

Async must be deliberate and documented.

---

# 8. Persistence Policy

Persistence does not currently exist.

When introduced:
- Must be abstracted behind an interface
- Must be injected
- Must not leak into capabilities
- Must not alter execution contract

---

# 9. LLM Integration Policy (v1.3)

LLM integration must:

- Be abstracted behind an interface (BaseLLMClient)
- Be injected via AgentService
- Not be hardcoded
- Preserve testability

Current state:

- LLM is used for intent classification, reference resolution (Phase 6), and structured continuation decisions (Phase 7).
- Prompt construction is metadata-driven via CapabilityRegistry.
- Structured JSON responses are enforced.
- Defensive validation occurs prior to execution.
- Capability-level LLM usage is permitted if injected and bounded.
- A bounded iterative reasoning loop exists inside RotomCore (Phase 8) that consumes the continuation contract and enforces a max-iteration guard.
- No autonomous, unbounded execution exists; all loops are capped and driven by structured continuation.

LLM usage remains strictly bounded by RotomCore orchestration.

When tool result injection is introduced (Phase 7), the LLM will receive capability results only for **structured reasoning continuation** (e.g. next-step decision, synthesis). The continuation response will be **structured** (e.g. done, next_capability, arguments), not free-form. Default response to the user remains the capability output unless the continuation contract explicitly provides a synthesized output.

---

# 10. Future Expansion Vectors

Implemented:
- Structured tool call arguments (v1.2)
- Metadata-driven orchestration (v1.3)
- Argument validation layer (v1.4)
- Session memory utilization (v1.5): context for intent classification, turn summaries per session
- Reference resolution (v1.6): optional rewrite of user message from session context before intent classification (resolve-then-classify)
- Tool result injection (Phase 7): continuation decider receives `CapabilityResult` and returns structured `ContinuationResult(done, next_capability, arguments, final_output)`; default decider is a no-op that always says `done=True`.
- Iterative reasoning loop (Phase 8): bounded loop inside RotomCore that consumes the Phase 7 continuation contract, supports multi-step capability chaining within a single request, and enforces a max-iteration guard.

Planned:

- **Response shaping:** User-facing “human-readable” or conversational response is **optional and capability-driven** (e.g. summarizer capability when user asks for summary), not a global LLM pass over every result.
- Persistent session memory
- Multi-step capability chaining
- Tool + LLM hybrid execution
- Potential productization

Not currently planned:

- Distributed execution
- Horizontal scaling
- Multi-user authentication

---

# 11. Architectural Invariants (Non-Negotiable)

- Capabilities remain pure.
- RotomCore constructs nothing.
- Dependency flow only moves downward.
- API schemas do not enter core logic.
- Session logic remains centralized.
- All integrations are abstracted.
- No premature complexity.
- **No automatic LLM rewriting of every capability output** — Default is to return capability output as the response; the LLM does not automatically rewrite or polish every result for tone or readability. When result injection is used (e.g. Phase 7), the LLM returns a structured continuation, not free-form user-facing text unless explicitly part of the continuation contract.

---

# 12. Architectural Revision Protocol

If a change requires breaking an invariant:

1. Update ARCHITECTURE.md first.
2. Document the reason.
3. Then modify implementation.

Architecture leads code.

---

Version Updated: v1.6
Document Updated: 2026-02-25
