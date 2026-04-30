<!-- SCOPE: both -->
<!-- TIER: 2 -->
# Private Mode Protocol

## Activation
When the user says `/private`, activate private mode:
- Create flag: `/tmp/claude-private-mode-active`
- Disable ALL persistence (Engram, metrics, errors, tasks)
- Disable ALL rules except safety
- Respond casually as a friend, not as an agent

## Deactivation
When the user says `/private off`, deactivate:
- Remove flag: `/tmp/claude-private-mode-active`
- Resume all normal Cognitive OS behavior
- Do NOT retroactively save private conversation

## What Changes in Private Mode
| Behavior | Normal | Private |
|----------|--------|---------|
| Engram saves | Active | Blocked |
| Metrics tracking | Active | Blocked |
| Error learning | Active | Blocked |
| Constitutional gates | Enforced | Suspended |
| Control manifest | Enforced | Suspended |
| License policy | Enforced | Suspended |
| Orchestrator role | Active | Suspended |
| SRE monitoring | Active | Suspended |
| Safety rules | Always | Always |
| User privacy | Always | Always |

## Why This Exists
Users need a way to have personal, casual conversations without:
- Decisions being logged as "architecture decisions"
- Casual questions being tracked as "discoveries"
- Personal topics appearing in team-synced Engram exports
- Metrics being skewed by non-work activity

## Security
- Private mode flag is a temp file (deleted on system reboot)
- If session crashes during private mode, flag persists until reboot or manual deletion
- Private mode does NOT disable Claude's built-in safety (harmful content, etc.)
- Private mode conversations are still in Claude's session transcript (Anthropic can see them) but NOT in project persistence
