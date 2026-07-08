---
type: concept-synthesis
source: docs/04-Concepts/architecture/surface-5-and-secure-cosd-roadmap.md
provenance: "Define the next implementation shape for two optional extensions: a real Bubble Tea Surface 5 operator TUI, and secure remote-capable cosd access beyond the local file queue/local-only API slice."
---

## What it is

Roadmap for two related extensions: (1) a Bubble Tea Surface 5 operator TUI answering "can I see, from one terminal, whether COS is ready/healthy/blocked/waiting?", and (2) secure remote-capable `cosd` access beyond the current local-only API. Both map to existing COS feature surfaces (status, coverage, reliability, receipts, cosd daemon, task queue, headless pipeline, inbox, validation locks, worktree safety) rather than inventing new ones.

## Key mechanics

**TUI (ADR-195, accepted/implemented as read-only MVP):**
- Tabs: Overview, Release, cosd, Coverage, Reliability, Receipts, Headless, Inbox — each backed by an existing JSON artifact/CLI (`cos-status --json`, `cos-coverage --json`, `cos-boring-reliability --json`, `cos-action-receipt stats`, etc.)
- Command contract: `cos tui`, `cos tui --snapshot` (deterministic non-interactive), `cos tui --project-dir`
- Non-goals: no CLI replacement, no git mutation, no provider/model calls, no secret exposure
- Every action emits `surface_kind=ui, surface_id=tui, mode=operable` receipts; mutating actions require confirmation + whitelist entry
- `scripts/cos-tui` remains a compatibility shim until Go TUI reaches parity

**Secure cosd (ADR-193 baseline, ADR-194 accepted/implemented):**
- Current endpoints: `GET /healthz`, `GET /status`, `POST /submit-intent`, `POST /process-once` via `scripts/cosd serve --host 127.0.0.1 --port 8765` or `serve-unix --socket /tmp/cosd.sock`
- Policy: default bind `127.0.0.1` only; non-local bind refused unless `--allow-remote` + bearer-token auth (`--token-file`/`COSD_API_TOKEN_FILE`, never printed); write endpoints always require auth when remote/auth enabled; every write appends `.cognitive-os/cosd/api-audit.jsonl`; no custom TLS (document reverse-proxy termination instead)
- Expansion order: (1) read-only, (2) bounded writes (submit-intent, process-once, message ack), (3) task queue, (4) provider tasks (after adapter auth/redaction), (5) never v1: direct protected-branch push, destructive cleanup, raw remote shell execution

**Recommended sequencing**: secure cosd auth/remote guard first (narrower safety-critical slice) → TUI read-only MVP → TUI operable actions (after confirmation+receipts proven) → task-control-plane API expansion.

## Relations & where used

ADR-161 (remote control plane/provider adapter boundary), ADR-189 (harness implementation coverage), ADR-190 (harness action receipts), ADR-192 (Bubble Tea adoption), ADR-193 (cosd local network API), ADR-194 (cosd secure remote API — accepted/implemented), ADR-195 (Surface 5 operable TUI contract — accepted/implemented). Related docs: `cos-service-runtime-boundary.md`, `service-control-plane-implementation-plan.md`, `agent-message-bus.md`, `boring-reliability-control-plane.md`.

## Status / caveats

ADR-194 and ADR-195 are accepted and implemented (secure auth/remote-bind refusal, read-only TUI MVP). Remaining work: TUI operable actions (mutations) gated on confirmation UX + receipts, and task-control-plane API expansion gated on secure auth/audit stability.
