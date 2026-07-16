---
id: ADR-002
status: accepted
date: 2026-07-16
---

# ADR-002: LLM-Independent Architecture, Ollama-First

## Decision

Application code depends on a provider-independent LLM port. Ollama is the default local implementation. Gemini is optional and isolated in an adapter.

## Rationale

The product must work locally without per-request fees and later adopt paid models without redesigning domain logic.

## Consequences

Prompts, schemas, citations, and retry policy belong outside provider SDKs. Provider capability differences are explicit. Paid fallback is opt-in and never silent.
