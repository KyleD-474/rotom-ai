
# Rotom AI Orchestration Engine

Rotom is a modular AI orchestration system designed to route user intent
to structured capabilities while maintaining strict architectural
discipline.

This project emphasizes:

- Clear separation of concerns
- Dependency injection
- Capability purity
- Structured failure handling
- Centralized session lifecycle management
- Extensibility toward LLM and tool integration
- LLM-native reasoning with deterministic execution (introduced v1.1)

------------------------------------------------------------------------

## Architecture Philosophy

Rotom follows strict layered boundaries:

API → Service → Agents → Capabilities

Core invariants:

- Capabilities are pure and stateless
- RotomCore constructs nothing (all dependencies are injected)
- API schemas do not leak into core logic
- Session lifecycle is owned by RotomCore
- Integrations must be abstracted behind interfaces
- Execution remains deterministic even when reasoning is probabilistic

Full architectural rules are defined in `ARCHITECTURE.md`.

------------------------------------------------------------------------

## Current Features (v1.1)

- FastAPI endpoint: `/run`
- LLM-based intent classification (OpenAI-backed)
- Structured JSON capability routing
- Capability registry pattern
- Structured failure handling inside RotomCore
- Execution timing injection (perf_counter)
- In-memory session store (non-persistent)
- Dockerized deployment
- Environment-based LLM configuration (OPENAI_API_KEY, OPENAI_MODEL)

------------------------------------------------------------------------

## Project Structure

rotom/
│
├── docker-compose.yml
├── ARCHITECTURE.md
├── README.md
│
└── rotom-api/
    └── app/
        ├── api/
        ├── services/
        ├── agents/
        │   ├── intent/
        │   └── llm/
        ├── capabilities/
        ├── core/
        ├── models/
        └── schemas/

------------------------------------------------------------------------

## Running Locally

### Using Docker

From the project root:

    docker compose up

The API will be available at:

    http://localhost:8000/run

------------------------------------------------------------------------

## Example Request

POST `/run`

{ 
  "input": "Summarize this article...", 
  "session_id": "test-session" 
}

------------------------------------------------------------------------

## Roadmap

Planned architectural expansions:

- Structured tool call arguments
- Iterative agent reasoning loop
- Persistent session memory
- Multi-step capability chaining
- Tool + LLM hybrid orchestration
- Long-running daemon mode

------------------------------------------------------------------------

## Development Principles

- Architecture leads implementation.
- All dependencies are injected.
- No premature complexity.
- Capabilities remain pure.
- LLM reasoning must be structured and validated.
- Architectural changes require updating ARCHITECTURE.md first.

------------------------------------------------------------------------

Document Updated: 2026-02-24


------------------------------------------------------------------------

## Current Features (Updated in v1.2)

The following capabilities were added in v1.2 without removing prior functionality:

- Structured tool invocation contract:
    - `{ "capability": "<name>", "arguments": { ... } }`
- CapabilityInvocation internal execution model
- BaseIntentClassifier updated to return structured invocation data
- BaseCapability updated to accept structured arguments
- Defensive invocation validation inside RotomCore

------------------------------------------------------------------------

## Roadmap Status Update (v1.2)

The following roadmap item has been IMPLEMENTED as of v1.2:

- Structured tool call arguments

All other roadmap items remain unchanged and planned as originally documented.

------------------------------------------------------------------------

Version Updated: v1.2
Document Updated: 2026-02-24

Changes in v1.2:

- Introduced structured tool invocation (`capability` + `arguments`).
- Added CapabilityInvocation internal transport model.
- Updated BaseIntentClassifier interface contract.
- Updated BaseCapability execution contract.
- Added defensive invocation validation inside RotomCore.
