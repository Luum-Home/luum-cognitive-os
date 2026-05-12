# SO Incident Runbook (ADR-028 D5)

> Audience: on-call operator / orchestrator agent.
> Prerequisites: `scripts/so-vitals.sh` on PATH, `pytest` available.

---

## 1. Symptoms Catalogue

| Symptom | Diagnostic command | Indicator |
|---------|--------------------|-----------|
| Slow session / hook lag | `jq -r '[.duration_ms] | add/length' .cognitive-os/metrics/hook-health.jsonl` | p95 > 2 000 ms for `SessionStart`; p95 > 200 ms for `PreToolUse`; p95 > 500 ms for `PostToolUse` |
| High CPU (hooks / MCP) | `ps aux --sort=-%cpu \| head -20` | Any `claude`/`mcp`/`python3` process > 80 % CPU for > 30 s |
| High RAM | `bash scripts/so-vitals.sh --json \| jq .ram_mib` | `ram_mib` > 300 (SLO 5 breach) |
| Stuck agent / orphan | `bash scripts/so-agent-status.sh` | Agent last heartbeat > 5 min ago; PID in registry but not in `ps` |

---

## 2. Diagnosis Decision Tree

### Step 1 — Collect vitals

```bash
bash scripts/so-vitals.sh --json | tee /tmp/so-vitals-$(date +%s).json | jq .
```

Examine each section and map findings:

| Section | Red flag | Triage path |
|---------|----------|-------------|
| `agents` | `stale_heartbeat: true` or count > expected | → §2.2 Agent issue |
| `processes` | `orphan_count > 0` | → §2.3 Orphan processes |
| `orphans` | Non-empty list | → §2.3 Orphan processes |
| `jsonl` | `growth_mib > 1` for this session | → §2.4 JSONL growth |
| `disk` | `available_mib < 500` | → §2.5 Disk pressure |
| `valkey` | `ping` fails | → §2.6 Valkey down |
| `ram_mib` | > 300 | → §2.7 RAM over SLO |

### Step 2.1 — Hook latency

```bash
# p95 per hook event type (requires jq)
jq -s 'group_by(.hook_event) | map({event: .[0].hook_event, p95: (map(.duration_ms) | sort | .[ceil(length*0.95)-1])})' \
  .cognitive-os/metrics/hook-health.jsonl
```

If p95 exceeds SLO for > 5 consecutive records → consider emergency stop (§3) while
diagnosing which hook is slow.

Identify slow hook:
```bash
jq -s 'sort_by(.duration_ms) | reverse | .[0:5]' .cognitive-os/metrics/hook-health.jsonl
```

### Step 2.2 — Agent issue (stale heartbeat)

```bash
bash scripts/so-agent-status.sh
cat .cognitive-os/metrics/agent-heartbeat.jsonl | tail -5 | jq .
```

If agent is genuinely stuck (no output, PID alive): send SIGTERM, then re-check.
If agent PID is gone but registry entry remains: run reaper manually:
```bash
bash scripts/so-reaper.sh --dry-run   # inspect
bash scripts/so-reaper.sh             # clean
```

### Step 2.3 — Orphan processes

```bash
bash scripts/so-reaper.sh --dry-run
```

If > 0 orphans in registry: `bash scripts/so-reaper.sh` to kill registered expired
processes. If processes outside registry are suspected, investigate manually (reaper
has safe-kill contract — it does NOT touch unregistered PIDs).

### Step 2.4 — JSONL growth

```bash
du -sh .cognitive-os/metrics/*.jsonl | sort -rh | head -10
```

Identify largest file; check if rotation is misconfigured:
```bash
grep 'metrics-rotation' .claude/settings.json
```

### Step 2.5 — Disk pressure

```bash
df -h .
```

Trigger manual rotation / clean old sessions:
```bash
bash scripts/cos-sessions.sh --prune-older-than 7d
```

### Step 2.6 — Valkey down

```bash
valkey-cli ping 2>/dev/null || redis-cli ping 2>/dev/null
```

If no response: check container `docker ps | grep valkey` and restart if needed.
Agent-bus pub/sub is non-critical — sessions degrade gracefully without it.

### Step 2.7 — RAM over SLO

Identify large MCP processes:
```bash
ps aux | grep -E 'mcp|engram|node' | awk '{print $6/1024 " MiB\t" $11}' | sort -rn | head -10
```

Restart MCP server that is leaking (re-registers automatically on next session start).

---

## 3. Kill-Switch Activation

### When to activate

Activate `so-emergency-stop.sh` when **any** of the following is true:

- p95 hook latency is > 3× SLO AND cannot be attributed to a specific hook.
- Orphan processes are accumulating across sessions despite manual reaper runs.
- RAM > 500 MiB and a specific MCP cannot be identified as the cause.
- A hook is known to be issuing destructive operations and cannot be isolated quickly.
- Security incident suspected (credential leak, malformed hook output).

### How to activate

```bash
bash scripts/so-emergency-stop.sh "brief reason here"
```

### What it does

1. Writes `.cognitive-os/runtime/hook-killswitch.flag` with timestamp + reason.
2. Calls `bash scripts/so-reaper.sh` to kill registry-tracked expired processes.
3. Backs up `.claude/settings.json` to `.claude/settings.json.bak`.
4. Calls `bash scripts/set-security-profile.sh minimal` so only the critical
   whitelist fires: `credential-guard.sh`, `license-guard.sh`,
   `pre-compaction-flush.sh`, `session-cleanup.sh`, `self-install.sh`,
   `session-init.sh`.
5. All other hooks self-suppress via `hooks/_lib/killswitch_check.sh` sourced
   at their top.
6. **Does NOT** touch processes outside the registry (safe-kill contract D1.B).
7. **Does NOT** delete data files or modify application code.
8. Exits 0 always; prints restoration instructions to stdout.

### What remains running

- The Claude session itself (user can still interact).
- Critical hooks (see whitelist above).
- MCP servers already running (they are not killed; they just receive no hook events).

---

## 4. Recovery Steps

After the underlying issue is resolved:

```bash
# Step 1 — remove the killswitch flag
rm -f .cognitive-os/runtime/hook-killswitch.flag

# Step 2 — restore full settings
cp .claude/settings.json.bak .claude/settings.json
# OR re-apply default profile:
bash scripts/apply-efficiency-profile.sh default

# Step 3 — re-collect vitals and confirm green
bash scripts/so-vitals.sh --json | jq '{ram_mib,orphan_count,stale_agents}'

# Step 4 — run sanity contract tests
pytest tests/contracts/ -v --tb=short

# Step 5 — confirm no killswitch flag remains
[ ! -f .cognitive-os/runtime/hook-killswitch.flag ] && echo "Killswitch cleared" || echo "FLAG STILL PRESENT"
```

All four steps must pass before declaring the incident resolved.

---

## 5. Postmortem Template

Write a postmortem when **any** of the following occurred:
- Kill-switch was activated.
- A zero-tolerance SLO (process leak, destructive git op, missing test run) was breached.
- Incident lasted > 30 min or affected > 1 user session.

### Postmortem: {short title} — {date}

**1. What happened**
Chronological narrative of the incident: when it was detected, how it manifested,
which SLO was breached, what signals were visible in vitals / metrics.

**2. Blast radius**
Which sessions / users were affected. Were any commits made, files modified, or
external calls made during the degraded window? Was data lost?

**3. Root cause**
The specific hook, process, configuration, or external dependency that caused the
breach. Distinguish proximate cause (what broke) from root cause (why it was
possible to break).

**4. Fix applied**
Exact commands run, files changed, PRs opened. Reference commits by hash.

**5. Prevention**
- [ ] What monitoring / alert would have caught this earlier?
- [ ] What code or configuration change prevents recurrence?
- [ ] What chaos test covers this failure mode? If none: create it.
- [ ] Was a contract test added / updated?
