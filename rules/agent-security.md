<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Agent Security — Least Privilege Protocol

## Principle of Least Privilege

Every agent gets ONLY the access needed for its specific task. No broad permissions, no permanent access, no inherited escalation.

## Permission System

Use `lib/agent_permissions.py` to manage agent access. The orchestrator MUST grant scoped permissions before launching any sub-agent and revoke them on task completion.

### Permission Levels

| Level | Name | Access | Use Case |
|-------|------|--------|----------|
| 0 | NONE | No access | Default for unknown agents |
| 1 | READ | Read files only | Research, analysis, exploration |
| 2 | SUGGEST | Suggest changes (dry-run) | Plan review, code review |
| 3 | WRITE | Modify files | Documentation, implementation |
| 4 | EXECUTE | Run commands + modify files | Testing, building, SDD phases |
| 5 | ADMIN | Full access | Orchestrator only |

### Permission Profiles

| Profile | Level | Tools | Paths | TTL |
|---------|-------|-------|-------|-----|
| `readonly` | READ | Read, Glob, Grep | `**/*` | 60 min |
| `documentation` | WRITE | Read, Write, Edit, Glob, Grep | `docs/*.md`, `*.md`, `skills/*/SKILL.md` | 30 min |
| `implementation` | EXECUTE | Read, Write, Edit, Glob, Grep, Bash | `**/*` (blocks hooks/, rules/, .claude/) | 60 min |
| `sdd_phase` | EXECUTE | Read, Write, Edit, Glob, Grep, Bash, Agent | `**/*` | 120 min |
| `security_audit` | READ | Read, Glob, Grep, Bash | `**/*` | 30 min |

## Time-Scoped Access

All permissions auto-expire. Default: 30 minutes, maximum: 120 minutes. Expired grants are automatically denied and cleaned up. No permanent grants exist.

## Always-Blocked Paths

These paths are NEVER accessible regardless of permission level or profile:

```
.env, .env.*, *.key, *.pem, *.p12,
secrets/*, **/credentials*, **/password*, .git/config
```

Even ADMIN-level agents cannot read or write these paths. Agents requiring secrets MUST use `lib/secret_ref.py` (SecretRef) to resolve values from environment variables at runtime.

## Monotonic Attenuation

Sub-agents inherit AT MOST the parent's permissions. They can NEVER escalate:
- Child level <= parent level
- Child tools subset of parent tools
- Child TTL <= parent remaining TTL
- Child blocked paths include all parent blocked paths

Use `AgentPermissionManager.create_child_grant()` to enforce this.

## Audit Trail

Every access check is logged to `.cognitive-os/metrics/access-audit.jsonl` with: timestamp, agent_id, action, target, permission_level, granted (bool), reason. Call `flush_audit_log()` at session end.

## Credential Handling

- NEVER pass plaintext secrets in agent prompts or config
- Use `SecretRef` objects: `{"source": "env", "id": "API_KEY"}`
- Resolve at runtime via `lib/secret_ref.py`
- Mask resolved values in logs via `mask_secrets()`

## Post-Task Cleanup

When a task completes (success or failure), the orchestrator MUST call `revoke(agent_id)`. At session end, call `revoke_all()` to clear all remaining grants.

## Phase Behavior

| Phase | Over-Privilege Action |
|-------|----------------------|
| reconstruction | WARN — log advisory, proceed |
| stabilization | WARN — log advisory, proceed |
| production | BLOCK — deny excess permissions |
| maintenance | BLOCK — deny excess permissions |

## Integration

- **Agent Identity** [`agent-identity`]: Trust levels map to max permission levels (0->NONE, 1->READ, 2->WRITE, 3->EXECUTE)
- **Agent Customization** [`agent-customization`]: `tools_allowed` in customization files align with permission profiles
- **Credential Management** [`credential-management`]: SecretRef replaces all plaintext credential handling
