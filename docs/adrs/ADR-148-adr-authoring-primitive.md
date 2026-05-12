---

adr: 148
title: ADR Authoring Primitive
status: accepted
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos-new-adr
  - scripts/cos_new_adr.py
  - tests/unit/test_cos_new_adr.py
tier: maintainer
tags: [adr, governance, authoring, contract]
---

# ADR-148: ADR Authoring Primitive

## Status

**Accepted** — 2026-05-04

## Context

The ADR ledger and contract tests now detect overestimated implementation claims, but authors can still create malformed ADRs and discover the problem only after audit failures. Recent ADRs drifted on required sections and implementation evidence shape, which forced cleanup after the fact.

The SO already has three pieces of ADR governance:

- `scripts/adr_reserve.py` atomically reserves ADR numbers across concurrent sessions.
- `hooks/adr-section-validator.sh` warns or blocks malformed ADR sections on write/edit.
- `tests/audit/test_adr_contracts.py` enforces the ADR-067+ section contract in CI/local validation.

Those pieces are necessary but not sufficient as an authoring path. A maintainer or agent should have one primitive that starts from the correct structure and uses the existing reservation mechanism before writing a new ADR.

## Decision

Add `scripts/cos-new-adr` as the canonical ADR authoring primitive. It wraps `scripts/cos_new_adr.py`, reserves an ADR number through `scripts/adr_reserve.py`, and writes a draft with:

- YAML frontmatter;
- `## Status`, `## Context`, `## Decision`, `## Consequences`, `## Alternatives rejected`, and `## Verification`;
- a substantive alternatives table;
- a fenced verification command;
- optional implementation-file declarations for accepted or implemented ADRs.

This primitive does not decide architecture. It enforces draft shape and coordination so new ADRs begin inside the same contract that the ledger and tests later audit.

## Consequences

### Positive

- New ADRs can be created without relying on agent memory for required sections.
- ADR number collisions are less likely because reservation is part of the authoring path.
- The structure used by authors matches the structure enforced by tests and hooks.
- Missing implementation files remain falsifiable because the generated frontmatter includes `implementation_files`.

### Negative

- Authors have one more command to learn.
- The helper can only guarantee shape; it cannot guarantee that the decision is wise.
- Existing hand-written ADR workflows remain possible, so tests and hooks are still required.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep relying on tests after hand-written ADRs | Rejected because the failure arrives after the author already created drift. |
| Make the hook auto-rewrite malformed ADRs | Rejected because hooks should not silently mutate architectural decision records. |
| Create only a skill and no script | Rejected because skills depend on agent behavior, while scripts are directly testable and reusable from any harness. |

## Verification

```bash
python3 -m pytest tests/unit/test_cos_new_adr.py tests/audit/test_adr_contracts.py tests/unit/test_adr_implementation_ledger.py -q
```

## Implementation Evidence

- Implemented in `scripts/cos-new-adr`: shell entrypoint that resolves the project and invokes the Python authoring primitive.
- Implemented in `scripts/cos_new_adr.py`: ADR reservation, frontmatter rendering, required-section rendering, dry-run, and JSON output.
- Implemented in `tests/unit/test_cos_new_adr.py`: generated draft shape, dry-run behavior, and CLI JSON reporting.
