---
adr: 189
title: Surface Implementation Coverage for Agentic Primitives
status: accepted
implementation_status: implemented
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation/shipped/delivered evidence
---

# ADR-189: Surface Implementation Coverage for Agentic Primitives

## Status

Accepted — 2026-05-06
Updated — 2026-05-06: expanded from IDE harness coverage to surface coverage while preserving `primitive_harness_coverage.py` and the legacy `harnesses` JSON key for compatibility.

## Context

ADR-019 and the scope-classification governance primitive classify every agentic primitive by intended audience:

```text
os-only | project | both
```

That axis is necessary but not sufficient. A primitive marked `both` can be valid for both the Cognitive OS repository and consumer projects while still not being implemented the same way in every agent IDE, CLI, CI, UI, service, or report surface. Claude Code and Codex are the forcing IDE example: Claude Code exposes runtime events such as `SubagentStart`, `PreCompact`, `TeammateIdle`, and task events that Codex does not currently expose through the same hook projection surface. Conversely, Codex has dedicated adapter hooks.

The same issue exists outside IDEs. `cos status`, `cos coverage`, and primitive coverage reports are CLI/report surfaces with exit-code and JSON contracts. A dashboard is a UI surface that can observe reports without operating hooks. Treating all implementation as “wired hook” would undercount CLI/UI/report support and overclaim IDE parity.

## Decision

Add a mandatory implementation axis based on surfaces:

```text
scope: os-only | project | both
×
family: hook | skill | rule | script | template
×
surface_kind: ide-harness | cli | shell-ci | ui | service | report
×
surface_id: claude | codex | cursor | cos-cli | shell-ci | dashboard | tui | acc-report | etc.
×
state: installed | projected | wired | executable | behavior-proven | observable | operable | json-contract | exit-code-contract
```

The canonical machine-readable report remains, for compatibility:

```text
docs/06-Daily/reports/primitive-harness-coverage-latest.json
```

The generator also remains:

```bash
python3 scripts/primitive_harness_coverage.py --project-dir .
```

Compatibility rule: existing consumers may keep reading `harnesses`; new consumers should read `surfaces` and `surface_kind`.

## Surface roles

| Surface kind | Meaning | Runtime hook required? |
|---|---|---|
| `ide-harness` | IDE/agent host projection such as Claude, Codex, Cursor, VS Code Copilot, OpenCode, Cline, Aider. | Only for hook primitives that claim lifecycle execution. |
| `cli` | `cos` command surface with exit-code and JSON/human output contracts. | No. |
| `shell-ci` | Non-interactive shell/CI command projection. | No. |
| `ui` | Dashboard/TUI surface that observes or operates OS reports/primitives. | No; must declare observe-only vs operable. |
| `service` | Long-running service/API surface. | Only if the service exposes lifecycle events. |
| `report` | Generated report consumed by ACC, dashboard, or agents. | No. |

## Current surface IDs

| Surface ID | Kind | Current role |
|---|---|---|
| `claude` | `ide-harness` | Native lifecycle hook, rule, and skill projection. |
| `codex` | `ide-harness` | Codex hook/settings projection where equivalent events exist, plus Codex adapters. |
| `cursor`, `vscode-copilot`, `opencode`, `cline`, `aider`, etc. | `ide-harness` | Structural projection unless native runtime proof is recorded. |
| `shell-ci` | `shell-ci` | Command projection for CI/shell execution. |
| `cos-cli` | `cli` | `cos status`, `cos coverage`, and `cos primitive harness-coverage` command contracts. |
| `dashboard` | `ui` | Observe-only UI that consumes generated reports. |
| `tui` | `ui` | Not reported as implemented until a real TUI exists. |
| `acc-report` | `report` | ACC/report surface consuming primitive harness/surface coverage. |

## CLI coverage contract

The CLI surface is proven by commands that exit with a stable code and, where declared, emit JSON:

```bash
bash scripts/cos status --json
bash scripts/cos coverage --json
bash scripts/cos primitive harness-coverage --print-json
```

`cos coverage` routes to `scripts/cos-coverage`. `cos primitive harness-coverage` and `cos primitive surface-coverage` route to `scripts/primitive_harness_coverage.py`.

## UI coverage contract

The dashboard is observe-only until an operation path is explicitly added. Its contract is:

- it consumes `docs/06-Daily/reports/primitive-harness-coverage-latest.json`;
- it exposes primitive surface counts and gap counts;
- it does not claim hook execution or mutation authority;
- a future TUI must declare the same observe-only vs operable distinction before being counted.

## State semantics

| State | Meaning |
|---|---|
| `installed` | The primitive file exists in the measured project/source tree. |
| `projected` | A surface exposes the primitive structurally, as a command, as a report row, or as UI-visible state. |
| `wired` | A runtime hook, report pipeline, or UI/report consumer is connected to the surface. |
| `executable` | The primitive can be invoked as an executable script/hook. |
| `behavior-proven` | Automated or manual tests reference the primitive directly enough to count as behavior evidence. |
| `observable` | A CLI/UI/report surface can show the primitive or its aggregate state. |
| `operable` | A CLI/UI/service surface can mutate or execute the primitive intentionally. |
| `json-contract` | The surface has a JSON output contract. |
| `exit-code-contract` | The surface has a documented process exit-code contract. |

## Consequences

- `SCOPE: both` no longer implies equal behavior across Claude, Codex, CLI, UI, and reports.
- CLI-only, UI-observable, report-only, shell-CI, and IDE-event-native primitives can be represented without forcing all support into “wired hook”.
- ACC and dashboards can consume the same report and state whether gaps are parity bugs, acceptable event asymmetries, structural-only support, or CLI/report-only support.
- The legacy script/report name remains stable to avoid breaking current automation.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `python3 scripts/primitive_harness_coverage.py --project-dir .` writes JSON and Markdown reports.
2. Each row includes scope, family, harness states, surface states, coverage, gap, gap policy, gap severity, and gap status.
3. The report includes `surface_kind` and `surface_id` for every measured surface.
4. `cos status --json`, `cos coverage --json`, and `cos primitive harness-coverage --print-json` exit 0 and emit JSON.
5. Dashboard code consumes the same primitive harness/surface coverage report in observe-only mode.
6. Unit and contract tests prove IDE, CLI, shell-CI, report, and UI surface semantics.
```

## Verification

```bash
python3 -m pytest tests/unit/test_primitive_harness_coverage.py tests/contracts/test_primitive_harness_coverage_contract.py tests/contracts/test_cos_cli_surface_contract.py -q
python3 scripts/primitive_harness_coverage.py --project-dir .
bash scripts/cos status --json
bash scripts/cos coverage --json
bash scripts/cos primitive harness-coverage --print-json
```

## Alternatives rejected

- Treat every primitive as a hook-runtime item only; rejected because CLI, UI, report, and shell-CI surfaces would be misreported as harness gaps.
