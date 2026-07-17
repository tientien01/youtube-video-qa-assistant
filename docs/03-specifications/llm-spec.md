---
id: SPEC-LLM-001
document_status: approved
implementation_status: verified
normative: true
last_verified: 2026-07-17
related_adrs: [ADR-002]
---

# LLM and Generation Specification

## Decision

The application MUST be LLM-independent. Ollama is the first-class local adapter, not an application dependency. Gemini remains an optional adapter during migration.

## Provider contract

The application-level contract MUST support:

- messages and system instructions;
- generation options and timeouts;
- streaming capability discovery;
- structured output schema;
- finish reason and usage metadata when available;
- typed errors for unavailable, timeout, rate limit, invalid output, and context overflow.

Provider SDK request/response types MUST remain inside adapters. Prompt templates, citation rules, and output schemas belong to the application layer.

## Local models

- Light profile generation default: `qwen3:4b`.
- Standard profile generation default: `qwen3:8b`.
- Model names and context limits MUST be configuration, never constants in use cases.
- Local operation MUST NOT require a paid API key.
- Cloud fallback MUST be explicit and opt-in; it MUST never happen silently.

## Structured answer

Chat generation SHOULD return a schema equivalent to:

```json
{
  "answer": "...",
  "citations": [{"chunk_id": "...", "claim": "..."}],
  "answer_language": "vi",
  "insufficient_evidence": false
}
```

The application MUST validate citation IDs against supplied context. Invalid citations MUST be rejected, repaired once under a bounded policy, or removed with an explicit warning. The model MUST be instructed to abstain when evidence is insufficient.

## Testing

- Unit and application tests use a deterministic `FakeLlmProvider`.
- Adapter contract tests apply to every provider.
- Optional Ollama smoke tests are separate from the deterministic suite.
- Tests MUST cover invalid JSON, unknown citations, timeout, provider unavailable, context overflow, and bilingual output policy.
