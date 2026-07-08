---
type: quality-synthesis
source: docs/09-Quality/manual-tests/service-control-plane-proof-drills.md
provenance: "Defines opt-in proof drills (P0-P7) for the future cosd service control plane, each proving one specific safety property before that capability is claimed as implemented."
---

## What it is
An eight-drill (P0-P7) opt-in proof suite for the not-yet-production `cosd` service control plane. These drills must never run in normal unit/audit/contract lanes; each one proves a narrow, specific claim rather than general readiness.

## Key mechanics
- **P0 — Contract inventory**: asserts the research doc, implementation plan, and this proof-drill doc all exist, without claiming a production daemon.
- **P1 — Local no-model queue** (implemented): `cos-task-submit` → `cos-worker-run-once` → `cos-queue-drain` proves one task can be admitted and completed with no provider credentials, producing an artifact bundle with task/lease/result/logs.
- **P2 — Account-backed Codex CLI probe** (future): proves an authenticated Codex CLI session can execute without COS reading `~/.codex/auth.json`; expects `auth_probe.status` of `ready`/`auth_required`, no token-like strings in logs, and worker output that is propose-only.
- **P3 — Account-backed Claude Code probe**: same shape for `claude`, expecting no printed OAuth/API secrets and no reads of `~/.claude` or macOS Keychain; current status: `cos-auth-probe` exists and returns `unsupported` (no CLI) or `auth_required` (CLI present, non-invasive status probe unproven).
- **P4 — Docker sidecar CLI proof** (future): proves a containerized official CLI path works only with explicit, provider-documented auth mounted into the container, never opaque host secret folders.
- **P5 — Container auth-negative proof** (future): proves a container without explicit auth fails safely (`auth_required`/`unsupported`, no stack trace, no retry storm, no host secret probing).
- **P6 — Crash/resume** (implemented for simulated crash + lease-expiry): proves worker leases are safe — a stale lease gets requeued or marked `needs_human`, and a second worker cannot publish under an expired lease.
- **P7 — Provider lab promotion**: defines the bar (documented auth/output contract, auth-probe status mapping, no scraping of stored secrets, `auth_required` on missing auth, one redacted no-op task) for promoting a lab-only provider (Kimi, MiniMax, DeepSeek, etc.) out of lab status.

## Relations & where used
Extends the `proof-drill-registry.md` classification model to the `cosd` service control plane specifically; P2/P3 reference the same `cos-auth-probe` contract used in `qwen-code-structural-projection.md`'s runtime-delegation gap list.

## Status / caveats
Mixed implementation state within one document: P1 and P6 are marked implemented; P0, P2, P4, P5, P7 describe future/not-yet-built command shapes. Treat drills marked "future command shape" as design intent, not proof of current behavior — this split is called out explicitly in the source and preserved here rather than resolved.
