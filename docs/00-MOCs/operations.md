# MOC: Operations

Day-to-day running of the system: incidents, releases, capabilities, ops reference.

## Start here

1. [`docs/runbooks/`](../runbooks/) — step-by-step ops playbooks (one per scenario)
2. [`docs/incidents/`](../incidents/) — past incident reports + response patterns
3. [`docs/release/`](../release/) — release procedures and versioning

## Capabilities

- [`docs/capabilities/`](../capabilities/) — capability catalogue (what the OS can do)
- [`docs/acc/`](../acc/) — Aspirational/Concrete/Confirmed reality classification, latest snapshot at `docs/acc/latest.json`
- [`docs/agent-capability-coverage.md`](../agent-capability-coverage.md)
- [ADR-189 Harness implementation coverage](../adrs/ADR-189-harness-implementation-coverage.md)
- Run `/component-reality-check` (or `scripts/aspirational_audit.py`) for REAL/DORMANT/ASPIRATIONAL classification.

## Releases

- [`docs/release/`](../release/) — release notes, version bumps, changelog
- [ADR-246 Release transaction freeze](../adrs/ADR-246-release-transaction-freeze.md)
- Skills: `bump-version`, `tag-release`, `push-release`, `generate-changelog`, `validate-release`
- Go binary releases: `cmd/cos` + the `cos release` subcommand

## Incidents

- [`docs/incidents/`](../incidents/) — chronological incident reports
- [ADR-228 Retry contract](../adrs/) (retry taxonomy + attempt limits)
- Skills: `auto-rollback`, `crash-recovery`, `error-analyzer`
- Append-only error log: `error-learning.jsonl` (60s dedup; 3+ same = warning)

## Cost governance

- [`docs/agent-efficiency-strategy.md`](../agent-efficiency-strategy.md) — model routing rules
- [ADR-049 LLM dispatch](../adrs/) — Qwen-primary preserves Claude Max; kill-switches via `COS_DISABLE_LLM_FALLBACK=1`
- [ADR-059 SO existential validation (KPI ledger)](../adrs/ADR-059-so-existential-validation.md)
- Skill: `cost-predictor` (`/cost-predict`)

## Observability

- [`docs/measurements/`](../measurements/) — historical snapshots
- [`docs/reports/`](../reports/) — analysis reports (named `<topic>-YYYY-MM-DD.md`)
- Metrics: `.cognitive-os/metrics/*.jsonl` (gitignored append-only logs)
- ADR-028 SLO catalogue + error budget

## Integrations

- [`docs/integrations/`](../integrations/) — third-party integration notes (Engram, MCP, etc.)
- [`docs/migration-from/`](../migration-from/) — migration playbooks from other systems
- [`docs/setup/`](../setup/) — local setup + bootstrap

## Pending-truth & closure primitives (ADR-273/274/275)

Day-to-day "what's pending and how do I close it" surface. See the
4-layer map at [`docs/architecture/pending-truth-architecture.md`](../architecture/pending-truth-architecture.md)
for the full system.

**Obtain (read side)** — aggregators walking source surfaces into ledgers:
- `scripts/cos-pending-truth-aggregator` — TASKS → `docs/reports/pending-truth-latest.json` (ADR-273 Slice A)
- `scripts/cos-pending-truth-verify` — deterministic verifier (ADR-273 Slice B)
- `scripts/cos-operational-guide-audit.py` — §OG audit (ADR-274)
- `scripts/cos-adr-partial-ledger` — DECISIONS in partial/blocked/deferred
- `scripts/cos-adr-partial-audit` — `adr-partial-lifecycle` findings to control-plane

**Project (where it's consumed)** — one ranked surface at SessionStart:
- `scripts/cos-session-start-projector` — top-N actionable across all sources (ADR-275)
- Wired into `.claude/settings.json`, `.codex/hooks.json`, `.cognitive-os/cos-runner-hooks.json`

**Close (write side)** — atomic + audited:
- `scripts/cos-pending-truth-close` — closes TASKS with bilateral proof (ADR-275)
- `scripts/cos-adr-close` — closes DECISION records (ADR lifecycle)
- Closure trail: `.cognitive-os/audit/closure-trail.jsonl`
- `scripts/cos-closure-trust-signal.py` — HIGH|MEDIUM|LOW|ZERO trust signal
- Canonical status vocabulary: [`docs/adrs/STATUS-TAXONOMY.md`](../adrs/STATUS-TAXONOMY.md)

**Prevent drift** — advisory hooks (active in maintainer profile):
- `hooks/pending-truth-drift-detector.sh` — PostToolUse Edit/Write nudge
- `hooks/pending-truth-verify-weekly.sh` — Stop async verifier re-run
- `hooks/pending-truth-staleness-gate.sh` — PreToolUse Bash advisory
- `.githooks/pre-commit` Gate 3 — ADR lifecycle + INDEX.md staleness

## Related MOCs

- [decisions.md](decisions.md) — ADRs that scoped each ops surface
- [quality.md](quality.md) — gates that fire on every release/commit

Last updated: 2026-05-12
