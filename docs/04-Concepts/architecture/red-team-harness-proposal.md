# Proposal: red-team-harness

**Change**: `red-team-harness`
**Phase**: reconstruction (rewrite > patch)
**Date**: 2026-05-02
**Status**: PROPOSED — awaiting operator commit decision
**Cross-refs**: ADR-105 (claim verification contract), ADR-106 (multi-session safety primitives), ADR-107 (human-approved rollback), `docs/04-Concepts/architecture/POST-MORTEM-2026-04.md` and post-mortem 2026-05-02 (false-done compounding), `docs/04-Concepts/architecture/cross-harness-authoring.md`, RULES-COMPACT §13 (naming) and §14 (lane taxonomy).

---

## Intent

Prevent **false-done compounding** — the failure mode where one agent declares completion, a peer accepts it, and the chain of trust amplifies an unverified state into an irrecoverable production claim. This is the root failure documented in the 2026-05-02 post-mortem and codified by ADR-105. The red-team harness is a **standing adversarial test** that re-creates the exact failure surfaces (archived-but-unwired, regex-but-unsemantic, plan-checkbox-but-no-evidence, partial completion, etc.) and grades the SO's verification stack against them on every CI run.

Meta-invariant: the harness itself must be red-teamed. Any component shipped as `<!-- SCOPE: both -->` must execute end-to-end inside a non-SO mini-repo before the marker is committed. R10 (false portability declaration) is the recursive false-done this project exists to prevent.

---

## Scope

### In Scope (3 layers — all)

- **Layer 1 — Detection primitives**: parameterized `verify-archived.sh` and `plan-claim-validator.sh` that detect archive-presence-fallacy and plan-checkbox-without-evidence patterns; both portable.
- **Layer 2 — Scenario corpus**: 6 red-team scenarios (5 `both` + 1 `os-only`) packaged as YAML fixtures with mini-repo generators.
- **Layer 3 — Harness skill + runner + aggregator + contract test**: `redteam-harness` skill (`SCOPE: both`), `run-redteam-scenario.sh` runner, `redteam-aggregate.py` reducer, project-local `redteam-baseline.{json,md}` baseline, and a per-component portability test suite.
- **Driver projection**: hook registration via `scripts/_lib/settings-driver.sh` (NOT raw `.claude/settings.json` edits) so Codex/Cursor receive equivalent wiring.
- **Cross-harness authoring compliance**: every `both` artifact passes the 5-item self-check from `cross-harness-authoring.md` §Agent Self-Check.

### Out of Scope (deferred to separate changes — confirmed)

- **ADR-106 P1**: stash-leak alarm (the `silent-stash-loss` scenario is in scope, but the underlying alarm/instrumentation is a separate change).
- **ADR-106 P2**: plan-file lockfile.
- **Cross-session reconciler** (parallel work in `scripts/cos_session_backlog.py` / async-review spawner — coexist, do not modify).
- **`cos pull-scenarios` skill** (consumer-side scenario sync). This change leaves the structure ready (versioned scenario YAML, `RED-TEAM-CHANGELOG.md`) but the pull tooling ships separately.
- **Promote contract test from warn→block**: shipped warn-only initially; promotion is its own micro-change after baseline stabilizes.
- **Centralized fleet hub telemetry**: project-local baseline only (see OQ10).

---

## Approach

### Architectural decisions (locked)

| # | Decision | Rationale |
|---|---|---|
| KD1 | **Replay-only by default**, live opt-in via `COS_REDTEAM_LIVE=1` | Replay is deterministic, cheap, CI-safe. Live exercises the real verification pipeline but adds flakiness; gate behind explicit opt-in. |
| KD2 | **Tempdir mini-repos** for fixtures (NOT git worktrees) | The exploration documented worktree-mutation hazards as an actual incident pattern. Tempdirs are inert, disposable, parallel-safe. |
| KD3 | Scenarios `both` live under **`tests/red_team/scenarios/`** in SO; propagated via `cos_init` scope filtering | Single source of truth in SO; consumers receive copies with `version:` field. |
| KD4 | Aggregator output = **`docs/06-Daily/reports/redteam-baseline.{json,md}`** (project-local) | Each repo has its own baseline. Optional `--hub-url` flag reserved for future fleet view (out of scope). |
| KD5 | **Evolution**: scenarios versioned in SO; consumers pull via `cos pull-scenarios` (skill OUT of scope here). This change ships only the structure: `version:` + `min_harness_version:` fields, plus `RED-TEAM-CHANGELOG.md`. | Keeps current change focused; pull tooling is a separable concern. |
| KD6 | **Every `both` component ships with a CI-pinned portability test BEFORE its scope marker is committed** (gate, not backlog) | R10 mitigation: refusing to red-team the harness itself would be the recursive false-done this project exists to prevent. Accepted +7h cost to estimate. |
| KD7 | **Skill name = `redteam-harness`** (no hyphen) | The hyphenated `red-team` skill already exists for Promptfoo integration; no name collision. |
| KD8 | **CI integration ships warn-only initially**, promote to blocking in a separate post-baseline change | Avoid noisy CI on day 1; gather baseline metrics before enforcement. |
| KD9 | **`lib/orchestrator_verify.py` lives at `packages/verification-audit/lib/orchestrator_verify.py`** with a symlink at `lib/orchestrator_verify.py` | Matches existing convention (`cross_verifier.py`, `staged_verification.py` already in that package). Symlinks in `lib/*.py` are real files in `packages/*/lib/`. |
| KD10 | **Hook registration via `scripts/apply-efficiency-profile.sh`** (NOT raw `.claude/settings.json` edit) | Per pre-commit warnings + ADR-019 driver projection; the script handles cross-harness wiring. |

---

## Component Table (refined)

Sequencing wave (W0–W6 + W7 portability rehearsal). Reuse = leverage existing primitive; New = first introduction.

| # | Component | Scope | Layer | Reuse/New | Wave | Portability test required? |
|---|---|---|---|---|---|---|
| 1 | `scripts/verify-archived.sh` (parameterize + `--archive-dir`/`--source-dir`/`--manifest`) | both | 1 | Reuse-rewrite | W0 | YES (`tests/red_team/portability/verify-archived.bats`) |
| 2 | `packages/verification-audit/lib/orchestrator_verify.py` (+ symlink `lib/orchestrator_verify.py`) | os-only | 1 | New | W1 | No |
| 3 | `hooks/plan-claim-validator.sh` (parameterize via `COS_PLAN_GLOB`, `COS_METRICS_DIR`) | both | 1 | New | W2 | YES (non-SO `COS_PLAN_GLOB` mini-repo) |
| 4 | `rules/trust-score.md` (link to harness, document the verbs covered) | os-only | 1 | Modify | W2 | No |
| 5 | `templates/agent-preamble.md` (already `os-only`) — add red-team verb-check block | os-only | 1 | Modify | W2 | No |
| 6 | Scenario `archive-presence-fallacy` (parameterized) | both | 2 | New | W3 | YES (mini-repo `attic/` ↔ `lib/`) |
| 7 | Scenario `unwired-constant` | both | 2 | New | W3 | YES |
| 8 | Scenario `plan-checkbox-no-evidence` | both | 2 | New | W3 | YES (shares fixture with #3) |
| 9 | Scenario `silent-stash-loss` | os-only | 2 | New | W4 | No (defers to ADR-106 P1) |
| 10 | Scenario `regex-false-positives` | both | 2 | New | W4 | YES |
| 11 | Scenario `partial-completion-claim` | both | 2 | New | W4 | YES |
| 12 | `scripts/run-redteam-scenario.sh` (`--scenarios-dir`, `--out-dir` flags) | both | 3 | New | W5 | YES (run with non-default dirs) |
| 13 | `scripts/redteam-aggregate.py` (`--input-dir`, `--output {json,md}`) | both | 3 | New | W5 | YES (3 fake JSONLs in tempdir) |
| 14 | `skills/redteam-harness/SKILL.md` (`audience: both`, `bin/cos-skill run` entry) | both | 3 | New | W5 | YES (`cos-skill describe` in non-SO repo) |
| 15 | `tests/contracts/test_redteam_baseline.py` | os-only | 3 | New | W6 | No |
| 16 | `templates/contracts/test_redteam_baseline.template.py` (consumer-customizable) | both | 3 | New | W6 | YES (instantiate template in fake consumer) |
| 17 | `docs/01-Build-Log/root/RED-TEAM-COVERAGE.md` (verb→scenario map) | os-only | 3 | New | W6 | No |
| 18 | `.cognitive-os/test-lanes.yaml` registration (lane `red_team`, parallel-safe rationale) | os-only | 3 | Modify | W6 | No |
| 19 | `.claude/settings.json` hook registration via `scripts/apply-efficiency-profile.sh` (driver-projected) | os-only (driver-projected) | 3 | Modify | W6 | No (verified by harness-driver-parity test) |
| 20 | `docs/01-Build-Log/root/RED-TEAM-CHANGELOG.md` (versioned scenario log, structure-only) | both | 3 | New | W6 | No |

**Net split**: 9 `both` + 8 `os-only` + 1 driver-projected + 2 (template + changelog) = 20 components across 3 layers.

---

## 11 Open-Question Resolutions

| OQ | Resolution | Justification |
|---|---|---|
| OQ1 (scenario YAML schema versioning) | Each YAML carries `version:` (semver) and `min_harness_version:`. Aggregator emits stale-fixture warnings. | Versioning prevents R9 (drift) without coupling to a registry. |
| OQ2 (which verbs from ADR-105 to cover first) | All 5 ADR-105 verbs: `archived`, `wired`, `tested`, `verified`, `claimed`. One scenario per verb minimum. | Parity with ADR-105 contract; coverage map in `RED-TEAM-COVERAGE.md`. |
| OQ3 (replay vs live) | Replay default; live behind `COS_REDTEAM_LIVE=1`. | KD1. Determinism for CI; live for staging exercise. |
| OQ4 (mini-repo vs in-tree fixtures) | Tempdir mini-repos generated per-test. | KD2. Worktree-mutation hazard documented in incident. |
| OQ5 (hook integration point) | `hooks/plan-claim-validator.sh` registered via `scripts/apply-efficiency-profile.sh` → driver dispatch. | KD10. Avoids raw settings.json edits flagged by pre-commit. |
| OQ6 (CI lane assignment) | New lane `red_team` in `.cognitive-os/test-lanes.yaml` with documented parallel-safety reason (tempdir isolation, no shared fixtures). Warn-only on CI initially. | RULES-COMPACT §15. |
| OQ7 (aggregator output format) | JSON (machine) + Markdown (human review). Schema documented in skill body. | Dual-format covers CI gating + post-mortem reading. |
| OQ8 (orchestrator_verify.py home) | `packages/verification-audit/lib/orchestrator_verify.py` (real file) + symlink `lib/orchestrator_verify.py`. | KD9. Matches existing package convention. |
| OQ9 (scenario distribution) | **Copy-with-version**: SO ships scenarios under `tests/red_team/scenarios/`; `cos_init --install-scope project` copies to consumer. `cos_init --upgrade` re-syncs. `version:` field tracks staleness. | Reproducibility wins over single-source-of-truth pull-on-demand at this maturity. Reference (shared install path) creates consumer-side coupling we cannot yet manage. |
| OQ10 (aggregator destination) | **Project-local default**: `docs/06-Daily/reports/redteam-baseline.{json,md}`. Optional `--hub-url` flag reserved (no hub implementation in this change). | Each project needs its own baseline; fleet view is premature. |
| OQ11 (evolution / pull mechanism) | **Push-via-cos_init-upgrade** with `RED-TEAM-CHANGELOG.md`; the consumer-pull skill `cos pull-scenarios` is OUT of scope but the structure (versioned YAMLs + changelog) lands here. | Defers tooling complexity; scenarios remain useful via existing `cos_init` upgrade path. |

---

## Wave Sequencing (W0–W7)

Each wave is **independently mergeable** unless noted. DoD per wave is verified before moving on.

### W0 — `verify-archived.sh` parameterization (`both`)
- **Delivers**: flagged CLI (`--archive-dir`, `--source-dir`, `--manifest`); SO-default behavior preserved.
- **Dependencies**: none.
- **DoD**: existing SO usage still passes; new flags documented in `--help`; portability test under `tests/red_team/portability/verify-archived.bats` runs in fixture mini-repo `attic/scripts/ ↔ scripts/` and asserts exit code matrix (4 cases: present/missing × wired/unwired). Bash naming compliant (RULES §13).
- **Blast radius**: low (1 script + 1 test fixture + 1 portability test).
- **Mergeable independently**: YES.

### W1 — `lib/orchestrator_verify.py` (`os-only`)
- **Delivers**: real file at `packages/verification-audit/lib/orchestrator_verify.py` + symlink at `lib/orchestrator_verify.py`. Implements verb-→evidence mapping per ADR-105.
- **Dependencies**: ADR-105 (already merged).
- **DoD**: `pytest tests/contracts/test_orchestrator_verify.py` passes; snake_case naming (RULES §13); imports cleanly via both real path and symlink.
- **Blast radius**: medium (new lib consumed downstream by W6 contract test).
- **Mergeable independently**: YES, but no consumer until W6.

### W2 — `plan-claim-validator.sh` hook + rules/templates updates
- **Delivers**: hook with `COS_PLAN_GLOB`/`COS_METRICS_DIR` env contract; `rules/trust-score.md` and `templates/agent-preamble.md` updated to reference harness.
- **Dependencies**: W0 (uses same flag-parameterization pattern).
- **DoD**: portability test installs hook in non-SO tempdir with `COS_PLAN_GLOB=plans/*.md`, triggers Edit on `[x]` transition, asserts WARN/BLOCK fires. Hook registered via `scripts/apply-efficiency-profile.sh`, NOT raw settings.json.
- **Blast radius**: medium (touches hook chain).
- **Mergeable independently**: YES (warn-only mode).

### W3 — Layer 2 scenarios batch A: `archive-presence-fallacy`, `unwired-constant`, `plan-checkbox-no-evidence` (all `both`)
- **Delivers**: 3 scenario YAMLs + fixtures + portability tests.
- **Dependencies**: W0 (verify-archived for #6), W2 (plan-claim-validator for #8).
- **DoD**: each scenario runs in tempdir, grades pass/fail correctly; portability test executes from non-SO mini-repo and produces same grade.
- **Blast radius**: low (additive, scenarios isolated in `tests/red_team/scenarios/`).
- **Mergeable independently**: YES.

### W4 — Layer 2 scenarios batch B: `silent-stash-loss` (os-only), `regex-false-positives` (both), `partial-completion-claim` (both)
- **Delivers**: 3 scenario YAMLs + fixtures.
- **Dependencies**: none (silent-stash-loss exercises ADR-106 P1 stash-reflog patterns but does not require its alarm to be implemented — scenario marks expected fail until P1 lands).
- **DoD**: scenarios grade correctly; `silent-stash-loss` documented as "tied to ADR-106 P1; expected to flip from `xfail` to `pass` when P1 ships."
- **Blast radius**: low.
- **Mergeable independently**: YES.

### W5 — Runner + aggregator + skill (Layer 3, all `both`)
- **Delivers**: `scripts/run-redteam-scenario.sh`, `scripts/redteam-aggregate.py`, `skills/redteam-harness/SKILL.md`. Skill canonical entry: `bin/cos-skill run redteam-harness`.
- **Dependencies**: W3, W4 (scenarios must exist).
- **DoD**: `bin/cos-skill run redteam-harness` produces `docs/06-Daily/reports/redteam-baseline.{json,md}` with all 6 scenarios graded; portability tests for runner + aggregator + skill execute from a fake consumer mini-repo. snake_case (Python) / kebab-case (shell) per RULES §13.
- **Blast radius**: high (new skill, new scripts, schema introduced).
- **Mergeable independently**: YES (warn-only on CI).

### W6 — Contract test + docs + lane registration + driver wiring
- **Delivers**: `tests/contracts/test_redteam_baseline.py` (os-only, asserts SO baseline), `templates/contracts/test_redteam_baseline.template.py` (both, consumer-customizable), `docs/01-Build-Log/root/RED-TEAM-COVERAGE.md` verb-map, `docs/01-Build-Log/root/RED-TEAM-CHANGELOG.md` (structure only), `.cognitive-os/test-lanes.yaml` lane `red_team` (parallel-safety reason: tempdir-isolated fixtures, no shared mutation), and hook registration through `scripts/apply-efficiency-profile.sh` (driver-projected).
- **Dependencies**: W5 (baseline file format must be stable).
- **DoD**: contract test runs in `red_team` lane, completes; lane registration parsed by `cos-test`; harness-driver-parity test confirms hook fires under Codex driver; `cos_init.py --install-scope project --dry-run` in fake consumer dir shows all `both` files propagate, no `os-only` leaks.
- **Blast radius**: high (CI lane registration, hook chain, driver projection — but warn-only).
- **Mergeable independently**: YES (warn-only).

### W7 — Consumer install rehearsal (validation gate, no new code)
- **Delivers**: scripted execution of `cos_init.py --install-scope project --dry-run` against a fixture consumer dir; assertion report.
- **Dependencies**: W6.
- **DoD**: 9 `both` files propagate; 8 `os-only` files do NOT propagate; driver-projected hook registration produces correct settings for Codex driver.
- **Blast radius**: low (test-only).
- **Mergeable independently**: YES.

---

## Risk Mitigation

| Risk | Severity | Mitigation phase | Strategy |
|---|---|---|---|
| R1 — Scenario YAMLs become stale vs reality | MED | W3-W6 | `version:` + `min_harness_version:`; aggregator warns on stale; `RED-TEAM-CHANGELOG.md`. |
| R2 — CI flakiness from live-mode | MED | W5 | KD1: replay default; live behind `COS_REDTEAM_LIVE=1`. |
| R3 — Worktree mutation hazard | HIGH | W3-W4 | KD2: tempdir mini-repos only. Documented in skill body. |
| R4 — Hook chain regression | HIGH | W2 | Hook registered via `scripts/apply-efficiency-profile.sh`; warn-only mode initially; existing pre-commit warning re settings.json explicitly addressed by KD10. |
| R5 — Plan-claim-validator false positives | MED | W2 | Warn-only initially; promote to block in separate change after baseline. |
| R6 — Aggregator schema churn | MED | W5 | JSON schema versioned; `--output md` for human review independent of machine schema. |
| R7 — Coverage gaps vs ADR-105 verbs | MED | W6 | `RED-TEAM-COVERAGE.md` enforces verb→scenario map; gap = open task. |
| R8 — Scope creep in consumer forks | MED | W5 | `tests/red_team/scenarios/local/` (gitignored from upstream); aggregator tags `source: upstream\|local`. |
| R9 — Versioning drift | MED | W3-W6 | `version:` + `min_harness_version:` + changelog. |
| R10 — False portability declaration (recursive false-done) | HIGH | W0, W2, W3, W4, W5, W6 (gate at every wave) | KD6: every `both` component ships with CI-pinned portability test BEFORE scope marker commit. **Verify phase will re-execute all portability tests and any FAIL = retry, not warn.** |

---

## Acceptance Criteria (whole change)

- [ ] All 6 scenarios run via `bin/cos-skill run redteam-harness` and produce `docs/06-Daily/reports/redteam-baseline.{json,md}`.
- [ ] `cos_init.py --install-scope project --dry-run` against a fake consumer dir: 9 `both` files propagate, 8 `os-only` files do not (W7 rehearsal asserts this).
- [ ] All 9 `both` components have a passing portability test in `tests/red_team/portability/` (KD6 gate).
- [ ] Driver-projected hook registration works under both Claude Code and Codex drivers (harness-driver-parity test passes).
- [ ] `tests/contracts/test_redteam_baseline.py` passes in the `red_team` lane.
- [ ] `templates/contracts/test_redteam_baseline.template.py` instantiates correctly in a fake consumer.
- [ ] CI runs harness in warn-only mode (no blocking failures introduced; promotion to blocking is a separate change).
- [ ] `RED-TEAM-COVERAGE.md` maps all 5 ADR-105 verbs to ≥1 scenario.
- [ ] `RED-TEAM-CHANGELOG.md` exists with v1.0.0 entry covering the 6 initial scenarios.
- [ ] Naming compliance: Python snake_case, shell kebab-case (RULES §13).
- [ ] Lane `red_team` registered with parallel-safety rationale (RULES §15).
- [ ] `lib/orchestrator_verify.py` resolves to `packages/verification-audit/lib/orchestrator_verify.py` via symlink and imports identically from both paths.

---

## Cross-Session Conflict Map

The following areas are touched by parallel sessions today. Coexistence strategy:

| Parallel work | Path | Coexistence |
|---|---|---|
| `auto-repair-rollback` package (ADR-107 implementation) | `packages/auto-repair-rollback/**` | No overlap. Harness consumes ADR-105 contract; ADR-107 implements rollback flow. Independent. |
| ADR-107 (human-approved rollback) | `docs/02-Decisions/adrs/ADR-107-human-approved-rollback.md` | Read-only reference. No edits. |
| `scripts/adr_implementation_ledger.py` (untracked, parallel session) | `scripts/adr_implementation_ledger.py` | No file overlap. Harness writes its own scripts under `scripts/run-redteam-scenario.sh` and `scripts/redteam-aggregate.py`. Both adhere to RULES §13 snake_case Python / kebab-case shell. |
| `tests/contracts/test_primitive_scope_classification.py` (untracked, parallel) | `tests/contracts/test_primitive_scope_classification.py` | Different test file. Harness adds `test_redteam_baseline.py`. No collision. |
| Various hooks under `hooks/` (modified, parallel) | `hooks/edit-lock-*.sh`, `hooks/skill-frontmatter-validator.sh`, etc. | Harness adds **only** `hooks/plan-claim-validator.sh` (new file, no edit). Pre-commit warning about settings.json explicitly addressed via `scripts/apply-efficiency-profile.sh` registration. |
| `templates/prompt-hooks/*.md` (modified, parallel) | various | No overlap. Harness modifies `templates/agent-preamble.md` only. |
| `scripts/cos_session_backlog.py` (modified, parallel) | `scripts/cos_session_backlog.py` | No overlap. Harness scripts are separate files. |

**Merge order recommendation**: harness waves W0-W7 commit on rebased branches; if a parallel session lands first, only `templates/agent-preamble.md` is a re-merge candidate (W2 modifies it). Trivial 3-way merge expected.

---

## Estimate (confirmed: 19–27h)

| Wave | Hours | Notes |
|---|---|---|
| W0 verify-archived param + portability | 2-3 | Includes bats portability test. |
| W1 orchestrator_verify.py + symlink | 2-3 | Real file in package + tests. |
| W2 plan-claim-validator + rule/template updates | 3-4 | Hook + driver wiring + portability test (+1h). |
| W3 scenarios A (3 × `both`) | 3-4 | Includes 3 portability fixtures (+1h). |
| W4 scenarios B (1 os-only + 2 both) | 2-3 | 2 portability fixtures (+1h). |
| W5 runner + aggregator + skill | 4-5 | Includes runner+aggregator+skill portability tests (+2h). |
| W6 contract tests + docs + lane + driver wiring | 2-3 | template instantiation portability test (+1h). |
| W7 consumer install rehearsal | 1 | Pure validation, no new code (+1h vs original). |
| **Total** | **19–27h** | Matches re-explored estimate including +7h for KD6 portability gates. |

---

## Out of Scope (explicit)

- ADR-106 P1 stash-leak alarm implementation.
- ADR-106 P2 plan-file lockfile.
- Cross-session reconciler (`scripts/cos_session_backlog.py` and async-review spawner — coexist, no edits).
- `cos pull-scenarios` consumer-pull skill (structure ready, tooling separate).
- Promotion of harness CI integration from warn → block (separate post-baseline change).
- Centralized fleet hub telemetry / `--hub-url` implementation.
- Custom consumer scenarios (`tests/red_team/scenarios/local/` is gitignored from upstream sync; consumers manage their own).

---

## Rollback Plan

Per-wave rollback. Each wave commits separately; revert by `git revert <wave-commit>`.

- W0–W2: revert leaves SO with current behavior (no harness wiring); no consumer impact.
- W3–W4: scenarios are additive in `tests/red_team/scenarios/`; revert removes them; no other code references them yet.
- W5: revert removes runner/aggregator/skill; CI lane stays empty (no failures).
- W6: revert un-registers lane and contract test; harness-driver-parity test removed.
- W7: pure validation step — no rollback needed (test-only commit).

If KD6 gate fires in verify (a `both` component fails its portability test), revert ONLY the failing component's wave and re-propose with refined parameterization. Other waves stand.

---

## Dependencies

- **Internal**: ADR-105 merged (claim verification contract); existing `scripts/cos_init.py::scope_allows`; `scripts/_lib/settings-driver.sh`; `scripts/apply-efficiency-profile.sh`; `bin/cos-skill`.
- **External**: none. Harness is pure-bash + pure-python on stdlib.
- **Defers to**: ADR-106 P1 (when it lands, `silent-stash-loss` flips xfail→pass — handled by aggregator's expected-fail registry).

---

## Success Criteria

- [ ] Harness ships green in CI (warn-only) within W6.
- [ ] `cos_init` propagation rehearsal (W7) passes: 9/8/1 split realized with no leaks.
- [ ] Zero `<!-- SCOPE: both -->` markers committed without paired portability test (KD6 enforced via verify phase).
- [ ] Within 30 days post-merge, ≥1 false-done failure mode caught in CI (validates the harness has standing-test value, not just shelfware).
