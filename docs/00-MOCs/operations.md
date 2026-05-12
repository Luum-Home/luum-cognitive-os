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

## Related MOCs

- [decisions.md](decisions.md) — ADRs that scoped each ops surface
- [quality.md](quality.md) — gates that fire on every release/commit

Last updated: 2026-05-12
