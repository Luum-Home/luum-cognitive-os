<!-- SCOPE: os-only -->
---
name: docs-execution-audit
description: "Use when you need this Cognitive OS skill: Classify documentation items as done, weak-proof, planned, proposed, stale, or unknown using repository evidence.; do not use when a narrower skill directly matches the task."
invoke: /docs-execution-audit
tag: os-only
model: haiku
audience: os-dev
effort: haiku
summary_line: Audit what the docs say is done vs what repo evidence proves.
version: "1.0.0"
platforms: ["claude-code", "codex"]
prerequisites: []
routing_patterns:
  - pattern: '\bdocs[- ]?execution[- ]?audit\b'
    confidence: 0.95
  - pattern: '\bclassify\s+documentation\s+items?\b'
    confidence: 0.8
  - pattern: '\bdoc\s+evidence\s+audit\b'
    confidence: 0.75
---

# Documentation Execution Audit

Run:

```bash
python3 scripts/docs_execution_audit.py \
  --json-out docs/06-Daily/reports/docs-execution-latest.json \
  --md-out docs/06-Daily/reports/docs-execution-latest.md
```

Use this when asking what remains across all documentation, what is stale, or what is marked done without enough proof.

## Contextual Trigger

Use when the user asks: qué está hecho, qué falta, docs stale, documentación pendiente, roadmap reality, docs execution coverage.
