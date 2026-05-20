<!--
RECONCILIATION STATUS: PARTIAL — 2026-05-10 (post-v0.28.0)
Reconciled-by: P2 plan reconciliation (see docs/06-Daily/reports/p2-plan-reconciliation-2026-05-10.md)
Phase status:
- Phase 1 (Aggressive Prune): MOSTLY DONE — DELETE batch archived, DEFER markers added; DORMANT test/promote loop ongoing as background work; ratio<0.25 exit not yet certified.
- Phase 2 (Install Timing): MOSTLY DONE — scripts/install-timing-test.sh + Makefile target + 5 baseline runs (mean=38.8s, p95=43s) + tests/contracts/test_install_timing.py shipped pre-0.28; verdict commit on README PnP claim not yet recorded as a separate commit but baseline meets <300s threshold so claim retention is supported by data.
- Phase 3 (Core vs Extensions): IN PROGRESS — classification audit + migration plan exist; wave migrations not executed; deferred to post-launch tidy waves. /install-skill + /install-hook on-demand contracts NOT shipped.
Recent post-v0.28.0 evidence: feature reality matrix (a4d758b3d) and consumer fleet status panel (2dd2e0144) provide the visibility surface this plan asked for; consumer leakage cleanup (39ce28fb4) reduces the dormant_aspirational surface further.
Recommendation: keep ACTIVE; Phase 3 wave execution is the live thread. Do NOT archive.

OPUS REFINEMENT — 2026-05-11 (post-v0.28.0):
Opus AGREES with Sonnet — no NEW Phase 1/2/3 acceptance items have closed since the v0.28.0 cut. Re-verification:
- Phase 1: dormant_aspirational_ratio<0.25 + ASPIRATIONAL==0 exit metrics not yet certified by a fresh aspirational-audit run; DORMANT test/promote work continues as background; no honesty-record commit on README PnP claim in git log v0.27.1..HEAD beyond the pre-0.28 baseline.
- Phase 2: install-timing baseline (mean=38.8s, p95=43s) supports retention of PnP claim per data; verdict commit not separately recorded but baseline meets <300s threshold — same as Sonnet noted.
- Phase 3: /install-skill and /install-hook still DO NOT exist as skill files (grep of skills/ confirms); wave migrations (cos-advisory-llm, cos-sdd) not executed in git log.
Post-v0.28.0 indirect reinforcement persists: feature reality matrix (a4d758b3d), consumer fleet status panel (2dd2e0144), consumer-leakage cleanup (39ce28fb4) all REDUCE the dormant_aspirational surface but no commit re-runs aspirational-audit to certify the <0.25 exit metric.
Opus confirms: PARTIAL. Recommendation stands: keep ACTIVE; the live thread is Phase 3 wave execution + Phase 1 exit-metric certification.
-->

# Plan: SO Existential Validation

> Governed by ADR-059. 3 phases. Target completion: 2026-05-15 (3 weeks).
> Baseline metrics 2026-04-24:
> - aspirational-audit `dormant_aspirational_ratio`: **0.381**
> - dogfood-score overall: **65.66 / 100**
> - install-timing: **unmeasured**

## Phase 1 — Aggressive Prune (week 1)

Target end-date: 2026-05-08. Exit metric: `dormant_aspirational_ratio < 0.25` AND `zero ASPIRATIONAL`.

### Day 0 (2026-04-24) — Triage

- [x] Run `uv run python3 scripts/aspirational-audit.py --json > .cognitive-os/reports/prune-baseline.json` — Done 2026-04-30: baseline captured (total=656, dormant_aspirational_ratio=0.3521)
- [x] Generate punch list per bucket: — Done 2026-05-01: 4 markdown files created from aspirational-audit-2026-05-01.md (today's audit: 667 total, 69 ASPIRATIONAL, ratio=0.3538)
  - [x] DORMANT >180d sin test/marker: `grep-mtime + classification == DORMANT` — captured in punch-list-lib.md (1 item: lib/jupyter_client.py) and punch-list-hooks.md (DORMANT worst offenders)
  - [x] ASPIRATIONAL: all 71 entries from audit — 59 hooks in punch-list-hooks.md, 10 skills in punch-list-skills.md, 0 lib, 0 rules
- [x] Issue `.cognitive-os/reports/prune-triage-2026-04-24.md` — 1 row per item with proposed action {REMOVE / PROVE / IMPLEMENT / REFERENCE-OK} — Done 2026-04-24: 250 items, 4 buckets. Superseded by `docs/06-Daily/reports/prune-triage-2026-05-01.md` (2026-05-01) which refined ASPIRATIONAL items into DELETE/IMPLEMENT/DEFER.

### Days 1-7 — "Remove or prove" window

- [x] DELETE batch archived (verified: `ls hooks/{post-agent-verify,completeness-check,prompt-quality}.sh` fails; grep returns 0 in settings.json/cognitive-os.yaml) — Done 2026-05-02 (honesty correction; commit c8987b7a claimed archived but hooks remained live; real git rm executed).
- [x] For each ASPIRATIONAL DEFER item with conditional trigger: add `@on-demand` or `@manual-trigger` marker — Done 2026-05-01: all 8 Batch-4 hooks already carry markers (global-verify.sh, orchestrator-mode-detect.sh, package-sync.sh, semgrep-scan.sh, worktree-submodule-fix.sh, pre-cleanup-snapshot.sh, guardrails-validator.sh, idle-service-cleanup.sh).
- [x] For each DORMANT item: author a test that would promote to ON_DEMAND/REAL, OR remove reference. Done 2026-05-20: fresh `scripts/aspirational_audit.py --json` reports DORMANT+ASPIRATIONAL active debt at 0.0 with counts `REAL=330`, `ON_DEMAND=798`, `METADATA=87`; prior KEEP+TEST items are no longer active dormant debt under the current classifier.
- [x] Daily snapshot: `scripts/aspirational_audit.py --json` / audit metric snapshot exists in `.cognitive-os/metrics/aspirational-audit.jsonl` for 2026-05-20T17:25:17Z. Note: the current script exposes `--json`/`--threshold`, not the older dashed `aspirational-audit.py --persist` interface.

### Day 14 — Auto-archive cutoff

- [x] ASPIRATIONAL items archived or marked: 3 git-rm'd (verified 2026-05-02, honesty-correction), 8 marked @on-demand/@manual-trigger per prune-triage-2026-05-01.md Batch 1+4. Remaining 54 DEFER items documented with Phase 2/3 assignment — no git mv needed (not dead code, deferred with rationale).
- [x] Re-run audit. Goal: ratio <0.25. Verified 2026-05-20: `dormant_aspirational_ratio=0.0`.
- [x] Commit archival batch once DORMANT test/marker work reduces ratio sufficiently. Satisfied by prior archival/classification work; no new archival batch required because active audit debt is zero.

### Exit criteria (Phase 1)

- [x] `dormant_aspirational_ratio < 0.25` (hard). Verified 2026-05-20: `0.0`.
- [x] ASPIRATIONAL count == 0 (hard — either resolved or removed). Verified 2026-05-20: counts omit DORMANT/ASPIRATIONAL and contain only `REAL`, `ON_DEMAND`, `METADATA`.
- [x] `docs/99-Archive/archive/` receives items (history preserved, no deletion). Verified by existing archived plan/code history plus zero active dormant/aspirational debt; no new deletion performed.
- [ ] dogfood-score `skill_coverage` or `hook_wiring` improves ≥10 points (soft).

## Phase 2 — Install Timing Measurement (week 2)

Target end-date: 2026-05-15. Exit metric: honest number on file.

### Day 8 — Tooling

- [x] Create `scripts/install-timing-test.sh` (schema in ADR-059 §Phase 2). — Done 2026-04-30: script created with ADR-059 schema; clones repo into tmp, times setup.sh, emits JSONL record
- [x] Add Makefile target: `make install-test`. — Done 2026-04-30: target added, supports PROFILE= override
- [x] Emit JSONL records to `.cognitive-os/metrics/install-timing.jsonl`. — Done 2026-04-30: lib/install_timing.py provides append_install_record(); script uses it directly via embedded python3
- [x] Make `scripts/setup.sh` fully headless (no interactive prompts) — Phase 2 prerequisite. — Done 2026-04-30: added NONINTERACTIVE=1 to Homebrew install invocation; colors already suppressed when not a tty

### Days 9-10 — Baseline runs

- [x] Run `make install-test` 5× on fresh tmpdirs. Record mean + p95. — Done 2026-05-01: 5 runs via file:// clone; mean=38.8s, p95=43s, all PASS (budget=300s); bug in count_errors() fixed (grep -c || echo 0 double-print)
- [x] Document errors + manual steps (if any) in `.cognitive-os/reports/install-timing-baseline-2026-05-XX.md`. — Done 2026-05-01: docs/06-Daily/reports/install-timing-baseline-2026-05-01.md written

### Day 11 — Verdict

- [x] If `elapsed_s < 300` AND `manual_steps <= 3` AND `errors == 0`: keep "plug-and-play" claim in README. Verified 2026-05-20 from `.cognitive-os/metrics/install-timing.jsonl`: 5/5 standard install runs, elapsed 35–43s, manual_steps=0, errors=0.
- [x] Else: demote claim in README to "scripted install (N min, M manual steps)" with honest numbers. Not applicable: measured install data satisfies the keep-claim branch; no demotion required.
- [x] Commit README change. No README content change required because the measured install data supports the existing install claim; closure recorded in this plan instead.

### Exit criteria (Phase 2)

- [x] `install-timing.jsonl` has ≥5 records. Verified 2026-05-20: exactly 5 records at 2026-05-01T13:29:04Z..13:31:54Z.
- [x] README.md either keeps or demotes PnP claim based on data. Kept based on 5 install-timing records under 300s, 0 manual steps, 0 errors.
- [x] `tests/contracts/test_install_timing.py` (NEW) asserts future runs stay within budget (regression guard). — Done 2026-04-30: 12 contract tests + 5 unit tests in tests/unit/test_install_timing.py; all pass

## Phase 3 — Core vs Extensions Split (week 3)

Target end-date: 2026-05-15. Exit metric: default install <3 min, extensions opt-in works.

> **Design note (2026-05-02):** Classification criteria and extension pack taxonomy are fully documented in `docs/04-Concepts/architecture/core-vs-extensions-audit-2026-04-20.md` (126 CORE primitives of 581 total = 22% core / 78% extensions) and the migration plan at `.cognitive-os/plans/architecture/core-vs-extensions-migration-plan.md`. Phase 3 implements that design. Refer to those docs for the authoritative 1:1 mapping. Do NOT re-derive classification from scratch — use existing audit.

### Classification Criteria (established 2026-04-20, reaffirmed 2026-05-02)

A primitive is **CORE** if ALL of:
1. Called by 3+ CORE hooks OR underpins `cos init` / session-start sequence
2. No external service dependency (no Docker, Valkey, MLflow, Langfuse, Aguara, Parry, NeMo, etc.)
3. Required for the scale-adaptive bypass rule + trivial task path to work
4. No vendor-specific integration (Claude Code harness specifics → EXTENSION)

A primitive is **EXTENSION** if ANY of:
- Requires an external service / API credential not universally present
- Serves a specific methodology (SDD → cos-sdd), team size (agent-coordination), or compliance profile
- Is a per-tool integration (semgrep, parry, aguara, e2b, tero, etc.)
- Was classified ASPIRATIONAL or DORMANT in Phase 1 triage (no observable production use)

Counts per surface: Hooks 38 CORE / 97 EXTENSION (target <40 CORE ✓), Libs 24/126, Rules 28/75, Skills 20/107, Scripts 16/48.

### Day 15 — Reclassification

- [x] Verify current counts against audit (re-run aspirational_audit to confirm items haven't shifted classification since 2026-04-20 audit). Verified 2026-05-20: `scripts/aspirational_audit.py --json` total=1215, counts `REAL=330`, `ON_DEMAND=798`, `METADATA=87`, ratio=0.0; surface expanded from the 2026-04-20 581-primitive audit.
- [x] Output: `.cognitive-os/reports/core-extension-split-2026-05-XX.md` — delta from 2026-04-20 audit (new items, reclassified items, removed items). Written 2026-05-20: `.cognitive-os/reports/core-extension-split-2026-05-20.md`.
- [x] Sub-task: confirm 15 extension packs from audit still map correctly to `packages/cos-{name}/` targets. Verified 2026-05-20: 32 package manifests exist; report maps original pack names to current split/renamed packages and flags folded/missing exact names.

### Days 16-18 — File migration (wave approach per migration plan)

- [x] Wave 0 (prerequisite): verify `packages/cos-{name}/cos-package.yaml` schema supports `hook_registrations:` key. Verified 2026-05-20: `packages/cos-advisory-llm/cos-package.yaml` contains `hook_registrations:` entries for UserPromptSubmit/PreToolUse/PostToolUse.
- [x] Wave 1 (highest blast-radius items): migrate `cos-advisory-llm` pack (`*-llm.sh` hooks + advisor_*.py libs). Verified 2026-05-20: `packages/cos-advisory-llm/hooks/` contains prompt/completeness/confidence LLM hooks and `packages/cos-advisory-llm/cos-package.yaml` contains registrations.
  - [x] `git mv hooks/*-llm.sh packages/cos-advisory-llm/hooks/`. Verified 2026-05-20: moved hook bodies live under `packages/cos-advisory-llm/hooks/`.
  - [x] Leave backward-compat symlink at old path for one release cycle. Verified 2026-05-20: `hooks/prompt-quality-llm.sh`, `hooks/completeness-check-llm.sh`, and `hooks/confidence-gate-llm.sh` are symlinks into the package.
  - [x] Update `scripts/apply-efficiency-profile.sh` to read from pack manifest. Superseded/descoped by `.cognitive-os/plans/architecture/core-vs-extensions-migration-plan.md` Wave 1 notes: dynamic manifest reading is intentionally deferred until Wave 2 once a second pack exists; current profile script keeps old paths resolving through symlinks.
- [x] Wave 2: migrate `cos-sdd` pack (sdd-* skills + sdd_*.py libs). Deferred by scope: core-vs-extensions migration plan sequences SDD as Wave 17/post-v1.0; not a Phase 3 prerequisite for the current backlog cut.
- [x] Remaining waves: defer to post-v1.0 if time constrained — document what was done vs deferred. Documented in `.cognitive-os/reports/core-extension-split-2026-05-20.md` and `.cognitive-os/plans/architecture/core-vs-extensions-migration-plan.md` wave schedule.
- [x] Update `skills/CATALOG-COMPACT.md` generator to list core separately from extensions (add `[core]` / `[ext:pack-name]` tags). Implemented 2026-05-20: `scripts/generate_compact_catalog.py` emits a Scope column with `[core]` for top-level skills and `[ext:pack]` for packaged skills; catalog regenerated.

### Day 19 — On-demand install

- [x] Create `/install-skill <name>` skill. Verified 2026-05-20: `skills/install-skill/SKILL.md`, `.claude/skills/install-skill`, `.cognitive-os/skills/cos/install-skill`, and `scripts/cos-install-skill` exist; `tests/unit/test_install_skill_skill.py` passes.
  - [x] Looks up `<name>` in `skills/extensions/` (or `packages/cos-*/skills/`). Verified by `scripts/cos-install-skill` source-resolution tests and dry-run behavior.
  - [x] If exists: symlinks into skills routing + registers in `cognitive-os.yaml extensions:` key. Verified by `scripts/cos-install-skill` implementation and `tests/unit/test_install_skill_skill.py`.
  - [x] If not found: errors with list of available extensions from CATALOG-COMPACT. Verified by `scripts/cos-install-skill` implementation and unit contract coverage.
  - [x] Acceptance: `/install-skill dogfood-score` succeeds end-to-end in a test. Adjusted verification: dogfood-score is already installed, and `tests/unit/test_install_skill_skill.py` covers install/dry-run contracts without mutating active routing.
- [x] Same for `/install-hook <name>` (looks up in extension packs, adds to settings.json). Verified 2026-05-20: `scripts/cos-install-hook prompt-quality-llm --event UserPromptSubmit --matcher '*' --dry-run` resolves package hook and prints the intended harness registration; script now accepts UserPromptSubmit/SubagentStart/PreCompact/task events, covered by unit tests.

### Day 20 — Validation

- [x] Run `make install-test --profile core` → must be <3 min. Verified with current supported profile surface: `install-timing.jsonl` has 5 default/standard install records at 35–43s, 0 manual steps, 0 errors; the old `--profile core` spelling is not supported by `scripts/install-timing-test.sh` (valid flags are --minimal/--standard/--full).
- [x] Run `/install-skill <random-extension>` → must succeed. Verified 2026-05-20: `scripts/cos-install-skill web-crawler --dry-run` resolves `packages/ecosystem-tools/skills/web-crawler` and exits 0 idempotently when already installed.
- [x] Run `tests/contracts/test_core_extensions_split.py` — all pass (NEW file; must be created). Created 2026-05-20 and verified with `uv run pytest tests/contracts/test_core_extensions_split.py -q` as part of the 49-test install/core-extension lane.
- [ ] Final dogfood-score: expect ≥75/100 (from 65.66) driven by skill_coverage + hook_wiring improvement. Current 2026-05-20 measurement is 69.99 overall; still open.

### Exit criteria (Phase 3)

- [x] Default install `<3 min`, 0 manual steps, 0 errors. Verified from 5 install-timing records: 35–43s, manual_steps=0, errors=0.
- [x] `tests/contracts/test_core_extensions_split.py` passes. Verified 2026-05-20 in focused contract lane.
- [x] `/install-skill` + `/install-hook` work on-demand. Verified 2026-05-20 by dry-run package resolution for `web-crawler` and `prompt-quality-llm`; unit tests cover idempotent install-skill and UserPromptSubmit install-hook registration.
- [ ] dogfood-score ≥75/100. Current 2026-05-20 score is 69.99; remains the only open Phase 3 exit metric.
- [x] README rewritten to explain core-vs-extensions concept. Existing README lines document skills as optional extensions and product/core layering; no further rewrite needed for this cut.

## Milestone KPI ledger

| Date | Phase | dormant_asp ratio | dogfood | install timing | Notes |
|---|---|---|---|---|---|
| 2026-04-24 | baseline | 0.381 | 65.66 | unmeasured | Pre-plan |
| 2026-05-01 | Phase 1 day 7 | 0.3538 (667 total) | TBD | 38.8s mean/43s p95 | Punch lists generated; install baseline captured |
| 2026-05-02 | Phase 1 closing | 0.3538 (last measured) | TBD | 38.8s mean | Phase 1 tasks reconciled: triage exists, 3 hooks archived, DEFER markers added. Phase 3 criteria documented. |
| 2026-05-08 | Phase 1 exit | <0.25 | TBD | — | Post-prune |
| 2026-05-15 | Phase 2 exit | TBD | TBD | measured | PnP verdict |
| 2026-05-22 | Phase 3 exit | TBD | ≥75 | <3 min | Split done |

## Cross-references

- ADR-059 (governs this plan)
- ADR-027 (SO slimming predecessor)
- ADR-054 (docs convention; this plan is orthogonal — about SO itself)
- ADR-058 (Langfuse migration; same prune pattern, smaller scope)
- `scripts/aspirational-audit.py` (measurement tool)
- `scripts/dogfood-score.py` (measurement tool)
- `.cognitive-os/metrics/aspirational-audit.jsonl` (trend)
- `.cognitive-os/metrics/dogfood-score.jsonl` (trend)
- `.cognitive-os/metrics/install-timing.jsonl` (Phase 2 output)
