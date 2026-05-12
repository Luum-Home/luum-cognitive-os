---
adr: 216
title: Tool Discovery Pre-Use Gate
status: accepted
implementation_status: implemented
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: 'tool-discovery pre-use manifest, evaluator CLI, Bash gate integration, and tests implement the gate'
---

# ADR-216 — Tool Discovery Pre-Use Gate

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted  
**Date**: 2026-05-06  
**Related**: ADR-188, ADR-208, ADR-212  
**Source**: repeated dogfood evidence of ad-hoc external tool selection over existing COS primitives

---

## Context

Three times in one session, the orchestrator bypassed existing Cognitive OS
primitives and reached for mainstream/ad-hoc tools first:

1. Skill-router false positives were treated as isolated suggestions instead of
   using ADR-188 `skill-bypass.jsonl` evidence.
2. Confidentiality-enforcer behavior was treated as a noisy hook instead of
   checking the broader `secret-detector` / `content-policy` boundaries.
3. License audit started as a `pip-licenses + go-licenses + license-checker`
   chain even though COS already had `agentic-tool-license-matrix.sh`,
   `cos-deps-install.sh`, `/repo-scout`, and `/repo-forensics` primitives.

The root cause is model bias: defaulting to internet-known tools rather than
first asking, "what primitive does this OS already provide?"

ADR-208 gates dependency adoption. ADR-188 gates ignored high-confidence skills.
This ADR gates raw tool use before Bash execution.

## Decision

Add a manifest-backed Tool Discovery Pre-Use Gate. When a Bash command matches
an ad-hoc external tool pattern for a task with a known COS primitive, the gate
must either:

1. block and point to the canonical primitive;
2. warn when the match is low-risk/research-only;
3. allow explicit operator override with `COS_ALLOW_TOOL_DISCOVERY_BYPASS=1`.

Initial P1 rule: block stack-specific license-audit tools such as
`pip-licenses`, `go-licenses`, and `license-checker` unless the command is using
COS's canonical license/adoption primitives.

## Enforcement

- Policy lives in `manifests/tool-discovery-preuse.yaml`.
- Core evaluator lives in `lib/tool_discovery_preuse.py`.
- CLI lives in `scripts/cos-tool-discovery-preuse` and route
  `cos tool-discovery preuse --command CMD`.
- Existing `hooks/skill-router-bash-gate.sh` calls the evaluator for Bash
  commands, keeping skill/tool-use preflight in one Bash gate.

## Consequences

### Positive

- Prevents the exact license-audit ad-hoc chain from recurring.
- Creates a low-friction path to add more primitive-first rules as dogfood
  evidence accumulates.
- Keeps bypasses explicit and auditable.

### Negative / trade-offs

- Adds another Bash preflight check.
- False positives are possible for commands used only to compare tools; override
  is intentionally explicit.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_tool_discovery_preuse.py tests/behavior/test_tool_discovery_preuse_gate.py -q
scripts/cos tool-discovery preuse --command 'pip-licenses --format=json' --json
```

Tests must prove ad-hoc license-audit commands block, canonical COS primitives
pass, and explicit operator override passes.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
