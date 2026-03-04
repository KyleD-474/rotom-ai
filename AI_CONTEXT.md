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
- Single-request, **bounded multi-step** (goals-based flow inside RotomCore: plan → goals → goal_checker → response_formatter)
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
- ReferenceResolver (LLMReferenceResolver, Phase 6)
- RotomCore

RotomCore constructs nothing.

---

## 2.3 Agent Layer (`app/agents`)

Contains:
- RotomCore
- IntentClassifier abstractions
- LLM client abstractions
- Reference resolver abstractions (Phase 6)

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

# 3. Execution Contract (v1.7)

Current invocation contract (per step in the loop):

    {
      "capability": "<string>",
      "arguments": { ... }
    }

Execution Flow (single request, possibly multi-step, always bounded):

1. Receive input.
2. (Phase 5) Load recent session context for this session (if any) from session memory.
3. (Phase 6, when session + context) Optionally rewrite user message via reference resolver so references (“that”, “it”, “again”) are resolved.
4. **Goals-based flow (always):** Build plan (list of goals) via plan_builder. For each goal:
   - 4.1 Build step context (original input, artifacts or previous output).
   - 4.2 LLM classifies intent for this goal → `{capability, arguments}`.
   - 4.3 Resolve capability, validate arguments, execute; inject timing and session_id.
   - 4.4 Append this step to session memory (user message once per request, assistant summary per step).
   - 4.5 Goal checker decides if goal is satisfied; if not, retry until satisfied or per-goal/max-iteration limits.
5. Response formatter produces final `CapabilityResult.output` from accumulated output_data; metadata includes `synthesized=True`.

Multi-step reasoning is **bounded and explicit**: no unbounded loops; goal_checker decides per-goal satisfaction.

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

- BaseIntentClassifier (base_intent_classifier.py)
- BaseLLMClient (base_llm_client.py)
- BaseCapability (base_capability.py)
- BaseSessionMemory (base_session_memory.py, Phase 5)
- BaseReferenceResolver (base_reference_resolver.py, Phase 6)
- Plan builder, goal checker, and response formatter (goals-based path)

Base interfaces live in descriptively named modules (base_*.py). Concrete implementations are swappable.

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

## 5.6 Response Shaping

User-facing response shaping (e.g. summarization, conversational formatting) is **optional and capability-driven**, not a global post-step. A summarizer capability is invoked when the user asks for a summary; echo returns literal output. We do not mandate that every capability result be passed through the LLM for “human-readable” polish—that would reduce control and determinism.

---

# 6. Current Progress (v1.6)

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
- Session memory utilization (Phase 5): contextual memory injection, abstract BaseSessionMemory interface, intent classifier receives optional context, RotomCore reads context and appends turn summaries; capabilities do not access session or memory
- Reference resolution (Phase 6): optional preprocessing via BaseReferenceResolver / LLMReferenceResolver; when session context exists, user message is rewritten to resolve references (“that”, “it”, “again”) before intent classification; classifier runs on rewritten message only; memory stores original user message
- Goals-based multi-step (Phase 8.5): plan builder, per-goal intent classifier and goal checker, response formatter; single path with no plan-free continuation decider; bounded by max-iteration and per-goal limits.

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

## Phase 5 – Session Memory Utilization ✓

- Introduce contextual memory injection
- Still single-step execution
- Abstract memory behind interface
- No capability access to session state

## Phase 6 – Reference Resolution (Resolve-Then-Classify) ✓

- Optional preprocessing step: given session context + raw user message, LLM produces a single **rewritten** message where references (“that”, “it”, “again”, etc.) are resolved from context.
- Intent classification then runs on the rewritten message only; no need to hardcode referring phrases in the classifier.
- Keeps classifier simple and scales to more tools and more complex context.
- Still single-step execution; only the input to the classifier changes.
- **Implemented:** Reference resolver in agent layer; RotomCore orchestrates resolve-then-classify when session + context + resolver present; original user message stored in memory.

## Phase 7 – Tool Result Injection (Removed)

- The continuation decider and plan-free reactive loop (Phase 7/8) have been **removed** in favor of the goals-based flow. See Phase 8.5 below. Historical docs: rotom-api/docs/PHASE7_FLOW.md, PHASE8_FLOW.md.

## Phase 8 – Iterative Reasoning Loop (Removed)

- The plan-free continuation loop has been **removed**. Multi-step behavior is now entirely goals-based (Phase 8.5).

## Phase 8.5 – Goals-Based Multi-Step ✓

- **Plan builder:** One LLM call turns `user_input` into a structured list of **goals** (user-level steps).
- **Per goal:** Intent classifier (goal + context) → capability + args; run capability; append to **output_data**; **goal checker** (goal + run + result) → satisfied? Repeat until satisfied, then next goal.
- **Response formatter:** When all goals are satisfied, one LLM call turns `user_input` + `output_data` + goals into the final user-facing response.
- This is the **single path**; goal_checker decides per-goal satisfaction. See [rotom-api/docs/PHASE8_5_PLAN.md](rotom-api/docs/PHASE8_5_PLAN.md).

## Phase 9 – Persistent Storage

- Abstract persistence layer
- Inject via interface
- No leakage into capability layer

## Phase 10 – Hybrid Tool + LLM Execution

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
- **Automatic LLM rewriting of every capability output** — The LLM does not automatically rewrite or “polish” every capability result for tone or readability; default is to return capability output unchanged. Response shaping (e.g. summarization, formatting) is optional and capability-driven when needed.

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
