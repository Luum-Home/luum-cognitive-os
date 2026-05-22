# Manual Test — Token Savings Paired Benchmark

## Purpose

Corroborate Cognitive OS token-savings claims against local real projects without leaking repository names, paths, domain details, customer names, or sensitive code.

This benchmark has two layers:

1. **Structural audit** — read-only local estimate of prompt/context footprint.
2. **Paired live run** — same task run in vanilla mode and SO mode, with provider token/cost telemetry and a quality receipt.

Reports MUST anonymize projects as `project-001`, `project-002`, etc. Do not publish local paths or repository names.

## Privacy rules

- Never write absolute project paths into committed docs.
- Never include project names in public reports.
- Never include code snippets, proprietary domain terms, secrets, customer names, ticket IDs, or branch names.
- Use `scripts/cos-token-savings-audit` without `--show-paths` for shareable reports.
- If a report needs path details for local debugging, keep it uncommitted and pass `--show-paths` only locally.

## Project selection

Choose 2–3 local projects that already have at least one SO marker:

- `cognitive-os.yaml`
- `.cognitive-os/`
- `AGENTS.md`
- `.claude/settings.json`

Prefer small/medium tasks that are real but non-sensitive:

1. identify repository purpose and validation command;
2. find the smallest trustworthy test/check command;
3. plan a small documentation update using repo conventions.

## Structural audit command

From the Cognitive OS repo:

```bash
scripts/cos-token-savings-audit --root "$HOME/Projects" --limit 3 --write
```

Expected outputs, path-redacted by default:

```text
.cognitive-os/reports/token-savings-audit-anonymized.json
.cognitive-os/reports/token-savings-audit-anonymized.md
```

The structural report compares:

- estimated vanilla prompt/context tokens;
- estimated SO prompt/context tokens;
- files that would be read in each mode;
- estimated savings.

It does **not** prove live retries, provider cost, or answer quality.

## Paired live run protocol

For each anonymized project and each selected task, run two passes.

### Pass A — vanilla mode

Disable SO affordances in the task prompt and environment:

- no memory-first lookup;
- no micro catalog;
- no result truncation advantage;
- no context diet;
- prompt/manual governance only;
- no Engram lookup unless the vanilla baseline would have it.

Record:

```yaml
project_id: project-001
task_id: orientation
mode: vanilla
prompt_tokens: ACTUAL_OR_ESTIMATED
tool_output_tokens: ACTUAL_OR_ESTIMATED
files_read_count: N
retries: N
provider_cost_usd: ACTUAL_OR_ESTIMATED
quality_status: pass|partial|fail
quality_notes: redacted summary only
```

### Pass B — SO mode

Enable SO affordances:

- project SO context installed;
- micro/compact catalogs as designed;
- memory-first lookup when relevant;
- context budget and truncation hooks active where supported;
- context diet for Agent/subagent payloads where supported.

Record the same fields:

```yaml
project_id: project-001
task_id: orientation
mode: so
prompt_tokens: ACTUAL_OR_ESTIMATED
tool_output_tokens: ACTUAL_OR_ESTIMATED
files_read_count: N
retries: N
provider_cost_usd: ACTUAL_OR_ESTIMATED
quality_status: pass|partial|fail
quality_notes: redacted summary only
```

## Comparison fields

For each pair, compute:

```text
total_tokens = prompt_tokens + tool_output_tokens
token_savings = vanilla_total_tokens - so_total_tokens
token_savings_percent = token_savings / vanilla_total_tokens
file_read_delta = vanilla_files_read_count - so_files_read_count
retry_delta = vanilla_retries - so_retries
cost_delta_usd = vanilla_cost_usd - so_cost_usd
quality_delta = compare pass/partial/fail and notes
```

## Acceptance criteria

A publishable benchmark receipt must satisfy:

1. At least 2 projects and 2 tasks per project.
2. Project names and paths redacted.
3. No proprietary code or domain details copied into the report.
4. Both vanilla and SO modes use the same task statement.
5. Token/cost source is labeled as actual provider telemetry, hook ledger, or estimate.
6. Quality is recorded as pass/partial/fail with redacted rationale.
7. Any claim over 70% savings includes the specific baseline condition that caused it, such as full-rule loading or repeated rediscovery.

## Reporting language

Use:

> In this anonymized paired benchmark, SO mode reduced measured token use by X%–Y% across N tasks, while preserving or improving quality in M/N cases.

Do not use:

> Cognitive OS always saves X%.

## Related tooling

- `scripts/cos-token-savings-audit`
- `scripts/cos-preamble-budget`
- `scripts/cos-context-budget-report`
- `docs/04-Concepts/architecture/token-savings-qa.md`
