# Phase-Aware Agent System

The phase system gives agents awareness of the project's lifecycle stage. Instead of making conservative decisions by default, agents adapt their behavior based on whether the project is being rebuilt, stabilized, or running in production.

## The 4 Phases

### reconstruction
Full rebuild mode. Agents are aggressive: they rewrite non-compliant code instead of patching it, break backwards compatibility when standards demand it, and treat architecture violations as blockers. This is the phase for establishing standards.

### stabilization
Standards are established. Agents still rewrite non-compliant code but respect backwards compatibility. Architecture violations generate tasks instead of blocking. Coverage enforcement begins.

### production
Live system. Agents use feature flags for all changes, maintain backwards compatibility, and document risky changes as proposals rather than implementing them directly. Architecture violations are logged but not blocking.

### maintenance
Stable system. Agents only fix bugs and security issues. All improvements are documented as future work. Minimal changes, maximum stability.

## Configuration

The current phase is set in `cognitive-os.yaml`:

```yaml
project:
  name: my-project
  phase: reconstruction    # reconstruction | stabilization | production | maintenance
```

To change the phase, edit the `phase` field. All agents will immediately use the new phase on their next invocation.

## How Phase Affects Agent Behavior

| Behavior | reconstruction | stabilization | production | maintenance |
|----------|---------------|---------------|------------|-------------|
| Break existing patterns | Yes | No | No | No |
| Rewrite over patch | Yes | Yes | No | No |
| Follow standards strictly | Yes | Yes | Yes | Yes |
| Skip backwards compat | Yes | No | No | No |
| Document as future work | No | No | Yes | Yes |
| Auto-remediate architecture | Yes | Yes | No | No |

## Architecture Compliance Checker

The `architecture-compliance.sh` hook (PostToolUse on Agent) automatically checks agent output for violations:

**Detected violations:**
- Using `huma` instead of `ginext`
- Using `chi` directly instead of `ginext` router
- DTOs placed in `domain/dtos/` instead of `application/dtos/`
- App code missing `internal/` prefix

**Phase-dependent response:**
- **reconstruction**: Violations are BLOCKERS. Agent must fix immediately.
- **stabilization**: Violations create tasks for remediation.
- **production/maintenance**: Violations are logged for tracking only.

Violations are logged to `.claude/metrics/architecture-violations.jsonl` for KPI tracking.

## Phase Injection

The `inject-phase-context.sh` hook (PreToolUse on Agent) reads `cognitive-os.yaml` and injects phase-specific rules into every agent's prompt. Agents receive clear instructions about what they can and cannot do in the current phase.

## Auto-Remediation Triggers

When `architecture-compliance.sh` detects violations in reconstruction phase:
1. The violation is logged with timestamp, phase, and details
2. A warning is output to the orchestrator
3. The orchestrator is instructed to have the agent fix the violation before marking the task complete

## KPI Integration

Architecture compliance is tracked as a KPI:
- **Metric**: % of Go services following standard patterns
- **Target**: 100%
- **Alert threshold**: <90%
- **Data source**: `.claude/metrics/architecture-violations.jsonl`

## Transition Guide

| From | To | When |
|------|----|------|
| reconstruction | stabilization | All services follow ginext standard, core patterns established |
| stabilization | production | Coverage targets met, no outstanding architecture violations |
| production | maintenance | Feature development paused, only ops work |
| maintenance | reconstruction | Major overhaul planned |
