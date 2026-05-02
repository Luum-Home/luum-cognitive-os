# Codex Governed Tool Layer

> Alternative enforcement layer for Codex surfaces that do not have native
> Agent or Edit/Write hook matchers.

## Problem

Codex projects supported lifecycle hooks and Bash tool hooks through
`.codex/hooks.json`. That is honest, but incomplete. The most valuable Cognitive
OS gates are attached to tool-specific surfaces that Codex does not currently
emit natively:

- Agent launch: dispatch, clarification, blast radius, phase context,
  working-directory injection, tailored context, pre-agent snapshot,
  prelaunch tracking, error-pattern detection, completeness, reinvention, and
  native heartbeat.
- Agent completion: claim validation, completion gate, checkpoint, trust score,
  confidence, rollback, work queue sync, feedback tracking, auto repair,
  dequeue notification, state heartbeat, and review spawning.
- File mutation: secret detection, docs convention, edit locks, content policy,
  frontmatter/header/ADR validation, confidentiality, surface-fix detection,
  doc sync, and parked edit-lock draining.

Without an alternative layer, Codex-hosted work loses those guarantees.

## Implementation

Use:

```bash
python3 scripts/cos-codex-guard.py pre-agent --prompt "..."
python3 scripts/cos-codex-guard.py post-agent --prompt "..." --output @agent-result.txt
python3 scripts/cos-codex-guard.py pre-edit --file-path path/to/file --content @new-content.txt
python3 scripts/cos-codex-guard.py post-write --file-path path/to/file --content @written-content.txt
```

The command reads `cognitive-os.yaml > harness.hooks`, selects hook entries by
canonical event and matcher, and runs them with a synthetic hook payload. It
sets `COGNITIVE_OS_HARNESS=codex` and canonical project env so older hooks that
still read `CLAUDE_PROJECT_DIR` remain compatible while the portability cleanup
continues.

`--list` shows the exact scripts the action would run without executing them.
This is the operator-facing audit surface and the contract used by tests.

## Required Codex Operating Protocol

Until Codex has native Agent/Edit/Write hook coverage, a Codex-hosted agent must
follow this protocol:

1. Before using `spawn_agent`, run `pre-agent` with the delegated task prompt.
2. After the spawned agent returns, run `post-agent` with the original prompt and
   the agent result.
3. Before large or sensitive direct file mutation, run `pre-edit` or `pre-write`
   with the intended file path and content.
4. After mutation, run `post-edit` or `post-write` for validation and metrics.
5. Treat exit code `2` as a hard block. Do not bypass it by manually performing
   the underlying action.

## Future IDE/Tool Pattern

Every new harness should classify each surface as one of:

| Tier | Meaning | Example |
|---|---|---|
| Native projection | Harness emits the event directly and settings driver projects it. | Claude Code `PreToolUse:Agent` |
| Governed runner | Harness lacks the event, but COS can wrap the action explicitly. | Codex `pre-agent` |
| COS-owned runtime | Harness has no reliable hook model; COS executes the whole workflow. | Bare CLI `cos-agent spawn` |
| Unsupported | No safe native or governed path exists yet. | Unverified IDE events |

The product rule is: **do not claim portability for a surface until it is native
or governed and tested.**

## Validation

```bash
python3 -m pytest tests/unit/test_codex_guard_layer.py -q
python3 scripts/cos-codex-guard.py pre-agent --list
python3 scripts/cos-codex-guard.py post-agent --list
python3 scripts/cos-codex-guard.py pre-edit --list
python3 scripts/cos-codex-guard.py post-write --list
```

## Related

- [ADR-112 — Codex Governed Tool Layer](../adrs/ADR-112-codex-governed-tool-layer.md)
- [Harness Driver Parity](harness-driver-parity.md)
- [Bootstrap Portability](bootstrap-portability.md)
