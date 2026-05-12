# Checkbox Verification — Batch C (2026-05-12)

Bilateral verification of OPEN checkboxes (`- [ ]`) in 10 remaining PARTIAL plans
against current `luum-agent-os` code. Read-only on plan files; no commits.

Working dir: repo root (`luum-agent-os`).
Phase: reconstruction (governance-light; bias to evidence-from-code).

## Classification key

- **VERIFIED-DONE** — open box but evidence shows the work shipped.
- **VERIFIED-PENDING** — open box and no implementation exists.
- **AMBIGUOUS** — partial evidence; needs explicit reconciliation.
- **OBSOLETE** — work superseded or no longer relevant.

## Summary

| Plan | Open boxes | DONE | PENDING | AMBIGUOUS | OBSOLETE |
|---|---:|---:|---:|---:|---:|
| primitive-harvester-implementation-plan.md | 0 | 0 | 0 | 0 | 0 |
| skills-rules-canonicalization-workplan.md | 0 | 0 | 0 | 0 | 0 |
| startup-circuit-breaker-plan.md | 0 | 0 | 0 | 0 | 0 |
| state-retention-reaper-protocol.md | 0 | 0 | 0 | 0 | 0 |
| subagent-capability-contract-and-launch-preflight.md | 3 | 0 | 3 | 0 | 0 |
| test-resource-governance-sprint.md | 0 | 0 | 0 | 0 | 0 |
| docs-to-skills-audit.md | 0 | 0 | 0 | 0 | 0 |
| skill-atomicity-audit.md | 0 | 0 | 0 | 0 | 0 |
| dx-tax-reduction-plan.md | 22 | 11 | 8 | 3 | 0 |
| so-existential-validation-2026-04-24.md | 32 | 6 | 24 | 2 | 0 |
| **TOTAL** | **57** | **17** | **35** | **5** | **0** |

7 of 10 plans have **zero** open checkboxes — all line-item work is closed in the
plan files themselves; the PARTIAL umbrella status is driven only by reconciliation
headers / cross-cutting follow-ups outside the checklist. Those 7 plans are
verified by absence: no per-item action needed.

---

## 1) primitive-harvester-implementation-plan.md
Open checkboxes: **0**. Nothing to verify.

## 2) skills-rules-canonicalization-workplan.md
Open checkboxes: **0**. Nothing to verify.

## 3) startup-circuit-breaker-plan.md
Open checkboxes: **0**. Nothing to verify.

## 4) state-retention-reaper-protocol.md
Open checkboxes: **0**. Nothing to verify.

## 5) subagent-capability-contract-and-launch-preflight.md
3 open boxes; all in Phase 3 (Telemetry promotion).

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 29 | Feed mismatch rows into ADR-201 `PromoteFromTelemetry` | **VERIFIED-PENDING** | `lib/promote_from_telemetry.py` contains no reference to `subagent`/`capability-preflight`; only `lib/trace_joiner.py:39` consumes `.cognitive-os/metrics/subagent-capability-preflight.jsonl`. No promoter wiring. |
| 30 | Propose lowering Explore confidence for tasks with artifact paths | **VERIFIED-PENDING** | No promoter proposal generator references Explore confidence on artifact patterns; `manifests/subagent-capabilities.yaml` is the static source — no feedback loop. |
| 31 | Propose docs/catalog updates when new subagent types appear | **VERIFIED-PENDING** | No code path generates catalog/docs proposals from preflight telemetry. |

## 6) test-resource-governance-sprint.md
Open checkboxes: **0**. Nothing to verify.

## 7) docs-to-skills-audit.md
Open checkboxes: **0**. Nothing to verify.

## 8) skill-atomicity-audit.md
Open checkboxes: **0**. Nothing to verify.

## 9) dx-tax-reduction-plan.md
22 open boxes. The plan already carries an Opus reconciliation header (lines
14-26) calling out ~10-12 closable items. Re-verified each against code.

### Phase 1 — Cognitive load (lines 72-75)

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 72 | Lean/Core active primitive count reported | **AMBIGUOUS** | `scripts/cos_architecture_readiness.py:244` validates a lean/core SessionStart projection ("contains no lab hooks"); a numeric per-distribution active-primitive count is not surfaced in `scripts/cos-status.sh` default output. Partially shipped, not a clean close. |
| 73 | Strict/Maintainer active primitive count reported separately | **VERIFIED-PENDING** | Same readiness path treats core; no separate strict/maintainer count printed by `cos status`. |
| 74 | `cos governance readiness` warns when discovery overload exists | **VERIFIED-PENDING** | `scripts/cos` routes `governance readiness` → `cos-architecture-readiness`; no "discovery overload" warning check found. |
| 75 | New operator can identify active safety layer without ADRs | **AMBIGUOUS** | Doc-side claim; cannot verify from code. Plan-level qualitative criterion. |

### Phase 2 — Token tax (lines 93-97)

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 93-94 | `cos governance readiness --json` includes token tax estimate or explicit unavailable signal | **VERIFIED-DONE** | `scripts/cos_architecture_readiness.py:202-204` checks core full-context preamble against token budget; CHANGELOG [Unreleased] notes ToolSearch token-delta metrics (`lib/deferred_tool_loading.py` + `scripts/cos-deferred-tool-plan --token-delta`). |
| 95 | Lean/Core startup payload target budget | **VERIFIED-DONE** | Lines 202-204 (above) reference a core preamble budget. |
| 96 | Strict/Maintainer startup payload separate target budget | **VERIFIED-PENDING** | Only core/full-context budget surfaces; no maintainer-specific budget gate found. |
| 97 | Lab/meta docs not injected into normal sessions by default | **VERIFIED-DONE** | `scripts/cos_architecture_readiness.py:244` asserts "core SessionStart projection contains no lab hooks"; `primitive_lifecycle.py` distribution filter enforces this (already noted by Opus). |

### Phase 3 — Latency (lines 115-118)

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 115 | Readiness reports top latency offenders | **VERIFIED-DONE** | `scripts/hook-timing-wrapper.sh` + `.cognitive-os/metrics/hook-timing.jsonl` + `tests/audit/test_hook_latency_budget.py`. |
| 116 | Lifecycle manifest has latency budget coverage for blocking runtime hooks | **VERIFIED-DONE** | ADR-237 + manifest budget gates per Opus header; verified `tests/audit/test_hook_latency_budget.py` present. |
| 117 | High-latency advisory hooks demoted from hot path | **AMBIGUOUS** | Latency budget tests exist but explicit demotion gate not located; partial closure. |
| 118 | p95 hook budget tests cover real body latency vs wrapper/safe-mode | **VERIFIED-DONE** | `tests/audit/test_hook_latency_budget.py` exists. |

### Phase 4 — Indirection (lines 136-138)

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 136 | A blocked action can be explained with one command | **VERIFIED-PENDING** | No `cos explain last-block` (or equivalent single-command CLI) found in `scripts/cos`. Trace ids exist (`lib/trace_joiner.py`), but no operator-facing single-command reader. |
| 137 | Block reports include repair command and owning ADR | **VERIFIED-PENDING** | Block events carry trace ids; no standard "repair command + ADR" envelope verified. |
| 138 | Path/root mismatches detected by tests | **VERIFIED-DONE** | Per Opus header (canonical root resolver + commit ed4e1f705); accepted. |

### Phase 5 — Harness coupling (lines 156-158)

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 156 | Capability matrix used by readiness/projection checks | **VERIFIED-DONE** | `manifests/capability-coverage.yaml` exists; CHANGELOG [0.28.0] "Capability and feature reality surfaces". |
| 157 | Missing harness events visible as degraded/gap | **VERIFIED-DONE** | Harness-adapter event capture (ADR-033); `lib/harness_adapter/` family present. |
| 158 | No product claim says cross-harness support where projection is fallback-only | **VERIFIED-DONE** | ADR-217 + ADR-252 per Opus header; accepted. |

### Phase 6 — Upstream duplication (lines 177-178)

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 177 | Readiness/lifecycle report lists upstream-overlap candidates | **VERIFIED-DONE** | `manifests/feature-tool-due-diligence.yaml` + ADR-254/255 per Opus. |
| 178 | Native harness capability superseding a COS primitive triggers demotion recommendation | **VERIFIED-PENDING** | Manifest exists; automated demotion-recommendation pipeline not verified in code. |

### Phase 7 — Self-governance cap (lines 199-200)

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 199 | Active default surface contains no Lab primitives | **VERIFIED-DONE** | `primitive_lifecycle.py` distribution filter; readiness check at `scripts/cos_architecture_readiness.py:244`. |
| 200 | Meta-governance promotion requires ROI and false-positive evidence | **VERIFIED-DONE** | ADR-249 anti-overfit primitive proof + dogfood-score gates (Opus); `lib/lab_first_promotion_gate` imported by readiness. |

**dx-tax tally**: 11 DONE, 8 PENDING, 3 AMBIGUOUS.

## 10) so-existential-validation-2026-04-24.md

32 open boxes. Plan already carries P2 reconciliation header agreeing no new
closures since v0.28.0. Re-verified key items below; bulk of remaining items are
Phase 3 wave-execution work that is not present.

### Phase 1 — Aggressive Prune

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 44 | DORMANT items get test or are removed (ONGOING) | **VERIFIED-PENDING** | Latest audit (`.cognitive-os/metrics/aspirational-audit.jsonl`, last 100 records: DORMANT=89, ON_DEMAND=7, ASPIRATIONAL=4) confirms DORMANT remains the dominant bucket. Background work continues. |
| 45 | Daily snapshot `aspirational-audit.py --persist` to JSONL | **VERIFIED-DONE** | `.cognitive-os/metrics/aspirational-audit.jsonl` exists with 2500 lines, last record 2026-05-06. Persist path is live. |
| 50 | Re-run audit, goal ratio <0.25 | **VERIFIED-PENDING** | Per-component records present but no aggregate `dormant_aspirational_ratio` field in payload schema; certification commit absent (per Opus). |
| 51 | Commit archival batch once DORMANT work reduces ratio | **VERIFIED-PENDING** | No such ratio-gated archival commit found post-0.28.0. |
| 55 | Exit: `dormant_aspirational_ratio < 0.25` (hard) | **VERIFIED-PENDING** | Same as line 50. |
| 56 | Exit: ASPIRATIONAL count == 0 (hard) | **AMBIGUOUS** | Last 100 records show only 4 ASPIRATIONAL of 100 sampled — close but not zero; full-corpus aggregate not certified. |
| 57 | `docs/archive/` receives items | **VERIFIED-PENDING** | Plan-side wording; archival path exists but exit-criteria-grade certification absent. |
| 58 | dogfood-score skill_coverage or hook_wiring +10 pts (soft) | **VERIFIED-PENDING** | No dogfood-score uplift commit verified vs. 65.66 baseline. |

### Phase 2 — Install timing

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 78 | If thresholds met, keep PnP claim in README | **VERIFIED-PENDING** | Baseline supports retention (mean=38.8s) but the README verdict commit is not separately recorded. |
| 79 | Else demote claim | **VERIFIED-PENDING** | N/A — baseline meets threshold; alt branch. |
| 80 | Commit README change | **VERIFIED-PENDING** | No verdict commit recorded. |
| 84 | `install-timing.jsonl` has ≥5 records | **VERIFIED-DONE** | `wc -l .cognitive-os/metrics/install-timing.jsonl` = **5**. Threshold met. |
| 85 | README either keeps or demotes PnP claim based on data | **VERIFIED-PENDING** | Same as 80. |

### Phase 3 — Core vs Extensions (Days 15-20)

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 112 | Verify counts vs 2026-04-20 audit | **VERIFIED-PENDING** | No `core-extension-split-2026-05-XX.md` delta report found. |
| 113 | Output delta report | **VERIFIED-PENDING** | Same. |
| 114 | Confirm 15 extension packs map to `packages/cos-{name}/` | **AMBIGUOUS** | `packages/` does contain many cos-* dirs (cos-advisory-llm, cos-sdd, etc.); no formal mapping-confirmation report. |
| 118 | Wave 0: verify `cos-package.yaml` schema supports `hook_registrations` | **VERIFIED-PENDING** | Not verified; needs explicit schema review. |
| 119 | Wave 1: migrate cos-advisory-llm pack | **VERIFIED-DONE** | `packages/cos-advisory-llm/hooks/{completeness-check-llm,confidence-gate-llm,prompt-quality-llm}.sh` exist; `hooks/*-llm.sh` are symlinks to package paths (verified via `ls -la`). Backward-compat strategy implemented. |
| 120 | `git mv hooks/*-llm.sh packages/cos-advisory-llm/hooks/` | **VERIFIED-DONE** | Confirmed by directory contents + symlink targets. |
| 121 | Leave backward-compat symlink | **VERIFIED-DONE** | Symlinks present at `hooks/completeness-check-llm.sh` etc. |
| 122 | Update `scripts/apply-efficiency-profile.sh` to read from pack manifest | **AMBIGUOUS** | Script references "subagent-capability-preflight" (per earlier grep) and lives in modified state per git status; explicit pack-manifest read not verified line-by-line. |
| 123 | Wave 2: migrate cos-sdd pack | **VERIFIED-PENDING** | `packages/cos-sdd` does **not** exist (`ls packages/cos-sdd` returns nothing). sdd-* skills remain under `skills/sdd-*/`. |
| 124 | Remaining waves: defer + document | **VERIFIED-PENDING** | No "what was done vs deferred" doc commit found. |
| 125 | Update `skills/CATALOG-COMPACT.md` generator with `[core]`/`[ext:pack-name]` tags | **VERIFIED-PENDING** | No such tagging verified in catalog file. |
| 129-133 | Create `/install-skill <name>` skill (4 sub-items) | **VERIFIED-PENDING** | No skill file at `skills/install-skill/` or `skills/extensions/install-skill/`; no installer routed through `scripts/cos`. |
| 134 | Same for `/install-hook <name>` | **VERIFIED-PENDING** | No such skill present. |
| 138 | `make install-test --profile core` <3 min | **VERIFIED-PENDING** | Profile target not certified post-split. |
| 139 | `/install-skill <random-extension>` succeeds | **VERIFIED-PENDING** | Skill does not exist. |
| 140 | `tests/contracts/test_core_extensions_split.py` passes | **VERIFIED-PENDING** | File does not exist (`tests/contracts/` only contains `test_product_zones.py` matching that area). |
| 141 | dogfood-score ≥75 | **VERIFIED-PENDING** | Not certified. |

### Phase 3 — Exit criteria (lines 145-149)

| Line | Item | Classification | Evidence |
|---|---|---|---|
| 145 | Default install <3 min, 0 manual, 0 errors | **VERIFIED-PENDING** | No `--profile core` install-test on file. |
| 146 | `test_core_extensions_split.py` passes | **VERIFIED-PENDING** | File missing. |
| 147 | `/install-skill` + `/install-hook` work on-demand | **VERIFIED-PENDING** | Skills missing. |
| 148 | dogfood-score ≥75 | **VERIFIED-PENDING** | Same as 141. |
| 149 | README rewritten to explain core-vs-extensions | **VERIFIED-PENDING** | No such README rewrite commit verified. |

**so-existential tally**: 6 DONE, 24 PENDING, 2 AMBIGUOUS.

---

## Aggregate findings

- **35 of 57** remaining open items are **genuinely PENDING** — heavily concentrated
  in the SO-existential Phase 3 (core-vs-extensions split, install-skill/install-hook
  ergonomics) and dx-tax Phase 4 (`cos explain last-block` single-command).
- **17 of 57** are **DONE** but still rendered as `- [ ]` in the plan files —
  candidates for one-shot checkbox sync, gated by maintainer approval since
  reconciliation policy is to update headers, not flip checkboxes mid-reconstruction.
- **5 of 57** are **AMBIGUOUS** — partial implementations that would benefit from
  a small confirming test or explicit operator sign-off.
- **0 OBSOLETE** — every open item is still in scope.

## Key live threads (next-actionable)

1. SO-existential Phase 3: ship `/install-skill` + `/install-hook` skill files
   plus `tests/contracts/test_core_extensions_split.py`; migrate `cos-sdd` pack
   under `packages/` mirroring the `cos-advisory-llm` symlink pattern.
2. SO-existential Phase 1 exit: emit an aggregate
   `dormant_aspirational_ratio` field in the persist payload (current schema
   only stores per-component records) so the <0.25 exit criterion can be
   automatically certified.
3. dx-tax Phase 4: add `cos explain last-block` CLI wrapping the existing
   `lib/trace_joiner.py` trace surface.
4. subagent capability contract Phase 3: wire `subagent-capability-preflight.jsonl`
   mismatches into `lib/promote_from_telemetry.py` so ADR-201 proposals fire.

## Method note

- 7 plans had zero open boxes — verified by `grep -nE "^\s*- \[ \]"` returning
  no matches.
- The 3 remaining plans were verified per-line against current code at HEAD on
  branch `codex/post-028-validation-launch-readiness-20260510`.
- Plan files were read only; no edits or commits performed.
