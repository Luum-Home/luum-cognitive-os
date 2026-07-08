---
type: concept-synthesis
source: docs/04-Concepts/root/identity-stack.md
---

## What it is
A 6-layer identity architecture for Cognitive OS agents, providing cryptographic identity, credential management, permissions, discovery, delegation, and infrastructure identity — phased from zero-new-infrastructure now to a full cryptographic stack later.

## Key mechanics
- 6 layers (bottom to top): Layer 1 Cryptographic Identity (AIM/OpenA2A, Apache 2.0 — Ed25519 + post-quantum keys, trust scoring, signed audit trail, DID-compatible); Layer 2 Credential Vault (OneCLI, Apache 2.0 — placeholder tokens like `{{STRIPE_KEY}}`, runtime injection, rotation tracking); Layer 3 Permissions (Cerbos, Apache 2.0 — YAML policy engine, MCP tool-level ACLs, integrates with Agent spec `tools.allowed`); Layer 4 Discovery (A2A Agent Cards, Apache 2.0 — JWS-signed `/.well-known/agent.json`); Layer 5 Delegation (Agent Passport, MIT — monotonic attenuation, Delegation Capability Tokens/DCTs, MCP middleware); Layer 6 Infra Identity (SPIFFE/SPIRE, Apache 2.0 — X.509 SVIDs, workload attestation, CNCF graduated, enables mTLS).
- All tools use SaaS-safe licenses (Apache 2.0 or MIT), compliant with `docs/03-PoCs/research/license-analysis.md`.
- 3 implementation phases: Phase 1 (NOW) — name/type/session-ID identification, WHO/WHAT/WHEN/WHERE/WHY audit trail logging, trust levels 0-3, zero new tools required, via CLAUDE.md rules + Engram; Phase 2 (near-term) — Cerbos + OneCLI + Agent Passport MCP middleware; Phase 3 (long-term) — AIM + A2A Agent Cards + SPIFFE/SPIRE, integrated with the Squad Model.
- Example Cerbos policy shown: role-based allow/deny on `mcp_tool` resource by `tool_name` attribute.

## Relations & where used
Integrates with: Control Plane (agent registration = AIM key gen), Multi-Agent (orchestrator creates DCTs when spawning sub-agents), Tool System/MCP (Cerbos gates tool access), Engram (audit entries signed with Ed25519 key), Security/NeMo (identity validation added to constitutional gates), Observability (agent identity attached to Langfuse traces). Related docs: README (13 infrastructure layers), recommended-stack.md, implementation-phases.md, `.claude/rules/constitutional-gates.md`.

## Status / caveats
Only Phase 1 is implemented today (name/type/session-ID + rule-based trust levels + Engram text logs). Phases 2-3 require new infrastructure not yet deployed (Cerbos server, OneCLI CLI, Agent Passport npm package, AIM library, SPIRE server, DNS/well-known endpoint).
