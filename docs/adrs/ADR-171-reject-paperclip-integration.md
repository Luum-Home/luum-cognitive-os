---

adr: 171
title: Reject Paperclip Integration — API was Aspirational, Multi-Surface Replaces It
status: accepted
implementation_status: implemented
date: 2026-05-05
supersedes: [ADR-043]
superseded_by: null
implementation_files:
  - .claude/settings.json
  - .codex/hooks.json
  - cognitive-os.yaml
  - docker-compose.cognitive-os.yml
  - docs/adrs/ADR-043-tombstone.md
  - hooks/_lib/registration-allowlist.txt
  - scripts/_lib/settings-driver-claude-code.sh
  - scripts/apply-efficiency-profile.sh
  - templates/security-profiles/minimal.json
  - templates/security-profiles/standard.json
  - templates/security-profiles/paranoid.json
tier: maintainer
tags: [paperclip, ui, integration-removal, aspirational-cleanup]
---

# ADR-171: Reject Paperclip Integration — API was Aspirational, Multi-Surface Replaces It

## Status

Accepted. Supersedes ADR-043.

## Context

ADR-043 extracted Paperclip from the mandatory Docker stack to a local-daemon path, on the premise that Paperclip could serve as a primary Cognitive OS UI surface.

Live verification on 2026-05-05 found that the COS-side client expected REST endpoints such as `/api/notifications`, `/api/agents/status`, `/api/artifacts`, `/api/projects`, `/api/issues`, `/api/spend`, and `/api/org-chart`, while released Paperclip builds expose a tRPC application API plus health endpoints. The COS integration therefore passed stubbed tests without proving an end-to-end contract against the upstream daemon.

This is the aspirational-not-real failure pattern: the repository carried hooks, docs, package metadata, tests, and client code for an integration that had not demonstrated runtime value.

A draft of this ADR was recovered from local ACI artifacts after ADR-171 had been accidentally replaced by a generic tombstone during a parallel-session cleanup. This accepted ADR is the semantic owner of number 171; `ADR-171-tombstone.md` must not exist alongside it.

## Decision

Reject Paperclip as an active Cognitive OS surface and hard-purge the integration from the active repository surface.

The accepted disposition is **delete + explicit decision record**, not archive-in-place:

1. ADR-043 is no longer active; its slot is represented by `ADR-043-tombstone.md` and this ADR explains why the local-daemon premise was rejected.
2. Paperclip hook symlinks and package hook files are removed.
3. Paperclip client shims are removed from active libraries and packages.
4. Paperclip docs and smoke/audit reports are removed from the active docs surface when they would mislead readers into believing the integration is supported.
5. Paperclip tests are removed because they exercised mocked transport behavior for an unsupported integration.
6. Docker/compose references to Paperclip are removed from active default surfaces.
7. Future revival is allowed only through a new ADR that verifies the real upstream API first and starts in a lab profile.

## Consequences

### Positive

- The active product surface no longer advertises an unsupported integration.
- Startup and post-tool hooks no longer spend time on HTTP calls to a mismatched API.
- The decision trail remains explicit even though the implementation surface is removed.
- The incident creates a reusable rule: third-party integration primitives need live upstream proof before promotion.

### Negative

- Git history is now the archaeology path for the removed integration.
- Any future Paperclip revival must rebuild against the real upstream API rather than relying on old stubs.
- Existing reports that referenced Paperclip must be read as historical context only.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep Paperclip archived in place | Rejected after operator instruction to remove the integration surface rather than preserve active tree artifacts. |
| Keep tests as historical checks | Rejected because passing mocked tests made the unsupported integration look healthier than it was. |
| Repair the client against tRPC immediately | Rejected as speculative work without a current buyer or product need. |
| Leave ADR-171 as a tombstone | Rejected because recovered artifacts prove ADR-171 has semantic decision ownership. |

## Verification

```bash
grep -R -n -i paperclip hooks lib packages scripts tests .claude .codex cognitive-os.yaml docker-compose.cognitive-os.yml --exclude-dir=.git
python3 -m pytest tests/unit/test_adr_tombstone.py tests/contracts/test_adr_numbering_integrity.py -q
```

## Cross-references

- ADR-043 — rejected local-daemon predecessor.
- ADR-169 — dashboard demotion; a related UI-surface cleanup.
- ADR-170 — operator CLI as primary UI surface.
- ADR-172 — multi-surface UI architecture.
- `docs/reports/postmortem-cross-session-collision-2026-05-05.md` — explains how ADR-171 was temporarily replaced by a tombstone.
- `docs/reports/file-by-file-review-2026-05-05.md` — file-level disposition matrix.
