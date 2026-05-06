# Session Close Report — Lethal Trifecta and Harness Action Receipts — 2026-05-06

## Purpose

This report records the closure state for the workstream that started with a
`lethal_trifecta` false positive and expanded into a portable receipt model for
harness and VCS actions.

The durable outcome is that Cognitive OS now treats Codex Desktop `::git-*`
markers as harness-specific advisory receipts, not as Cognitive OS agentic
primitives or repository safety boundaries. The portable primitive is the
vendor-neutral Harness Action Receipt / VCS Action Receipt model.

## Scope Completed

### 1. Lethal trifecta false-positive fix

The original defect was in the deterministic `lethal_trifecta` gate. The gate
matched three regex dimensions over tool input:

- private data or memory wording,
- untrusted or third-party source wording,
- external communication or mutation wording.

Security and research documents can legitimately describe all three dimensions
at once. A comparative matrix about MCP tools, private memory persistence, and
GitHub repository citations therefore looked like a complete exfiltration chain
even though the action was only writing documentation.

The fix keeps the gate active for executable or runtime-sensitive surfaces, but
exempts `Write` actions whose target path is intentionally documentary:

- `docs/research/`
- `docs/reports/`
- `docs/adrs/`

The exemption is path- and tool-specific. It does not weaken the gate for `Bash`,
for hooks, for libraries, or for scripts.

Remote commit:

```text
39fe617b fix lethal trifecta research doc writes
```

Primary files:

- `lib/lethal_trifecta.py`
- `tests/unit/test_lethal_trifecta.py`
- `tests/contracts/test_lethal_trifecta_gate.py`

### 2. Harness Action Receipts decision and architecture

The session clarified that Codex Desktop directives such as `::git-stage{...}`
are not operating-system primitives. They are harness UI metadata emitted after
the corresponding Git action succeeds.

Cognitive OS now documents the portable interpretation:

- Harness directives are adapter receipts.
- Receipts can be advisory, observed, verified, or authoritative depending on
  evidence.
- Receipts are useful for dashboards, audit trails, and operator visibility.
- Receipts are not security boundaries unless promoted by independently verified
  evidence.

Committed baseline:

```text
08e55eac docs: define harness action receipts
```

Primary files:

- `docs/adrs/ADR-190-harness-action-receipts.md`
- `docs/architecture/harness-action-receipts.md`
- `lib/harness_action_receipts.py`
- `scripts/cos-action-receipt`
- `tests/unit/test_harness_action_receipts.py`

### 3. Runtime integration for VCS receipts

The follow-up implementation wired receipts into the existing VCS guard and
merge surfaces.

Integrated surfaces:

- `hooks/direct-main-guard.sh`
- `hooks/git-commit-scope-guard.sh`
- `hooks/git-context-capture.sh`
- `scripts/merge-to-main.sh`
- `dashboard/app/page.tsx`
- `dashboard/lib/cos-api.ts`

Implemented receipt behaviors include:

- blocked push receipts,
- bypass receipts,
- merge enqueue/fail/land receipts,
- observed commit context receipts,
- `vcs.push` promotion with stronger evidence from:
  - pre-push hook refs,
  - remote ref verification,
  - provider API acceptance.

Committed runtime integration:

```text
8dd2b66f feat(receipts): emit and report VCS action receipts
```

Validation evidence captured during the session:

```text
python3 -m pytest tests/unit/test_harness_action_receipts.py -q
python3 -m pytest tests/unit/test_harness_action_receipts.py tests/unit/test_direct_main_guard.py tests/unit/test_projected_hook_gap_behaviors.py tests/behavior/test_git_context_hook.py -q
python3 -m pytest tests/red_team/portability/test_cos-merge-queue-worker.py tests/red_team/portability/test_cos-merge-queue-bench.py -q
python3 -m pytest tests/unit/test_multi_agent_coordination_primitives.py -q
python3 -m py_compile lib/harness_action_receipts.py
bash -n scripts/cos-action-receipt hooks/direct-main-guard.sh hooks/git-commit-scope-guard.sh hooks/git-context-capture.sh scripts/merge-to-main.sh
```

### 4. Dashboard local toolchain documentation

Dashboard validation initially appeared blocked because `npm` was unavailable in
the non-interactive shell. The actual project-local toolchain is exposed through
`fnm`.

Documented validation sequence:

```bash
eval "$(fnm env --shell zsh)"
cd dashboard
npm run build
```

Known-good versions observed during the session:

```text
node v22.14.0
npm 10.9.2
```

Important lint boundary:

- `npm run build` is the current reliable dashboard gate.
- `npm run lint` currently delegates to deprecated `next lint` and can prompt for
  interactive ESLint setup when no config exists.
- Do not answer that prompt or generate lint config as part of an unrelated
  change.

Committed documentation:

```text
a396d52c docs: document dashboard fnm validation
```

Primary file:

- `docs/dashboard-architecture.md`

## Current Repository State at Close

At the time this closure report was written, `main` was aligned with
`origin/main` for the lethal-trifecta, receipts, dashboard, and related committed
work. The working tree still contained local changes outside this closed scope.
Those changes must be reviewed as a separate workstream before being committed,
reverted, or split.

Pending local paths observed outside this closure-report commit:

- `Formula/cognitive-os.rb`
- `cmd/cos/go.mod`
- `dashboard/app/page.tsx`
- `dashboard/lib/cos-api.ts`
- `docs/business/master-plan-checklist.md`
- `docs/reports/primitive-harness-coverage-latest.json`
- `docs/reports/primitive-harness-coverage-latest.md`
- `docs/reports/primitive-harness-partials-latest.json`
- `docs/reports/primitive-harness-partials-latest.md`
- `hooks/inject-phase-context.sh`
- `manifests/primitive-harness-gap-policy.yaml`
- `scripts/cos`
- `scripts/cos-tui`
- `scripts/cos_daemon.py`
- `scripts/cosd`
- `tests/behavior/test_agent_background_execution.py`
- `tests/behavior/test_session_isolation.py`
- `tests/behavior/test_skill_auto_selection.py`
- `tests/contracts/test_cos_tui_operable_surface_contract.py`
- `tests/contracts/test_primitive_harness_coverage_contract.py`
- `tests/integration/test_cosd_daemon.py`
- `.github/workflows/cos-binary-release.yml`
- `.goreleaser.yaml`
- `cmd/cos/internal/tui/`
- `docs/adrs/ADR-191-cos-binary-release-pipeline.md`
- `docs/adrs/ADR-192-surface-5-adopt-bubbletea.md`
- `docs/adrs/ADR-193-cosd-local-network-api.md`
- `infra/cosd/`
- `scripts/cos-headless-pipeline`
- `scripts/cos-root`
- `tests/contracts/test_standalone_distribution_contract.py`

## Decisions Preserved

1. Documentation/research paths are allowed to describe security concepts that
   would be dangerous if executed.
2. The lethal-trifecta gate remains strict for executable and runtime-sensitive
   actions.
3. Codex Desktop action directives are harness-specific receipts, not portable
   primitives.
4. Cognitive OS receipts must model trust explicitly and support promotion by
   independently verifiable evidence.
5. Dashboard validation must initialize `fnm` before assuming `node` or `npm` are
   present.

## Next Steps

1. Review the pending local paths as a separate scope.
2. Decide whether those changes are operator work, another agent's work, or
   disposable local residue.
3. If they are in scope, split them into focused commits with targeted tests.
4. If they are not in scope, leave them untouched or explicitly revert only after
   operator confirmation.
