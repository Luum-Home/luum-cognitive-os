<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Auto-Repair System

## Always Active

The auto-repair system monitors errors and applies known fixes autonomously.

### How it works
1. **Error detected** → error-learning.sh captures to JSONL
2. **Dispatcher fires** → auto-repair-dispatcher.sh classifies error
3. **Registry lookup** → checks remediation-registry for known fix
4. **Execute** → applies fix in isolated git worktree
5. **Verify** → runs build/test/lint in worktree
6. **Merge or discard** → success merges, failure discards + records

### Phase autonomy
- reconstruction/stabilization: full auto-repair (code + LLM + infra)
- production/maintenance: infra-only (restart, cache clear)

### Circuit breaker
- 2 consecutive failures per error_type:service → OPEN (block repairs)
- Global cap: 10 repairs/hour
- Cooldown: 1 hour, then HALF-OPEN (allow 1 attempt)

### Never auto-repaired
- Database migrations
- Authentication/authorization changes
- Payment/billing code
- Environment variables (.env files)
- Docker compose configuration
- Git history (rebase, force push)
- Security-sensitive files
- Third-party API integration changes

### Monitoring
- `metrics/repair-outcomes.jsonl` — all repair attempts
- `metrics/remediation-registry.jsonl` — known fix database
- `metrics/circuit-breaker/` — breaker state per error:service
- `/cognitive-os-status` reports repair stats in health check
