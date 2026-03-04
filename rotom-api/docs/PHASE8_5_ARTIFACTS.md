# Phase 8.5: Plan-Driven Artifact Store

This document describes the **artifact store** used in the goals-based path to pass prior step outputs to later goals without putting all prior results in every classifier prompt. See [PHASE8_5_PLAN.md](PHASE8_5_PLAN.md) for the overall Phase 8.5 flow.

---

## Problem

Goals like "get word count of summarized text" need the **summary** from an earlier step. Previously, the only context the intent classifier received was:

- Original user input
- **Previous step result** (the immediately preceding step’s output)

When the previous step was something else (e.g. "print Hello World!!!"), the classifier never saw the summary and could not pass it to `word_count`. It would sometimes use the only long text available—the original paragraph—producing the wrong count.

---

## Solution

Plan steps can declare:

- **`store_output_as`**: After this step runs, store `result.output` under a named key in a request-scoped artifact store.
- **`use_from_memory`**: Before classifying this goal, inject the content of these keys into the classifier context (e.g. "Content of 'summarized_text' (from a previous step): …").

Only the artifacts requested for the **current** goal are added to context, so token cost stays low.

---

## Lifecycle

- The artifact store is a **request-scoped** dict (`artifacts: Dict[str, str]`) created at the start of `_handle_goals_based` and used only for that single request.
- When the function returns, the variable goes out of scope and is garbage-collected. **No explicit clear is required.**
- Artifacts are not persisted to session memory in the baseline design. A future phase could add session-scoped artifact storage if cross-request reuse is needed.

---

## Plan Format

The plan builder may output a JSON array of **steps**. Each step is either:

- A **goal string** (plain string), or
- An **object** with:
  - `goal` (string, required): the goal description
  - `store_output_as` (string, optional): key under which to store this step’s output
  - `use_from_memory` (string or array of strings, optional): keys whose content to inject into context for this goal

Example:

```json
[
  "get word count of original text and output it",
  { "goal": "summarize original text and output it", "store_output_as": "summarized_text" },
  "print 'Hello World!!!'",
  { "goal": "get word count of summarized text and output it", "use_from_memory": "summarized_text" }
]
```

The producer step (summarize) and consumer step (word count of summary) share the key `"summarized_text"`.

---

## Backward Compatibility

A plain array of goal strings (no objects, no `store_output_as` / `use_from_memory`) is still valid. In that case, context for each goal falls back to "Previous step result" (the last step’s output) as before.
