# SRE Escalation Policy

## Level 1: Auto-Repair (No Human Needed)

Fully automated. The SRE agent applies the fix and logs it.

**Actions**:
- Container restarts (application or infrastructure)
- Dependency cascade restarts
- Cache service restarts (Redis/Valkey)
- Disk cleanup (`docker system prune -f`)
- Health check failure recovery (restart + verify)

**Criteria**:
- Action is listed in `auto-repair-actions.md` under "Safe" section
- Action is reversible
- Action does not touch data, code, or configuration files
- Max 3 retries before escalating to Level 3

**Logging**: All Level 1 actions are saved to Engram with topic_key `sre-fix/{container}/{error-type}`

---

## Level 2: Claude Analysis (No Human, But Logged)

The SRE agent performs deeper analysis without human intervention, but does NOT apply
fixes that require approval.

**Actions**:
- Error pattern analysis and classification
- Root cause identification by reading source code and logs
- Cross-referencing with Engram for similar past errors
- Fix proposal generation (stored for human review)
- Correlation analysis (multiple services failing = common cause)

**Criteria**:
- Error is not in the safe auto-repair list
- Error requires understanding of application logic
- Fix may involve code or configuration changes

**Logging**: Analysis saved to Engram with topic_key `sre-analysis/{container}/{error-type}`

---

## Level 3: Human Approval Required

The SRE agent presents findings and proposed fix. Waits for explicit human approval.

**Actions requiring approval**:
- Code changes (any source file modification)
- Database operations (queries, migrations, data fixes)
- Configuration file modifications (.env, docker-compose, etc.)
- Environment variable changes
- Infrastructure changes (network, volumes, ports)
- Message queue operations (purge, rebind)
- Anything not seen before AND requiring non-restart fix
- Any action that failed 3 times at Level 1

**Presentation format**:
```
SRE ALERT: Requires your approval

Service: {container_name}
Error: {error_type} - {error_message}
Root cause: {analysis}
Proposed fix: {description}
Files affected: {list}
Risk: {LOW/MEDIUM/HIGH}
Reversible: {YES/NO}

Approve this fix? (yes/no)
```

---

## Level 4: Emergency (Immediate Human Alert)

Critical situations that need immediate human attention. The SRE agent attempts
Level 1 fixes in parallel but alerts the human regardless.

**Triggers**:
- **All services down**: More than 80% of containers not running
- **Data corruption detected**: Inconsistent state in database logs
- **Security incident**: Unauthorized access attempts, credential exposure in logs
- **Payment processing failures**: Any error in financial transaction flows
- **Sustained high error rate**: More than 50% of requests failing for over 5 minutes
- **Infrastructure failure**: Core infrastructure (database, auth, cache) completely unresponsive after restart
- **Cascade failure**: Restarting one service causes others to fail

**Actions**:
1. Attempt Level 1 auto-repair in parallel
2. Generate detailed incident report
3. Save full context to Engram: `sre-incident/{timestamp}`
4. Alert via terminal output with high-visibility formatting
5. If Telegram integration is configured, send notification

**Incident report format**:
```
!! EMERGENCY -- SRE INCIDENT REPORT !!
Time: {timestamp}
Severity: CRITICAL

Affected services:
- {list of affected containers with status}

Error summary:
- {consolidated error description}

Actions already taken:
- {Level 1 fixes attempted and their results}

Recommended immediate actions:
1. {prioritized list}

Full logs saved to: /tmp/sre-incident-{timestamp}.log
```

---

## Notification Channels

| Level | Channel | Timing |
|-------|---------|--------|
| Level 1 | Health report only | End of scan cycle |
| Level 2 | Health report + Engram log | End of scan cycle |
| Level 3 | Interactive prompt in terminal | Immediately when detected |
| Level 4 | Terminal alert + Telegram (if configured) | Immediately when detected |

## Escalation Timeouts

| From | To | Timeout |
|------|-----|---------|
| Level 1 retry | Level 3 | After 3 failed retries |
| Level 3 waiting | Level 4 | After 10 minutes with no response (if error is CRITICAL) |
| Any level | Level 4 | If error rate exceeds 50% |
