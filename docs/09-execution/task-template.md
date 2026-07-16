---
id: EXEC-TEMPLATE-001
document_status: approved
normative: true
last_verified: 2026-07-16
---

# Task Template

```markdown
# TASK-ID: Outcome

Status: planned | ready | in_progress | verified
Depends on: task IDs or none

## Objective
One externally meaningful outcome.

## Required reading
- Normative specification
- Accepted ADR

## In scope
- Explicit changes

## Non-goals
- Explicit exclusions

## Invariants
- Behavior that must remain true

## Acceptance criteria
- [ ] Observable requirement
- [ ] Automated verification

## Verification
Exact commands from repository root.

## Documentation update
Capability rows and specifications affected.

## Commit
Exact suggested commit message.
```

An agent MUST inspect current code and `git status` before editing. A task MUST NOT assume a target capability already exists merely because a specification describes it.
