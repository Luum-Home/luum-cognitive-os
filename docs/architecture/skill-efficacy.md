# Skill Efficacy Measurement

> Status: MVP implemented.

Cognitive OS measures whether skills help rather than assuming every skill is valuable.

## Metrics

| Metric | Meaning |
|---|---|
| `skill_invocations` | Skill-enabled runs. |
| `paired_baselines` | Matched no-skill runs for the same task fingerprint. |
| `task_success_delta` | Success with skill minus matched baseline success. |
| `cost_delta_usd` | Cost with skill minus matched baseline cost. |
| `latency_delta_seconds` | Latency with skill minus matched baseline latency. |
| `tool_call_delta` | Tool calls with skill minus baseline. |
| `regression_rate` | Fraction of skill runs marked as regressions. |
| `security_findings` | Security findings attributed to skill runs. |
| `net_value_score` | Weighted score used to classify `high-value`, `watch`, or `negative-value`. |

## Runtime surface

- Library: `lib/skill_efficacy.py`
- Report: `scripts/skill_efficacy_report.py`
- Tests: `tests/unit/test_skill_efficacy.py`
