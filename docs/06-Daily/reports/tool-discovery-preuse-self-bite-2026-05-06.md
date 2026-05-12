# Tool Discovery Pre-Use Self-Bite — 2026-05-06

## Problem

The orchestrator repeatedly picked ad-hoc tools before checking existing COS
primitives. This is not a missing-tool problem; it is a missing-consumer/gate
problem.

## Evidence

| Incident | Existing primitive | Failure |
|---|---|---|
| Skill router false positives | ADR-188 + `skill-bypass.jsonl` | Treated as isolated annoyance instead of telemetry |
| Confidentiality enforcer noise | `secret-detector`, `content-policy`, confidentiality boundary | Treated as one noisy hook |
| License audit | `agentic-tool-license-matrix.sh`, `cos-deps-install.sh`, `/repo-scout`, `/repo-forensics` | Started with stack-specific tools |

## Fix

ADR-216 adds Tool Discovery Pre-Use Gate:

- manifest rules in `manifests/tool-discovery-preuse.yaml`;
- evaluator `lib/tool_discovery_preuse.py`;
- CLI `scripts/cos-tool-discovery-preuse`;
- Bash enforcement through `hooks/skill-router-bash-gate.sh`.

The first hard rule blocks ad-hoc license-audit commands (`pip-licenses`,
`go-licenses`, `license-checker`) and points to COS primitives.

## Follow-up

Future rules should cover additional recurring bypass clusters only after dogfood
evidence, not as a speculative broad NLP classifier.
