---
title: "MegaMemory Annex D — Explorer UX & Multi-Editor Installer"
date: 2026-05-11
parent: docs/03-PoCs/research/megamemory-comparison-2026-05-11.md
source-repo: ".cognitive-os/external-source-cache/MegaMemory (v1.6.2)"
---

> **License attribution.** Code excerpts and structural descriptions quoted from `0xK3vin/MegaMemory` v1.6.2 (MIT License, Copyright (c) 2026 0xk3vin — see https://github.com/0xK3vin/MegaMemory/blob/main/LICENSE). MIT permits direct vendoring with copyright preservation. See [`megamemory-annex-f-compliance-cleanroom-2026-05-11.md`](megamemory-annex-f-compliance-cleanroom-2026-05-11.md) for the full compliance protocol and port-vs-vendor decisions.

# Annex D — Explorer UX & Multi-Editor Installer

Two operator-experience surfaces that have no direct Engram equivalent: the
D3-force / Canvas graph explorer (`megamemory serve`) and the multi-target
installer (`megamemory install --target opencode|claudecode|antigravity|codex`).

---

## 1. The graph explorer

### 1.1 Architecture

- Single-binary `megamemory serve` HTTP server: `src/web.ts` (791 LoC).
- Static front-end: `web/index.html` (single file, no build step, no bundler).
- D3 v7.9.0 loaded from CDN (`web/index.html:7`): `https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js`.
- Rendering: HTML5 `<canvas id="graph">` (`web/index.html:478`) with manual 2D drawing inside D3's force-simulation tick callback. Not SVG.

### 1.2 Force simulation (`web/index.html:912-922`)

```js
simulation = d3.forceSimulation([])
  .force('charge', d3.forceManyBody()
    .strength(d => d._hasChildren ? -500 : -300).distanceMin(20).distanceMax(800))
  .force('center', d3.forceCenter(width / 2, height / 2).strength(0.02))
  .force('collision', d3.forceCollide()
    .radius(d => d.radius + 35).strength(0.7).iterations(3))
  .force('link', d3.forceLink([])
    .id(d => d.id)
    .distance(d => d.isParentEdge ? 120 : 260)
    .strength(d => d.isParentEdge ? 0.35 : 0.12));
```

Standard D3 force-directed layout. Distinctly: **parent edges are tighter and stronger** than relation edges, producing visible cluster centers. The Canvas-not-SVG choice is the right call for >500 nodes — DOM nodes get expensive fast.

### 1.3 Endpoints (`src/web.ts`)

Inspected briefly via grep. The server exposes endpoints feeding the front-end: node list, edge list, search (`understand` reused), get-by-id (`getConcept` reused). It uses the same `KnowledgeDB` + `embeddings` modules as the MCP server. **No duplicate query logic** — the explorer and the MCP server share their library functions, which is healthy.

### 1.4 Operator UX

- Run `megamemory serve` → opens `http://localhost:4321`.
- Banner prints DB path + URL + Ctrl-C hint (`src/web.ts:55-64`).
- Port collision: auto-retry by prompting for a new port (`listenWithRetry`, `src/web.ts:71+`).

### 1.5 COS analogue

**None today.** The closest is ADR-258's `.ai/` portable overlay (read-only file surface), which is not interactive. Engram has no graph visualizer.

### 1.6 Verdict

| Dimension | MegaMemory | COS | Verdict |
|---|---|---|---|
| Interactive graph view | Yes, single-binary, no build | None | **EXTERNAL_BETTER** |
| Operator setup cost | One command | n/a | — |
| Reuse of query layer | Yes (shared library functions) | n/a | — |
| Production-ready | At <10k nodes | n/a | — |
| **Is this a current COS requirement?** | — | **No** | Park as a future "operator tools" lane. |

### 1.7 If we ever want one

Two paths:

1. **Reuse this code directly (vendor under MIT).** Cost: pulls in a Node runtime as an operator dependency. Bad fit for a Python-first project.
2. **Re-implement.** A FastAPI endpoint serving a static HTML page with D3 + Canvas, fed by Engram's existing `mem_search`/`mem_get_observation` + a new `mem_graph` endpoint that returns node/edge JSON. Estimated 3-5 days of work for parity with the MegaMemory explorer.

Neither path is justified by current demand. Re-evaluate if an "Engram explorer" appears in user requests.

---

## 2. The multi-editor installer

### 2.1 Targets

From `src/install.ts:8` and `src/install.ts:552`:

```ts
export type InstallTarget = "opencode" | "claudecode" | "antigravity" | "codex";

const VALID_TARGETS: InstallTarget[] = [
  "opencode", "claudecode", "antigravity", "codex"
];
```

Four editors / agent harnesses, each with bespoke wiring (`src/install.ts:499-549` — `createTargetConfigs`).

### 2.2 Per-target wiring

**opencode** (`src/install.ts:501-516`):

- Config: `~/.config/opencode/opencode.json` (with `$schema` set to `https://opencode.ai/config.json`).
- AGENTS.md instruction snippet appended to `~/.config/opencode/AGENTS.md`.
- Tool plugin copied to `~/.config/opencode/tool/megamemory.ts` (the file is the `plugin/megamemory.ts` from the package, marked with the `MANAGED_FILE_MARKER` comment so future installs can detect "safe to overwrite").
- Commands copied to `~/.config/opencode/commands/{bootstrap-memory,merge}.md`.

**claudecode** (`src/install.ts:518-533`):

- Config: `~/.claude.json` (uses the JSONC parser at `src/install.ts:73-140` to strip comments).
- CLAUDE.md instruction snippet appended to `~/.claude/CLAUDE.md`.
- Commands copied to `~/.claude/commands/`.
- MCP wiring: registers a server entry under `mcpServers` keyed `megamemory`, pointing at the resolved entrypoint (`node /path/to/dist/index.js` or globally-installed `megamemory`).

**antigravity** (`src/install.ts:534-540`):

- Config: `./mcp_config.json` in project cwd (per Antigravity's per-project model).

**codex** (`src/install.ts:541-549`):

- Config: `~/.codex/config.toml`.
- AGENTS.md instruction appended to `~/.codex/AGENTS.md`.
- Best-effort `codex mcp add megamemory -- node /path/...` via the codex CLI (`src/install.ts:479-490`); falls back to direct TOML write if the CLI fails.

### 2.3 Managed-file marker pattern (`src/install.ts:52-54`)

```ts
const AGENTS_MD_MARKER = "## Project Knowledge Graph";
const MANAGED_FILE_MARKER =
  "MegaMemory-managed file. Safe for megamemory install to update.";
```

- Idempotent appends: if the marker already exists, **skip** (`src/install.ts:252-260`).
- Non-managed existing files left untouched with a WARN (`src/install.ts:286-292`).

This is **good defensive design** for installers that mutate user dotfiles. Worth borrowing.

### 2.4 JSONC parser (`src/install.ts:73-140`)

A hand-rolled JSONC stripper (line + block comments, string-aware). Avoids a runtime dep. Useful pattern for any tool that needs to read VS Code-style config files but does not want to depend on `jsonc-parser`.

### 2.5 Self-discovery (`src/install.ts:206-234`)

```ts
async function detectGlobalCommand(): Promise<CommandRuntime> {
  // which megamemory / where megamemory
  // if global → register "megamemory" as the command
  // else → register "node /path/to/dist/index.js"
}
```

The installer decides whether the harness should invoke the global binary or call `node` with an absolute path, depending on whether the user did `npm i -g`. Robust against npm linking quirks.

### 2.6 COS analogue

**ADR-258 portable overlay** generates a read-only `.ai/` surface from canonical sources. **Different model**:

- MegaMemory: write per-harness configs, register an MCP server, add instructions.
- COS: generate one neutral overlay that harnesses opt-in to via their own discovery.

`manifests/external-tools-adoption.yaml` covers the "is this tool registered" question structurally; harness wiring is per-harness's own adapter (`packages/*/`).

### 2.7 Verdict

| Dimension | MegaMemory | COS (ADR-258 + manifests) | Verdict |
|---|---|---|---|
| Number of supported harnesses | 4 | 1 canonical (Claude Code) + adapter taxonomy for others | MegaMemory: more breadth shipped; COS: stronger model. |
| Wiring style | Push (write per-harness configs) | Pull (harness reads the overlay) | **OURS_BETTER** for governance, **EXTERNAL_BETTER** for first-time install ergonomics. |
| Mutates user dotfiles | Yes (AGENTS.md, CLAUDE.md, opencode.json, ...) | No (or via explicit `cognitive-os-init`) | **OURS_BETTER** |
| Managed-file marker | Yes | Implicit (overlay path is generated) | MegaMemory's marker is a cleaner safety belt for any future COS push-mode installer. |
| JSONC handling | Bespoke parser | n/a | Borrow if we ever need to read Claude Code settings.json with comments. |
| Idempotent re-runs | Yes | Yes | **EQUIVALENT** |
| Self-discovery (global vs local entrypoint) | Yes | Implicit via PATH on harness side | MegaMemory's pattern is nicer when we ship Engram as a global daemon. |

### 2.8 Is the installer pattern useful for COS?

**Partially.** The COS philosophy is "the operator configures the harness; the COS does not modify the harness." That's the right default. But two sub-patterns are worth borrowing:

1. **`MANAGED_FILE_MARKER`** as a contract for any file COS writes into user space (e.g., `~/.claude/commands/cognitive-os-*.md`). This lets future `cognitive-os-init` runs safely re-emit those files without clobbering operator edits to files lacking the marker.

2. **The JSONC parser** as a utility for any future read of `settings.json`-style files that may contain comments. Currently we shell out to `jq` which is strict JSON — that breaks on commented `settings.json`. A small Python `jsonc.loads()` borrowed from this pattern would close that gap.

Park these as low-priority follow-ups in the next memory-bundle SDD's "operator tooling" lane.

---

## 3. Net for Annex D

MegaMemory ships **more polished operator UX** than COS has today on two narrow dimensions: a graph explorer and a multi-editor push installer. Neither is a current COS requirement.

The two ideas worth absorbing are tiny: a **managed-file marker** convention and a **JSONC stripper**. Total port cost: <1 day, deferred until a use case justifies it.
