---
report_type: external-tools-radar-errata
date: 2026-05-08
source_index: docs/reports/external-tools-radar-INDEX.md
source_radar: docs/reports/external-tools-radar-2026-05-08.md
status: append-only-errata
---

# External Tools Radar 2026-05-08 — Errata and Status Corrections

This file is an append-only correction layer over the 2026-05-08 radar and
cross-checks. The radar snapshot remains historically useful; this errata
prevents future implementation work from acting on stale claims.

## E1 — ADR-253 already exists

**Stale statements**

- `docs/reports/external-tools-radar-2026-05-08.md` Wave 1 H1 asks to create
  ADR-253 tombstone for squads.
- `docs/reports/cross-check-C-orchestration-2026-05-08.md` and
  `docs/reports/cross-check-E-observability-debt-2026-05-08.md` say no squad
  tombstone exists.

**Current reality**

- `docs/adrs/ADR-253-tombstone-squads.md` exists and records the squads
  tombstone/supersedence boundary.
- `docs/reports/external-tools-radar-INDEX.md` already lists ADR-253 in Phase
  3.B.

**Action**

Treat H1 as closed; do not spawn new tombstone work for squads unless the
ADR-253 format itself is being normalized.

## E2 — README H2/H3 already closed

**Stale statements**

- Radar H2 asks to change safety-mesh count from `11 + 3` to `12 + 2`.
- Radar H3 asks to reconcile Trust Report wording with advisory/log-only hook
  behavior.

**Current reality**

- `README.md` now says 12 hooks and 2 library/conditional layers.
- `README.md` describes Trust Report validation as advisory/logging in current
  profile rather than hard blocking.

**Action**

Treat H2/H3 as closed. Future work should be enforcement design only if we
want Trust Reports to block by default.

## E3 — Cross-check E has an internal count contradiction

`cross-check-E-observability-debt-2026-05-08.md` both verifies `11 + 3` and
later states the correct count is `12 + 2`. Use `12 + 2` as current truth.

## E4 — FastMCP dependency path correction

**Stale statement**

`external-tools-radar-2026-05-08.md` says root `requirements.txt` declares
`fastmcp>=2.0.0`.

**Current reality**

- FastMCP is genuinely used by MCP code.
- The dependency declaration is in package-level requirements such as
  `packages/advisor-mcp/requirements.txt`, not root `requirements.txt`.

**Action**

Do not treat this as a false adoption. Treat it as a dependency-path errata.

## E5 — Bubblewrap hardening state is partial, not fully closed

**Radar action**

H4 says to add `--die-with-parent`, seccomp, and drop broad `--ro-bind /`.

**Current reality**

- Some hardening landed: `--die-with-parent`, PID/UTS/IPC namespace isolation,
  cgroup try, and new session handling.
- Seccomp/BPF profile remains pending.
- Broad read-only host bind may be intentionally retained until a narrower
  profile is proven not to break process startup.

**Action**

State H4 as partial. Do not claim hardened sandbox until seccomp/capability and
read-only host exposure decisions are closed by tests/threat model.

## E6 — Langfuse deprecation is trace-sink true, repo-wide partial

**Stale/over-narrow statement**

Cross-check E proves `lib/record_completion.py` has zero `langfuse` hits and
then implies migration is complete.

**Current reality**

- Runtime trace sink appears migrated away from Langfuse.
- Some repo references may remain in dependency lists or package docs.
- Docker Compose Langfuse stack appears removed/documented as removed.

**Action**

Use this phrasing: "Langfuse is deprecated for runtime tracing; remaining
legacy references must be classified as package optional/docs/debt before
public claims." Do not claim repo-wide zero until a whole-repo grep/audit says
so.

## E7 — 85% token-reduction remains upstream/unmeasured locally

The `85% token reduction` figure belongs to upstream/provider deferred loading
research unless COS has a local benchmark. Public COS docs must not present it
as a measured COS outcome until instrumentation exists.

## E8 — `sdd-verify` pilot target is unresolved

Wave 3 proposes a DSPy pilot starting with `sdd-verify`, but this audit did
not find a top-level `skills/sdd-verify/SKILL.md`. Before implementation,
choose one of:

1. materialize/document `sdd-verify` as a real skill surface, or
2. switch the pilot to an existing structured-I/O skill such as
   `confidence-check`, if present and suitable.

## E9 — Phase 2 cluster path correction

The index previously implied a `docs/research/repo-scout/clusters/` subdir.
The actual cluster files are directly under `docs/research/repo-scout/` as
`cluster-*-2026-05-06.md`.

## E10 — Phase 0 `cos-vs-vanilla` date is a narrative date, not commit date

The index lists `docs/business/cos-vs-vanilla-dx-review.md` under 2026-03-27,
but git provenance reports later creation/review dates. Treat this row as
"origin framing" rather than exact artifact creation date unless provenance is
added.

## E11 — ADR-187 status chain is not fully normalized

ADR-187 appears in radar related ADRs as part of Surface 5 proof, but its file
still reads `status: proposed` while ADR-192 is the accepted Bubble Tea decision.
Do not cite ADR-187 alone as accepted implementation closure.

## E12 — ADR-236 provider-native deferred loading is not runtime-complete

COS has governance/indexing/planning for deferred tool loading. The actual
provider-native runtime mechanism such as MCP tool-list change notification is
not generally active. Label this as blueprint/partial unless a provider path is
proven.

## E13 — Orchestration ADR count needs precise arithmetic

The index says "14 ADRs drafted (ADR-222…236). 11/14 implemented". The numeric
range contains 15 slots, with tombstones/reserved slots mixed in. Future docs
should count active ADRs, tombstones, and reserved slots separately.
