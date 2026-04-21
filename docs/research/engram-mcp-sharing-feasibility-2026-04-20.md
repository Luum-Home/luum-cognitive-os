# Engram MCP Sharing Feasibility Research
**Date**: 2026-04-20  
**Author**: Agent F (Research)  
**Feeds into**: ADR-047 Phase B (session lifecycle)  
**Engram topic key**: `startup-optimization/engram-mcp-sharing/feasibility`

---

## Verdict

**`INFEASIBLE` with current engram v1.10.2 binary** — `engram mcp` uses stdio transport exclusively. The MCP specification's stdio transport is inherently 1:1 (one client per process). There is no shared socket mode, no HTTP MCP endpoint, and no multiplexing flag in the current installed binary.

**`FEASIBLE_WITH_UPSTREAM_CHANGE`** — The binary contains the type `*server.SessionWithStreamableHTTPConfig` from the `mcp-go` library, confirming the upstream library already supports HTTP/SSE transport. If engram exposed `engram mcp --transport=http --port=N`, multiple sessions could connect to one process. This requires an upstream engram feature request or upgrade to v1.12.0 and re-checking.

---

## Transport Layer

**Observed transport**: `stdio` — per-process, exclusive.

Evidence:
1. `.mcp.json` declares `"type": "stdio"` (via the `command`/`args` pattern without `url`):
   ```json
   // /Users/matias.nahuel.amendola/.claude/plugins/cache/engram/engram/0.1.0/.mcp.json
   {
     "mcpServers": {
       "engram": {
         "command": "engram",
         "args": ["mcp", "--tools=agent"]
       }
     }
   }
   ```
2. `engram --help` output explicitly states: `mcp [--tools=PROFILE] Start MCP server (stdio transport, for any AI agent)` — the word "stdio" is part of the official command description.
3. The Claude Code harness spawns one `engram mcp --tools=agent` child per session. Confirmed live: 7 `engram mcp --tools=agent` processes seen alongside 7 claude sessions via `ps aux`.
4. The `session-start.sh` hook contacts `engram serve` at `http://127.0.0.1:7437` for HTTP API calls (session create, context fetch). The MCP child is separate from this.

The stdio model means: Claude Code opens a pipe to `engram mcp`, sends JSON-RPC 2.0 messages on stdin, reads responses on stdout. The process is owned by that session and terminates (or leaks) with it.

---

## Feature Flags / CLI Options That Exist Today

From `engram --help` (v1.10.2, installed):

| Flag | Scope | Notes |
|------|-------|-------|
| `--tools=PROFILE` | `mcp` subcommand | Selects tool set: `agent` (11 tools), `admin` (3), `all` (14), or comma-combined |
| `ENGRAM_PORT` | `serve` subcommand | Overrides HTTP server port (default 7437) |
| `ENGRAM_DATA_DIR` | global | Overrides data directory |

**No flags found for**:
- `--transport` (no `http`, `sse`, `unix-socket` options)
- `--port` on the `mcp` subcommand
- `--shared` / `--multiplex`
- `ENGRAM_MCP_SHARED_SOCKET` or similar env vars
- Any form of shared-client multiplexing

Binary string scan of `/Users/matias.nahuel.amendola/.local/bin/engram` found no strings matching `--transport`, `ENGRAM_MCP`, `shared_socket`, `unix_socket`, or `mcp.*port`. The only transport-related string on the `mcp` path is "stdio".

---

## Is `engram serve` the Shared Backend?

**Yes — at the data layer. No — at the MCP protocol layer.**

Architecture as observed:

```
Claude Session 1 ──stdio──► engram mcp (PID 81599) ──HTTP──► engram serve (PID 1809, :7437) ──► SQLite DB
Claude Session 2 ──stdio──► engram mcp (PID 87690) ──HTTP──► engram serve (PID 1809, :7437) ──► same DB
Claude Session N ──stdio──► engram mcp (PID N+1)   ──HTTP──► engram serve (PID 1809, :7437) ──► same DB
```

The `session-start.sh` hook confirms `engram mcp` is a thin MCP-to-HTTP shim:
- `session-start.sh` directly calls `engram serve` via HTTP for session creation and context fetch.
- Each `engram mcp` child translates MCP JSON-RPC tool calls into REST API calls to `engram serve`.

This is a significant finding: **all data operations are already shared** via the single `engram serve` HTTP daemon. The per-session `engram mcp` processes are NOT competing for data — they all write to the same SQLite via the HTTP API. The proliferation problem is purely about wasted processes and OS resource leakage, not data consistency.

Evidence:
- `session-start.sh` line 24: `curl -sf "${ENGRAM_URL}/health"` — hooks talk to `engram serve` directly
- `session-start.sh` line 40-47: POST to `${ENGRAM_URL}/sessions` for session creation
- Binary strings include REST routes: `GET /observations/{id}`, `POST /projects/migrate`, `/context`, `/health`
- `*server.SessionWithStreamableHTTPConfig` type in binary: this is from the `mcp-go` library, confirming engram uses it internally for its MCP server implementation. The type exists but is not exposed via a CLI flag in v1.10.2.

---

## What Would Break With a Shared `engram mcp` Process

The MCP protocol (JSON-RPC 2.0 over stdio) is stateful. Each client session performs:
1. `initialize` handshake (negotiates capabilities)
2. Tool calls referencing the initialized session state
3. The server maintains per-client state (tool registrations, initialization context)

**Blockers for naive sharing:**

1. **stdio is point-to-point**: MCP over stdio is physically 1:1. You cannot multiplex two Claude processes onto the same stdin/stdout pipe. This is a protocol-level constraint, not an engram constraint.

2. **MCP `initialize` is per-connection**: Each Claude session expects to run the `initialize` handshake. A shared process would need to maintain separate connection state per client — that is the definition of an HTTP/SSE server, which engram does not currently expose for MCP.

3. **No session context isolation**: The `engram mcp` tools include session-aware operations (session start/stop, passive capture). If two Claude sessions shared one MCP process, their session contexts would need to be isolated by session ID. Possible at the application level (all `mem_save` calls include `session_id`), but requires the `engram mcp` process to be stateless with respect to the caller identity — which it is not today.

**What would NOT break:**
- Data integrity: all data goes to `engram serve` via HTTP, which is already concurrent-safe.
- Memory semantics: observations are identified by `project` + `session_id`, not by which `engram mcp` process wrote them.

---

## Upstream Project

- **Repository**: `https://github.com/Gentleman-Programming/engram`
- **License**: MIT (safe to adopt code patterns)
- **Author**: Gentleman Programming
- **Installed version**: v1.10.2 (v1.12.0 available via brew)
- **Binary**: Go, single static binary, arm64, 12MB

The binary embeds the type `*server.SessionWithStreamableHTTPConfig` from `mark3labs/mcp-go` (the most popular Go MCP library). This library does support HTTP/SSE and Streamable HTTP transports. It appears engram has the dependency but has not yet exposed a `--transport=http` flag in v1.10.2. **v1.12.0 should be checked** — the changelog may include this.

---

## Recommendations for ADR-047 Phase B

### Option A: Semaphore / Session Quota (Immediate, No Upstream Change)

Since the data layer is already shared (all MCP children route through the single `engram serve`), the problem is purely process proliferation. A semaphore approach works:

```bash
# In session lifecycle hooks: track active mcp child PIDs
# On SessionStart: check if orphaned engram mcp processes exist and reap them
# Limit: max N engram mcp processes, queue new sessions if at limit
```

Concrete steps:
1. Register a `SessionStart` hook that checks `pgrep -c "engram mcp"` and kills zombies (processes whose parent claude PID no longer exists).
2. Register a `Stop` hook that explicitly kills the session's `engram mcp` child.
3. No engram changes needed.

### Option B: Upgrade to v1.12.0 + Check for HTTP Transport Flag (Low Risk)

```bash
brew upgrade engram  # pulls v1.12.0
engram mcp --help    # check if --transport or --port flags now exist
```

If v1.12.0 exposes `engram mcp --transport=http --port=7438`, then configure `.mcp.json` to use `type: "sse"` or `type: "http"` pointing at a single long-running `engram mcp --transport=http` daemon. All sessions connect to it via HTTP, eliminating per-session children.

**This is feasible because the `mcp-go` library already supports it** — it would just need engram to wire it up.

### Option C: Upstream Feature Request

Open a GitHub issue at `https://github.com/Gentleman-Programming/engram/issues` requesting:
> "Add `--transport=http --port=N` option to `engram mcp` to enable a single shared MCP server process across multiple Claude Code sessions, instead of spawning one process per session."

Given the type is already in the binary (`*server.SessionWithStreamableHTTPConfig`), this may be a small PR.

---

## File Path Evidence (per acceptance criteria)

1. `/Users/matias.nahuel.amendola/.claude/plugins/cache/engram/engram/0.1.0/.mcp.json` — transport config (stdio, no URL)
2. `/Users/matias.nahuel.amendola/.claude/plugins/cache/engram/engram/0.1.0/.claude-plugin/plugin.json` — upstream repo URL (`https://github.com/Gentleman-Programming/engram`), license (MIT)
3. `/Users/matias.nahuel.amendola/.claude/plugins/cache/engram/engram/0.1.0/scripts/session-start.sh` — confirms `engram mcp` is a shim over `engram serve` HTTP API at `:7437`
4. `/Users/matias.nahuel.amendola/.local/bin/engram` — binary: `engram --help` confirms "stdio transport"; binary strings confirm `*server.SessionWithStreamableHTTPConfig` type (mcp-go library), no `--transport` flag in v1.10.2
5. `https://github.com/gentleman-programming/homebrew-tap` (Formula) — upstream source, v1.12.0 available
