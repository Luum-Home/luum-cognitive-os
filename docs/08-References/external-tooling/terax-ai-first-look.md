---
title: terax-ai — primer acercamiento (Tauri 2 + Rust + React 19)
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

# terax-ai — primer acercamiento

Investigación motivada por la pregunta operativa: para construir una UI propia
del SO con stack `Tauri 2 + Rust + React 19`, ¿qué referencias concretas en el
ecosistema existen hoy?

Este documento captura el **primer acercamiento** (audit superficial vía
README, `package.json`, `Cargo.toml`, métricas GitHub). Un audit profundo
(IPC patterns, calidad de código, governance, bus factor, anti-patrones) está
delegado a un agente y se persistirá bajo el topic key `research/terax-ai-audit`
en engram + actualización de esta página cuando vuelva.

## Qué es

- Emulador de terminal AI-native (ADE — AI Development Environment).
- **NO es un agent OS** — comparte stack con lo que queremos, no propósito.
- Tauri 2 + Rust + React 19.1 — 7 MB binary final (vs 100+ MB típicos de Electron).
- Repo creado 21 abril 2026 — ~3 semanas de vida.
- Última versión publicada: v0.6.3 (13 mayo 2026, mismo día del audit).
- Push más reciente: hace 24 h. Proyecto muy activo.

## Stack frontend (package.json)

| Capa | Pieza |
|---|---|
| Framework | React 19.1, TypeScript 5.8, Vite 7, pnpm |
| Styling | Tailwind v4 + shadcn/ui + Radix UI |
| State | **Zustand 5** (más simple que Jotai) |
| Editor inline | CodeMirror 6 |
| Terminal embebido | xterm.js + WebGL |
| LLM clients | Vercel AI SDK v6 (anthropic, openai, google, groq, cerebras, xai, openai-compatible) |
| Otros | Motion (animations), Zod 4, Shiki (syntax highlight) |

## Stack Rust (Cargo.toml)

| Crate | Rol |
|---|---|
| `tauri v2` + 8 plugins | store, autostart, updater, window-state, opener, log, os, process |
| `reqwest 0.12` | HTTP client con `rustls-tls` + `stream` features |
| `portable-pty 0.9` | PTY real (terminal nativa) |
| `grep-regex` / `grep-searcher` / `globset` / `ignore` | Búsqueda en filesystem |
| `keyring 3.6` | Credenciales OS-native (Keychain / Credential Manager) |

**Ausencias notables** en el manifest Rust:

- **No tokio** — async-await sin runtime explícito (probable `futures-util` directo).
- **No MCP libraries** — tool calling vive en el frontend (Vercel AI SDK).
- **No LLM client en Rust** — toda la lógica IA está en TS frontend.

## Veredicto: referencia, no base

**No sirve como base de la UI propia** porque:

1. Es un terminal emulator + asistente IA, no un cliente de agent management.
2. Sin sessions, sin multi-agent UI, sin consumo de backend HTTP+SSE (que es lo
   que ADR-291 va a exponer).
3. Vercel AI SDK habla con APIs LLM directo — luum-ui necesita hablar con su
   propio backend Python orquestador.

**Sí sirve como referencia concreta** de:

1. **Stack validado** en producción: Tauri 2 + Rust + React 19 + Tailwind v4 + shadcn corre como app de escritorio multiplataforma con binary de 7 MB.
2. **Patrones IPC Rust↔React** vía `@tauri-apps/api` (a auditar en profundidad).
3. **Componentes embeddable opcionales**: xterm.js (si quisiéramos terminal in-app), CodeMirror 6 (si quisiéramos editor inline).
4. **Plugin architecture Tauri** ya integrada: `store`, `autostart`, `updater`, `window-state`, `keyring`. Patrón válido a copiar.
5. **State management ligero**: Zustand 5 (preferible a Jotai en este contexto).

## Lo que explícitamente NO copiamos

- **Vercel AI SDK como cliente directo**: nuestro cliente UI consume el backend
  Python (ADR-291), no APIs de proveedores LLM. Reemplazo:
  `@tanstack/react-query` + `fetch` / `EventSource` para HTTP + SSE.
- **PTY / terminal embebido**: el SO no es un emulador de terminal.
- **File explorer / web preview / shell integration**: out of scope para
  cliente de agente.

## Banderas amarillas

- **Repo de 3 semanas con 2.7k★** — crecimiento muy rápido; posible hype, no
  necesariamente señal de calidad. Ratio `116 issues abiertos / 156 commits` es
  alto.
- **v0.6.3 es 0.x** — API / arquitectura pueden cambiar antes de 1.0.
- **Bus factor 1** — proyecto único de un solo autor (`crynta`). Sin equipo
  formal.
- **No se confirmó MCP support** — Vercel AI SDK soporta tool calling estilo
  OpenAI, pero MCP nativo no está confirmado.
- **Licencia Apache-2.0** — limpia, sin viralidad, permite uso comercial y fork.

## Posición en la investigación de UI propia

Esta página es la **primera entrada** del trabajo de selección de stack para el
cliente UI del SO. Forma parte de una serie:

- `external-tooling/terax-ai-first-look.md` (este doc) — primer acercamiento
  superficial.
- `research/terax-ai-audit` (engram, pendiente) — audit profundo: IPC,
  calidad, governance, anti-patrones.
- ADR-292 (no creado todavía) — decisión de stack para el cliente UI propio,
  alimentada por este audit + audit tarko + benchmarks propios.

Decisiones aún no tomadas:

1. ¿Tauri 2 confirmado o se evalúan alternativas (Electron, Wails, native)?
2. ¿Zustand o algo más simple (Valtio / Signal-based)?
3. ¿`@tanstack/react-query` + `EventSource` o cliente HTTP custom?
4. ¿xterm.js embebido cuando aparezca necesidad de terminal-in-app o nunca?

## Próximos pasos

- Esperar audit profundo (`research/terax-ai-audit`).
- Hacer el equivalente audit profundo de tarko (`research/tarko-separability-audit`
  ya en engram, completado).
- Comparar 1:1 patrones de los dos para decisión de stack en ADR-292.
- No tomar decisión de stack hasta tener los 2 audits + benchmark binary size
  + benchmark startup time propios.
