# ADR-112 — Codex Governed Tool Layer

<!-- SCOPE: OS -->

## Status

Accepted — 2026-05-02.

## Context

ADR-064 and ADR-081 made Codex a real harness adapter and settings projection,
but Codex still cannot emit every hook surface Claude Code emits. The largest
runtime gaps are not lifecycle events; they are tool-specific gates:

- `PreToolUse:Agent` before sub-agent launch.
- `PostToolUse:Agent` after sub-agent completion.
- `PreToolUse:Edit|Write` and `PostToolUse:Edit|Write` around file mutation.

Treating those gaps as acceptable because "Codex does not support the matcher"
would create false portability. Security, dispatch, snapshot, completeness,
trust-score, rollback, and review behavior would appear present in the OS while
silently not running in Codex-hosted work.

## Decision

Introduce a **governed tool layer** for harnesses that lack native tool matcher
coverage. The generic implementation is:

```text
scripts/cos_governed_runner.py
```

Codex keeps a compatibility wrapper at:

```text
scripts/cos_codex_guard.py
```

The runner reads the canonical `cognitive-os.yaml > harness.hooks` registry,
selects the same hook chain Claude Code would run for a synthetic tool event,
and executes that chain with canonical environment variables:

```text
COGNITIVE_OS_PROJECT_DIR -> CODEX_PROJECT_DIR -> CLAUDE_PROJECT_DIR -> cwd
COGNITIVE_OS_HARNESS=<harness>
```

Supported governed actions:

| Action | Synthetic event | Synthetic tool |
|---|---|---|
| `pre-agent` | `PreToolUse` | `Agent` |
| `post-agent` | `PostToolUse` | `Agent` |
| `pre-edit` | `PreToolUse` | `Edit` |
| `post-edit` | `PostToolUse` | `Edit` |
| `pre-write` | `PreToolUse` | `Write` |
| `post-write` | `PostToolUse` | `Write` |

The runner includes matcherless all-tool hooks by default, then matcher-specific
hooks, preserving the canonical registry order. Exit code `2` remains a block.
Other non-zero hook exits return a non-zero runner status so Codex cannot ignore
broken governance silently.

## Cross-Harness Generalization

This layer is not a Codex special case. Future IDEs and tools should be modeled
with the same three-tier driver strategy:

1. **Native projection** — project events the harness emits with proven
   semantics into the harness settings file.
2. **Governed tool layer** — execute missing but necessary tool chains through a
   runner/wrapper with canonical payloads.
3. **COS runner/control plane** — for harnesses with no reliable hooks, drive
   task, skill, and agent execution entirely through COS-owned commands.

Claude Code remains the reference native projection. Codex uses native lifecycle
and Bash hooks plus the governed tool layer. Future Cursor, OpenCode, IDE
plugins, and bare CLI integrations must declare which tier they use for each
hook surface in `manifests/harness-driver-capabilities.yaml` before claiming
portability.

## Consequences

- Codex can now run the omitted Agent and Edit/Write governance chains without
  pretending they are native Codex hooks.
- Agents must invoke the governed layer around `spawn_agent` and direct file
  mutation until Codex exposes equivalent native matchers.
- The portability claim becomes stricter: an event surface is either native,
  governed by a runner, or explicitly unsupported.
- The same mechanism gives future IDEs a migration path without copying Claude
  settings blindly.

## Acceptance Criteria

- `python3 scripts/cos_governed_runner.py --harness codex pre-agent --list` lists all canonical
  `PreToolUse:Agent` hooks plus matcherless all-tool hooks.
- `python3 scripts/cos_governed_runner.py --harness codex post-agent --list` lists all canonical
  `PostToolUse:Agent` hooks plus matcherless all-tool hooks.
- `python3 scripts/cos_governed_runner.py --harness codex pre-edit --list` and `post-write --list`
  cover file mutation gates omitted from Codex native projection.
- Unit tests prove chain selection and synthetic execution with canonical env.

## Related

- [ADR-064 — Harness-Agnostic Cognitive OS](ADR-064-harness-agnostic-cognitive-os.md)
- [ADR-081 — Codex Harness Adapter](ADR-081-codex-harness-adapter.md)
- [Codex Governed Tool Layer](../architecture/codex-governed-tool-layer.md)


## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Treat Codex matcher gaps as acceptable | Creates false portability by claiming governance exists while tool-specific chains are skipped. |
| Fork separate Codex-only governance logic | Duplicates the canonical hook registry and would drift from Claude Code behavior. |
| Require every harness to implement native hook matchers first | Blocks adoption for otherwise usable harnesses and ignores the runner/control-plane fallback path. |


## Verification

```bash
python3 -m pytest tests/unit/test_codex_guard_layer.py -q
python3 -m pytest tests/contracts/test_session_start_tooling_contract.py -q
```
