# ADR-049 — LLM Gateway Selection + Overflow Provider Strategy

## Status

**Accepted** — 2026-04-21. Supersedes implicit adoption of `litellm` (present
in `docker-compose.cognitive-os.yml` since ADR-022-era) and establishes the
canonical overflow strategy when Claude Code Max subscription hits rate limits.

## Context

### The original problem

User on Claude Code Max ($200/mo) hitting rate limits mid-session:

```
tarea en segundo plano completado
Agent "Fase 3.1: Campaigns tenant-scoped" completed
Error de API
You're out of extra usage · resets 2pm (America/Buenos_Aires)
```

Pattern: 4–5 opus-class sub-agents in parallel burns the 5h usage window,
no overflow valve. Subscription-based billing means "throttle or wait" when
exhausted — the paid quota cannot be topped up ad-hoc.

### Constraint: Claude Code native Agent tool is locked

Claude Code's built-in `Agent` tool dispatches via the user's subscription.
There is no public hook to redirect it to a different provider or API key.
Any overflow mechanism MUST run outside the native Agent tool — through a
separate orchestrator script (`scripts/orchestrator.py` + `ClaudeExecutor`,
which already exists as ADR-028 dogfood infrastructure).

### What's already in the stack

- `docker-compose.cognitive-os.yml` provisions **LiteLLM** (`berriai/litellm`)
  and **Bifrost** (`maximhq/bifrost`) — two LLM gateways.
- `lib/model_router.py` — multi-provider routing table (data-driven, no
  dispatch logic yet).
- `lib/cost_predictor.py` — cost estimation per provider/model.
- `scripts/orchestrator.py` — executor-mode entry point (used by
  `ORCHESTRATOR_MODE=executor`).
- `rules/model-routing.md` — documented cascade including OpenRouter free
  tier as last-resort fallback.

None of these are wired end-to-end. The LiteLLM container runs empty (no
routing config). Bifrost runs but is unreferenced. `model_router.py` has
routing tables but does not actually dispatch requests.

## Decision

**Remove LiteLLM. Do NOT adopt Bifrost as proxy. Implement direct-SDK
dispatch in `lib/model_router.py`. Build a multi-provider cascade using
Z.AI GLM + Qwen + MiniMax + OpenRouter, skipping Anthropic API direct as
the primary overflow path (reserved for critical tasks only).**

### Why not LiteLLM

**LiteLLM was the subject of a supply chain compromise in March 2026**
(Trend Micro Research publication, March 2026). The attack exploited
LiteLLM's Python dependency tree — a malicious package was injected
upstream and propagated via `pip install litellm`. Trust boundary:
every installer downloads and executes untrusted code.

Additional concerns independent of the specific incident:

- **Proxy pattern concentrates credentials**: LiteLLM holds all provider
  API keys in memory. A compromise of the proxy = compromise of every
  upstream provider account.
- **~8ms proxy overhead per request** at observed volume. Noise at low RPS
  but measurable in latency-sensitive orchestration loops.
- **No semantic cache**, exact-match only.
- **Active maintenance but high issue volume** — large attack surface due
  to Python deps + many provider adapters.

### Why not Bifrost (either)

Bifrost is genuinely better than LiteLLM on multiple dimensions:

| Dimension | LiteLLM | Bifrost |
|---|---|---|
| Language | Python (large dep tree) | Go (single compiled binary) |
| Overhead @ 5K RPS | ~8ms | ~11µs (50× faster) |
| Supply chain surface | pip + transitive deps | Binary ship, deps compiled by maintainer |
| License | MIT | Apache 2.0 |
| Documented CVEs | Multiple (incl. 2026 supply chain) | None found |
| Semantic cache | No | Yes |
| MCP support | No | Yes |
| Vault integration | Plugin-based | Native HashiCorp |

But Bifrost **still proxies API keys** and adds an additional container to
the security perimeter. For our use case (overflow dispatch for sub-agents
in dev, not production at 500+ RPS), the benefits of a proxy do not
justify the additional attack surface.

**Bifrost would be the right choice** if:
- We ran a multi-user production service at high RPS
- We needed semantic caching (prompt reuse across users)
- We needed advanced load balancing / cluster mode

None of those apply to orchestrating sub-agents for a single operator.

### Why direct SDKs

- **Smallest attack surface**: only the SDKs we actually import (`anthropic`,
  `openai` — OpenRouter/DeepSeek/Qwen/GLM are all OpenAI-compatible via
  `base_url` override).
- **No proxy container** to maintain, patch, monitor, or compromise.
- **Keys never leave Python process memory** + `.env` file. Standard
  secret-management practices apply (credential-management.md).
- **Latency**: zero proxy hop. Only network RTT to provider.
- **Cost**: zero infra cost (no LiteLLM/Bifrost container resources).
- **Complexity**: the "unified API" value prop of gateways is trivially
  replaced by a 30-line dispatch function since OpenAI-compatible is the
  de facto standard.

### Provider cascade

Primary → overflow → emergency, selected by cost and reliability for
sub-agent code tasks (the dominant workload):

| Priority | Provider | Access | Cost (1M in / 1M out) | Quality | Rationale |
|---|---|---|---|---|---|
| 1 | Claude Max subscription | Native Agent tool | $0 (until rate-limit hit) | ⭐⭐⭐⭐⭐ | Already paid |
| 2 | Z.AI GLM Coding Plan Lite | Subscription $9/mo | $0 marginal | ⭐⭐⭐⭐ | Includes GLM-5.1, GLM-5-Turbo, GLM-5v-Turbo (vision), GLM-4.7 fallbacks. Unlimited bursts. |
| 3 | Qwen 3.6 Plus | OpenRouter or Alibaba Cloud | $0.325 / $1.95 | ⭐⭐⭐⭐ (SWE-bench 78.8) | 1M context, strong code. Pay-per-use. |
| 4 | MiniMax M2.7 | MiniMax API | $0.30 / $1.20 | ⭐⭐⭐⭐ | 205K context, ultra-cheap for long-tail tasks. |
| 5 | OpenRouter free tier | OpenRouter (free models) | $0 | ⭐⭐⭐ (degraded) | Llama 3.1 70B, Nemotron, Qwen3 free. 50 req/day or 1000 with $10 balance. |
| (deferred) | Anthropic API direct | Anthropic SDK | $3 / $15 Sonnet, $15 / $75 Opus | ⭐⭐⭐⭐⭐ | Only for critical tasks where cost is justified. Not primary overflow. |

### Cost simulation

Burst: 4 opus-class agents, 200K input / 80K output total.

| Provider | Cost | vs Anthropic direct |
|---|---|---|
| Claude Max subscription | $0 | free |
| Z.AI GLM Coding Plan Lite | $0 marginal ($9/mo flat) | ∞× (unlimited bursts) |
| GLM-5.1 API pay-per-use | $0.63 | 14× cheaper |
| Qwen 3.6 Plus | $0.22 | 41× cheaper |
| MiniMax M2.7 | $0.16 | 56× cheaper |
| **Anthropic API direct Opus** | **$9.00** | baseline (reference) |

A month of typical overflow usage (say 20 bursts):
- GLM Coding Plan: **$9/mo** fixed
- Qwen 3.6 Plus via OpenRouter: **~$4.40/mo**
- MiniMax M2.7: **~$3.20/mo**
- Anthropic API direct: **~$180/mo**

Total recommended stack: **$220/mo** (Claude Max $200 + GLM Lite $9 +
Qwen/MiniMax ~$10) with effectively unlimited overflow.

Versus Anthropic API direct as overflow: **$260–380/mo** for marginally
better quality on 5% of tasks.

## Pros and cons summary

### LiteLLM

**Pros**
- Mature (~12k stars), many provider adapters.
- Unified API, extensive docs.
- Python-native, easy install.

**Cons**
- **Active supply chain compromise (March 2026)** — disqualifying.
- Proxy pattern concentrates keys.
- 8ms overhead per request.
- Large Python dep tree, sustained attack surface.
- No semantic cache.

**Verdict: REMOVE.**

### Bifrost

**Pros**
- Dramatically safer supply chain than LiteLLM (single Go binary).
- 50× less proxy overhead (11µs vs 8ms).
- Semantic cache + MCP support.
- Apache 2.0, Vault integration.
- Already present in `docker-compose.cognitive-os.yml`.

**Cons**
- Still a proxy (key concentration risk, container to maintain).
- No published security audit.
- Maxim (vendor) commercial pressure toward managed service.
- Adds complexity (separate container) not justified for single-operator
  sub-agent orchestration.

**Verdict: REMOVE for our use case. Re-evaluate if we pivot to
multi-operator production.**

### Direct SDKs (`anthropic` + `openai`)

**Pros**
- Smallest attack surface: only SDKs in `requirements.txt`, no proxy.
- Zero proxy overhead.
- Keys stay in Python process memory + `.env`.
- OpenRouter/DeepSeek/Qwen/GLM/MiniMax all OpenAI-compatible via
  `base_url` → one SDK covers 4 providers.
- Trivial to extend: add provider = add row to routing table.

**Cons**
- We write dispatch logic ourselves (~100–200 lines in `lib/model_router.py`).
- No free semantic caching — but Anthropic prompt caching handles the
  Anthropic-side case, and our workload doesn't reuse prompts across
  users.
- No unified observability out-of-box — but we already have
  `lib/cost_predictor.py` + `lib/cost_dashboard.py`.

**Verdict: ADOPT.**

### Anthropic API direct (as primary overflow)

**Pros**
- Same quality as Claude Max subscription.
- Zero learning curve, same SDK.

**Cons**
- **14–56× more expensive** than GLM/Qwen/MiniMax for the same task
  quality on sub-agent code work.
- Subscription + API direct = paying twice for Anthropic when cheaper
  providers cover the overflow window.

**Verdict: NOT PRIMARY overflow. Reserved as tier 6 for explicitly
critical tasks.**

### Z.AI GLM Coding Plan

**Pros**
- Fixed $9/mo (Lite) with effectively unlimited bursts for code work.
- Includes GLM-5.1 + GLM-5-Turbo + GLM-5v-Turbo (vision) + fallbacks.
- Open-source model family — reproducible on-prem if needed.
- Quality approaches Claude Opus 4.6 on coding benchmarks (per Apiyi.com
  benchmark, GLM-5.1 scores 45.3 on a coding eval vs Opus 4.6 in same
  range).

**Cons**
- Prices doubled Feb 2026 after viral adoption. Expect another bump.
- China-origin model family — some security-sensitive workloads may have
  policy concerns (not applicable to our OS dev, but worth flagging).
- Output quality variance higher than Claude on non-code tasks.

**Verdict: PRIMARY overflow for sub-agent code tasks.**

### Qwen 3.6 Plus

**Pros**
- SWE-bench 78.8 — top-tier code performance.
- 1M context window (largest in cheap tier).
- $0.325 / $1.95 — excellent cost per quality.

**Cons**
- Pay-per-use only (no subscription plan accessible from outside Alibaba
  Cloud ecosystem).
- Alibaba Cloud Model Studio signup friction for non-Chinese accounts;
  OpenRouter is the practical access path.

**Verdict: SECONDARY overflow, especially for long-context or coding-
heavy tasks.**

### MiniMax M2.7

**Pros**
- $0.30 / $1.20 — cheapest in the usable-quality tier.
- 205K context.
- Good for long-tail low-priority tasks (nightly batches, doc gen).

**Cons**
- Weaker at complex reasoning vs Claude / GLM-5.1 / Qwen 3.6.
- No subscription plan.
- Newer (Mar 2026 release), less community tooling.

**Verdict: TERTIARY overflow for cost-sensitive bulk work.**

### OpenRouter

**Pros**
- Unified access to 200+ models via OpenAI-compatible API.
- Pass-through pricing (no markup on underlying provider).
- Free tier for testing (50 req/day baseline, 1000 with $10 balance).
- BYOK mode: first 1M requests/mo free with own provider keys.

**Cons**
- 5.5% fee on credit purchases.
- Additional vendor in the chain (one more point of account compromise).

**Verdict: ADOPT for access to Qwen/MiniMax without separate signups,
AND as emergency free tier.**

## Consequences

### Positive

- **Supply chain attack surface reduced**: no LiteLLM, no proxy with
  aggregated API keys.
- **Cost envelope predictable**: $220/mo stack with unlimited overflow
  for code work. No surprise bills.
- **Provider independence**: cascade means no single vendor can hold
  service hostage via rate limits or price hikes.
- **Simpler debugging**: direct SDK calls, standard Python tracebacks,
  no proxy black-box.

### Negative

- **We own the dispatch logic**: `lib/model_router.py` becomes a
  first-class component we must maintain. Estimated 2–3 hours initial
  build + ongoing upkeep per provider addition (~30 min each).
- **Quality variance**: GLM/Qwen/MiniMax output can differ from Claude
  for non-code tasks. Mitigated by routing high-priority tasks to
  Anthropic API direct (tier 6) when budget permits.
- **Multiple API keys to manage**: Z.AI + Qwen (or OpenRouter BYOK) +
  MiniMax + OpenRouter + Anthropic API. Mitigation: `.env` + Vault
  integration planned.

### Neutral

- **Bifrost remains in docker-compose.cognitive-os.yml temporarily** —
  flagged for removal in same PR as LiteLLM, but keeping Docker cleanup
  atomic to avoid compose drift mid-transition.
- **ADR-022 references LiteLLM** — needs update pointer to this ADR.

## Rollout

1. ✅ Document analysis (this ADR) — DONE 2026-04-21.
2. **Remove LiteLLM** from docker-compose.cognitive-os.yml + `cognitive-os.yaml`
   `runtime.litellm` section — 30 min.
3. **Remove Bifrost** from same files — 15 min.
4. **Extend `lib/model_router.py`** with dispatch functions:
   `call_claude_subscription()` (via Agent tool), `call_glm()`, `call_qwen()`,
   `call_minimax()`, `call_openrouter_free()`, `call_anthropic_direct()`.
   Budget-aware cascade with retry on rate-limit. ~2h + tests.
5. **Add new validator contract** `meta.llm_providers_reachable` in
   `scripts/cos-config-audit.sh` that pings each configured provider
   at `cos-config-audit` time and reports availability. ~45 min.
6. **Deprecate `ORCHESTRATOR_MODE=executor` reliance on LiteLLM**:
   update `scripts/orchestrator.py` to use `lib/model_router.py` dispatch
   directly. ~1h.
7. **Rate-limit detector hook** (`hooks/rate-limit-detector.sh`): watches
   Claude Code stderr/tool results for "out of extra usage"; when seen,
   auto-sets `ORCHESTRATOR_MODE=executor` for rest of session. ~45 min.
8. **User-side API keys** (manual, not in this ADR's scope):
   - Z.AI Coding Plan Lite signup + `ZAI_API_KEY` in `.env`
   - OpenRouter signup + `OPENROUTER_API_KEY` in `.env` + $10 top-up
   - MiniMax signup + `MINIMAX_API_KEY` in `.env`
   - Qwen access via OpenRouter (simpler) or Alibaba Cloud (if DashScope
     direct preferred)
9. **Test with 5-agent parallel burst** while at Claude Max rate-limit,
   confirm fallback to GLM works, validate cost tracking.

**Total engineering effort: ~5 hours** across ~2 sessions.

## Related

- ADR-022 — LiteLLM adoption (superseded by this decision).
- ADR-028 — `ORCHESTRATOR_MODE=executor` framework (this ADR replaces its
  LiteLLM dependency with direct-SDK dispatch).
- ADR-042 — Valkey local daemon (precedent for pip-first / library-mode
  migration).
- `rules/model-routing.md` — routing table documentation (update after
  implementation).
- `rules/resource-governance.md` — budget enforcement (update with new
  cascade).
- `lib/model_router.py` + `lib/cost_predictor.py` — implementation surface.
- `rules/credential-management.md` — API key hygiene for new providers.

## Verification

After rollout completion:

```bash
# Validator reports all 5 providers reachable
python3 scripts/cos-config-audit.sh | grep llm_providers_reachable

# Direct SDK smoke test
python3 -c "from lib.model_router import dispatch; print(dispatch('test', budget_usd=0.01))"

# No LiteLLM/Bifrost containers
docker ps --filter name=cognitive-os- --format '{{.Names}}' | grep -E 'litellm|bifrost'
# (should return empty)

# ADR trail intact
grep -r 'ADR-049' docs/adrs/ADR-022.md docs/adrs/ADR-028.md rules/model-routing.md
```

## Open questions (non-blocking)

1. **Should we build a dedicated config file for provider cascade**
   (`providers.yaml`) instead of expanding `cognitive-os.yaml`? Argument
   for separation: provider tuning is high-churn (prices move monthly),
   main config is stable. Argument against: one more config surface.
2. **OpenRouter BYOK mode** — if we hold our own Anthropic API key,
   routing via OpenRouter BYOK gives us unified observability + 1M
   free requests/mo. Worth evaluating once direct-SDK baseline is
   shipped.
3. **Semantic cache** — if we find ourselves re-sending similar prompts
   (e.g. SDD phase templates), we may want to add a thin cache layer
   in `lib/model_router.py` (Python dict + TTL). Bifrost would have
   given this for free. Keep under observation.

## Sources

- [Trend Micro: LiteLLM Supply Chain Compromise (March 2026)](https://www.trendmicro.com/en_us/research/26/c/inside-litellm-supply-chain-compromise.html)
- [GitHub: maximhq/bifrost](https://github.com/maximhq/bifrost)
- [Bifrost vs LiteLLM: Best LLM Router (getmaxim.ai)](https://www.getmaxim.ai/articles/best-llm-router-for-enterprise-ai-bifrost-vs-litellm/)
- [Bifrost vs LiteLLM (truefoundry.com)](https://www.truefoundry.com/blog/bifrost-vs-litellm)
- [Z.AI GLM Coding Plan subscribe page](https://z.ai/subscribe)
- [Z.AI Pricing 2026 overview (vibecoding.app)](https://vibecoding.app/blog/zhipu-ai-glm-pricing-2026)
- [GLM Coding Plan price doubling after viral adoption (remio.ai)](https://www.remio.ai/post/the-glm-coding-plan-went-viral-in-north-america-then-the-price-doubled)
- [Qwen 3.6 Plus on OpenRouter](https://openrouter.ai/qwen/qwen3.6-plus)
- [MiniMax M2.7 pricing](https://pricepertoken.com/pricing-page/model/minimax-minimax-m2.7)
- [OpenRouter pricing FAQ](https://openrouter.ai/pricing)
- [LiteLLM vs Bifrost after supply chain wake-up (Medium, Mar 2026)](https://medium.com/@pranaybatta2014/litellm-vs-bifrost-in-2026-an-honest-comparison-after-the-supply-chain-wake-up-call-f53911ced0f2)
