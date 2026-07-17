---
id: SPEC-I18N-001
document_status: approved
implementation_status: verified
normative: true
last_verified: 2026-07-16
---

# Multilingual Specification

## Local V1 scope

Vietnamese and English are first-class languages for transcript selection, retrieval, prompts, answers, and evaluation. UI localization may be delivered incrementally after backend language behavior is verified.

## Behavior

- Default answer language follows the user's latest question.
- An explicit user language selection overrides automatic detection.
- Source quotations remain in the transcript language.
- The application MAY explain a quotation in the answer language but MUST retain the original citation.
- Retrieval MUST support a query language different from the transcript language.
- Language detection failure MUST use the session preference, then product default.

## Storage

Store BCP 47-compatible language codes when known. Preserve provider language codes separately when normalization would lose information.

## Evaluation

The release dataset MUST include `vi->vi`, `en->en`, `vi->en`, and `en->vi` retrieval cases. Generation evaluation MUST check answer-language compliance independently from factual grounding.

The Local V1 implementation exposes `answer_language` (`vi` or `en`) in chat
requests, responses, and stored history. When omitted, the latest question is
detected; uncertain input uses the caller/session fallback and then English as
the product default. Retrieval and evidence payloads are never translated.

## Future expansion

Adding a language requires transcript selection rules, sentence segmentation support or fallback, retrieval evaluation examples, prompt evaluation, and UI translations. Adding a language code alone is not sufficient.
