# Graphify Phase D Semantic Execution Receipt

Phase D covers Markdown/YAML-heavy slices. This receipt records backend readiness, explicit execution mode, per-slice commands, and outcomes without treating Graphify output as verification evidence.

## Summary

Timestamp: `2026-05-22T16:24:03.225236+00:00`
Backend: `ollama`
Mode: `blocked`
Backend ready: `False`
Backend reason: ollama API is not reachable at http://127.0.0.1:11434

## Slice Results

### `skills`

Output root: `/tmp/cos-graphify-phase-d/skills`
Return code: `2`
Status: `blocked-backend-unavailable`

Command:

```bash
<repo-root>/scripts/cos-graphify-build skills --include-docs --out /tmp/cos-graphify-phase-d/skills --backend ollama --skip-benchmark --timeout-seconds 60 --progress-seconds 10
```

### `rules`

Output root: `/tmp/cos-graphify-phase-d/rules`
Return code: `2`
Status: `blocked-backend-unavailable`

Command:

```bash
<repo-root>/scripts/cos-graphify-build rules --include-docs --out /tmp/cos-graphify-phase-d/rules --backend ollama --skip-benchmark --timeout-seconds 60 --progress-seconds 10
```

### `docs/04-Concepts/architecture`

Output root: `/tmp/cos-graphify-phase-d/docs__04-Concepts__architecture`
Return code: `2`
Status: `blocked-backend-unavailable`

Command:

```bash
<repo-root>/scripts/cos-graphify-build docs/04-Concepts/architecture --include-docs --out /tmp/cos-graphify-phase-d/docs__04-Concepts__architecture --backend ollama --skip-benchmark --timeout-seconds 60 --progress-seconds 10
```

### `docs/02-Decisions/adrs`

Output root: `/tmp/cos-graphify-phase-d/docs__02-Decisions__adrs`
Return code: `2`
Status: `blocked-backend-unavailable`

Command:

```bash
<repo-root>/scripts/cos-graphify-build docs/02-Decisions/adrs --include-docs --out /tmp/cos-graphify-phase-d/docs__02-Decisions__adrs --backend ollama --skip-benchmark --timeout-seconds 60 --progress-seconds 10
```

## Evidence vs Inference

Evidence:

- This receipt records commands and process outcomes for Phase D slices.

Inference boundary:

- Semantic graph output is retrieval support only; source review, tests, ADRs, and rules remain verification evidence.
