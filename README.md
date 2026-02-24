# Rotom AI Orchestration Engine

Rotom is a modular AI orchestration system designed to route user intent
to structured capabilities while maintaining strict architectural
discipline.

This project emphasizes:

-   Clear separation of concerns
-   Dependency injection
-   Capability purity
-   Structured failure handling
-   Centralized session lifecycle management
-   Extensibility toward LLM and tool integration

------------------------------------------------------------------------

## Architecture Philosophy

Rotom follows strict layered boundaries:

API → Service → Agents → Capabilities

Core invariants:

-   Capabilities are pure and stateless
-   RotomCore constructs nothing (all dependencies are injected)
-   API schemas do not leak into core logic
-   Session lifecycle is owned by RotomCore
-   Integrations must be abstracted behind interfaces

Full architectural rules are defined in `ARCHITECTURE.md`.

------------------------------------------------------------------------

## Current Features

-   FastAPI endpoint: `/run`
-   Rule-based intent classification
-   Capability registry pattern
-   Structured failure handling inside RotomCore
-   Execution timing injection (perf_counter)
-   In-memory session store (non-persistent)
-   Dockerized deployment

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
├── capabilities/
├── core/
├── models/
└── schemas/

------------------------------------------------------------------------

## Running Locally

### Using Docker

From the project root:

    docker compose up --build

The API will be available at:

    http://localhost:8000/run

------------------------------------------------------------------------

## Example Request

POST `/run`

{ "input": "echo hello world", "session_id": "test-session" }

------------------------------------------------------------------------

## Roadmap

Planned architectural expansions:

-   Persistent session memory
-   LLM abstraction layer
-   Multi-step capability chaining
-   Tool + LLM hybrid orchestration

------------------------------------------------------------------------

## Development Principles

-   Architecture leads implementation.
-   All dependencies are injected.
-   No premature complexity.
-   Capabilities remain pure.
-   Architectural changes require updating ARCHITECTURE.md first.

------------------------------------------------------------------------

## License

This project is licensed under the MIT License.
