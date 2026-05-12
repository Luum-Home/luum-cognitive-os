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
  - docs/02-Decisions/adrs/ADR-043-tombstone.md
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

## Operational Guide

### What changes for the operator

Before this ADR, the repository carried Paperclip hooks, client shims, tests, docs, and Docker references that appeared active but exercised only mocked transport behavior. The COS-side client expected REST endpoints (`/api/notifications`, `/api/agents/status`, etc.) that the upstream Paperclip daemon never exposed. Sessions silently spent time on HTTP calls to a mismatched API.

After this ADR:

| Surface | Before | After |
|---|---|---|
| Paperclip hooks and symlinks | Present in active hook directories | Removed from active tree |
| Paperclip client shims | In `lib/` and `packages/` | Removed |
| Paperclip tests | Passing against mocked transport | Removed (mocked tests obscured real integration state) |
| ADR-043 | Active ADR for local-daemon path | Replaced by `ADR-043-tombstone.md`; ADR-171 owns the rejection decision |
| Future revival path | Undefined | Requires a new ADR that verifies the real upstream tRPC API first, starting in a lab profile |

### What this answers (and what it doesn't)

**Answers:**
- "Is Paperclip a supported COS integration?" — No. This ADR hard-purges it. Git history is the archaeology path.
- "Why did the integration fail?" — The COS client expected REST endpoints; Paperclip exposes tRPC. The mocked tests masked this mismatch.
- "Can Paperclip be re-added later?" — Yes, but only via a new ADR that demonstrates a working contract against the real upstream API before any code lands.

**Does not answer:**
- "What Paperclip's actual tRPC API looks like" — consult Paperclip's upstream docs; this ADR does not document the external API.

### Daily operational pattern

No ongoing action required. The decision is a one-time hard-purge. Verify the purge is complete:

```bash
grep -R -n -i paperclip hooks lib packages scripts tests .claude .codex cognitive-os.yaml docker-compose.cognitive-os.yml --exclude-dir=.git
```

A clean result (no matches) is the steady-state. If any match appears, it is a regression and must be removed.

### Reading guide for cold readers

1. The core lesson is the **aspirational-not-real failure pattern**: the integration passed stubbed tests without proving an end-to-end contract against the real upstream daemon. This pattern is now a reusable rule — third-party integration primitives need live upstream proof before promotion.
2. ADR-043 (the predecessor) is represented by `docs/02-Decisions/adrs/ADR-043-tombstone.md`; read it for the original local-daemon premise.
3. ADR-172 (multi-surface UI architecture) documents what UI surfaces replace the dashboard/Paperclip role.
4. The verification command above is the authoritative check that the purge holds.

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
- `docs/06-Daily/reports/postmortem-cross-session-collision-2026-05-05.md` — explains how ADR-171 was temporarily replaced by a tombstone.
- `docs/06-Daily/reports/file-by-file-review-2026-05-05.md` — file-level disposition matrix.
