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
- [ ] Issue `.cognitive-os/reports/prune-triage-2026-04-24.md` — 1 row per item with proposed action {REMOVE / PROVE / IMPLEMENT / REFERENCE-OK}

### Days 1-7 — "Remove or prove" window

- [ ] For each DORMANT item: author a test that would promote to ON_DEMAND/REAL, OR remove reference.
- [ ] For each ASPIRATIONAL item: implement missing dep OR delete the reference from manifests.
- [ ] Daily snapshot: `scripts/aspirational-audit.py --persist` to `.cognitive-os/metrics/aspirational-audit.jsonl`.

### Day 14 — Auto-archive cutoff

- [ ] Unresolved items from triage → `git mv <path> docs/archive/<category>/<path>`.
- [ ] Commit: `chore(prune): archive <N> unresolved DORMANT/ASPIRATIONAL items`.
- [ ] Re-run audit. Goal: ratio <0.25.

### Exit criteria (Phase 1)

- [ ] `dormant_aspirational_ratio < 0.25` (hard).
- [ ] ASPIRATIONAL count == 0 (hard — either resolved or removed).
- [ ] `docs/archive/` receives items (history preserved, no deletion).
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
- [x] Document errors + manual steps (if any) in `.cognitive-os/reports/install-timing-baseline-2026-05-XX.md`. — Done 2026-05-01: docs/reports/install-timing-baseline-2026-05-01.md written

### Day 11 — Verdict

- [ ] If `elapsed_s < 300` AND `manual_steps <= 3` AND `errors == 0`: keep "plug-and-play" claim in README.
- [ ] Else: demote claim in README to "scripted install (N min, M manual steps)" with honest numbers.
- [ ] Commit README change.

### Exit criteria (Phase 2)

- [ ] `install-timing.jsonl` has ≥5 records.
- [ ] README.md either keeps or demotes PnP claim based on data.
- [x] `tests/contracts/test_install_timing.py` (NEW) asserts future runs stay within budget (regression guard). — Done 2026-04-30: 12 contract tests + 5 unit tests in tests/unit/test_install_timing.py; all pass

## Phase 3 — Core vs Extensions Split (week 3)

Target end-date: 2026-05-15. Exit metric: default install <3 min, extensions opt-in works.

### Day 15 — Reclassification

- [ ] Run audit: every hook + skill gets tagged `core` or `extension` based on:
  - Registered in default profile (settings.json)
  - Has ≥1 behavioral test
  - ≥1 REAL or ON_DEMAND classification
- [ ] Output: `.cognitive-os/reports/core-extension-split-2026-05-XX.md`

### Days 16-18 — File migration

- [ ] Create `hooks/core/` and `hooks/extensions/`. `git mv` per tag.
- [ ] Same for `skills/core/` and `skills/extensions/`.
- [ ] Update `scripts/apply-efficiency-profile.sh` default profile to reference `hooks/core/`.
- [ ] Update `skills/CATALOG-COMPACT.md` generator to list core separately from extensions.

### Day 19 — On-demand install

- [ ] Create `/install-skill <name>` skill that:
  - Looks up `<name>` in `skills/extensions/`
  - If exists: symlinks into `skills/core/` (or equivalent projection), registers routing.
  - If not found: errors with list of available extensions.
- [ ] Same for `/install-hook <name>`.

### Day 20 — Validation

- [ ] Run `make install-test --profile core` → must be <3 min.
- [ ] Run `/install-skill <random-extension>` → must succeed.
- [ ] Run `tests/contracts/test_core_extensions_split.py` — all pass.
- [ ] Final dogfood-score: expect ≥75/100 (from 65.66) driven by skill_coverage + hook_wiring improvement.

### Exit criteria (Phase 3)

- [ ] Default install `<3 min`, 0 manual steps, 0 errors.
- [ ] `tests/contracts/test_core_extensions_split.py` passes.
- [ ] `/install-skill` + `/install-hook` work on-demand.
- [ ] dogfood-score ≥75/100.
- [ ] README rewritten to explain core-vs-extensions concept.

## Milestone KPI ledger

| Date | Phase | dormant_asp ratio | dogfood | install timing | Notes |
|---|---|---|---|---|---|
| 2026-04-24 | baseline | 0.381 | 65.66 | unmeasured | Pre-plan |
| 2026-05-01 | Phase 1 day 7 | 0.3538 (667 total) | TBD | 38.8s mean/43s p95 | Punch lists generated; install baseline captured |
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
