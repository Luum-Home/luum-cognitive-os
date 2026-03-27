# Cognitive OS — Recommended Stack

> Best-of-breed selection for each Cognitive OS component.
> All choices comply with [Cognitive OS license policy](../research/license-analysis.md) (MIT, Apache 2.0, BSD only).

---

## Selection Criteria

1. **License** — Must be MIT, Apache 2.0, or BSD. No AGPL/SSPL/ELv2/BSL.
2. **Self-hostable** — Must be deployable on our infrastructure.
3. **Maturity** — Prefer production-proven tools with active communities.
4. **Fit** — Alignment with our existing stack (K8s, TypeScript/Go, MCP, Engram).
5. **Composability** — Tools that work well together without vendor lock-in.

---

## Recommended Stack

| Component | Primary Choice | Alternative | License | Why Primary |
|-----------|---------------|-------------|---------|-------------|
| Control Plane | **kagent** | AgentField | Apache 2.0 | CNCF Sandbox project. K8s-native with CRDs — fits our infrastructure direction. Declarative agent definitions. |
| Scheduler | **Temporal** | Hatchet | MIT | Most mature durable execution engine. Used by Stripe, Netflix, Snap. Handles failures, retries, timeouts automatically. |
| Sandbox | **E2B** | OpenSandbox | Apache 2.0 | Best documentation, largest community (11.4k stars). Firecracker microVMs with <200ms cold start. Self-hostable. |
| Multi-Agent | **LangGraph + A2A** | CrewAI | MIT + Apache 2.0 | LangGraph for stateful graph orchestration. A2A Protocol for inter-agent communication standard (Linux Foundation, 100+ companies). |
| Identity | **AIM (OpenA2A)** | — | Apache 2.0 | Only complete agent identity solution with Ed25519 crypto + W3C DIDs. No viable alternative at same maturity. |
| Memory | **Engram + Mem0** | Letta | Apache 2.0 | Engram already integrated for dev-time. Mem0 adds graph-based relationships and multi-agent shared memory for production. |
| Tools | **MCP + Registry** | — | Apache 2.0 | Industry standard. 1200+ servers. Already deeply embedded in our workflow. No reason to switch. |
| Observability | **Langfuse** | OpenLIT | MIT | Most complete self-hosted LLM observability (23k stars). Traces, prompts, evals, cost tracking in one platform. |
| Cost | **LiteLLM + Bifrost** | Portkey | MIT + Apache 2.0 | LiteLLM for budget caps and virtual keys. Bifrost for high-performance routing (11us overhead, Go). |
| Security | **NeMo + LLM Guard** | Invariant | Apache 2.0 + MIT | Complementary layers: NeMo for conversational policy (Colang), LLM Guard for content scanning (35 scanners). |

---

## Stack Interactions

```
                    +------------------+
                    |   Control Plane  |
                    |     (kagent)     |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v------+  +---v---+  +-------v--------+
     |   Scheduler   |  | Identity|  |  Observability |
     |  (Temporal)   |  |  (AIM) |  |   (Langfuse)   |
     +--------+------+  +---+---+  +-------+--------+
              |              |              |
     +--------v------+      |      +-------v--------+
     |    Sandbox    |      |      |  Cost Control  |
     |     (E2B)    |      |      | (LiteLLM+Bifrost)|
     +--------+------+      |      +----------------+
              |              |
     +--------v--------------v---------+
     |       Multi-Agent Orchestration |
     |        (LangGraph + A2A)        |
     +--------+------------------------+
              |
     +--------v------+  +-------------+
     |    Memory     |  |   Security  |
     | (Engram+Mem0) |  | (NeMo+Guard)|
     +---------------+  +-------------+
              |
     +--------v------+
     |  Tool System  |
     |  (MCP+C7)     |
     +---------------+
```

---

## Why These Over Alternatives

### kagent over Microsoft Agent Framework
Microsoft AF has 27k stars but is a dev framework, not infrastructure. kagent is purpose-built for K8s agent operations with CRDs, aligning with cloud-native infrastructure.

### Temporal over Hatchet
Temporal has 5+ years of production use at massive scale. Hatchet is simpler (Postgres-only) but lacks Temporal's ecosystem of SDKs, community, and battle-testing.

### E2B over OpenSandbox
E2B has better documentation, a larger community, and Firecracker-based security. OpenSandbox is viable but less proven in the agent sandbox space specifically.

### LangGraph over CrewAI/AutoGen
LangGraph provides the most granular control with graph-based state machines. CrewAI (44k stars) is simpler but more opinionated. AutoGen (55k stars) is evolving too rapidly for production commitment.

### Langfuse over OpenLIT
Langfuse is a complete platform (traces + prompts + evals + cost) while OpenLIT is focused on OTEL integration. Langfuse covers more use cases out of the box.

### LiteLLM + Bifrost over Portkey alone
LiteLLM handles budget enforcement (hard caps, alerts). Bifrost adds high-performance routing at 11us overhead in Go. Together they cover enforcement + performance. Portkey overlaps but doesn't match Bifrost's routing performance.

### NeMo + LLM Guard over single solution
NeMo Guardrails handles conversational policy (what agents can/cannot discuss). LLM Guard handles content scanning (PII, injection, toxicity). Different attack surfaces need different defenses. Invariant Guardrails adds MCP-aware policies as a future third layer.
