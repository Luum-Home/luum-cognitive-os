# Agent Identity Stack

> 6-layer identity architecture for the Cognitive OS, providing cryptographic identity, credential management, permissions, discovery, delegation, and infrastructure identity for AI agents.

## Overview

Agent identity is not a single concern — it spans six distinct layers, each solving a different problem. This document defines the stack, the tools selected for each layer, and the phased implementation plan.

## The 6-Layer Identity Stack

```
┌─────────────────────────────────────────────┐
│  Layer 6: Infra Identity (SPIFFE/SPIRE)     │
│  X.509 SVIDs, workload attestation          │
├─────────────────────────────────────────────┤
│  Layer 5: Delegation (Agent Passport)       │
│  Monotonic attenuation, DCTs, MCP middleware│
├─────────────────────────────────────────────┤
│  Layer 4: Discovery (A2A Agent Cards)       │
│  JWS-signed /.well-known/agent.json        │
├─────────────────────────────────────────────┤
│  Layer 3: Permissions (Cerbos)              │
│  YAML policies, MCP tool-level ACLs         │
├─────────────────────────────────────────────┤
│  Layer 2: Credential Vault (OneCLI)         │
│  Placeholder keys -> real keys at runtime   │
├─────────────────────────────────────────────┤
│  Layer 1: Cryptographic Identity (AIM)      │
│  Ed25519 + post-quantum, trust scoring      │
└─────────────────────────────────────────────┘
```

## Layer Details

| Layer | Tool | License | What it solves |
|-------|------|---------|---------------|
| Cryptographic Identity | AIM (OpenA2A) | Apache 2.0 | Ed25519 + post-quantum key pairs, audit trail signatures, trust scoring between agents |
| Credential Vault | OneCLI | Apache 2.0 | Placeholder keys in config, real keys injected at runtime, rotation tracking |
| Permissions | Cerbos | Apache 2.0 | YAML-based policy engine, MCP tool-level permissions, role-based access control |
| Cross-Agent Discovery | A2A Agent Cards | Apache 2.0 | JWS-signed `/.well-known/agent.json`, capability advertisement, agent registry |
| Delegation | Agent Passport | MIT | Monotonic attenuation (permissions can only narrow, never expand), Delegation Capability Tokens (DCTs), MCP middleware integration |
| Infra Identity | SPIFFE/SPIRE | Apache 2.0 | X.509 SVIDs for workload identity, CNCF graduated project, zero-trust networking |

All tools have SaaS-safe licenses (Apache 2.0 or MIT), compliant with `docs/research/license-analysis.md`.

## Architecture Diagram

```
                    ┌──────────────────┐
                    │   Orchestrator   │
                    │  (Coordinator)   │
                    └────────┬─────────┘
                             │ spawns with DCT
                             │ (Agent Passport)
                    ┌────────▼─────────┐
                    │   Sub-Agent      │
                    │  identity: AIM   │◄── Ed25519 key pair
                    │  creds: OneCLI   │◄── runtime secret injection
                    │  perms: Cerbos   │◄── YAML policy evaluation
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───┐  ┌──────▼─────┐  ┌────▼────────┐
     │  MCP Tool  │  │  MCP Tool  │  │  MCP Tool   │
     │ (allowed)  │  │ (allowed)  │  │ (BLOCKED)   │
     └────────────┘  └────────────┘  └─────────────┘
              │
              ▼
     ┌──────────────┐
     │  SPIFFE SVID │◄── workload attestation
     │  (mTLS)      │    for service-to-service
     └──────────────┘

Discovery flow (separate):
     Agent A ──► /.well-known/agent.json (Agent B) ──► verify JWS signature
                                                       ──► read capabilities
                                                       ──► establish trust
```

## How Each Layer Works

### Layer 1: Cryptographic Identity (AIM)

AIM (Agent Identity Management) from the OpenA2A project provides:

- **Ed25519 key pairs** for each agent, with post-quantum algorithm support for future-proofing
- **Trust scoring** between agents based on interaction history
- **Signed audit trail** — every action can be cryptographically attributed to a specific agent
- **DID-compatible** — agent identities can be represented as Decentralized Identifiers

### Layer 2: Credential Vault (OneCLI)

OneCLI solves the "agents should never see real API keys" problem:

- Config files use **placeholder tokens** (e.g., `{{STRIPE_KEY}}`)
- At runtime, OneCLI **injects real values** from a secure vault
- **Rotation tracking** — when keys rotate, OneCLI updates all references
- Agents interact with placeholders; they never handle raw secrets

### Layer 3: Permissions (Cerbos)

Cerbos provides fine-grained, policy-as-code access control:

- **YAML policy files** define what each agent role can do
- Policies evaluated per-request — no stale permission caches
- **MCP tool-level granularity** — Agent X can use `github` but not `kubernetes`
- Integrates with the Agent spec's `tools.allowed` field

Example policy:
```yaml
apiVersion: api.cerbos.dev/v1
resourcePolicy:
  resource: "mcp_tool"
  rules:
    - actions: ["execute"]
      roles: ["backend-dev"]
      effect: EFFECT_ALLOW
      condition:
        match:
          expr: request.resource.attr.tool_name in ["github", "database", "testing"]
    - actions: ["execute"]
      roles: ["backend-dev"]
      effect: EFFECT_DENY
      condition:
        match:
          expr: request.resource.attr.tool_name == "production-deploy"
```

### Layer 4: Cross-Agent Discovery (A2A Agent Cards)

Based on Google's Agent-to-Agent protocol:

- Each agent publishes a **signed Agent Card** at `/.well-known/agent.json`
- Cards advertise: capabilities, supported protocols, authentication methods
- **JWS signatures** prevent card tampering
- Enables agents to discover and verify each other without a central registry

### Layer 5: Delegation (Agent Passport)

Agent Passport handles the "orchestrator spawns sub-agent" trust chain:

- **Monotonic attenuation** — delegated permissions can only be narrower than the parent's
- **Delegation Capability Tokens (DCTs)** — cryptographic proof of who delegated what
- **MCP middleware** — intercepts tool calls and validates the agent's DCT before allowing execution
- Prevents privilege escalation: a sub-agent can never gain more access than its parent

### Layer 6: Infrastructure Identity (SPIFFE/SPIRE)

SPIFFE (Secure Production Identity Framework For Everyone) provides:

- **X.509 SVIDs** (SPIFFE Verifiable Identity Documents) for workload identity
- **Automatic certificate rotation** — no manual cert management
- **Workload attestation** — verifies agent identity based on runtime properties
- **CNCF graduated** — production-proven, widely adopted
- Enables **mTLS** between agent services without managing individual certificates

## Integration with Cognitive OS

The identity stack integrates with existing Cognitive OS surfaces and subsystems:

| Cognitive OS Surface / Subsystem | Identity Integration |
|---|---|
| Control Plane | Agent registration includes AIM key pair generation |
| Multi-Agent | Orchestrator creates DCTs (Agent Passport) when spawning sub-agents |
| Tool System (MCP) | Cerbos policies gate tool access per agent role |
| Memory (Engram) | Audit entries signed with agent's Ed25519 key |
| Security (NeMo) | Identity validation added to constitutional gates |
| Observability | Agent identity attached to all Langfuse traces |

## Implementation Phases

### Phase 1: Basic Identity (NOW)

What we implement immediately with zero new infrastructure:

- **Agent identification** via name, type, session ID, parent agent
- **Audit trail** logging (WHO, WHAT, WHEN, WHERE, WHY) per agent action
- **Trust levels** (0-3) as a conceptual framework enforced by rules
- **Credential rules** documented in `.claude/rules/agent-identity.md`

No new tools required. Implemented via CLAUDE.md rules and Engram observations.

### Phase 2: Permissions + Credentials (Near-term)

Add policy enforcement and secret management:

- **Cerbos** for YAML-based permission policies on MCP tools
- **OneCLI** for runtime credential injection (replace hardcoded env vars)
- **Agent Passport** MCP middleware for delegation tokens

Requires: Cerbos server (container), OneCLI CLI tool, Agent Passport npm package.

### Phase 3: Full Cryptographic Identity (Long-term)

Complete the stack with cryptographic primitives and infrastructure identity:

- **AIM** for Ed25519 key pairs and signed audit trails
- **A2A Agent Cards** for cross-agent discovery
- **SPIFFE/SPIRE** for infrastructure-level workload identity
- Integration with the Squad Model for organizational trust hierarchies

Requires: AIM library, SPIRE server (container), DNS/well-known endpoint for agent cards.

## What We Implement Now vs Later

| Concern | Now (Phase 1) | Later (Phase 2-3) |
|---------|---------------|-------------------|
| "Who is this agent?" | Name + type + session ID | AIM cryptographic DID |
| "What can it do?" | Trust level (rule-based) | Cerbos YAML policies |
| "Who sent it?" | Parent agent field | Agent Passport DCT |
| "What did it do?" | Engram text logs | Ed25519 signed audit entries |
| "Where are the secrets?" | Env vars (.env files) | OneCLI runtime injection |
| "Is this agent real?" | Session context | A2A Agent Card + JWS |
| "Can services trust it?" | Localhost assumption | SPIFFE X.509 SVID |

## Related Documents

- [Cognitive OS README](README.md) — Architecture vision and 13 infrastructure layers
- [Recommended Stack](recommended-stack.md) — Best-of-breed tool selection
- [Implementation Phases](implementation-phases.md) — 4-phase rollout plan
- [Constitutional Gates](../../.claude/rules/constitutional-gates.md) — Immutable security principles
