# Tooling Update Protocol

Guide for safely updating tools that integrate with Claude Code (MCP servers, hook
binaries, plugin executables). Distilled from the engram MCP outage of 2026-04-27.

## When to Use This Protocol

Use this guide whenever you update a tool that:

- Is declared as an MCP server in Claude Code's plugin configuration
- Is invoked by a Claude Code hook (PostToolUse, PreToolUse, Stop)
- Has a binary that Claude Code (or the macOS Operon sandbox) executes directly

Examples: `engram`, custom MCP servers, hook scripts referencing external binaries.

---

## The 3-Paths Trap

`which <tool>` only reports the **first** match in `$PATH`. If the same binary name
exists in multiple locations, the one that executes depends on PATH order — and that
order may differ between your shell session and Claude Code's spawned subprocess.

**Diagnosis:**
```bash
which -a engram          # show every location in PATH
ls -la $(which -a engram)  # check whether any are symlinks
```

If you see more than one result, determine which copy Claude Code is actually using:
```bash
python3 scripts/check_mcp_servers.py  # shows resolved path + version for each MCP
```

**Remediation:** consolidate to one canonical binary by symlinking every extra location
to the authoritative install:
```bash
# Example: brew canonical as authority
CANONICAL="$(brew --prefix)/bin/engram"
ln -sf "$CANONICAL" ~/.local/bin/engram
ln -sf "$CANONICAL" ~/go/bin/engram
```

---

## MCP Server Restart Requirement

MCP servers are spawned **once at Claude Code startup**. Neither editing the plugin
config nor replacing the binary on disk affects a running session.

After any binary change you must:

1. **Quit Claude Code completely** — `cmd-Q` on macOS (not just closing the window or
   tab). The MCP process must be terminated.
2. **Reopen Claude Code.** The new binary is spawned fresh.
3. **Verify** with `python3 scripts/check_mcp_servers.py`.

This is the single most common reason an upgrade appears to succeed but has no effect.

---

## Brew vs go install vs Manual Installer

| Situation | Preferred method | Why |
|---|---|---|
| macOS + Homebrew available | `brew install/upgrade` | Gatekeeper-trusted; survives macOS Operon sandbox in Claude Code's execution context |
| Linux CI or macOS without Homebrew | `go install` (for Go tools) | No brew available; standard Go toolchain path |
| Binary-only release (no tap, no Go source) | Download release asset, verify checksum | Only option when neither brew nor go install applies |
| Updating via `go install` after already having brew | Avoid — creates a second binary at `~/go/bin/` | Use `brew upgrade` to stay on one canonical path |

**Always run `brew update` before checking or installing** — the tap formula version
can lag upstream by one or two releases without a tap refresh.

---

## Verification Post-Update

After updating any MCP binary and restarting Claude Code:

```bash
# 1. Confirm the right binary is resolved
which -a <tool>

# 2. Check version
<tool> version   # or --version

# 3. Run the MCP health checker
python3 scripts/check_mcp_servers.py

# 4. (For engram) confirm memory tools are reachable in-session
#    — try any mem_search call; if it returns results, the MCP is live
```

Expected output from `check_mcp_servers.py` when healthy:
```
MCP Server Health
  engram    binary=/opt/homebrew/bin/engram  version=1.14.5  process=running  status=OK
```

Exit code 0 = all servers healthy. Exit code 1 = at least one issue detected.

---

## Rollback

The `deps-update.sh` script backs up the binary before replacing it:
- Brew path: `<original-path>.v<old-version>.bak`
- go path: `~/go/bin/engram.v<old-version>.bak`

To roll back:
```bash
# Example: restore engram 1.10.2
cp ~/.local/bin/engram.v1.10.2.bak ~/.local/bin/engram
# Quit and reopen Claude Code
```

If no backup exists, retrieve the previous release asset from GitHub releases and
reinstall: `brew install gentleman-programming/tap/engram@1.10.2` or
`go install github.com/Gentleman-Programming/engram/cmd/engram@v1.10.2`.

---

## Living Example: engram 2026-04-27 Case Study

**Symptoms**: `mem_search`, `mem_save`, and all engram MCP tools failed silently.
The MCP server appeared registered but returned no results.

**Root causes found:**
1. Three physical copies of `engram` existed across PATH (`~/go/bin/`, `~/.local/bin/`,
   `/opt/homebrew/bin/`). `which engram` showed only `~/go/bin/engram` (v1.13.1).
2. v1.13.1 was SIGKILL'd by macOS Operon sandbox when spawned from Claude Code.
3. `brew info` showed v1.12.0 (stale) until `brew update` refreshed the tap to v1.14.5.
4. `spctl -a -v` reported "rejected" for v1.13.1 but that alone does not predict
   SIGKILL — the sandbox kill came specifically from Claude Code's execution context.

**Fix applied:**
```bash
brew update
brew install gentleman-programming/tap/engram   # installed 1.14.5
cp ~/.local/bin/engram ~/.local/bin/engram.v1.10.2.bak
cp ~/go/bin/engram ~/go/bin/engram.v1.13.1.bak
ln -sf /opt/homebrew/bin/engram ~/.local/bin/engram
ln -sf /opt/homebrew/bin/engram ~/go/bin/engram
# Quit Claude Code (cmd-Q) and reopened
```

Full observation saved to Engram under topic key `tooling/engram-mcp-fix` (ID #13280).
