---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/so-incident-runbook.md
provenance: "ADR-028 D5 on-call runbook giving the operator/orchestrator a symptoms catalogue, diagnosis decision tree, kill-switch procedure, recovery checklist, and postmortem template for SO health incidents."
---

## What it is

The operational incident-response runbook for the Cognitive OS itself (SO = "sistema operativo"), covering symptom triage, a structured diagnosis tree, an emergency kill-switch, recovery steps, and a mandatory postmortem template.

## Key mechanics

- Symptoms catalogue maps four symptom classes to diagnostic commands and SLO indicators: slow session/hook lag (p95 > 2000ms SessionStart / 200ms PreToolUse / 500ms PostToolUse via `hook-health.jsonl`), high CPU (`ps aux` > 80% for > 30s), high RAM (`so-vitals.sh` `ram_mib` > 300, SLO 5 breach), stuck/orphan agents (`so-agent-status.sh`, heartbeat > 5 min stale).
- Diagnosis decision tree starts with `bash scripts/so-vitals.sh --json`, then routes by section: `agents.stale_heartbeat` → §2.2, `orphan_count > 0` → §2.3, `jsonl.growth_mib > 1` → §2.4, `disk.available_mib < 500` → §2.5, `valkey.ping` failure → §2.6, `ram_mib > 300` → §2.7. Each sub-section gives exact `jq`/shell commands: hook p95 per event type, stale-heartbeat SIGTERM-then-reaper flow (`so-reaper.sh --dry-run` then live), orphan process cleanup (reaper has a safe-kill contract — never touches unregistered PIDs), JSONL rotation checks, disk-pressure session pruning, Valkey ping/restart (agent-bus pub/sub is non-critical, sessions degrade gracefully), and MCP RAM-leak identification/restart.
- Kill-switch activation triggers: p95 latency > 3x SLO unattributable to a specific hook, accumulating orphans despite manual reaper runs, RAM > 500MiB with no identifiable MCP cause, a hook issuing destructive ops that can't be isolated quickly, or a suspected security incident.
- `so-emergency-stop.sh "reason"` writes a killswitch flag with timestamp/reason, runs the reaper, backs up `.claude/settings.json`, applies the `minimal` security profile (only `credential-guard.sh`, `license-guard.sh`, `pre-compaction-flush.sh`, `session-cleanup.sh`, `self-install.sh`, `session-init.sh` remain active — all other hooks self-suppress via `hooks/_lib/killswitch_check.sh`), never touches unregistered processes or deletes data/code, and always exits 0.
- Recovery is a strict 5-step sequence: remove the killswitch flag, restore `.claude/settings.json` (from backup or via `apply-efficiency-profile.sh default`), re-collect vitals, run `pytest tests/contracts/`, then confirm the flag is gone — all four checks must pass before declaring resolution.
- Postmortem is mandatory when the kill-switch was activated, a zero-tolerance SLO was breached (process leak, destructive git op, missing test run), or the incident lasted > 30 min / affected > 1 session. Template has five sections: what happened, blast radius, root cause (proximate vs. root), fix applied, prevention (checklist: monitoring gap, code/config fix, chaos-test coverage, contract test).

## Relations & where used

Implements ADR-028 D5; depends on `scripts/so-vitals.sh`, `scripts/so-agent-status.sh`, `scripts/so-reaper.sh`, `scripts/so-emergency-stop.sh`, `scripts/apply-efficiency-profile.sh`, `hooks/_lib/killswitch_check.sh`, and `tests/contracts/`.

## Status / caveats

None found — a stable, internally consistent operational procedure with no dated point-in-time claims.
