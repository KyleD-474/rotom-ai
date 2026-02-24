
# Rotom AI Orchestration System
## Architecture Constitution (v1.1)

This document defines the structural, behavioral, and dependency rules of the Rotom system.
All development must adhere to these constraints unless this document is explicitly revised.

Architecture leads code.

---

# 1. System Identity

Rotom is an AI orchestration engine responsible for:

- Interpreting user input
- Classifying intent (LLM-based as of v1.1)
- Routing to capabilities
- Managing execution lifecycle
- Handling structured failure
- Managing session state
- Returning structured results

Rotom is NOT:

- A monolithic AI agent
- A thin LLM wrapper
- A persistence-first system
- A tightly coupled framework

Rotom is an orchestration core.

LLM-based intent classification was introduced in v1.1.
Execution remains single-step and deterministic.

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
- IntentClassifier implementation (LLM-backed as of v1.1)
- LLMClient implementation (OpenAIClient currently)
- RotomCore

Must NOT:
- Contain routing logic
- Contain capability logic
- Contain business rules

---

## 2.3 Agent Layer (`app/agents`)

Contains:
- RotomCore
- Intent classification abstractions
- LLM client abstractions

Responsibilities of RotomCore:
- Orchestration
- Session lifecycle ownership
- Structured failure handling
- Execution timing injection
- Capability resolution

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
- No direct LLM awareness

Allowed:
- Debug logging
- Deterministic execution

Failure policy is NOT owned by capabilities.

---

## 2.5 Core Utilities (`app/core`)

Contains:
- Logging configuration
- Context utilities
- Session store implementations

Must NOT:
- Contain orchestration logic
- Contain capability logic

---

## 2.6 Models (`app/models`)

Internal domain models only.
Example:
- CapabilityResult

Must NOT:
- Be API schemas
- Be tied to FastAPI

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
- IntentClassifier implementation (LLM-backed as of v1.1)
- LLMClient implementation
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

# 5. Execution Contract (Updated v1.1)

Execution flow:

1. Receive input
2. LLM classifies intent via structured JSON
3. Validate capability against registry
4. Resolve capability
5. Execute capability
6. Catch unhandled exceptions
7. Produce CapabilityResult
8. Inject execution timing
9. Return structured response

CapabilityResult is the internal execution contract.

---

# 6. Logging Policy

- Debug logging allowed in all layers.
- Structured error logging centralized in RotomCore.
- Capabilities do not enforce failure policy.

No changes introduced in v1.1.

---

# 7. Async Policy

System is currently synchronous.

Async may only be introduced when:
- Multi-step LLM reasoning loops are added
- External APIs require concurrency
- Persistence requires it

v1.1 introduced LLM integration but did NOT introduce async.

Async must be deliberate and documented.

---

# 8. Persistence Policy

Persistence does not currently exist.

When introduced:
- Must be abstracted behind an interface
- Must be injected
- Must not leak into capabilities
- Must not alter execution contract

v1.1 does not introduce persistence changes.

---

# 9. LLM Integration Policy (Implemented v1.1)

LLM integration must:

- Be abstracted behind an interface (BaseLLMClient)
- Be injected via AgentService
- Not be hardcoded
- Preserve testability

Current state (v1.1):

- LLM is used for intent classification only.
- Structured JSON responses are enforced.
- Capability validation occurs after LLM output.
- No iterative reasoning loop yet.
- No multi-step planning yet.
- No tool argument injection yet.

RotomCore may orchestrate LLM usage but must not depend on a concrete implementation.

---

# 10. Future Expansion Vectors

Planned:

- Structured tool call arguments
- Iterative agent reasoning loop
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

---

# 12. Architectural Revision Protocol

If a change requires breaking an invariant:

1. Update ARCHITECTURE.md first.
2. Document the reason.
3. Then modify implementation.

Architecture leads code.

---

Document Updated: 2026-02-24
