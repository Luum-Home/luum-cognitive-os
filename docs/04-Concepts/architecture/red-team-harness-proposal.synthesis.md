---
type: concept-synthesis
source: docs/04-Concepts/architecture/red-team-harness-proposal.md
status: "PROPOSED — awaiting operator commit decision"
provenance: "Root failure documented in the 2026-05-02 post-mortem and codified by ADR-105 — false-done compounding, where one agent declares completion, a peer accepts it, and the trust chain amplifies an unverified state into an irrecoverable production claim."
---

## What it is
Proposal for `red-team-harness`: a standing adversarial test suite to prevent "false-done compounding" — the failure mode from the 2026-05-02 post-mortem, codified by ADR-105.

## Key mechanics
- Meta-invariant: the harness must red-team itself (R10) — every `SCOPE: both` component needs an end-to-end non-SO mini-repo pass before its marker is committed.
- 3-layer scope: Layer1 detection primitives (`verify-archived.sh`, `plan-claim-validator.sh`); Layer2 scenario corpus (6 scenarios: 5 `both` + 1 `os-only`, YAML + mini-repo generators); Layer3 skill + runner + aggregator + contract test.
- Explicitly out of scope: ADR-106 P1/P2, cross-session reconciler, `cos pull-scenarios` skill, warn->block CI promotion, centralized fleet hub telemetry.
- 10 locked architectural decisions (KD1-KD10): KD1 replay-only default (`COS_REDTEAM_LIVE=1` opt-in); KD2 tempdir mini-repos, not worktrees (documented mutation hazard); KD3 scenarios live under `tests/red_team/scenarios/`, propagated via `cos_init` scope filtering; KD4 aggregator output `docs/06-Daily/reports/redteam-baseline.{json,md}` project-local; KD5 versioned scenarios + `RED-TEAM-CHANGELOG.md`; KD6 mandatory portability-test-before-scope-marker gate (+7h estimate cost); KD7 skill name `redteam-harness` (no hyphen, avoids collision with existing `red-team` Promptfoo skill); KD8 CI ships warn-only first; KD9 `lib/orchestrator_verify.py` symlinks to `packages/verification-audit/`; KD10 hook registration via `scripts/apply-efficiency-profile.sh`, not raw settings.json.
- 20-component table across waves W0-W6: 9 `both` + 8 `os-only` + 1 driver-projected + 2 (template + changelog). W0 verify-archived parameterization; W1 `orchestrator_verify.py`; W2 `plan-claim-validator.sh` + rule/template updates; W3/W4 6 scenario YAMLs; W5 runner + aggregator + skill; W6 contract test + docs + lane + driver wiring; W7 consumer install rehearsal (no new code, validation only).
- 11 open-question resolutions (OQ1-OQ11): versioning fields (`version`/`min_harness_version`), 5 ADR-105 verb coverage (`archived`, `wired`, `tested`, `verified`, `claimed`), replay-vs-live default, tempdir-vs-in-tree fixtures, hook integration point, new CI lane `red_team`, dual JSON+Markdown output, `orchestrator_verify.py` package home, copy-with-version distribution model, project-local aggregator destination, push-via-`cos_init`-upgrade evolution mechanism.
- Risk table R1-R10 with severity/wave/mitigation; R10 (recursive false-done) is gated at every wave (W0, W2, W3, W4, W5, W6).
- Acceptance criteria: 12 checkboxes including all 6 scenarios runnable via `bin/cos-skill run redteam-harness`, the 9/8 file-split install rehearsal, all 9 `both` components portability-tested, Claude+Codex driver parity, naming compliance, lane registration, `RED-TEAM-COVERAGE.md` mapping all 5 verbs.
- Estimate: 19-27h total across 8 waves (per-wave hour breakdown given).

## Relations & where used
Cross-refs ADR-105, ADR-106, ADR-107, `POST-MORTEM-2026-04.md`, post-mortem 2026-05-02, `cross-harness-authoring.md`, RULES-COMPACT §13. Coexists with parallel work: `auto-repair-rollback` package, `scripts/adr_implementation_ledger.py`, `tests/contracts/test_primitive_scope_classification.py`, various `hooks/`, `templates/prompt-hooks/*.md`, `scripts/cos_session_backlog.py`.

## Status / caveats
Status: PROPOSED — awaiting operator commit decision. Per-wave rollback plan documented (git revert per wave-commit). If the KD6 gate fires during verify, only the failing component's wave is reverted and re-proposed; other waves stand.
