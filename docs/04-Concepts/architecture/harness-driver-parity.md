# Harness Driver Parity

> How Cognitive OS decides whether Claude, Codex, and future harness drivers are
> actually equivalent enough to carry the same operating-system behavior.

## Current Finding

The committed self-hosting projections are not byte-for-byte equivalent:

- `.claude/settings.json` carries the broad reference surface.
- `.codex/hooks.json` carries the Codex-native projection.

This difference is expected, but it must be governed. Claude Code exposes a
larger and more mature hook surface for tool-level events, subagent events, and
compact-time events. Codex is moving toward more hook coverage, but the local
runtime and public issue history show that tool-level coverage is still
evolving. Cognitive OS should therefore project every behavior the target
driver can safely express and report the rest as capability gaps instead of
copying unsupported events blindly.

## Source Of Truth

The long-term source of truth must not be `.claude/settings.json` or
`.codex/hooks.json`. Those files are driver projections.

The current enforceable capability source is:

```text
manifests/harness-driver-capabilities.yaml
```

It records:

- each driver settings path
- each driver settings shape
- supported, limited, extension, and unsupported hook events
- parity policy for deciding whether a missing hook is a regression or a
  capability gap

## Parity Audit

Run:

```bash
python3 scripts/harness_parity_audit.py --source claude --target codex --strict
```

The audit compares the reference driver against the target driver and reports:

- hooks already projected
- hooks missing on supported target events
- hooks missing on limited target events
- hooks that belong to unsupported target events

`--strict` fails only when the target driver misses a hook on an event marked
`supported`. Limited and unsupported events remain visible but do not fail the
audit, because they represent a roadmap gap rather than a broken projection.

## Current Codex Contract

Codex must project all Cognitive OS hooks for events currently marked
`supported`:

- `SessionStart`
- `UserPromptSubmit`
- `Stop`

That supported surface is enough to auto-load the portable memory lifecycle:

- `SessionStart` starts Engram when available and resumes incomplete task state.
- `UserPromptSubmit` captures relevant user intent asynchronously.
- `Stop` records session learning, git context, changelog, and Engram
  crystallization.

Codex must not blindly project unsupported or incomplete surfaces merely to
match Claude's hook count. Tool-level events such as `PreToolUse` and
`PostToolUse` need a proven Codex driver contract before they can carry
security, quality, or write-coordination guarantees.

Claude currently remains advantaged for two memory-related surfaces:

- `PreCompact` can run `pre-compaction-flush.sh` before context is destroyed.
- `PostToolUse` can run `engram-reinforce-on-access.sh` after Engram reads.

Those hooks are implemented with canonical env resolution so they are ready for
future drivers, but they are not projected into Codex until Codex exposes
equivalent event semantics.

## Why Not Copy Everything?

Copying all Claude hooks into Codex would make the files look aligned while
weakening the product:

- unsupported events may never fire
- limited events may fire for only part of the tool surface
- security gates could appear installed while silently missing the actual write
  path
- future maintainers would mistake a projection artifact for a real guarantee

The product promise is portability with evidence, not matching JSON counts.

## Roadmap

1. Keep `.claude/settings.json` and `.codex/hooks.json` generated from
   canonical driver contracts instead of hand-maintaining one from the other.
2. Extend `scripts/generate-project-settings.sh` so target driver capabilities
   filter generated events.
3. Add a canonical hook registry that describes Cognitive OS intent once:
   event, matcher, script, criticality, supported drivers, and fallback.
4. Implement Codex tool-level projection only after the local Codex version and
   test harness prove `PreToolUse` and `PostToolUse` coverage for the tools we
   depend on.
5. Treat future Cursor/OpenCode/OpenClaw drivers the same way: project from the
   canonical registry through a capability manifest, then audit parity.

## Related Evidence

- [Bootstrap Portability](bootstrap-portability.md)
- [Cross-Harness Authoring](cross-harness-authoring.md)
- [ADR-057: Cross-Harness Authoring and Driver Projection](../adrs/ADR-057-cross-harness-authoring-and-driver-projection.md)
- [ADR-064: Harness-Agnostic Cognitive OS](../adrs/ADR-064-harness-agnostic-cognitive-os.md)

## Governed Fallback Layer

Codex limited surfaces are no longer only a roadmap note. When a missing matcher
protects a high-value action, Cognitive OS can provide a governed runner that
executes the canonical hook chain explicitly. The first implementation is
`scripts/cos_governed_runner.py` with the Codex wrapper `scripts/cos_codex_guard.py`, documented in [Codex Governed Tool Layer](codex-governed-tool-layer.md).

This creates a stricter parity vocabulary:

- **native**: the driver projects and the harness emits the event.
- **governed**: COS wraps the action and runs the canonical hook chain.
- **unsupported**: no safe native or governed path exists yet.

Future Cursor, OpenCode, IDE plugin, and bare-CLI drivers should use the same
classification. Matching Claude Code hook counts is not the goal; preserving the
governance guarantee through either native or governed execution is the goal.
