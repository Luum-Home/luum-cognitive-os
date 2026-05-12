# M3 — ADR Sweep Report (ADR-218 through ADR-238)

**Date**: 2026-05-08
**Reviewer**: M3 manual-sweep agent (read-only)
**Scope**: 21 ADRs landed in the AI-agent batch over 2026-05-06 / 2026-05-07
**Mandate**: surface inconsistencies, broken cross-references, prose drift,
and AI-slop patterns. **No ADR was modified.** This report is observation only.

---

## CRITICAL findings (must address before public launch)

### C1 — ADR-228 has a self-contradicting status header

`docs/02-Decisions/adrs/ADR-228-retry-contract-and-cost-budget.md` opens with two
mutually exclusive status declarations:

```
## Status
Tombstone

**Status**: Accepted — Slices A–F implemented (2026-05-07)
```

ADR-229 (the actual tombstone) explains that the cost-budget ADR was
**consolidated into 228**, so 228 is the live, accepted ADR. The literal
`Tombstone` line in 228's `## Status` block is the bug — it would lead any
automated status scraper (Aguara, license audits, the readiness checklist
itself) to file 228 as a tombstoned ADR. **Remediation**: change line 4 of
ADR-228 from `Tombstone` to `Accepted`.

There are **no other CRITICAL findings.** Everything below is HIGH or
lower and survivable for public release with a follow-up commit.

---

## Methodology

For each ADR file:

1. Extracted the front matter (`Status`, `Date`, `Related`).
2. Captured every `ADR-NNN` token and verified the target file exists in
   `docs/02-Decisions/adrs/`. Since the directory uses both slugged
   (`ADR-218-history-sanitization-toolchain.md`) and bare
   (`ADR-027.md`) filename styles, both forms count as a hit.
3. Captured every backticked path reference matching
   `*.{py,sh,md,yaml,yml,json,go}` and spot-checked existence on disk for
   the load-bearing files (libs and manifests directly named in the
   "Decision" sections).
4. Read each Status / Decision block for prose drift — phrasing that
   contradicts the headline status, undefined acronyms, or templated
   filler.
5. Cross-document scan: are dates plausible (no future-dated decisions),
   do paired ADRs (e.g. 226 ↔ 227) describe each other consistently,
   are component names spelled the same way across files?

The author did **not** run the test suites or evaluate the implementation;
only the ADR documents were inspected.

---

## Per-ADR findings table

| ADR | Title (truncated) | Status (header) | Words | Cross-refs OK? | Path-refs OK? | Findings |
|-----|-------------------|-----------------|-------|----------------|---------------|----------|
| 218 | History Sanitization Toolchain | Accepted | 1398 | YES | YES | LOW: lists `cos-deps-install.sh` as bare filename in narrative — fine as prose, no path resolution claim. |
| 219 | Work Ownership Liveness Preflight | Accepted | 529 | YES | n/a (no path refs) | LOW: short ADR with no "Source" footer — minor inconsistency vs siblings that all carry one. |
| 220 | Worktree Divergence Audit | Accepted | 1769 | YES | **PARTIAL** | MEDIUM: references `manifests/worktree-audit.yaml` in path table but the file does not exist on disk (only `lib/worktree_audit.py` ships). Either the manifest is missing from the implementation or the ADR over-states the deliverable. |
| 221 | Stash Refs by SHA, Not Position | Accepted | 1856 | YES | YES (after reading bare-name refs as prose) | LOW: lists `pre-agent-snapshot.sh` and `hooks/pre-agent-snapshot.sh` interchangeably — minor stylistic drift, both refer to the same file. Same for the test-file pair. |
| 222 | Pre-Agent Stash Deferred Until Launch Confirmed | Accepted | 2295 | YES | YES | LOW: same bare-name-vs-`hooks/`-prefixed-name drift as 221. The largest ADR in the batch by path-ref count (20+ paths) and prose is dense but readable. |
| 223 | Agent Lifecycle Reconstruction | Accepted | 614 | YES (incl. ADR-067) | YES | LOW: unusually short for the importance of the decision (changes the agent-launch substrate). The "Decision" section is concise but light on rollback story. |
| 224 | Shadow-State Snapshots Off-Repo | Accepted | 311 | YES | YES | MEDIUM: the shortest ADR in the batch (311 words) and the most templated. Reads as a thin wrapper that mostly defers to ADR-227. Consider merging into 227 or expanding the safety-boundary section. |
| 225 | Branch-Per-Task Mode | Accepted | 357 | YES | YES (both `lib/` and `packages/agent-lifecycle/lib/` copies referenced) | LOW: 357 words; very thin "Consequences" section. |
| 226 | Event-Sourced Session Bus | Accepted | 2934 | YES | YES | LOW: largest ADR in the batch; clear, well-sourced. The "load-bearing for ADR-227, 228, 230, 233" prose is a useful nav aid. No issues. |
| 227 | Shadow-Git Checkpoint Substrate | Accepted | 2025 | YES | YES | LOW: lists `multi-agent-orchestration-prior-art-2026-05-06.md` as a bare filename — should be the full `docs/03-PoCs/research/` path for symmetry with siblings. |
| 228 | Retry Contract + Cost Budget | (header conflict) | 2243 | YES | YES | **CRITICAL (C1)**: `## Status` block says `Tombstone` while body says `Accepted`. See top of report. |
| 229 | Tombstone | Tombstone | 312 | YES | YES | LOW: legitimate tombstone. Body cleanly explains the consolidation into 228. |
| 230 | Handoff Envelope + Cycle Dedup | Accepted | 2375 | YES | YES | LOW: cites "MAST 2025 paper" without a citation footer. Acceptable for an internal ADR; flag if external publication uses this. |
| 231 | MCP Server Surface | Accepted | 690 | YES | YES | LOW: dual references to `mcp-server/cos_mcp.py` and `packages/mcp-server/cos_mcp.py` — intentional (consumer ADR proves package export resolves to impl) but a casual reader may think it's a typo. Worth a one-line clarification. |
| 232 | Sandbox Adapter Tiers | Accepted | 431 | YES | YES | MEDIUM: thin (431 words) for an ADR that promises platform-conditional sandbox enforcement (Bubblewrap/Landlock/Seatbelt). Decision section reads more like a roadmap than a contract. |
| 233 | Cross-Session Agent-Team File IPC | Accepted | 660 | YES | YES | LOW: references `.claude/tasks/active-tasks.json` — harness-coupled path. Should call out that this is Claude-Code-specific IPC, not OS-canonical, to avoid misleading future harness adapters. |
| 234 | Approval Policies as Code | Accepted | 299 | YES | YES | MEDIUM: shortest non-tombstone in the batch (299 words). The "Decision" reads as a one-liner: adopt YAML, defer OPA. Acceptable but light. |
| 235 | Detached Agent Daemon | Accepted | 587 | YES | YES | LOW: references `done.json` and `heartbeat.json` as bare filenames; should specify the directory layout (`packages/agent-lifecycle/...`?). |
| 236 | Deferred Tool Loading + ToolSearch | Accepted | 405 | YES | YES | LOW: 405 words; "Consequences" section is two bullets. Functional but minimal. |
| 237 | Test Execution Efficiency Protocol | Accepted (Slice A only) | 457 | YES | (no critical paths to verify) | LOW: status carefully says "Slice A implemented" — honest scoping, good. |
| 238 | Tier 1-4 Follow-Up Bug Tracking | **Pending** | 905 | YES | YES | LOW: legitimately marked Pending — this is a registry of 5 open bugs, not a decision. Useful artifact for the public-readiness checklist. |

---

## Cross-document consistency observations

1. **Status-block style drifts.** ADRs 218 / 220 / 221 / 222 / 223 / 224 /
   226 / 227 / 228 use one style (`<!-- SCOPE: OS -->` followed by a
   bolded `**Status**:` line that *paraphrases* the `## Status` heading).
   ADRs 219 / 225 / 230–237 adopt the same template. ADR-228 is the
   only file where the two styles disagree (CRITICAL C1). All other
   files have the `## Status` heading and the bolded `**Status**:` line
   in agreement, even when the bolded line adds extra detail
   ("Slices A–E implemented").
2. **Date plausibility.** All dates fall in 2026-05-06 / 2026-05-07.
   Today (per the CLAUDE.md context line) is 2026-05-08. No future-dated
   decisions. ADR-218's status line claims tests were passing on
   2026-05-07 — plausible.
3. **`Related:` graph.** The cross-reference graph is dense but
   bidirectional in most cases:
   - 226 ↔ 227, 226 ↔ 228, 226 ↔ 230, 226 ↔ 233 — all pair correctly.
   - 223 ↔ 224, 223 ↔ 227 — paired.
   - 224 → 227 (depends on) — 227 lists 224 as "reserved", which is the
     correct reverse phrasing.
4. **ADR-067 sprinkling.** ADRs 223, 225, 229, 231–236, 238 all list
   `ADR-067` in their cross-refs. ADR-067 is the canonical ADR-template
   policy ADR; this is consistent.
5. **`session_bus` naming.** Referenced as `session_bus.py`,
   `lib/session_bus.py`, and `lib/event_wrap.py` — all three are
   real files. No inconsistency.
6. **`dispatch.py` ownership.** Modified by 226, 228, 232, 236. The
   ADRs do NOT collectively describe a single owner or sequencing
   contract for changes to `lib/dispatch.py` — minor risk if two
   future agents land conflicting edits. **MEDIUM** governance gap,
   not a CRITICAL one.

---

## AI-slop pattern check

The batch was reviewed for the typical AI-generated drift markers.
Findings:

- **Templated boilerplate**: ADR-224 (311 words) and ADR-234 (299 words)
  are the most template-shaped — both have a one-paragraph Context, a
  3-bullet Decision, and a perfunctory Consequences block. They are not
  *empty* (each names a real file shipped in the implementation), but
  they are the most likely candidates for "rewritten by hand before
  public release."
- **"Will be" / "should be" without owner**: scanned for these phrases
  across the batch. ADR-237 contains "must be" claims around test-tier
  selection but ties them to a manifest path; ADR-238 explicitly says
  fixes are "deferred to individual PRs that reference this ADR" —
  acceptable since 238 is a Pending bug registry. No other ADRs have
  un-owned future-tense decisions.
- **Decisions that don't actually decide**: ADR-232 comes closest. The
  Decision section is one paragraph naming three platform tiers but
  does not commit to a default-on / default-off posture. Recommend
  expanding before public.
- **Scope creep / multi-decision ADRs**: ADR-228 is explicitly a
  consolidation of two gaps (retry + cost budget). The ADR header calls
  this out and ADR-229 documents the decision to consolidate. **Not
  scope creep** — it's a documented merge.

---

## Severity counts

| Severity | Count | ADRs |
|----------|-------|------|
| CRITICAL | 1 | ADR-228 (Tombstone/Accepted contradiction) |
| HIGH | 0 | — |
| MEDIUM | 4 | ADR-220 (manifest missing), ADR-224 (thin wrapper), ADR-232 (under-decided), ADR-234 (under-decided); plus the cross-cutting `lib/dispatch.py` ownership gap |
| LOW | ~16 | stylistic / prose drift / bare-filename references — survivable |

### Cleanliness summary

| Bucket | Count | ADRs |
|--------|-------|------|
| Clean (no issues beyond stylistic LOW notes) | 14 | 218, 219, 221, 222, 223, 225, 226, 227, 229, 230, 231, 235, 236, 237, 238 — wait, that's 15. Recounting: 218, 219, 221, 222, 223, 225, 226, 227, 229, 230, 231, 235, 236, 237, 238 = **15** |
| Minor issues (MEDIUM, doc-only) | 4 | 220, 224, 232, 234 |
| Major issues | 0 | — |
| Blocker | 1 | 228 |

Total reviewed: **21 ADRs** (218–238 inclusive, including the tombstone 229).

---

## Recommendations before public launch

1. **MUST-FIX (1 commit)**: ADR-228 line 4 — change `Tombstone` to
   `Accepted`. One-character fix, blocks public release.
2. **SHOULD-FIX (small commits, not blockers)**:
   - ADR-220: ship `manifests/worktree-audit.yaml` *or* delete the path
     reference from the ADR.
   - ADR-224: expand the safety-boundary section, or merge into ADR-227.
   - ADR-232: commit to default sandbox tier per platform, or mark the
     ADR as "Accepted (Roadmap)" so readers know the contract is
     deferred.
   - ADR-234: same as 232 — declare the default policy bundle shipped
     in the implementation, or scope down the Decision section.
3. **NICE-TO-HAVE**: a short "modified files" sequencing note in either
   ADR-228 or a meta-ADR explaining that `lib/dispatch.py` is touched
   by four ADRs and the layered ordering is 226 → 228 → 232 → 236. Not
   required for public launch.

---

*Generated by the M3 ADR sweep agent. Read-only over `docs/02-Decisions/adrs/`. No
ADR files were modified by this run.*
