# AI Gateway Architecture — Event Routing for Cognitive OS

## What is an AI Gateway?

An AI Gateway is an intermediary layer between clients and AI models that controls:
- **Authentication**: Who can access the model (API keys, tokens)
- **Consumption**: How much each client uses (token counting, credit system)
- **Rate limiting**: Usage caps per time window
- **Routing**: Which model handles which request
- **Observability**: Logging who requested what, when, and how much

## Competitive Landscape

### OpenClaw — Messaging Gateway

OpenClaw is a multi-channel messaging gateway that routes messages from WhatsApp, Telegram, Slack, Discord to AI agents.

| Aspect | OpenClaw | Cognitive OS |
|---|---|---|
| Purpose | Route messages from chat platforms to agents | Orchestrate coding agents with governance |
| Multi-agent | Isolated agents per channel/account | Orchestrator + delegated sub-agents |
| Routing | Deterministic by peer/guild/team/account | By skill type + model capability |
| Isolation | Workspace per agent (SOUL.md, AGENTS.md) | Session isolation + permissions + identity |
| Inter-agent comms | Off by default, allowlist | Valkey pub/sub + hcom cross-terminal |
| Warm sessions | Gateway is long-lived daemon | Engram persistent memory cross-session |
| Security | Device pairing + token auth | 6-tier permissions + content-policy + parry |
| Channels | WhatsApp, Telegram, Slack, Discord, Signal | Claude Code, (future: OpenCode, Aider, Cursor) |

### What OpenClaw Does That We Don't
1. **Always-on daemon** — receives events 24/7. Our Singularity is similar but manual
2. **Multi-platform input** — WhatsApp, Telegram as triggers. We only have GitHub webhooks + CLI

### What We Do That OpenClaw Doesn't
1. **Governance** — 55 rules, quality gates, trust scores, adversarial review
2. **Auto-repair** — MAPE-K loop, known-fix registry, circuit breaker
3. **Persistent memory** — Engram with organized topic keys
4. **Cost control** — model routing, budget caps, token economy
5. **Self-improvement** — consequence system, skill evolution
6. **Package manager** — cos install with security audit

### Complementary, Not Competing
OpenClaw = "how messages reach the agent" (gateway)
Cognitive OS = "what the agent does and how it's governed" (OS)
They could work together: OpenClaw as input channel -> Cognitive OS as the brain.

## AI Gateway Components (for Cognitive OS)

### What We Already Have
| Component | Implementation | Status |
|---|---|---|
| **Model routing** | lib/model_router.py | Active |
| **Cost tracking** | lib/cost_dashboard.py + metrics/ | Active |
| **Rate limiting** | hooks/rate-limiter.sh + lib/rate_limiter.py | Active |
| **Auth (agent-level)** | lib/agent_permissions.py | Active |
| **Token counting** | Estimated per-model pricing | Active |
| **Budget enforcement** | rules/resource-governance.md | Active |
| **Webhook triggers** | webhook-trigger service | Active |

### What We Could Add (Gateway Layer)
| Component | What | Priority |
|---|---|---|
| **Event channels** | Telegram/Discord/Slack as input sources | Medium |
| **API key management** | Per-user API keys with credit system | Medium |
| **Bifrost proxy** | High-performance LLM routing with budget hierarchy | High |
| **Always-on daemon** | Singularity as persistent service, not manual | Medium |
| **Multi-tenant** | Multiple users sharing one COS instance | Low |

## Gateway Integration Pattern

```
External Events (GitHub, Telegram, Slack, Webhooks)
         |
         v
    +-------------+
    |  AI Gateway  | <- Auth + Rate Limit + Token Count
    |  (FastAPI)   |
    +------+------+
           |
           v
    +-------------+
    | Cognitive OS | <- Rules + Skills + Memory + Governance
    |   (Agent)    |
    +------+------+
           |
           v
    +-------------+
    | LLM Provider | <- Claude, OpenAI, Ollama, OpenRouter
    |  (LiteLLM)   |
    +-------------+
```

## Relationship to Existing Components

- **LiteLLM** is already our LLM proxy (model routing, cost tracking)
- **webhook-trigger** is already our event receiver (GitHub webhooks)
- The missing piece is a **unified event gateway** that combines: multi-channel input + auth + rate limiting + routing to the right COS instance

## Future: Bifrost as High-Performance Gateway

Bifrost (github.com/maximhq/bifrost) is a Go-based high-performance AI gateway with:
- 4-tier budget hierarchy
- Sub-millisecond routing
- Provider fallback chains
- Could replace/complement LiteLLM for production deployments

See: docs/tool-stack.md for evaluation status.

## AI Gateway Landscape — Open Source Comparison

| Gateway | License | Language | Stars | Providers | Budget | Caching | Performance | Verdict |
|---|---|---|---|---|---|---|---|---|
| **LiteLLM** | MIT | Python | 41.3K | 100+ | Per-key | Exact-match | ~8ms P95 | **ADOPT** (current) |
| **Bifrost** | Apache-2.0 | Go | 3.3K | 15+ | 3-tier hierarchy | Semantic | 11µs (50x faster) | **WATCH** |
| **Portkey** | MIT | TypeScript | 11K | 200+ | Virtual keys | Yes | <1ms, 122KB | **WATCH** |
| **Kong AI** | Apache-2.0 | Lua/Go | 62K | Plugin-based | Enterprise only | Plugin | Proven | SKIP (overkill) |
| **Helicone** | Apache-2.0 | Rust+TS | 4.8K | Major | Cost tracking | Yes | Sub-ms | SKIP (overlaps Langfuse) |
| **Envoy AI** | Apache-2.0 | Go | 198 | Major | No | No | 1-3ms | SKIP (immature) |
| **FastAPI DIY** | N/A | Python | N/A | Build your own | Build your own | No | ~2-5ms | SKIP (learning only) |

### Recommendation

**Stay with LiteLLM.** Broadest coverage (100+ providers), MIT license, massive community (41.3K stars), existing integration in our docker-compose and model_router.py.

**Watch Bifrost** if we need high-throughput performance or move to Go infrastructure. Its 3-tier budget hierarchy could inspire improvements to our resource-governance.

**Watch Portkey** as a lightweight alternative (122KB footprint, 200+ providers, MIT).

### Why Not Build Our Own (FastAPI DIY)?

The tutorial approach (FastAPI + API keys + token counting) demonstrates the concepts but misses:
- Provider failover chains
- Semantic caching
- Distributed rate limiting
- Multi-tenant budget management
- Production observability

LiteLLM solves all of these out of the box. Building from scratch would take months to reach feature parity.
