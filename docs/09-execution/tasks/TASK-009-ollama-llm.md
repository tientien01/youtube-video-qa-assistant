# TASK-009: Complete the LLM-Independent Ollama Path

Status: planned

Depends on: TASK-001

## Objective

Upgrade the minimal LLM protocol and make Ollama the free local generation path without coupling application logic to it.

## Required reading

- `docs/03-specifications/llm-spec.md`
- `docs/08-decisions/ADR-002-llm-independent.md`
- `docs/03-specifications/multilingual-spec.md`

## In scope

- Application-level request/result/error/capability contracts.
- Deterministic fake provider.
- Ollama adapter with timeout, structured output, usage metadata, and health check.
- Adapt Gemini behind the same contract.
- Structured grounded answer schema and citation validation.
- Explicit provider selection; no silent paid fallback.

## Non-goals

- Tool calling or agents
- Cloud provider expansion
- Streaming before structured non-streaming output is verified

## Acceptance criteria

- [ ] Application tests pass with only the fake provider.
- [ ] Ollama and Gemini SDK types never leave adapters.
- [ ] Unknown citation IDs cannot reach a successful API response unnoticed.
- [ ] Ollama unavailable leaves ingest/retrieval healthy and generation explicitly unavailable.
- [ ] Provider/model are configurable and reported in generation metadata.

## Verification

`uv run --project backend pytest backend/tests/unit/llm backend/tests/integration/generation`

## Commit

`feat(llm): add provider-independent Ollama generation`
