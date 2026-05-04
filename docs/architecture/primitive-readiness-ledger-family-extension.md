# Primitive Readiness Ledger Family Extension Plan

> Follow-on plan for extending the script readiness ledger pattern to hooks, skills, and rules without weakening the script baseline.

## Current Baseline

`ADR-146` implements the first family ledger for `scripts/`. The generated reports are:

- `docs/reports/primitive-readiness-ledger-scripts-latest.json`
- `docs/reports/primitive-readiness-ledger-scripts-latest.md`
- `docs/reports/primitive-readiness-lifecycle-backlog-scripts-latest.json`
- `docs/reports/primitive-readiness-lifecycle-backlog-scripts-latest.md`

The script ledger now has explicit overrides for formerly low-confidence rows in `manifests/primitive-readiness-script-overrides.yaml`. The protected install/profile/projection surfaces have ADR-126 `candidate` lifecycle entries first because they can affect downstream SO installation by profile or harness. The remaining script lifecycle backlog is still active and must be worked from `docs/reports/primitive-readiness-lifecycle-backlog-scripts-latest.json`, not inferred from chat history.

The script ledger also emits `consumer_accessibility`, because SO-local documentation is not automatically visible to downstream projects. Future family ledgers should carry the same distinction between repository-local evidence and consumer-project availability.

## Protected install/profile surfaces

Before working normal lifecycle debt, keep `priority: protected` rows ahead of high-priority rows. These rows manage automatic primitive installation, profile application, or harness projection and require profile-projection review before any demotion/archive/downgrade. The first script pass added candidate lifecycle metadata for the protected rows; future hook/skill/rule ledgers should use the same protected-first ordering when profile projection is involved.

## Extension Order

1. **Hooks** — highest runtime risk because hooks can block, mutate, or slow tool calls.
2. **Skills** — primary agent-facing UX and shared/project package boundary.
3. **Rules** — doctrine/context/enforcement boundary; many rules should link to hooks or remain context-only.

## Family-Specific Role Sets

### Hooks

| Role | Meaning |
|---|---|
| `runtime-safety` | Blocking or advisory runtime guard. |
| `observability` | Metrics/logging/telemetry hook. |
| `memory-lifecycle` | Session, Engram, compaction, recovery, or summary lifecycle hook. |
| `driver-specific` | Harness-specific projection or compatibility hook. |
| `lab` | Experimental or maintainer-only hook. |
| `archive` | Deprecated/unprojected hook candidate. |

### Skills

| Role | Meaning |
|---|---|
| `shared-agent-tool` | Skill intended for all projects/agents once packaged. |
| `so-maintainer` | Maintainer-only SO operation skill. |
| `project-extension` | Project-specific or package-local extension. |
| `compatibility-wrapper` | Skill wrapping a script/hook/driver. |
| `lab` | Experimental skill. |
| `archive` | Deprecated skill candidate. |

### Rules

| Role | Meaning |
|---|---|
| `hook-enforced` | Rule excluded from context because a hook enforces it. |
| `context-only` | Behavioral guidance loaded for agents. |
| `doctrine` | Durable architecture/product policy not directly enforced. |
| `driver-specific` | Rule only valid for specific harnesses. |
| `lab` | Experimental governance language. |
| `archive` | Superseded/deprecated rule. |

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. Each new family ledger emits JSON and Markdown.
2. Every target in the family receives one allowed role.
3. Each row includes role_source, confidence, consumers, evidence, lifecycle metadata when present, and next_action.
4. Optional fail flags exist but default command remains advisory for the first baseline.
5. Unit tests cover synthetic classification; contract tests cover repository completeness.
6. The continuity plan links the family ledger once implemented.
```

## Non-Goals

- Do not force all hooks/skills/rules into one generic role taxonomy.
- Do not fail the repository on first-pass low-confidence rows.
- Do not claim universal IDE support from a local ledger alone; harness support still requires capability profiles and proof paths.

## Next Implementation Slice

Implement `--target-family hooks` in the readiness ledger or create `scripts/primitive_readiness_hooks_ledger.py` if the taxonomy diverges too much from scripts. Prefer extending the existing CLI only if the code stays readable.
