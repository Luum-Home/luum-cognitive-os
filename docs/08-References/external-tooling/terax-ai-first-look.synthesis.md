---
type: reference-synthesis
source: docs/08-References/external-tooling/terax-ai-first-look.md
provenance: "First-pass superficial audit (2026-05-13) of the terax-ai repo as a possible stack reference for building an owned Tauri 2 + Rust + React 19 UI client for the OS, tied to ADR-291."
---

## What it is

A first-pass (README/package.json/Cargo.toml-level) research note evaluating `terax-ai` (an AI-native terminal emulator, Tauri 2 + Rust + React 19) as a potential stack reference — not a base — for building an owned UI client for Cognitive OS, per the operational question raised in ADR-291.

## Key mechanics

- **Verdict up front**: reference-only, not a base. `terax-ai` is a terminal emulator plus AI assistant, not an agent-management client; it has no sessions/multi-agent UI/HTTP+SSE backend consumption model, and its LLM calls go directly from the frontend (Vercel AI SDK) rather than through an owned orchestration backend.
- **Frontend stack observed**: React 19.1, TypeScript 5.8, Vite 7, pnpm, Tailwind v4 + shadcn/ui + Radix UI, Zustand 5 (state), CodeMirror 6, xterm.js + WebGL, Vercel AI SDK v6 (multi-provider), Zod 4, Shiki.
- **Rust stack observed**: `tauri v2` + 8 plugins (store, autostart, updater, window-state, opener, log, os, process), `reqwest` with rustls-tls, `portable-pty` (real PTY), `grep-regex`/`grep-searcher`/`globset`/`ignore` (filesystem search), `keyring` (OS-native credential storage). Notable absences: no tokio, no MCP libraries, no Rust-side LLM client — all AI logic lives in the TS frontend.
- **What's reusable as a pattern**: validated production stack proving a 7 MB cross-platform binary (vs. 100+ MB Electron), Rust↔React IPC via `@tauri-apps/api` (flagged for deeper audit), optionally embeddable xterm.js/CodeMirror 6, the integrated Tauri plugin architecture, and Zustand as lighter-weight than Jotai.
- **What is explicitly NOT to copy**: direct Vercel-AI-SDK-to-provider client pattern (COS's UI must talk to its own Python orchestration backend instead, via `@tanstack/react-query` + fetch/EventSource for HTTP+SSE); PTY/embedded terminal; file explorer/web preview/shell integration — all out of scope for an agent client.
- **Yellow flags recorded**: repo only ~3 weeks old at capture with 2.7k stars (fast growth, possibly hype not quality signal), 116 open issues / 156 commits ratio called "high," v0.6.3 (pre-1.0, API may shift), bus factor of 1 (single author, no formal team), MCP support unconfirmed, Apache-2.0 license (clean, non-viral, commercial-use permitted).

## Relations & where used

Feeds `ADR-291-agent-runtime-web-service.md`. Names a pending deep audit under Engram topic key `research/terax-ai-audit` (IPC patterns, code quality, governance, bus factor, anti-patterns) that should be reflected back into this page once complete, and a sibling completed audit `research/tarko-separability-audit` for 1:1 comparison feeding a not-yet-created ADR-292 stack decision.

## Status / caveats

This is explicitly labeled **research/status: research**, a **first pass only** ("superficial audit through README, package.json, Cargo.toml, and GitHub metrics") captured 2026-05-13 — the source doc itself states the deep audit is still pending and that no stack decision (Tauri vs. Electron/Wails/native, Zustand vs. alternatives, react-query+EventSource vs. custom client, embedded terminal or not) should be made until both the terax-ai and tarko deep audits plus binary-size and startup-time benchmarks exist. Facts about the referenced repo (star count, commit count, version, activity) are a point-in-time snapshot as of the capture date and will be stale by the time this is read.
