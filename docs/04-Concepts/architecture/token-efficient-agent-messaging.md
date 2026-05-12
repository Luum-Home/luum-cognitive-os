# Token-Efficient Agent Messaging

## Purpose

Cognitive OS treats sub-agent output as a constrained interface, not as prose to reread. The goal is to preserve status, files, tests, findings, blockers, and trust score while avoiding raw transcript reads and unbounded notification bursts.

## Architecture

| Layer | Durable source | LLM-facing rendering | Implementation |
|---|---|---|---|
| Agent final result | Agent text output | `RESULT:` + `TRUST_REPORT:` contract | `templates/agent-preamble.md`, `lib/return_contract_parser.py` |
| Agent transcript | JSONL output file | extracted assistant text + compact result | `lib/agent_output_extractor.py` |
| Agent notifications | in-memory digest entries / metrics | bounded digest, newest rows + totals | `lib/notification_digest.py` |
| Structured records | JSON/JSONL storage | Markdown table, TSV, or `key=value` | `lib/format_converter.py` |
| Large command output | raw tool output | command-aware summaries | `lib/smart_truncator.py` |
| Repeated stable prompts | provider request messages | cacheable prompt segments | `lib/prompt_cache.py` |

Storage remains JSONL where auditability matters. The optimization happens only at the LLM-context boundary.

## Contract

```text
RESULT:
  status: completed|failed|partial
  summary: [1-2 sentences]
  files_created: [paths or none]
  files_modified: [paths or none]
  tests: [N passed, N failed]
  blockers: [none, or reason if partial/failed]

TRUST_REPORT: SCORE=<0-100> STATUS=<HIGH|MEDIUM|LOW|CRITICAL> EVIDENCE=<N> UNCERTAINTIES=<N>
```

`lib/return_contract_parser.py` also accepts the older Workstream 2 shape with uppercase keys, `FILES_CHANGED`, `KEY_FINDINGS`, `BLOCKERS`, and `TOKENS_ESTIMATE`. This compatibility is intentional because archived plans, tests, and older agents may still emit that form.

## Format choices

- Use `key=value` for a single record or a small nested object.
- Use TSV for agent-only lists of more than three uniform records.
- Use Markdown tables for human-facing lists where visual scanning matters.
- Do not use binary formats such as MessagePack/CBOR/protobuf for LLM context unless a future benchmark proves an LLM-facing benefit.

## Orchestrator reading protocol

1. Prefer the task notification `<result>` field.
2. If a JSONL transcript must be inspected, use `lib/agent_output_extractor.py`; do not read raw JSONL into context.
3. Keep `compact_result` when present; fall back to assistant text only when the agent did not provide a parseable contract.
4. Batch many completions through `NotificationDigest.format_digest()` so bursts stay bounded.

## Validation

```bash
python3 -m pytest \
  tests/unit/test_return_contract_parser.py \
  tests/unit/test_agent_output_extractor.py \
  tests/unit/test_notification_digest.py \
  tests/unit/test_format_converter.py \
  tests/unit/test_completion_gate_perf.py -q
```
