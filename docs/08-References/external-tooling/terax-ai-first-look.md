---
title: terax-ai — first pass (Tauri 2 + Rust + React 19)
type: external-reference
status: research
date_captured: 2026-05-13
research_topic: client-ui-stack
relates_to:
  - docs/02-Decisions/adrs/ADR-291-agent-runtime-web-service.md
sources:
  - https://github.com/crynta/terax-ai
  - https://raw.githubusercontent.com/crynta/terax-ai/main/package.json
  - https://raw.githubusercontent.com/crynta/terax-ai/main/src-tauri/Cargo.toml
license_observed: Apache-2.0
verdict: reference-only-not-base
deep_audit_pending: research/terax-ai-audit (engram topic_key)
---

# terax-ai — first pass

Research motivated by the operational question: to build an owned UI for the OS
with the `Tauri 2 + Rust + React 19` stack, what concrete ecosystem references
exist today?

This document captures the **first pass**: a superficial audit through README,
`package.json`, `Cargo.toml`, and GitHub metrics. A deeper audit covering IPC
patterns, code quality, governance, bus factor, and anti-patterns should be
delegated to an agent and persisted under the `research/terax-ai-audit` Engram
topic key, then reflected back into this page.

## What it is

- AI-native terminal emulator (ADE — AI Development Environment).
- **Not an agent OS**: it shares the stack we want, not the product purpose.
- Tauri 2 + Rust + React 19.1; final binary is about 7 MB versus typical
  100+ MB Electron binaries.
- Repository created on April 21, 2026; about 3 weeks old at capture time.
- Latest published version at capture time: v0.6.3 on May 13, 2026.
- Most recent push at capture time: 24 h ago. Very active project.

## Frontend stack (package.json)

| Layer | Piece |
|---|---|
| Framework | React 19.1, TypeScript 5.8, Vite 7, pnpm |
| Styling | Tailwind v4 + shadcn/ui + Radix UI |
| State | **Zustand 5** (simpler than Jotai) |
| Inline editor | CodeMirror 6 |
| Embedded terminal | xterm.js + WebGL |
| LLM clients | Vercel AI SDK v6 (anthropic, openai, google, groq, cerebras, xai, openai-compatible) |
| Other | Motion (animations), Zod 4, Shiki (syntax highlight) |

## Rust stack (Cargo.toml)

| Crate | Role |
|---|---|
| `tauri v2` + 8 plugins | store, autostart, updater, window-state, opener, log, os, process |
| `reqwest 0.12` | HTTP client with `rustls-tls` + `stream` features |
| `portable-pty 0.9` | Real PTY (native terminal) |
| `grep-regex` / `grep-searcher` / `globset` / `ignore` | Filesystem search |
| `keyring 3.6` | OS-native credentials (Keychain / Credential Manager) |

**Notable absences** in the Rust manifest:

- **No tokio** — async-await without an explicit runtime; likely direct `futures-util`.
- **No MCP libraries** — tool calling lives in the frontend through Vercel AI SDK.
- **No Rust LLM client** — all AI logic is in the TypeScript frontend.

## Verdict: reference, not base

**Not suitable as the owned UI base** because:

1. It is a terminal emulator plus AI assistant, not an agent-management client.
2. It has no sessions, no multi-agent UI, and no HTTP+SSE backend consumption,
   which is what ADR-291 will expose.
3. Vercel AI SDK talks directly to LLM APIs; luum-ui needs to talk to its own
   Python orchestration backend.

**It is useful as a concrete reference** for:

1. **Validated production stack**: Tauri 2 + Rust + React 19 + Tailwind v4 +
   shadcn runs as a cross-platform desktop app with a 7 MB binary.
2. **Rust↔React IPC patterns** via `@tauri-apps/api` (to audit deeply).
3. **Optional embeddable components**: xterm.js for a future in-app terminal,
   CodeMirror 6 for a future inline editor.
4. **Integrated Tauri plugin architecture**: `store`, `autostart`, `updater`,
   `window-state`, `keyring`. Valid pattern to copy.
5. **Lightweight state management**: Zustand 5, preferable to Jotai in this context.

## What we explicitly do not copy

- **Vercel AI SDK as a direct client**: our UI client consumes the Python backend
  from ADR-291, not provider LLM APIs. Replacement: `@tanstack/react-query` +
  `fetch` / `EventSource` for HTTP + SSE.
- **PTY / embedded terminal**: the OS is not a terminal emulator.
- **File explorer / web preview / shell integration**: out of scope for the agent client.

## Yellow flags

- **3-week-old repo with 2.7k stars** — very fast growth; possible hype, not
  necessarily a quality signal. The `116 open issues / 156 commits` ratio is high.
- **v0.6.3 is 0.x** — API and architecture may change before 1.0.
- **Bus factor 1** — single-author project (`crynta`) with no formal team.
- **MCP support not confirmed** — Vercel AI SDK supports OpenAI-style tool
  calling, but native MCP support is not confirmed.
- **Apache-2.0 license** — clean, non-viral, permits commercial use and forks.

## Position in owned UI research

This page is the **first entry** in stack-selection work for the owned OS UI
client. It is part of a series:

- `external-tooling/terax-ai-first-look.md` (this doc) — first superficial pass.
- `research/terax-ai-audit` (Engram, pending) — deep audit: IPC, quality,
  governance, anti-patterns.
- ADR-292 (not created yet) — stack decision for the owned UI client, fed by
  this audit + the tarko audit + local benchmarks.

Decisions not yet made:

1. Tauri 2 confirmed, or are alternatives being evaluated (Electron, Wails, native)?
2. Zustand or something simpler (Valtio / Signal-based)?
3. `@tanstack/react-query` + `EventSource` or custom HTTP client?
4. Embedded xterm.js when terminal-in-app is needed, or never?

## Next steps

- Wait for the deep audit (`research/terax-ai-audit`).
- Run the equivalent deep audit for tarko (`research/tarko-separability-audit`,
  already in Engram, completed).
- Compare both patterns 1:1 for the ADR-292 stack decision.
- Do not make the stack decision until both audits, binary-size benchmark, and
  local startup-time benchmark exist.
