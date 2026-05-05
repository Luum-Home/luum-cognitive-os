---
adr: 169
title: Dashboard Formal Demotion — Paperclip is the UI, Cognitive OS is the engine
status: accepted
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - dashboard/ARCHIVED.md
  - hooks/_lib/registration-allowlist.txt
  - cognitive-os.yaml
  - scripts/_lib/settings-driver-claude-code.sh
  - hooks/paperclip-sdd-sync.sh
  - hooks/paperclip-agent-status.sh
  - hooks/paperclip-cost-stream.sh
  - hooks/paperclip-squad-sync.sh
  - hooks/paperclip-task-sync.sh
  - hooks/paperclip-sync.sh
  - docs/paperclip-integration.md
tier: maintainer
tags: [ui, dashboard, paperclip, demotion, architecture-fork]
---

# ADR-169: Dashboard Formal Demotion — Paperclip is the UI, Cognitive OS is the engine

## Status

Accepted.

## Context

On 2026-03-27, the project committed in `docs/paperclip-integration.md` to:

> *"This integration eliminates the need to build a custom web dashboard (originally planned as Phase 2). Instead, Cognitive OS pushes state to Paperclip via its REST API, and Paperclip renders the UX."*
>
> ***"Paperclip is the UI, Cognitive OS is the engine."***

The `dashboard/` directory was last modified 2026-03-29 (two days after the deprecation decision) and reached approximately 30% of a usable admin surface: app skeleton, two routes (`/rules`, `/skills`), three components, an API client stub.

On 2026-05-05, two days after a long architectural review and three releases (v0.23.0 → v0.24.0 → v0.25.0), the question of resurrecting the dashboard surfaced. A read-only audit of Paperclip integration ([`docs/reports/paperclip-integration-audit-2026-05-05.md`](../reports/paperclip-integration-audit-2026-05-05.md)) found:

- 3 of 8 documented mappings were REAL (Singularity inbox, Safety mesh blocks, Retry queue resilience).
- 4 of 8 mappings were PARTIAL: hooks present and tested, but **not registered in `.claude/settings.json`**, so they fired zero times per session.
- 1 of 8 mappings was MISSING (cos packages → skills marketplace; no API method, no hook).
- The dashboard's unique territory (rules / skills / stat-card views) was real but small.

The audit's recommendation was Path B: bounded gap, does not justify dashboard resurrection. Wire the 4 partial hooks first, decide mapping #5, and formally demote `dashboard/` after Paperclip reaches its documented surface.

## Decision

1. **`dashboard/` is formally demoted to archived.** A `dashboard/ARCHIVED.md` notice is added. Files are preserved on disk (not deleted) so the demotion is reversible if the falsifiable claim below fires.
2. **The six Paperclip hooks** (`paperclip-squad-sync`, `paperclip-task-sync`, `paperclip-sdd-sync`, `paperclip-agent-status`, `paperclip-cost-stream`, `paperclip-sync`) are wired into `.claude/settings.json` via the canonical projection path:
   - `cognitive-os.yaml > harness.hooks` gains six entries.
   - `hooks/_lib/registration-allowlist.txt` is extended with five new entries.
   - `scripts/_lib/settings-driver-claude-code.sh` adds the six hooks to its SessionStart, PostToolUse Agent, and Stop projection groups.
   - `hooks/paperclip-{sdd-sync,agent-status,cost-stream,squad-sync,task-sync}.sh` are added as symlinks to the canonical implementations under `packages/paperclip-integration/hooks/`.
   - All six hooks project as `async: true` so they never block the session.
3. **Mapping #5 (cos packages → skills marketplace) is intentionally deferred.** The architecture diagram in `docs/paperclip-integration.md` is updated to remove the active line and document the deferral with reactivation conditions.

## Acceptance Criteria

1. `grep -c "paperclip" .claude/settings.json` returns 6.
2. `dashboard/ARCHIVED.md` exists and is the first file a reader of `dashboard/` should encounter.
3. Nothing else in the repo imports from `dashboard/app`, `dashboard/components`, or `dashboard/lib`. (Verified pre-commit: zero matches under `docs/`, `scripts/`, `hooks/`, `lib/`, `packages/`, `rules/`.)
4. The architecture diagram in `docs/paperclip-integration.md` no longer lists `cos packages → Paperclip skills marketplace` as an active mapping; the deferred-mapping callout names mapping #5 and points at the audit report.
5. `bash -n scripts/_lib/settings-driver-claude-code.sh` passes.
6. `python3 -c "import yaml; yaml.safe_load(open('cognitive-os.yaml'))"` parses without error after the insertion.

## Border Cases

- **Someone clones the repo and runs the dashboard.** They will see `ARCHIVED.md` as the most recently-touched file and the deprecation notice. `node_modules/` and `.next/` are gitignored, so they will need to `npm install` before anything could run — at which point they should read the notice and stop.
- **An external evaluator wants a UI demo.** The path is now Paperclip via [`docs/runbooks/run-cos-in-docker.md`](../runbooks/run-cos-in-docker.md), not the dashboard.
- **Paperclip is unreachable.** The 6 wired hooks are all `async: true` and call into `lib/_lib/paperclip-notify.sh` which logs and degrades gracefully when the daemon is down. Sessions are not blocked. The retry queue (mapping #8, REAL) holds events for redelivery.
- **Mapping #5 is needed urgently.** Implement `push_skills()` on `PaperclipClient` and add a hook. This ADR does not require pre-commitment to a particular API shape. Reactivation does not require revoking ADR-169.

## Consequences

**Positive.**

- The 6 documented mappings that were dead because of unwired hooks are now live. Paperclip receives session events on every Claude Code session.
- The architectural intent declared on 2026-03-27 is finally enacted. The deprecation is no longer maintainer cache — it is filesystem-visible.
- A future contributor reading the repo gets a clear answer to *"why is `dashboard/` half-built?"*: it was deliberately demoted in favour of Paperclip.
- The 2026-05-05 audit's falsifiable claim is preserved as a tripwire: if the integration goes silent, the demotion is revisited.

**Negative / trade-offs.**

- The dashboard's unique territory (rules / skills / stat-card views) is now an open gap covered partially by the in-session `paperclip-dashboard/SKILL.md`. If that coverage proves insufficient, mapping #5 must be implemented or the dashboard must be revoked.
- Async hooks accumulate latency variability if the Paperclip daemon is unreachable. The retry queue caps memory use; latency observability is via `hook-timing.jsonl`.
- This ADR commits the project to maintaining the Paperclip integration as the single UI surface. If the integration project changes direction or is archived upstream, the COS will need a new UI plan within ADR-132's existing trigger framework.

## Alternatives Rejected

- **Resurrect `dashboard/` to completion.** Rejected: net-new surface area without demotion-compensation, contradicts the 2026-03-27 architectural decision, duplicates a Paperclip integration that is 6 of 7 mappings live after this ADR.
- **Delete `dashboard/` outright.** Rejected: loss of architectural exploration evidence; demotion should be reversible if the falsifiable claim fires.
- **Keep `dashboard/` undocumented and untouched.** Rejected: this is the *"maintainer cache no transferible"* pattern ADR-132 catalogues. The directory looks like in-flight work to anyone who hasn't read the 2026-03-27 paperclip-integration doc.
- **Add a separate skills-marketplace web app instead of mapping #5.** Rejected: same architectural problem (parallel UI to Paperclip) at smaller scale. If skills inventory needs UI, it should live in Paperclip via a `push_skills()` extension or be documented as a CLI affordance.

## Falsifiable Claim

The dashboard demotion holds while **all** of the following remain true. If any breaks for the indicated duration, this ADR must be revisited:

1. **Paperclip integration delivers signal.** At least one of `metrics/.paperclip-cost-last-push`, `.cognitive-os/runtime/paperclip.port`, or a non-empty `paperclip-sync.jsonl` exists within 14 days of normal session use. (Hook-dead signal.)
2. **No paperclip-only gap requires UI.** Mapping #5 (skills marketplace) is either implemented within 90 days or formally removed from `docs/paperclip-integration.md` rather than carried as deferred-indefinitely. (Mapping-frozen signal.)
3. **No external request for COS-instance admin.** No external consumer requests a COS-instance admin UI within 6 months that Paperclip cannot serve via existing or extensible mappings. (External-demand signal.)

If conditions 1–3 hold for one calendar year, the demotion is judged correct and `dashboard/` may be deleted in a follow-up ADR.

## Cross-references

- [`docs/paperclip-integration.md`](../paperclip-integration.md) — the 2026-03-27 architecture decision this ADR enacts.
- [`docs/reports/paperclip-integration-audit-2026-05-05.md`](../reports/paperclip-integration-audit-2026-05-05.md) — the audit that produced the recommendation.
- [`dashboard/ARCHIVED.md`](../../dashboard/ARCHIVED.md) — the in-tree demotion notice.
- [ADR-043](ADR-043-paperclip-local-daemon.md) — local-daemon path for Paperclip.
- [ADR-132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md) — the maintainer-cache transferability frame this ADR addresses.
- [ADR-133](ADR-133-expansion-without-monsterization.md) — lab-first promotion contract; the wiring-not-resurrection path satisfies its requirements.
- [`docs/runbooks/run-cos-in-docker.md`](../runbooks/run-cos-in-docker.md) — the external-evaluator path that does not depend on the dashboard.
