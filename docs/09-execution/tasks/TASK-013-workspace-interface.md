# TASK-013: Implement the Approved Video Learning Workspace

Status: planned

Depends on: TASK-008, TASK-009, TASK-010

## Objective

Replace the current generic tab/card interface with the approved local-first
video learning workspace while preserving evidence traceability and real runtime
state.

## Required reading

- `docs/00-product/interface-specification.md`
- `docs/00-product/product-vision.md`
- `docs/03-specifications/multilingual-spec.md`
- `docs/05-api/api-guidelines.md`

## In scope

- Application shell, responsive navigation, top bar, breadcrumb, language, and health.
- Home, Library, and primary `/library/:videoId` workspace routes.
- Synchronized video player, transcript, conversation, and Evidence panels.
- Design tokens, shared UI primitives, loading/empty/error/job states.
- Real local runtime health; no hard-coded Ollama or storage status.
- Responsive and accessibility behavior defined by the interface specification.
- Visual/browser acceptance fixtures and screenshots.

## Non-goals

- Inventing backend APIs or persisting fake data for unfinished destinations
- Pixel-copying nonfunctional custom YouTube controls
- Cross-video research
- Authentication, collaboration, billing, or production deployment UI
- An unrelated frontend state-management framework migration

## Acceptance criteria

- [ ] Desktop video workspace matches the approved mock hierarchy and proportions.
- [ ] Timestamp, transcript, citation, evidence, and player selection stay synchronized.
- [ ] Home/Library display real persistent ingest stages, retry, and cancellation.
- [ ] Health and model/storage cards report real backend facts or explicit unavailability.
- [ ] Planned destinations are disabled/labelled and never masquerade as working pages.
- [ ] Empty, loading, ready, insufficient-evidence, failed, and provider-offline states are complete.
- [ ] Responsive layouts satisfy all four documented breakpoints without horizontal overflow.
- [ ] Keyboard navigation, focus, accessible names, reduced motion, and AA contrast are verified.
- [ ] Visual/browser regression tests cover the required reference states.

## Verification

```powershell
uv run --project backend pytest backend/tests/integration/api
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

## Commit

`feat(ui): implement evidence-first video workspace`
