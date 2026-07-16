# TASK-012: Verify End-to-End Vietnamese and English Behavior

Status: planned

Depends on: TASK-008, TASK-009, TASK-010, TASK-011

## Objective

Make Vietnamese and English first-class, tested product behavior rather than prompt convention.

## Required reading

- `docs/03-specifications/multilingual-spec.md`
- `docs/00-product/product-vision.md`

## In scope

- Explicit language preference and fallback policy.
- Same-language answer behavior.
- Cross-language retrieval verification.
- Original-language quotations and citations.
- Backend and frontend language metadata.
- End-to-end bilingual acceptance suite.

## Non-goals

- Languages beyond Vietnamese and English
- Full translation-management workflow

## Acceptance criteria

- [ ] `vi->vi`, `en->en`, `vi->en`, and `en->vi` retrieval cases pass the approved release gate.
- [ ] Answers follow explicit selection or latest-question language.
- [ ] Source text and timestamp identity remain unchanged by answer translation.
- [ ] Language-detection uncertainty follows documented fallback.

## Verification

`uv run --project backend pytest backend/tests/e2e/bilingual`

## Commit

`feat(i18n): verify bilingual grounded experience`
