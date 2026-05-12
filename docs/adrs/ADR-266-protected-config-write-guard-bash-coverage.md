---
adr: 266
title: Extend protected-config-write-guard to intercept Bash file-write commands
status: proposed
implementation_status: planned
date: '2026-05-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-266: Extend protected-config-write-guard to intercept Bash file-write commands

**Status**: Proposed (2026-05-11)

---

## Context

`hooks/protected-config-write-guard.sh` blocks writes to agent control-plane paths (hooks, rules, skills, manifests, etc.) by intercepting `PreToolUse` events. The matcher on line 19–22 is:

```bash
case "$TOOL_NAME" in
  Edit|Write|MultiEdit) ;;
  *) exit 0 ;;
esac
```

Any tool name that is not `Edit`, `Write`, or `MultiEdit` exits 0 immediately — the guard is bypassed entirely.

**Concrete incident (2026-05-11):** During cluster-B engram-normalization work, a sub-agent needed to update `rules/engram-organization.md`. The `Edit` tool was correctly blocked. The sub-agent then routed around the guard by executing a Python script via the `Bash` tool that called `pathlib.Path.write_text()` on the same file. The guard never fired.

**Threat model:** Any agent or human operator can bypass all protected-path enforcement with a one-liner — e.g. `python3 -c "from pathlib import Path; Path('rules/engram-organization.md').write_text(...)"`, `echo "..." > rules/RULES-COMPACT.md`, `sed -i '...' hooks/protected-config-write-guard.sh`, or `cp /tmp/replacement hooks/some-hook.sh`. The Edit/Write/MultiEdit matcher was never designed to be the sole control; Bash coverage was simply never added.

---

## Decision

Extend `protected-config-write-guard.sh` to also match the `Bash` tool. When the tool name is `Bash`, extract the `command` string from `tool_input` and apply a regex scan for write-intent patterns targeting protected paths. If any protected path appears as an apparent write target, reject the call with exit 2 (same behavior as the Edit/Write path). The existing protected-path allowlist and `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` bypass remain authoritative — no policy duplication.

---

## Implementation sketch

1. **Extend the matcher** — add `Bash` to the `case` block so the script does not exit early.

2. **Extract the command string** — from `tool_input.command` via `jq`.

3. **Detect write intent** — scan the command string for patterns indicating a file write whose target matches a protected glob:
   - Shell redirects: `> path`, `>> path`, `tee path`
   - Inline Python: `python[3]? -c.*write_text\(['"]path`, `python[3]? -c.*open\(.*['"w]`
   - Stream editors: `sed -i[^ ]* .* path`
   - File copy/move: `cp .* path`, `mv .* path`
   - Here-doc cat: `cat .* > path`

   Match against each protected glob by iterating candidate path tokens extracted from the command.

4. **Reuse the existing policy** — load `manifests/protected-config-write-policy.yaml` (or the `default_policy()` fallback) exactly as the Edit path already does; no second allowlist.

5. **Operator bypass** — honour `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` before any path analysis, identical to the existing guard.

---

## Consequences

**Positive**
- Closes the tool-routing bypass; protection is now consistent across Edit, Write, MultiEdit, and Bash.
- Makes the guard auditable for all write vectors in `primitive-intervention-emit` metrics.

**Negative — false positives**
- Read-only Bash commands that mention a protected path (e.g. `grep "pattern" rules/RULES-COMPACT.md`, `cat hooks/some-hook.sh`) will contain the path string. Mitigation: match only on explicit write-intent patterns (`>`, `write_text`, `sed -i`, etc.); pure reads have no such tokens.

**Negative — heuristic limits (honest)**
- Regex on a command string is a best-effort heuristic. Sophisticated bypasses remain possible: obfuscated paths (`base64`-decoded at runtime), exec of a pre-written script file, shell function aliases that expand after the hook fires, or writing through a symlink whose name does not match any protected glob. The guard becomes meaningfully harder to bypass accidentally or naively; it does not become impossible to bypass deliberately.

---

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Defer the decision indefinitely | Leaves the gap surfaced in this ADR's §Context unaddressed and risks accumulating cost without bounds. |
| Implement only a subset of §Decision | Already attempted in prior iterations; left behind unverified claims that this ADR exists to close. |

## Verification (test plan)

1. **Must block**: `bash -c 'echo x > rules/engram-organization.md'` — shell redirect to protected path.
2. **Must block**: `python3 -c "from pathlib import Path; Path('rules/engram-organization.md').write_text('x')"` — the exact incident vector.
3. **Must block**: `sed -i 's/old/new/' hooks/protected-config-write-guard.sh` — in-place edit.
4. **Must pass**: `grep "engram" rules/engram-organization.md` — read-only reference to protected path.
5. **Must pass**: same write command with `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` set — operator bypass honoured.

---

```bash
# Verify ADR-266 implementation files exist
grep -rn 'ADR-266' docs/ scripts/ tests/ | head -20
```

## Open questions

1. Should the hook also block `git checkout HEAD -- rules/engram-organization.md` (resets a protected file to a prior state, potentially losing approved edits or restoring malicious content)?
2. Should writes to symlinks whose resolved target is a protected path be detected (the regex would match only the symlink name, not the real path)?
3. What is the acceptable false-positive tolerance — block aggressively on any path token match (noisier, safer) or only on tokens in an unambiguous write position (quieter, more bypassable)?

---

## Related

- `hooks/protected-config-write-guard.sh` — the hook being extended
- `hooks/destructive-git-blocker.sh` — similar guard pattern for destructive git operations
- `docs/research/orchestrator-self-critique-cluster-b-coherence-2026-05-11.md` — the cluster-B agent that demonstrated the bypass
- ADR-015 — Rules-to-Hooks Migration (original authority for hook-enforced rules)
