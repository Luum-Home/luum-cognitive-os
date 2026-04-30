# Primitive Gap Matrix — 2026-04

> Working report for the Cognitive OS primitive-by-primitive reality audit.

## Evidence Standard

A primitive is not considered real just because a file exists or a document describes it.

Evidence priority:

1. Runtime invocation path: settings, hook registration, command, router, or workflow.
2. Behavioral test that executes the primitive and checks side effects.
3. Runtime metric or artifact emitted by real usage.
4. Consumer that reads or acts on the primitive output.
5. Documentation, ADR, or roadmap mention.
6. File existence only.

## Classification

| Label | Meaning |
|---|---|
| `proven` | Wired, behaviorally tested or observed, emits/affects runtime state, and has a consumer or user-visible outcome. |
| `partial` | Implemented and partly wired, but missing tests, consumer, metrics, or clear user-visible closure. |
| `aspirational` | Present mainly as docs, ADRs, dead files, unregistered hooks, or uninvoked scripts. |
| `harmful-overhead` | Real behavior, but cost/noise/latency/confusion currently exceeds observed value. |

## Severity

| Severity | Definition | Default Action |
|---|---|---|
| `blocker` | Misleading product claim, unsafe behavior, or daily-workflow regression. | Fix or disable before more feature work. |
| `high` | Large DX/runtime cost, low proof, or core primitive gap. | Prioritize in reduction sprint. |
| `medium` | Real gap but bounded or optional. | Harden, demote, or document. |
| `low` | Cosmetic, stale, or low-risk cleanup. | Batch with nearby work. |

## Baseline Snapshot

Measured on 2026-04-30 from the self-hosting repo working tree.

| Primitive Family | Count / Signal | Initial Classification | Severity | Notes |
|---|---:|---|---|---|
| Hooks | 165 files; 80 registered; 76 registered + test-mentioned | partial | high | Hook wiring and latency directly affect daily DX. Needs row-level audit first. |
| Rules | 112 files | partial | high | Need verify actual `<!-- TIER: N -->` loader metadata and default/contextual load paths. |
| Skills | 143 skills; dogfood coverage 35/143 | partial | high | Catalog size outpaces behavioral proof and discoverability. |
| Agents/Subagents | 1 file in `agents/` + `.claude/agents/` | partial | medium | COS behavior versus harness-native delegation needs separation. |
| Memory | 9 memory-named files in lib/hooks/skills | partial | high | High value if closed-loop; risk if save/read paths are manual or disconnected. |
| MCP/Tools | 174 files mention MCP/mcp | partial | high | Likely mixed real integrations, optional services, docs-only references, and setup risk. |
| Config/Projection | 2 known projection/config script signals plus `cognitive-os.yaml` | partial | high | Portability claims depend on this being real and tested across drivers. |
| Metrics/Observability | 94 JSONL streams; 72 non-empty; 22 empty | partial | medium | Need separate decision-grade metrics from dead/noisy streams. |
| Tests/Quality Gates | 538 `test_*.py` files | partial | high | Volume is high; behavior quality must be audited to avoid test theater. |
| Docs/ADRs | 371 docs; 58 ADRs | partial | high | Product claims need proof mapping and stale claim cleanup. |

## Hook Findings

_Status: not yet row-audited._

Initial known risks:

- 89 hook files are not both registered and test-mentioned.
- Some hooks are test-mentioned but not registered, which can create false confidence.
- Hook timing evidence exists and shows p95 cost above 1.6 seconds with max above 13 seconds.
- The next audit pass must map hook → lifecycle → metric stream → test type → consumer → action.

## Skill Findings

_Status: not yet row-audited._

Initial known risks:

- Dogfood reports only 35/143 covered by its skill coverage heuristic.
- Broad mention heuristic finds 91/143 mentioned in tests/settings, meaning many mentions likely are not behavioral proof.
- The next audit pass must cluster skills by purpose and identify duplicates, manual-only skills, and hidden-maintainer-knowledge skills.

## Rule Findings

_Status: not yet row-audited._

Initial known risks:

- The loader contract uses `<!-- TIER: N -->`, not YAML `tier:` metadata.
- Tier/load reality must be verified from actual parser and compact index behavior.
- The next audit pass must distinguish governance rules that are enforced from advisory prose.

## Open Work Queue

1. Run hook row-level audit and fill hook table.
2. Run skill row-level audit and cluster duplicate/low-proof skills.
3. Run rule tier/load audit using `lib/ref_key_loader.py` semantics.
4. Run metrics ownership audit for all JSONL streams.
5. Run test-quality audit and map theater tests to primitive families.

## Periodic Automation

A weekly scheduled workflow now runs the family-level primitive gap snapshot:

- workflow: `.github/workflows/primitive-gap-audit.yml`
- script: `scripts/primitive_gap_snapshot.py`
- JSON artifact: `primitive-gap-snapshot.json`
- latest Markdown report: `docs/reports/primitive-gap-latest.md`
- trend metric: `docs/reports/primitive-gap-history.jsonl` in CI, or `.cognitive-os/metrics/primitive-gap-snapshot.jsonl` for local runs

The workflow intentionally does not fail on high risk yet. The current baseline is high-risk, so failing the scheduled job would create noise instead of useful escalation. Once the family-level baseline is cleaned up, enable `--fail-high-risk` or a narrower regression threshold for blocker/high deltas.

## Growth Prevention Gate

The periodic automation is now preventive, not just observational. `scripts/primitive_gap_snapshot.py --fail-on-regression` compares the current snapshot with the previous trend entry and exits non-zero when new growth worsens the primitive gap profile.

Regression conditions:

- overall risk worsens;
- a family severity worsens;
- a family loses proven signal;
- a family gains aspirational signal;
- a family unproven surface count grows (`total - proven_signal`);
- hook p95 latency grows beyond `--latency-regression-ms` (default 500 ms).

This intentionally permits the current high-risk baseline to exist while blocking additional unproven growth.

## Documentation Duplicate Guard

Existing protection before this audit:

- `hooks/reinvention-check.sh` is registered as a PreToolUse Agent hook and emits `reinvention-checks.jsonl`.
- It is advisory and primarily detects code/file creation around `lib/`, `hooks/`, scripts, and plugin source matches.
- It does not fully prevent documentation duplication or ensure agents update previous docs instead of creating parallel docs.

Added protection:

- script: `scripts/docs_duplicate_audit.py`
- tests: `tests/unit/test_docs_duplicate_audit.py`
- baseline: `docs/reports/docs-duplicate-baseline.json`
- latest JSON: `docs/reports/docs-duplicate-latest.json`
- latest Markdown: `docs/reports/docs-duplicate-latest.md`
- CI behavior: weekly workflow fails on new near-duplicate Markdown pairs versus baseline.

Current scan: 364 docs scanned, 0 duplicate pairs at threshold 0.72.

Pre-write guard added:

- hook: `hooks/project-docs-convention.sh`
- trigger: PreToolUse `Edit|Write` docs Markdown target that does not exist yet
- behavior: soft-warns agents to search/update existing docs before creating a new one and lists candidate docs by filename/content terms
- strict opt-in: `COS_STRICT_DOCS_REINVENTION=1` returns exit 2 for new docs creation
- tests: `tests/unit/test_project_docs_writers.py`

## Provenance and ADR Coordination Guards

Two live DX regressions came from parallel sessions producing indistinguishable
commits and racing for ADR numbers. These are now treated as coordination
primitives with behavioral proof.

Commit provenance:

- hook: `.githooks/prepare-commit-msg`
- script: `scripts/commit_provenance.py`
- behavior: appends `X-COS-Origin`, `X-COS-Session`, and `X-COS-Harness`
  trailers to local commit messages, using session/harness environment when
  available and safe `unknown` fallbacks otherwise
- tests: `tests/unit/test_commit_provenance.py`
- proof standard: includes a real temporary git repository commit with
  `core.hooksPath=.githooks`, then verifies trailers in `git log`

ADR reservation:

- script: `scripts/adr_reserve.py`
- state: `.cognitive-os/locks/adr-reservations.json`
- lock: `.cognitive-os/locks/adr-reservations.json.lock`
- behavior: reserves the next monotonic ADR number with title, slug,
  session, owner, expiry, and target path metadata
- tests: `tests/unit/test_adr_reserve.py`
- proof standard: includes concurrent subprocess reservations to verify
  cross-process uniqueness under the file lock

Remaining gap:

- ADR file creation now gets a PreToolUse warning/block path when the target ADR
  number has no active reservation (`COS_STRICT_ADR_RESERVATION=1` to block).
- Expired ADR reservations can be listed and cleaned up with
  `scripts/adr_reserve.py --list --json` and
  `scripts/adr_reserve.py --cleanup-expired --json`.
- `lib/adr_detector.py` now writes generated drafts under canonical `docs/adrs/`
  and reserves the ADR number before writing.

## Row-Level Primitive Audit

Family-level counts were useful but too coarse. The row-level audit now emits a
concrete keep/harden/demote/delete queue for hooks, skills, rules, and metrics.

- script: `scripts/primitive_row_audit.py`
- latest JSON: `docs/reports/primitive-row-audit-latest.json`
- latest Markdown: `docs/reports/primitive-row-audit-latest.md`
- tests: `tests/unit/test_primitive_row_audit.py`
- current rows: 639

The audit maps:

- hook file → registered lifecycle events → test mention → metric emission
- skill file → frontmatter/trigger → runtime reference → test mention
- rule file → compact-index/load reference → `<!-- TIER: N -->` metadata → test mention
- metric stream → size/non-empty signal → producer/consumer mentions

## Claim-to-Proof and Reduction Backlog

Product claims are now audited separately from primitive files.

- claim audit script: `scripts/claim_proof_audit.py`
- latest claim JSON: `docs/reports/claim-proof-latest.json`
- latest claim Markdown: `docs/reports/claim-proof-latest.md`
- reduction backlog script: `scripts/reduction_backlog.py`
- latest backlog JSON: `docs/reports/reduction-backlog-latest.json`
- latest backlog Markdown: `docs/reports/reduction-backlog-latest.md`
- tests: `tests/unit/test_claim_proof_and_reduction.py`

Current outputs:

- claim rows: 193
- unmapped claim rows: 0 (`--fail-unmapped` now blocks regressions)
- reduction backlog items: 0

Reduction triage notes:

- P1 `delete-or-wire` hook rows are now resolved by distinguishing dormant
  behavior-tested hooks, projected profile hooks, and optional package aliases
  from truly dead surface.
- P1 registered-hook hardening is covered by behavior tests for
  `dequeue-notify.sh`, `memory-prefetch.sh`, `profile-drift-autoapply.sh`, and
  `skill-frontmatter-validator.sh`.
- P2 weak claims are resolved by demoting overconfident product language and
  filtering code/config fragments that are not product claims.
- P2 optional/dormant primitives are recorded in
  `manifests/reduction-demotions.json`.
- Skill/rule runtime contracts are covered by
  `tests/unit/test_skill_and_rule_runtime_contracts.py`.

The weekly primitive gap workflow now runs the row audit, claim-to-proof audit,
and reduction backlog generator after the family-level snapshot and duplicate
docs audit. It also uploads and commits the generated row/claim/backlog reports.

## Alternatives Comparison

Evidence-bound alternatives comparison now lives at:

- `docs/reports/alternatives-comparison-2026-04.md`

It explicitly marks where COS wins, where it loses, and where it should stop
presenting aspirational behavior as current product behavior.
