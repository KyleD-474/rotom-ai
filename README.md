# Rotom AI Orchestration Kernel

Rotom is a **bounded AI orchestration kernel** for a persistent, personal AI system — like a "Jarvis" on your Linux PC. It is designed to have appropriate access to your files, the internet, and an LLM when necessary, and to support planning, tool execution, memory use, and hybrid reasoning **without losing control**.

Rotom is not a chatbot. It is not an uncontrolled agent. It is the **orchestration layer**: intent classification, tool gatekeeper, and execution boundary. The LLM cannot access systems unless a capability exists.

---

## Vision

> A bounded AI orchestration kernel capable of planning, tool execution, memory use, and hybrid reasoning — without losing control.

- **AI flexibility** — LLM for intent and reasoning when needed  
- **Systems-level discipline** — explicit steps, iteration limits, auditable tool use  
- **Deterministic orchestration** — RotomCore owns the loop; capabilities are pure execution units  
- **Replaceable LLM backend** — abstracted behind interfaces  

For a full set of intended use cases (trip planning, research, developer automation, browser automation, workflows, enterprise gateway, etc.), see **[USECASES.md](USECASES.md)**.

---

## Architecture

Strict layered boundaries:

**API → Service → Agents → Capabilities**

Core invariants:

- Capabilities are pure and stateless
- RotomCore constructs nothing (all dependencies are injected)
- API schemas do not leak into core logic
- Session lifecycle is owned by RotomCore
- Integrations are abstracted behind interfaces
- Execution remains bounded and deterministic at the orchestration level

Full rules: **[ARCHITECTURE.md](ARCHITECTURE.md)**.  
Project context and roadmap: **[AI_CONTEXT.md](AI_CONTEXT.md)**.

---

## Current Features (v1.4)

- FastAPI endpoint: `/run`
- LLM-based intent classification (OpenAI-backed, metadata-driven prompts)
- Structured JSON capability routing: `{ "capability": "<name>", "arguments": { ... } }`
- Argument validation: required keys and no extra keys enforced before execution
- Capability registry pattern
- Structured failure handling and execution timing injection
- In-memory session store (non-persistent)
- Dockerized deployment
- Environment-based LLM configuration (`OPENAI_API_KEY`, `OPENAI_MODEL`)

---

## Project Structure

```
rotom/
├── docker-compose.yml
├── ARCHITECTURE.md
├── AI_CONTEXT.md
├── USECASES.md
├── README.md
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
```

---

## Running Locally

From the project root:

```bash
docker compose up
```

API: **http://localhost:8000/run**

---

## Example Request

**POST** `/run`

```json
{
  "input": "Echo back: Hello world",
  "session_id": "test-session"
}
```

---

## Roadmap

- ~~Structured tool call arguments~~ (v1.2)
- ~~Metadata-driven orchestration~~ (v1.3)
- ~~Argument validation layer~~ (v1.4)
- Session memory utilization
- Tool result injection into LLM
- Iterative reasoning loop (bounded, max-iteration guard)
- Persistent storage (abstracted)
- Hybrid tool + LLM execution

---

## Development Principles

- Architecture leads implementation.
- All dependencies are injected.
- No premature complexity.
- Capabilities remain pure.
- LLM usage is structured and validated.
- Architectural changes require updating ARCHITECTURE.md first.

---

*Document updated: 2026-02-25*
