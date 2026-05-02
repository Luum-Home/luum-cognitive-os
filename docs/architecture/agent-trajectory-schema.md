# Agent Trajectory Schema

> Status: MVP implemented via ACI capture.

Cognitive OS records normalized tool events as trajectory rows so benchmark and skill-efficacy evaluators can inspect behavior, not just final answers.

## JSONL path

- Session/global metrics: `.cognitive-os/metrics/agent-trajectory.jsonl`
- Hook: `hooks/aci-observation-capture.sh`
- Schema helper: `lib/agent_trajectory.py`

## Fields

| Field | Meaning |
|---|---|
| `timestamp` | Event time. |
| `session_id` | Current session or process fallback. |
| `task_id` | Current task id or session fallback. |
| `tool` | Tool name. |
| `command_class` | Normalized ACI command class. |
| `status` | `success` or `failure`. |
| `exit_code` | Exit code. |
| `summary` | Compact ACI summary. |
| `risk_tags` | Propagated safety tags. |
| `artifact_path` | Full output artifact when applicable. |

## Manual verification

Run a hook payload through `hooks/aci-observation-capture.sh` and confirm both `aci-observations.jsonl` and `agent-trajectory.jsonl` receive a row.
