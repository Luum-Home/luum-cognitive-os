<!--
RECONCILIATION STATUS: SUPERSEDED
Superseded by: ADR-028 (SO Reliability & Observability Framework — covers the "aspirational→enforced" transition with SLOs + error budgets), ADR-031 (aspirational-audit recurring), ADR-041 (exercised coverage pipeline)
Reconciled: 2026-04-21
Reason: the "everything that MUST happen goes in deterministic code" principle and the complexity gate have been absorbed into the ADR-028 framework with explicit SLOs. Wiring-rate tracking is now continuous (ADR-031/041).
-->

# MEGA PLAN: Stabilization — From Aspirational to Enforced

**Created**: 2026-04-11
**Status**: DRAFT — awaiting user approval
**Phase transition**: reconstruction → stabilization
**Trigger**: User declared OS unmanageable. Audit found 43% wiring rate (140 of 384 components unwired).

---

## 1. The Problem

The Cognitive OS has 384 components (132 libs, 109 hooks, 143 skills). Only 43% are actually wired into the system. The rest are dead code that:
- Was built but never connected
- Was documented in rules but never enforced
- Was listed in catalogs but never created (phantom entries)
- Creates false confidence ("we have cost governance" — no, we have an unused cost_predictor.py)

### Root Cause
Everything was built in `reconstruction` phase where speed > governance. Rules were written as markdown (probabilistic LLM compliance). Nothing prevents unwired code from being committed.

### The Golden Rule (from this session)
> **Everything that MUST happen goes in deterministic code (hooks, CI, git hooks), not in LLM instructions.**

### The Complexity Gate (from this session)
> **Every change must reduce complexity or hold it constant. Changes that add components without wiring them are rejected.**

This applies retroactively: worktrees, branches, and pending work from before stabilization are evaluated against this gate. If they add complexity without solving the wiring problem, they are deleted — not deferred, deleted. "Defer" is how dead code accumulates.

### The Merge Criteria (for all pending and future work)
Before any branch/worktree merges to main, it must pass:
1. **Wiring check**: every new file is imported/registered/cataloged (deterministic script)
2. **Net complexity**: does not increase unwired component count
3. **Tests exist**: new code has tests that pass
4. **No phantom entries**: doesn't reference things that don't exist

If it fails any of these → fix it or delete it. No exceptions, no "we'll wire it later."

---

## 2. The Audit Data

### 82 Unwired Libs (0 callers outside tests)
Full list in engram topic `audit/wiring-gaps-2026-04`.

**Critical 6 (referenced by rules but never called):**
- `cost_predictor.py` — rules say "estimate cost before launching"
- `wiring_validator.py` — built to detect unwired components, is itself unwired
- `agent_progress_tracker.py` — preamble references progress markers
- `sdd_pipeline.py` — CLAUDE.md says "Use SDDPipeline.get_phases()"
- `cost_dashboard.py` — rules say "use CostDashboard.format_session_report()"
- `trust_report_parser.py` — trust-score rule references it

### 17 Unregistered Hooks
Files in `hooks/` that are not in `.claude/settings.json`:
agent-output-verifier, audit-id-enricher, code-review-on-commit, context-diet, memu-sync, metrics-calibrator-trigger, mlflow-sync, package-sync, paperclip-sync, pre-commit-gate, registration-check, session-knowledge-extractor, sync-to-repo, task-completed, task-created, teammate-idle, tool-discovery-trigger

### 14 Phantom Skills (in CATALOG.md but don't exist)
add-mock-provider, check-health, cost-predictor, estimation-report, framework-patterns, performance-dashboard, sre-agent-config, start-stack, tob-agentic-actions-auditor, tob-insecure-defaults, tob-static-analysis, tob-supply-chain-risk-auditor, tob-variant-analysis

### 27 Invisible Skills (exist but not in CATALOG.md)
analyze-improvements, apply-improvements, auto-generated, configure-quality-gates, cos-docker-setup, cos-install, cos-quickstart, cos-setup, detect-stack, dogfood-check, ecosystem-eval, evaluate-tool, generate-config, propose-improvements, queue-drain, recall-search, register-component, release-plan, run-benchmark, scaffold-project, sdd-compound, session-report-executive, skill-creator, smart-commit, switch-security-profile, test-agent-teams, usage-report

### Broken Chains
1. **Cost governance**: cost_predictor → budget_calculator → cost_dashboard → claude_usage_reader. All built, none wired.
2. **Agent lifecycle**: agent_progress_tracker → agent_dashboard → agent_permissions → agent_context_injector. All built, none wired.
3. **Memory management**: memory_decay → memory_first → memory_retriever. All built, none wired.
4. **SDD pipeline**: sdd_pipeline.py → sdd_resume.py. Built, orchestrator uses manual logic.
5. **Pre-compaction**: flush relies on LLM reading text output (non-deterministic).

---

## 3. The Enforcement Stack

All tools MIT/BSD/Apache licensed.

### 3.1 Pre-commit hooks (run on every `git commit`)
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.x
    hooks:
      - id: ruff          # unused imports (F401), unused vars (F841)
        args: [--fix]
      - id: ruff-format   # formatting

  - repo: https://github.com/jendrikseipp/vulture
    rev: v2.x
    hooks:
      - id: vulture        # unused functions, classes, unreachable code
        args: [lib/, hooks/, --min-confidence, "80"]

  - repo: local
    hooks:
      - id: wiring-validator
        name: Component wiring check
        entry: python3 -m lib.wiring_validator --strict
        language: python
        pass_filenames: false
        stages: [pre-push]  # heavier check, run on push not commit

      - id: catalog-sync
        name: Skill catalog sync check
        entry: python3 scripts/check-catalog-sync.py
        language: python
        pass_filenames: false

      - id: hook-registration
        name: Hook registration check
        entry: python3 scripts/check-hook-registration.py
        language: python
        pass_filenames: false

      - id: test-ratchet
        name: Test count ratchet (never decrease)
        entry: python3 scripts/check-test-ratchet.py
        language: python
        pass_filenames: false
        stages: [pre-push]
```

### 3.2 Architecture tests (run with pytest)
```python
# tests/architecture/test_wiring.py
"""Architecture fitness functions — deterministic validation of OS wiring."""

import pytest_archon  # or custom

def test_every_lib_has_caller():
    """Every lib/*.py must be imported by at least 1 non-test file."""

def test_every_hook_is_registered():
    """Every hooks/*.sh must appear in .claude/settings.json."""

def test_every_skill_in_catalog():
    """Every .cognitive-os/skills/*/SKILL.md must be in CATALOG.md."""

def test_no_phantom_skills():
    """Every skill in CATALOG.md must exist as a directory."""

def test_no_orphan_config_keys():
    """Every key in cognitive-os.yaml must be read by at least 1 file."""

def test_critical_chains_wired():
    """Validate that critical component chains are connected."""
    # cost_predictor is imported by something
    # trust_report_parser is imported by something
    # etc.
```

### 3.3 CI pipeline (GitHub Actions)
```yaml
# .github/workflows/quality-gate.yml
name: Quality Gate
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff vulture
      - run: ruff check lib/ hooks/
      - run: vulture lib/ hooks/ --min-confidence 80

  architecture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pytest import-linter
      - run: pytest tests/architecture/ -v

  wiring:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python3 scripts/check-catalog-sync.py
      - run: python3 scripts/check-hook-registration.py
      - run: python3 -m lib.wiring_validator --strict

  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt pytest
      - run: pytest tests/ -q --tb=line

  gate:
    needs: [lint, architecture, wiring, tests]
    runs-on: ubuntu-latest
    steps:
      - run: echo "All gates passed"
```

### 3.4 Custom enforcement scripts

**`scripts/check-catalog-sync.py`**: Compare skills in filesystem vs CATALOG.md. Exit 1 on mismatch.

**`scripts/check-hook-registration.py`**: Compare hooks in `hooks/*.sh` vs `.claude/settings.json`. Exit 1 on unregistered hooks.

**`scripts/check-test-ratchet.py`**: Compare test count with baseline. Exit 1 if count decreased.

**`scripts/check-lib-wiring.py`**: For each `lib/*.py`, verify it's imported by at least 1 non-test file OR is in an explicit allowlist of "standalone utilities".

---

## 4. Triage: What to Do with 140 Unwired Components

### Decision framework
For each unwired component, ONE of:

| Decision | Criteria | Action |
|---|---|---|
| **WIRE** | Valuable, clear integration point | Connect it to the system |
| **DEFER** | Valuable but no integration point yet | Move to `lib/_deferred/` with README explaining when to wire |
| **DELETE** | Not valuable or superseded | Remove from codebase |
| **ALLOWLIST** | Standalone utility, doesn't need wiring | Add to allowlist in wiring validator |

### Batch 1: Critical 6 libs (WIRE immediately)
These are referenced by rules and should be working:
1. `wiring_validator.py` → wire as pre-push hook + CI check
2. `cost_dashboard.py` → wire into session-hygiene.sh (Stop hook)
3. `trust_report_parser.py` → wire into PostToolUse hook for Agent
4. `agent_progress_tracker.py` → wire into preamble injection
5. `cost_predictor.py` → wire into PreToolUse hook for Agent
6. `sdd_pipeline.py` → wire into SDD skill orchestration

### Batch 2: 17 unregistered hooks (TRIAGE)
For each: register it, or delete it.

### Batch 3: Catalog sync (FIX)
- Add 27 invisible skills to CATALOG.md
- Remove 14 phantom entries from CATALOG.md

### Batch 4: 82 remaining libs (TRIAGE sessions)
Over 3-4 sessions, triage each lib: WIRE, DEFER, DELETE, or ALLOWLIST.

---

## 5. The 3-Layer Validation System

### Layer 1: Tests (known behavior)
What we have. Covers logic. Doesn't detect structural problems.

### Layer 2: Static analysis (structural integrity)
**NEW.** Pre-commit and CI checks that detect:
- Orphan files (nothing imports them)
- Phantom catalog entries
- Unregistered hooks
- Unused functions/classes
- Architecture violations (wrong imports)

### Layer 3: Runtime observability (actual execution)
**PARTIALLY BUILT.** `component_usage_tracker.py` exists but isn't wired consistently.
Wire into session-init to track what actually executes vs what should execute.
After 10 sessions of data, flag components that never fired.

### Enforcement matrix

| What must happen | Layer | Mechanism | Deterministic? |
|---|---|---|---|
| Every lib is imported somewhere | Static | check-lib-wiring.py (pre-push) | YES |
| Every hook is registered | Static | check-hook-registration.py (pre-commit) | YES |
| Every skill is in CATALOG | Static | check-catalog-sync.py (pre-commit) | YES |
| Tests don't decrease | Static | check-test-ratchet.py (pre-push) | YES |
| No dead code | Static | vulture (pre-commit) | YES |
| Agent result matches prompt | Runtime | PostToolUse hook + keyword comparison | YES |
| Cost estimated before launch | Runtime | PreToolUse hook calls cost_predictor | YES |
| Trust report included | Runtime | PostToolUse hook checks TRUST_REPORT: | YES |
| Components actually execute | Runtime | usage tracker + session analysis | YES |

---

## 6. Execution Plan

### Phase 1: Foundation (1 session)
1. Install enforcement stack: `pre-commit`, `ruff`, `vulture`
2. Create `.pre-commit-config.yaml` with basic checks
3. Create `scripts/check-catalog-sync.py`
4. Create `scripts/check-hook-registration.py`
5. Create `tests/architecture/test_wiring.py` (basic versions)
6. Run `pre-commit install && pre-commit install --hook-type pre-push`
7. Verify: `pre-commit run --all-files`

### Phase 2: Catalog & Hook Cleanup (1 session)
1. Fix CATALOG.md: add 27 missing skills, remove 14 phantoms
2. Triage 17 unregistered hooks: register or delete
3. Run catalog-sync and hook-registration checks — must pass

### Phase 3: Critical Wiring (2-3 sessions)
1. Wire the 6 critical libs (Batch 1)
2. Wire work_queue into agent lifecycle (from frozen worktree)
3. Wire component_usage_tracker into session-init
4. Wire trust_report_parser into PostToolUse
5. Each wiring: code change + test + architecture test update

### Phase 4: Lib Triage (3-4 sessions)
1. Triage 82 unwired libs in batches of 20
2. For each: WIRE, DEFER, DELETE, or ALLOWLIST
3. `lib/_deferred/` directory for deferred components with README
4. Wiring validator allowlist for standalone utilities

### Phase 5: CI Pipeline (1 session)
1. Create `.github/workflows/quality-gate.yml`
2. Enable branch protection on main
3. Required checks: lint, architecture, wiring, tests
4. Verify: create test PR, confirm gate blocks on failure

### Phase 6: Runtime Layer (1-2 sessions)
1. Wire agent result verification (prompt vs output keyword match)
2. Wire cost estimation into agent launch
3. Wire trust report validation
4. 10-session burn-in period for observability data

### Total: ~10 sessions to full stabilization

---

## 7. Success Criteria for "Stabilized"

The OS is considered stabilized when ALL of these are true:

- [ ] Wiring rate >= 90% (currently 43%)
- [ ] 0 phantom skills in CATALOG.md
- [ ] 0 unregistered hooks in hooks/
- [ ] All 6 critical libs wired and tested
- [ ] pre-commit runs on every commit with 0 failures
- [ ] pre-push wiring validator passes
- [ ] Architecture tests pass: `pytest tests/architecture/ -v`
- [ ] CI pipeline blocks PRs that fail quality gate
- [ ] Test count ratchet prevents regression
- [ ] Agent result verification catches prompt/output mismatch
- [ ] Work queue persists agent state across sessions
- [ ] `cognitive-os.yaml` phase = "stabilization" (then "production" after burn-in)

---

## 8. What's Frozen Until Stabilization

All feature work stops. These worktrees are preserved but not merged until Phase 3+:

| Worktree | Content | Merge when? |
|---|---|---|
| agent-a9686e66 | Format converter | After Phase 3 (wiring complete) |
| agent-a94c0490 | Skill scoping | After Phase 2 (catalog cleanup) |
| agent-a7f4acda | uv migration | After Phase 1 (foundation) |
| agent-a889f6a9 | Work queue wiring | Phase 3 (critical wiring) — HIGH PRIORITY |
| agent-ae43390c | WS4 skill parameterization | After Phase 2 |
| agent-a424c44c | WS1 RULES-COMPACT slim | After Phase 1 |

Pending workstreams (NOT started, deferred):
- WS10: Security tools activation
- WS6 remaining: Scope tags for hooks/rules
- WS8: Auto-classification detector
- Docker→pip Phases 2-4
- Format conversion layer Phase 2 (TOON, ISON)
- OS Visual UI evaluation
- Multi-device portability

---

## 9. Decisions from This Session

1. **Phase transition**: reconstruction → stabilization (ENFORCED in cognitive-os.yaml)
2. **Golden rule**: everything that MUST happen goes in deterministic code, not LLM instructions
3. **3-layer validation**: tests + static analysis + runtime observability
4. **Enforcement stack**: pre-commit + ruff + vulture + import-linter + custom scripts
5. **Triage framework**: WIRE / DEFER / DELETE / ALLOWLIST for every unwired component
6. **Feature freeze**: no new components until wiring rate >= 90%
