# Curl Examples for Rotom API

Assume the API is running at `http://localhost:8000` (e.g. `uvicorn app.main:app --reload` or Docker).

---

## Verify functionality

### 1. Health check (liveness)

```bash
curl -s http://localhost:8000/health
# Expected: {"status":"ok"}
```

### 2. Stateless run (no session) – direct capability

```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"input": "echo hello world"}'
# Expected: JSON with capability "echo", output "hello world", success true
```

### 3. Stateless run – another capability

```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Summarize this: Rotom is an AI orchestration kernel."}'
# Expected: JSON with capability "summarizer_stub", success true
```

### 4. Session + first message (Phase 5 context; no rewrite yet)

Use a fixed `session_id` so the next request shares context:

```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"input": "echo Phase 6 test", "session_id": "curl-session-1"}'
# Expected: echo runs, success true. Memory stores this turn for session curl-session-1.
```

### 5. Same session + follow-up (Phase 6: reference resolution)

Send a referring message in the same session. The resolver should rewrite it, then the classifier runs on the rewritten message:

```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"input": "do that again", "session_id": "curl-session-1"}'
# Expected: echo runs again with the same (or resolved) message; success true.
# Internally: resolver rewrites "do that again" using context → classifier gets rewritten message.
```

### 6. Session isolation

Use a different session; it has no prior context, so "do that again" may not resolve the same way or may fail classification:

```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"input": "do that again", "session_id": "curl-session-other"}'
# Expected: 200 with some capability result (LLM-dependent). No context from curl-session-1.
```

---

## Attempt to break it

### 7. Missing body (422)

```bash
curl -s -w "\nHTTP_CODE:%{http_code}" -X POST http://localhost:8000/run \
  -H "Content-Type: application/json"
# Expected: 422 Unprocessable Entity (validation error)
```

### 8. Empty JSON body (422)

```bash
curl -s -w "\nHTTP_CODE:%{http_code}" -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: 422 (missing "input")
```

### 9. Wrong type for input (422)

```bash
curl -s -w "\nHTTP_CODE:%{http_code}" -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"input": 123}'
# Expected: 422 (input must be string) or 200 if FastAPI coerces; check contract.
```

### 10. Wrong key (422 or ignored)

```bash
curl -s -w "\nHTTP_CODE:%{http_code}" -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"message": "echo hello"}'
# Expected: 422 (missing "input")
```

### 11. Invalid JSON (400 or 422)

```bash
curl -s -w "\nHTTP_CODE:%{http_code}" -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{invalid json}'
# Expected: 400 Bad Request or 422
```

### 12. Empty string input (200, but LLM may struggle)

```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"input": ""}'
# Expected: 200; classifier may return invalid or unexpected capability → possible 500 or error in metadata
```

### 13. Very long input (stress)

```bash
curl -s -w "\nHTTP_CODE:%{http_code}" -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d "{\"input\": \"$(printf 'x%.0s' {1..100000})\"}"
# Expected: 200 or 413/500 depending on limits; watch memory/LLM token limits
```

### 14. Null session_id (valid – same as omitted)

```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"input": "echo hi", "session_id": null}'
# Expected: 200, stateless behavior
```

### 15. Wrong method on /run (405)

```bash
curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:8000/run
# Expected: 405 Method Not Allowed (GET not allowed)
```

### 16. Non-existent path (404)

```bash
curl -s -w "\nHTTP_CODE:%{http_code}" -X POST http://localhost:8000/runny \
  -H "Content-Type: application/json" \
  -d '{"input": "echo hi"}'
# Expected: 404 Not Found
```

---

## Quick copy-paste (verify flow)

Run in order; same session for 4 and 5 to exercise Phase 6:

```bash
# Start server first, then:
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/run -H "Content-Type: application/json" -d '{"input": "echo first message", "session_id": "test-session"}'
curl -s -X POST http://localhost:8000/run -H "Content-Type: application/json" -d '{"input": "do that again", "session_id": "test-session"}'
```
