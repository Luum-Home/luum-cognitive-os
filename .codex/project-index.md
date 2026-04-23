# Cognitive OS — Codex Project Index

> Compact operator index for working in this repository without re-reading the full codebase.

## Product Truth

Cognitive OS is best understood as the operational layer for coding agents:

- governance
- verification
- portability
- durable runtime contracts across provider and harness churn

Do not treat it as a generic "agent platform" first.

The strongest current wedge is:

**governable, verifiable, portable coding agents in real repositories**

## Core Surfaces

- `hooks/` — runtime enforcement and lifecycle behavior
- `hooks/_lib/` — shell helpers and shared runtime support
- `lib/` — Python runtime logic, routing, metrics, config loading, portability helpers
- `pkg/hook/` — canonical Go hook context model
- `internal/provider/` — provider normalization and response shaping
- `scripts/cos-init.sh` — bootstrap into external projects
- `hooks/self-install.sh` — self-hosted synchronization and runtime projection
- `cmd/cos/` — package manager and installer surface
- `cognitive-os.yaml` — product/runtime configuration source of truth

## Product-Critical Documents

- `docs/business/durable-product-master-plan.md`
- `docs/business/master-plan-execution-requirements.md`
- `docs/business/master-plan-checklist.md`
- `docs/business/product-messaging.md`
- `docs/business/feature-reality-audit.md`
- `docs/architecture/bootstrap-portability.md`
- `docs/model-evolution-resilience.md`
- `docs/kernel-contract.md`

## Current Strategic Direction

- Keep the kernel small and protected.
- Prefer capability-centric decisions over model-centric decisions.
- Treat harness settings as drivers, not as the system itself.
- Document every significant analysis and turn it into an artifact.
- Avoid letting squads, dashboards, or control-plane language dominate the product story.

## Reality Checks

- Some surfaces are truly portable.
- Some are only driver-projected.
- Some are still Claude-advantaged or Claude-only in practice.
- Do not claim portability beyond what tests and drivers currently prove.

## Default Working Posture

- Start with the smallest real slice.
- Prefer changing the core only when the benefit is stable and durable.
- Convert important reasoning into docs, checklists, contracts, or tests.
- When uncertain, make the product simpler rather than more total.
- Prefer shared contracts and resolvers over re-implementing the same rule in multiple layers.
- Treat repository artifacts as primary durable memory and use MCP memory only when it is actually available in the current session.
- If we discover a real bug while touching adjacent code, fix it or record it explicitly before moving on.
