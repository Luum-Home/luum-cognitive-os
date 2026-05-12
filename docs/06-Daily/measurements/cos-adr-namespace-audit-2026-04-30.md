# COS ADR Namespace Fragmentation Audit

**Date**: 2026-04-30
**Type**: Read-only investigation
**Trigger**: Orchestrator drafted ADR-002 stub before discovering the real ADR-002 in `docs/04-Concepts/architecture/adrs/`

---

## A. Inventory by Directory

### `docs/02-Decisions/adrs/` — Canonical (ADR-027+)

**61 files**, date range: 2026-04-17 to 2026-04-30 (reconstruction phase and beyond).

Naming convention: `ADR-NNN[-topic].md` with optional letter suffix for addenda (`ADR-027a`, `ADR-028b`, etc.).

Selected entries (all Accepted unless noted):

| File | Title | Status |
|------|-------|--------|
| ADR-027.md | SO Slimming — Test Strategy, Context Overhead | Accepted |
| ADR-028.md | SO Reliability & Observability Framework | Accepted |
| ADR-033.md | Harness-Agnostic Event Capture | Accepted |
| ADR-049.md | LLM Gateway Selection and Overflow Providers | Accepted |
| ADR-054.md | Project Docs Convention | Accepted |
| ADR-066.md | Polyglot Language Boundaries | Accepted |
| ADR-071.md | Engram Lifecycle Evolution | Accepted |
| ADR-072.md | Test Lane Taxonomy | Accepted |
| ADR-082.md | Plan Location Convention | Accepted |
| ADR-084.md | Headless and Clustered Runtime Shape | Proposed (retroactive) |

### `docs/04-Concepts/architecture/adrs/` — Legacy (ADR-001, ADR-002, ADR-006 to ADR-027)

**26 files** (including README and 026a-decisions.md addendum), date range: 2026-03-23 to 2026-04-28.

Naming convention: lowercase `NNN-topic.md` for ADR-006 through ADR-027; `ADR-NNN-topic.md` (uppercase) for ADR-001 and ADR-002 which were filed later.

| File | Title | Status |
|------|-------|--------|
| ADR-001-abc-parallel-... | A+B+C parallel — dedup, fix broken infra, add global-verify | Draft |
| ADR-002-docker-pip-... | docker-pip localhost envs + targeted_test_resolver + redis dep | Draft |
| 006-agpl-license-compliance.md | AGPL License Compliance -- Replace Redis and MinIO | Accepted |
| 012-prompt-driven-governance.md | Prompt-Driven Governance -- Declarative Hook Logic | Accepted |
| 021-vendor-agnostic-with-adapters.md | Vendor-Agnostic State with Provider Adapters | Accepted |
| 027-headless-clustered-runtime-direction.md | Headless and Clustered Runtime Direction | Accepted |

### `docs/04-Concepts/architecture/cos-dispatch/adrs/` — Local subsystem namespace

**12 files** (including README), all Accepted. Date range: 2026-04-16.

Naming convention: lowercase `NNN-topic.md` (no `ADR-` prefix). Numbers 001–011 are local to the cos-dispatch module.

| File | Title |
|------|-------|
| 001-reuse-klaudiush-predicates.md | Reuse klaudiush Predicate System |
| 002-transformer-separate-interface.md | Transformer as Separate Interface from Validator |
| 006-override-result-type.md | `override` Result Type in Executions |

### `docs/04-Concepts/architecture/harness-adoption-gap/` — Local subsystem namespace

**3 ADR files** (no README). Format: `ADR-NNN-topic.md`. These use a local 3-number sequence scoped to the harness-adoption-gap work stream.

| File | Title | Status |
|------|-------|--------|
| ADR-001-harness-skills-sync-path.md | Harness Skills Sync Path | Accepted |
| ADR-002-simplify-profiles.md | Simplify Install Profiles | Accepted |
| ADR-003-agent-git-safety.md | Agent Git Operations Safety | Accepted |

**Grand total: 97 ADR files across 4 locations.**

---

## B. Collisions

The following ADR numbers exist in more than one namespace. All are within different directories, so they represent disambiguation failures rather than file duplicates — but any bare citation `ADR-NNN` is ambiguous.

| Number | `docs/02-Decisions/adrs/` | `docs/04-Concepts/architecture/adrs/` | `docs/04-Concepts/architecture/cos-dispatch/adrs/` | `docs/04-Concepts/architecture/harness-adoption-gap/` |
|--------|-------------|--------------------------|----------------------------------------|------------------------------------------|
| ADR-001 | *(none)* | ADR-001 (draft: parallel dedup + infra fix) | 001 (reuse klaudiush predicates) | ADR-001 (harness skills sync path) |
| ADR-002 | *(none)* | ADR-002 (draft: docker-pip + test resolver) | 002 (transformer interface) | ADR-002 (simplify profiles) |
| ADR-003 | *(none)* | *(none)* | 003 (sqlite over jsonl) | ADR-003 (agent git safety) |
| ADR-006 | *(none)* | 006 (AGPL compliance) | 006 (override result type) | *(none)* |
| ADR-007 | *(none)* | 007 (cognitive OS rebrand) | 007 (eager failure sequences) | *(none)* |
| ADR-008 | *(none)* | 008 (multi-tool support) | 008 (review subcommand) | *(none)* |
| ADR-009 | *(none)* | 009 (package architecture) | 009 (go-only auto-generation) | *(none)* |
| ADR-010 | *(none)* | 010 (hook architecture v2) | 010 (real-behavior tests) | *(none)* |
| ADR-011 | *(none)* | 011 (dual gateway) | 011 (phase 5 ordering) | *(none)* |
| **ADR-027** | **ADR-027 (SO Slimming — ACCEPTED)** | **027 (headless runtime direction — Accepted)** | *(none)* | *(none)* |

**Collision summary**: 10 number collisions. ADR-027 is the only collision in the main project namespace (`docs/02-Decisions/adrs/` vs `docs/04-Concepts/architecture/adrs/`). ADR-001 through ADR-011 have triple or double collisions but these are explainable: cos-dispatch and harness-adoption-gap use isolated local namespaces.

---

## C. Cross-Reference Resolution

All production citations use the `ADR-NNN` short form. The startup hook indexes only `docs/02-Decisions/adrs/` (see Section E), so tooling resolves to that directory. Citations to numbers < 027 resolve to `docs/04-Concepts/architecture/adrs/` by convention only — the convention is documented in `docs/02-Decisions/adrs/README.md` but not enforced by any tool.

| Source file | Citation | Resolves cleanly? | Notes |
|------------|----------|-------------------|-------|
| `install.sh:4,43,106,116,117,122,251,428` | ADR-002 | AMBIGUOUS | 3 ADR-002s exist. Context (profile collapse) points to `harness-adoption-gap/ADR-002-simplify-profiles.md`, but an early `docs/04-Concepts/architecture/adrs/ADR-002-docker-pip-...` draft also covers similar territory. |
| `cognitive-os.yaml:538,541` | ADR-002 | AMBIGUOUS | Same ambiguity as install.sh |
| `docs/02-Decisions/adrs/ADR-027.md:215` | ADR-028 | Resolves cleanly | Lives in `docs/02-Decisions/adrs/` |
| `docs/02-Decisions/adrs/ADR-027a.md:5,6` | ADR-027 | Resolves cleanly | Same dir |
| `AGENTS.md:70` | ADR-072 | Resolves cleanly | Explicit full path given |
| `rules/startup-protocol.md` | *(references `docs/02-Decisions/adrs/`)* | Resolves cleanly | Full path cited |
| `rules/lane-taxonomy.md` | ADR-072 | Resolves cleanly | Full path given |
| `rules/research-first-protocol.md` | *(templates at `docs/02-Decisions/adrs/`)* | Resolves cleanly | Full path |
| `.github/workflows/go-quality.yml:4` | ADR-066 | Resolves cleanly | No path, but 066 only in `docs/02-Decisions/adrs/` |
| `docs/00-MOCs/entrypoints/HOW-TO-USE-COS.md:170` | ADR-021 | AMBIGUOUS | ADR-021 lives in `docs/04-Concepts/architecture/adrs/`, no path given |
| `docs/00-MOCs/entrypoints/README.md:34` | ADR-081 | Resolves cleanly | Full path given |
| `cognitive-os.yaml:373` | ADR-075 | Resolves cleanly | Only in `docs/02-Decisions/adrs/` |
| `cognitive-os.yaml:452,453` | ADR-058 | Resolves cleanly | Only in `docs/02-Decisions/adrs/` |
| `docker-compose.cognitive-os.yml` | ADR-049,058,060,042 | Resolves cleanly | All in `docs/02-Decisions/adrs/` (>= 027) |
| `docs/04-Concepts/architecture/stabilization-roadmap.md` | *(references `docs/04-Concepts/architecture/adrs/`)* | Resolves cleanly | Full path given |
| `docs/04-Concepts/architecture/why-skills-and-rules-became-claude-centered.md` | ADR-008, ADR-015 | Resolves cleanly | Explicit `docs/04-Concepts/architecture/adrs/` path |
| `docs/05-Methodology/root/prompt-driven-governance.md` | ADR-012 | AMBIGUOUS | No path; 012 only in `docs/04-Concepts/architecture/adrs/`, but not obvious to discovery tools |
| `tests/unit/test_efficiency_optimization.py:88` | ADR-002 | AMBIGUOUS | Same 3-way ambiguity |
| `docs/04-Concepts/architecture/adrs/026a-decisions.md` | *(parent ADR)* | Resolves cleanly | Explicit relative path |
| `docs/02-Decisions/adrs/ADR-028.md` | ADR-027 | Resolves cleanly | Same dir |

**Summary**: 4 of the top 20 real-code citations are ambiguous. All ambiguous ones involve low-numbered ADRs (001–021) where the canonical file is in `docs/04-Concepts/architecture/adrs/` but the citation site omits the path. The `ADR-002` citation in `install.sh` is the highest-risk because 3 different ADR-002 files exist across 3 namespaces.

---

## D. Convention Drift

### cos-dispatch namespace
`docs/04-Concepts/architecture/cos-dispatch/adrs/` was created as an isolated decision log for the `cos-dispatch` Go subsystem (the vendor-agnostic hook dispatcher). Its local-only numbering (`001`–`011`, no `ADR-` prefix) is intentional — these are internal design decisions for a component, not project-level architecture records. The README is explicit: "Records are immutable once accepted; supersession is recorded via a new ADR that references the old one." There is no cross-reference with project ADR numbers. The convention is appropriate for a subsystem with its own release lifecycle.

### harness-adoption-gap namespace
`docs/04-Concepts/architecture/harness-adoption-gap/` is a focused work-stream directory (the harness adoption gap investigation from 2026-04-16). Its 3 ADR files use `ADR-NNN-topic.md` format (same as the main project) but start at 001 — this is pure local sequencing. No README exists in this directory, and these 3 files were never registered with the project ADR index. They are de facto orphans.

### architecture/adrs ADR-001, ADR-002 anomaly
These two files (`ADR-001-abc-parallel-...`, `ADR-002-docker-pip-...`) use the uppercase `ADR-NNN` prefix unlike every other file in `docs/04-Concepts/architecture/adrs/` which uses lowercase `NNN-topic.md`. Both have status `Draft`. They appear to have been filed retroactively in the wrong location, after the `docs/02-Decisions/adrs/` directory was already established as canonical. They represent internal project work for the same numbered slots as harness-adoption-gap ADR-001/ADR-002.

---

## E. Tooling Gap

### What the startup hook indexes

From `hooks/session-startup-protocol.sh` line 88:
```sh
ADRS_DIR="$PROJECT_DIR/docs/02-Decisions/adrs"
ADR_COUNT=$(_count_md "$ADRS_DIR")
```

Only `docs/02-Decisions/adrs/` is counted and cross-referenced. The hook also references `docs/04-Concepts/architecture/plans/` for plans correlation, but does not scan:

- `docs/04-Concepts/architecture/adrs/` — **NOT indexed** (26 files, ADR-006 to ADR-027, core historical decisions)
- `docs/04-Concepts/architecture/cos-dispatch/adrs/` — **NOT indexed** (local subsystem; acceptable by design)
- `docs/04-Concepts/architecture/harness-adoption-gap/` — **NOT indexed** (orphaned, no README)

### Impact
Any tool that calls `_count_md "$ADRS_DIR"` or iterates `docs/02-Decisions/adrs/` to check for ADR existence will produce false negatives for ADR-006 through ADR-026. This is what caused the "draft ADR-002 stub" incident — the orchestrator saw no ADR-002 in `docs/02-Decisions/adrs/` and prepared to create one.

No written convention in `rules/`, `AGENTS.md`, `CONTRIBUTING.md`, or `.cognitive-os/` specifies which directories constitute the ADR namespace. The `docs/02-Decisions/adrs/README.md` documents the split rationale but is not consulted by any tool.

---

## F. Recommendation

**Option A (Consolidate to `docs/02-Decisions/adrs/`)**: Migrate all `docs/04-Concepts/architecture/adrs/` files (ADR-006 to ADR-027) into `docs/02-Decisions/adrs/` with renaming to uppercase `ADR-NNN-topic.md` format. Update `docs/04-Concepts/architecture/adrs/README.md` to say "MOVED — see `docs/02-Decisions/adrs/`". Update startup hook to scan only `docs/02-Decisions/adrs/`.

**Option B (Keep namespaces, update tooling)**: Expand the startup hook to scan both `docs/02-Decisions/adrs/` and `docs/04-Concepts/architecture/adrs/`. Add a merged index. Keep cos-dispatch and harness-gap as isolated local namespaces.

**Option C (Hybrid)**: Keep the split (A for new, legacy for old) but make the startup hook namespace-aware and generate a unified `docs/02-Decisions/adrs/INDEX.md` that includes cross-namespace entries with full paths.

### Recommendation: Option A (consolidate)

Rationale mirroring ADR-082 (plans consolidation):

1. **The problem is identical to the plans split** — two directories, one canonical, one legacy, both tracked but only one indexed by tooling. ADR-082 chose Option A for plans and it worked.
2. **The `docs/04-Concepts/architecture/adrs/README.md` already points to `docs/02-Decisions/adrs/` as canonical** and acknowledges that ADR-027+ live there. Consolidation just completes what was started.
3. **26 files is a manageable migration** — rename files, update relative links in `docs/04-Concepts/architecture/` documents that reference them by relative path, add redirecting README stubs.
4. **cos-dispatch and harness-gap are NOT candidates for consolidation** — they are local namespaces for components. They should remain isolated and their ADR numbers documented as non-project-global.
5. **Only one rule needs writing**: "All project-level ADRs live in `docs/02-Decisions/adrs/`. Component subsystem ADRs live in `{component}/adrs/` with local numbering. Never use bare `ADR-NNN` citations; always use full paths for ADRs in `docs/04-Concepts/architecture/`."

---

## G. Top 5 Highest-Risk References to Fix First

| Rank | Location | Citation | Risk |
|------|----------|----------|------|
| 1 | `install.sh:4,43,106,116,117,122,251,428` | `ADR-002` (bare) | Critical installer code; 3 different ADR-002 files exist; currently resolves by reader inference only. Wrong interpretation could justify wrong behavior. |
| 2 | `cognitive-os.yaml:538,541` | `ADR-002` (bare) | Core config file; same triple-ambiguity as install.sh; consulted at every session start. |
| 3 | `hooks/session-startup-protocol.sh:88` | `ADRS_DIR="$PROJECT_DIR/docs/02-Decisions/adrs"` | Missing `docs/04-Concepts/architecture/adrs/`; this is the root cause of the "ghost ADR" incident. A one-line addition of a second scan path would prevent recurrence. |
| 4 | `docs/05-Methodology/root/prompt-driven-governance.md` | `ADR-012` (bare) | Referenced document lives in `docs/04-Concepts/architecture/adrs/012-prompt-driven-governance.md`; no path given; a new ADR-012 in `docs/02-Decisions/adrs/` would shadow it silently. |
| 5 | `docs/00-MOCs/entrypoints/HOW-TO-USE-COS.md:170` | `ADR-021` (bare) | Same pattern — ADR-021 lives in `docs/04-Concepts/architecture/adrs/`; bare citation is ambiguous now that the main sequence is at ADR-084 and growing. |
