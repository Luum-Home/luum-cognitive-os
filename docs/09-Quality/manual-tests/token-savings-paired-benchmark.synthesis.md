---
type: quality-synthesis
source: docs/09-Quality/manual-tests/token-savings-paired-benchmark.md
provenance: "Defines the paired-benchmark protocol for corroborating Cognitive OS token-savings claims against real local projects while protecting project identity and proprietary content."
---

## What it is
A manual test protocol for producing a defensible, anonymized token-savings benchmark: a structural (read-only) audit layer plus a paired live-run layer comparing vanilla mode against SO (Cognitive OS) mode on the same task.

## Key mechanics
- **Privacy rules**: reports must anonymize projects as `project-001`, `project-002`, etc.; no absolute paths, repository/customer/project names, code snippets, proprietary terms, or ticket/branch names in committed docs; use `scripts/cos-token-savings-audit` without `--show-paths` for shareable output.
- **Project selection**: 2-3 local projects with an existing SO marker (`cognitive-os.yaml`, `.cognitive-os/`, `AGENTS.md`, `.claude/settings.json`); prefer small/medium, non-sensitive tasks (identify repo purpose + validation command, find smallest trustworthy check, plan a small doc update).
- **Structural audit**: `scripts/cos-token-savings-audit --root "$HOME/Projects" --limit 3 --write`, producing path-redacted `token-savings-audit-anonymized.{json,md}` comparing estimated vanilla vs. SO prompt/context tokens and files read; explicitly does not prove live retries, cost, or answer quality.
- **Paired live run**: Pass A (vanilla — no memory-first lookup, no micro catalog, no truncation advantage, no context diet, prompt/manual governance only) vs. Pass B (SO — project context installed, micro/compact catalogs, memory-first lookup, context budget/truncation hooks, context diet); both record `prompt_tokens`, `tool_output_tokens`, `files_read_count`, `retries`, `provider_cost_usd`, `quality_status`, `quality_notes` (redacted).
- **Comparison fields**: `token_savings`, `token_savings_percent`, `file_read_delta`, `retry_delta`, `cost_delta_usd`, `quality_delta`.
- **Acceptance criteria**: >=2 projects x >=2 tasks each; names/paths redacted; no proprietary content; same task statement across modes; token/cost source labeled (actual telemetry, hook ledger, or estimate); quality recorded pass/partial/fail; any claim over 70% savings must cite the specific baseline condition that caused it.
- **Reporting language**: mandates a ranged, conditioned claim ("SO mode reduced measured token use by X%-Y% across N tasks...") and explicitly forbids an unconditioned absolute claim ("Cognitive OS always saves X%").

## Relations & where used
Related tooling: `scripts/cos-token-savings-audit`, `scripts/cos-preamble-budget`, `scripts/cos-context-budget-report`, and `docs/04-Concepts/architecture/token-savings-qa.md`.

## Status / caveats
Protocol/methodology document, not a run log — no benchmark results are embedded in the source. Repeatable procedure that produces its own dated, anonymized artifacts when executed.
