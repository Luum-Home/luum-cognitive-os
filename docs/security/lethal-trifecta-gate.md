# Lethal Trifecta Gate

> Status: MVP implemented. Core is deterministic, dependency-free, and safe to run before tools execute.

## Purpose

The gate protects against one action combining private data access, untrusted content exposure, and external communication or side effects.

## Decision table

| Private data | Untrusted content | External communication | Decision |
|---|---|---|---|
| yes | yes | yes | Block with exit 2 |
| yes | no | yes | Warn |
| no | yes | yes | Warn |
| yes | yes | no | Warn |
| otherwise | otherwise | otherwise | Allow |

## Runtime surfaces

| Surface | File |
|---|---|
| Classifier | `lib/lethal_trifecta.py` |
| Hook | `hooks/lethal-trifecta-gate.sh` |
| Metrics | `.cognitive-os/metrics/lethal-trifecta.jsonl` |
| Unit tests | `tests/unit/test_lethal_trifecta.py` |
| Contract tests | `tests/contracts/test_lethal_trifecta_gate.py` |

## Design constraints

- No external dependency is required on the hot path.
- Optional scanners such as Snyk Agent Scan, promptfoo, garak, or Augustus may enrich red-team lanes but are not required for the block.
- Every evaluated action writes a canonical MetricEvent row.
