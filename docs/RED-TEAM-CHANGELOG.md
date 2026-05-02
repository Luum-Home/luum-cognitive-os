# Red-Team Harness Changelog

All notable changes to the red-team harness are documented here.
Format: `[version] YYYY-MM-DD — summary — wave`.

---

## [1.0.0] 2026-05-02 — Initial 6-scenario harness

**Wave**: W0-W6 (full initial build)

### Added

**Infrastructure (W0-W2)**
- `scripts/verify-archived.sh` — bilateral archive verification with `--archive-dir`,
  `--source-dir`, `--manifest`, `--config-globs`, `--quiet`, `--json` flags.
  Exit codes: 0=pass, 1=source present, 2=archive missing, 3=stale config ref, 4=bad args.
- `packages/verification-audit/lib/orchestrator_verify.py` + symlink `lib/orchestrator_verify.py` —
  ADR-105 high-stakes claim extractor and verifier. Composes `lib.ground_truth`.
- `hooks/plan-claim-validator.sh` — PreToolUse hook that enforces `(verified: …)` references
  on markdown checkbox completions. Mode: warn (promote to block via `COS_PLAN_VALIDATOR_MODE=block`).

**Scenarios (W3-W4)**
- `archive-presence-fallacy.yaml` (`both`) — Verb: `archived`. Archive copies exist while
  originals remain live and wired. Replicates the Wave C false-done incident 2026-05-02.
- `unwired-constant.yaml` (`both`) — Verb: `wired`. Constant added to code but not surfaced
  in config or exposed via env; agent claims it is wired without evidence.
- `plan-checkbox-no-evidence.yaml` (`both`) — Verb: `verified`. Plan checkbox marked `[x]`
  without any `(verified: …)` reference in the same paragraph.
- `regex-false-positives.yaml` (`both`) — Verb: `tested`. Regex-based claim extractor flags
  false positives from comments and docs that look like ADR-105 claims.
- `partial-completion-claim.yaml` (`both`) — Verb: `verified`. Agent claims partial batch
  complete; missing items not counted. Includes meta-scenario sub-case: rubber-stamp portability
  test detection (Layer 3 anti-rubber-stamp guard).
- `silent-stash-loss.yaml` (`os-only`, `xfail`) — Verb: `completed`. Pre-agent snapshot
  stashes work that is never re-applied. Tied to ADR-106 P1; flips xfail→pass when P1 ships.

**Runner + Aggregator + Skill (W5)**
- `scripts/run-redteam-scenario.sh` (`both`) — Layer 3 scenario runner. Replay (default)
  and live (COS_REDTEAM_LIVE=1) modes. Writes per-scenario JSON to `--out-dir`.
- `scripts/redteam_aggregate.py` (`both`) — Aggregates per-scenario JSON into
  `redteam-baseline.{json,md}`. Schema version 1.0.0. Verb coverage matrix included.
- `skills/redteam-harness/SKILL.md` (`both`) — Skill entrypoint. Invokable via
  `bin/cos-skill run redteam-harness`.

**Contract + Docs + Lane (W6)**
- `tests/contracts/test_redteam_baseline.py` (`os-only`) — Contract test: baseline produced,
  6 scenarios graded, all ADR-105 verbs covered.
- `templates/contracts/test_redteam_baseline.template.py` (`both`) — Consumer-customizable
  version of the contract test.
- `tests/contracts/test_redteam_portability_coverage.py` (`os-only`) — KD6 enforcement:
  walks SCOPE: both artifacts, asserts paired portability test, ≥4 test cases, ≥1 falsification.
- `hooks/scope-marker-portability-gate.sh` (`both`) — Pre-commit KD6 gate (warn-only, KD8).
- `docs/RED-TEAM-COVERAGE.md` — Verb→scenario map, KD6 gate status table.
- `docs/RED-TEAM-CHANGELOG.md` — This file.
- `.cognitive-os/test-lanes.yaml` — `red_team` lane registered (parallel-safe).

**Portability tests (KD6, all waves)**

All 10 `both`-scoped red-team artifacts paired with portability tests in
`tests/red_team/portability/`. Each test has ≥4 cases and ≥1 falsification probe.
See `docs/RED-TEAM-COVERAGE.md` for the full matrix.

### Configuration

- Default mode: replay (CI-safe, no LLM calls)
- Live mode: set `COS_REDTEAM_LIVE=1`
- Plan validator: `COS_PLAN_VALIDATOR_MODE=warn` (default) or `block`
- Portability gate: `COS_SCOPE_GATE_MODE=warn` (default) or `block`

### Known xfail

- `silent-stash-loss` — xfail until ADR-106 P1 (stash-leak alarm) ships.

---

*Next entry: when a scenario is added, status changes (xfail→pass), or schema bumped.*
