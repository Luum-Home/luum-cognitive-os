<!-- SCOPE: both -->
# Capability Levels — Auto-Disable Components

## Purpose

Higher-capability models do not need the same safety nets as lower-capability ones. Capability levels allow automatic disabling of agentic primitives (hooks, rules) that become redundant when the model is capable enough to handle those concerns internally.

## Levels

| Level | Name | Description |
|-------|------|-------------|
| 1 | basic | All safety nets active. For weaker models that need maximum guardrails. |
| 2 | good | All safety nets active. Model is competent but benefits from all checks. |
| 3 | excellent | Context management disabled. Model handles its own context efficiently. |
| 4 | autonomous | Multiple safety nets disabled. Model is self-correcting and self-aware. |
| 5 | autonomous+ | Most safety nets disabled. For future models that are self-correcting. Session, metrics, security, and error capture remain active. |

## Configuration

In `cognitive-os.yaml`:

```yaml
model_capability:
  level: 3  # 1=basic, 2=good, 3=excellent, 4=autonomous, 5=autonomous+
  auto_disable:
    3: [context-management]
    4: [clarification-gate, assumption-tracking, confidence-gate, model-routing, blast-radius]
    5: [completeness-check, epic-task-detector, scope-proportionality, trust-score-validator,
        claim-validator, tool-loop-detector, consequence-evaluator, infra-intent-detector,
        pre-cleanup-snapshot, architecture-compliance, auto-skill-generator]
```

## Cumulative Disabling

Components disabled at level N remain disabled at level N+1. For example:
- Level 3 disables: `context-management`
- Level 4 disables: `context-management` + `clarification-gate` + `assumption-tracking` + `confidence-gate` + `model-routing` + `blast-radius`
- Level 5 disables: all of the above + `completeness-check` + `epic-task-detector` + `scope-proportionality` + `trust-score-validator` + `claim-validator` + `tool-loop-detector` + `consequence-evaluator` + `infra-intent-detector` + `pre-cleanup-snapshot` + `architecture-compliance` + `auto-skill-generator`

## Hook Integration

Hooks can check capability level by calling `check_capability_level` from `hooks/_lib/common.sh`:

```bash
source "$(dirname "$0")/_lib/common.sh"
check_capability_level "clarification-gate"  # exits 0 if disabled at current level
```

## Python API

The `lib/capability_levels.py` module provides:

| Function | Description |
|----------|-------------|
| `get_capability_level(config_path)` | Read level from config (default: 3) |
| `get_disabled_components(level, config_path)` | List of disabled components at this level |
| `should_component_run(component_name, level, config_path)` | Check if a component should run |
| `format_capability_report(level, config_path)` | Human-readable report |

## Safety

- Core safety rules (user privacy, security, credential management) are NEVER auto-disabled regardless of capability level
- Only performance and quality-of-life components can be disabled
- The `auto_disable` map is configurable per project

### Always-active components (never disabled, even at level 5)

These components are foundational and remain active at every capability level:

| Component | Reason |
|-----------|--------|
| `session-init.sh`, `session-cleanup.sh` | Session lifecycle management |
| `error-pipeline.sh` | Error capture -- foundational for learning |
| `secret-detector.sh` | Security -- never optional |
| `content-policy.sh` | Security -- never optional |
| `result-truncator.sh` | Context protection |
| `completion-gate.sh` | Acceptance criteria verification |
