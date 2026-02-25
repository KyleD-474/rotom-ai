# AI_CONTEXT.md
## Rotom AI Orchestration Engine – Project Context

---

# 1. Project Identity

**Project Name:** Rotom AI  
**Purpose:** Bounded AI orchestration kernel for a persistent, personal AI system  
**Core Principle:** Architecture leads implementation  

**Vision:** A persistent AI system (like "Jarvis" from Iron Man) that lives on your Linux PC, with appropriate access to files, the internet, and LLM when necessary — capable of planning, tool execution, memory use, and hybrid reasoning, **without losing control**.

Rotom is not a chatbot. It is not an uncontrolled agent. It is an **AI orchestration kernel**: the control layer that routes structured intent to deterministic capabilities, enforces iteration limits and execution boundaries, and keeps orchestration auditable and bounded.

For concrete use cases (trip planning, research, developer automation, browser automation, workflows, etc.), see **USECASES.md**.

Execution is currently:
- Single-step
- Synchronous
- Deterministic
- Stateless at capability layer
- Non-persistent (InMemorySessionStore only)

---

# 2. Core Architecture

## Layering (Strict Downward Dependency Flow)

API → Service → Agents → Capabilities

No upward or lateral dependency violations allowed.

---

## 2.1 API Layer (`app/api`)

- FastAPI endpoint (`/run`)
- Request validation via schemas
- No business logic
- No orchestration logic
- Schemas never enter core logic

---

## 2.2 Service Layer (`app/services`)

Responsible for dependency wiring only.

Constructs:
- SessionStore (InMemorySessionStore)
- CapabilityRegistry
- LLMClient (OpenAIClient)
- IntentClassifier (LLMIntentClassifier)
- RotomCore

RotomCore constructs nothing.

---

## 2.3 Agent Layer (`app/agents`)

Contains:
- RotomCore
- IntentClassifier abstractions
- LLM client abstractions

### RotomCore Responsibilities

- Interpret user input
- Invoke intent classifier
- Enforce invocation contract
- Resolve capability from registry
- Execute capability
- Handle structured failure
- Inject execution timing
- Manage session lifecycle
- Return CapabilityResult

RotomCore does NOT:
- Construct dependencies
- Perform validation beyond contract enforcement
- Access external APIs directly

---

## 2.4 Capability Layer (`app/capabilities`)

Capabilities are:

- Stateless
- Deterministic
- Session-unaware
- LLM-unaware
- Persistence-unaware
- Pure execution units

Each capability implements:

    execute(arguments: dict) -> CapabilityResult

Each capability defines metadata:

- name
- description
- argument_schema (dict[str, str])

---

## 2.5 Registry Pattern

CapabilityRegistry:

- Stores instantiated capability objects
- Resolves capabilities by name
- Exposes:
    - list_capabilities()
    - list_metadata()
    - get(name)

Registry decouples RotomCore from capability construction.

---

# 3. Execution Contract (v1.2)

Current invocation contract:

    {
      "capability": "<string>",
      "arguments": { ... }
    }

Execution Flow:

1. Receive input
2. LLM classifies intent
3. Validate structured invocation
4. Resolve capability
5. Execute capability with arguments
6. Catch failures
7. Produce CapabilityResult
8. Inject execution timing
9. Return structured response

No multi-step reasoning yet.

---

# 4. Technologies Used

- Python 3
- FastAPI
- Docker / Docker Compose
- OpenAI API (via OpenAIClient abstraction)
- Structured logging (custom logger)
- Manual dependency injection
- No ORM
- No database
- No async execution (yet)

---

# 5. Design Patterns Established

## 5.1 Dependency Injection

- All dependencies constructed in AgentService
- RotomCore constructs nothing
- LLM client injected via abstraction
- Registry injected
- SessionStore injected

## 5.2 Abstraction Boundaries

- BaseIntentClassifier
- BaseLLMClient
- BaseCapability

Concrete implementations are swappable.

## 5.3 Pure Capability Pattern

Capabilities:
- No orchestration logic
- No session logic
- No LLM logic
- No persistence logic

They only execute deterministic behavior.

## 5.4 Defensive Contract Enforcement

RotomCore enforces:

- Structured invocation shape
- Capability existence
- Structured failure capture

LLM output is validated before execution.

## 5.5 Metadata-Driven Prompt Generation (Phase 3)

LLMIntentClassifier builds prompt dynamically from:

- Registry metadata
- Capability descriptions
- Argument schemas

Prevents argument drift (e.g., "text" vs "message").

---

# 6. Current Progress (v1.4)

Completed:

- LLM-based intent classification
- Structured JSON invocation contract
- CapabilityInvocation model
- Defensive validation in RotomCore
- Metadata-driven prompt generation
- Elimination of argument key drift
- Session ID managed centrally
- Dockerized runtime
- Argument validation layer (Phase 4): validate arguments against capability argument_schema before execution; required keys and no extra keys enforced

System is stable and deterministic.

---

# 7. Architectural Invariants (Non-Negotiable)

- Capabilities remain pure.
- RotomCore constructs nothing.
- API schemas do not enter core logic.
- Session lifecycle owned by RotomCore.
- Downward-only dependency flow.
- LLM integration abstracted.
- No premature complexity.
- Architecture document must be updated before invariant-breaking changes.

---

# 8. Future Plans (Roadmap)

## Phase 4 – Argument Validation Layer ✓

- Validate arguments before capability execution
- Enforce required keys (all argument_schema keys must be present)
- Reject unknown arguments (no extra keys)
- Still single-step, still synchronous
- No schema libraries; validation in RotomCore

## Phase 5 – Session Memory Utilization

- Introduce contextual memory injection
- Still single-step execution
- Abstract memory behind interface
- No capability access to session state

## Phase 6 – Tool Result Injection

- Feed capability results back into LLM
- Introduce structured reasoning continuation
- Still bounded execution

## Phase 7 – Iterative Reasoning Loop

- Multi-step planning
- Max-iteration guard
- Controlled loop inside RotomCore
- No autonomous infinite loops

## Phase 8 – Persistent Storage

- Abstract persistence layer
- Inject via interface
- No leakage into capability layer

## Phase 9 – Hybrid Tool + LLM Execution

- LLM may synthesize outputs directly
- RotomCore orchestrates hybrid reasoning

---

# 9. Explicit Non-Goals (Current Scope)

- Distributed execution
- Horizontal scaling
- Multi-user authentication
- Complex schema validation
- Async concurrency
- **Agent autonomy without bounds** — Rotom is always bounded; no uncontrolled loops or unbounded autonomy

---

# 10. Operational Philosophy

Rotom evolves incrementally.

Each phase:
- Strengthens structure
- Preserves invariants
- Avoids premature complexity
- Maintains deterministic orchestration

The system is being intentionally shaped into a **bounded AI orchestration kernel**: AI flexibility with systems-level discipline, explicit boundaries, deterministic orchestration, and a replaceable LLM backend — not a chatbot, not an uncontrolled agent.

---

# END OF CONTEXT
