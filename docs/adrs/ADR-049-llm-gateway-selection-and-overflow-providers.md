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
| 2 | **Alibaba Qwen Coding Plan Pro** | Subscription $50/mo (first month $15, second $25 promo) | $0 marginal | ⭐⭐⭐⭐⭐ | **SELECTED OVERFLOW PROVIDER.** Multi-model aggregator: Qwen3.6-plus (1M context, SWE-bench 64.8), Qwen3-Max, Qwen3-Coder variants, plus **Kimi-K2.5, GLM-5, MiniMax-M2.5 bundled**. 90K req/mo, 6000/5h, 45K/week. Works with Claude Code, Cursor, Cline, Qwen Code. ToS: interactive coding tools only (no batch/cron). |
| 3 | Qwen 3.6 Plus | OpenRouter or Alibaba Cloud | $0.325 / $1.95 | ⭐⭐⭐⭐ (SWE-bench 78.8) | 1M context, strong code. Pay-per-use. |
| 4 | MiniMax M2.7 | MiniMax API | $0.30 / $1.20 | ⭐⭐⭐⭐ | 205K context, ultra-cheap for long-tail tasks. |
| 5 | OpenRouter free tier | OpenRouter (free models) | $0 | ⭐⭐⭐ (degraded) | Llama 3.1 70B, Nemotron, Qwen3 free. 50 req/day or 1000 with $10 balance. |
| (deferred) | Anthropic API direct | Anthropic SDK | $3 / $15 Sonnet, $15 / $75 Opus | ⭐⭐⭐⭐⭐ | Only for critical tasks where cost is justified. Not primary overflow. |

### Cost simulation

Burst: 4 opus-class agents, 200K input / 80K output total.

| Provider | Cost | vs Anthropic direct |
|---|---|---|
| Claude Max subscription | $0 | free |
| Alibaba Qwen Coding Plan Pro | $0 marginal ($50/mo flat) | ∞× (90K req/mo headroom) |
| GLM-5.1 API pay-per-use | $0.63 | 14× cheaper |
| Qwen 3.6 Plus | $0.22 | 41× cheaper |
| MiniMax M2.7 | $0.16 | 56× cheaper |
| **Anthropic API direct Opus** | **$9.00** | baseline (reference) |

A month of typical overflow usage (say 20 bursts):
- Alibaba Qwen Coding Plan Pro: **$50/mo** fixed (first month $15 promo)
- Qwen 3.6 Plus via OpenRouter: **~$4.40/mo**
- MiniMax M2.7: **~$3.20/mo**
- Anthropic API direct: **~$180/mo**

Total recommended stack: **$250/mo** (Claude Max $200 + Alibaba Qwen
Coding Pro $50) with effectively unlimited overflow for interactive
coding work.

Versus Anthropic API direct as overflow: $260–380/mo for marginally
better quality on 5% of tasks.

### Single-overflow decision (MiniMax Max vs Qwen Pro at $50/mo)

Both subscriptions are exactly $50/mo. Exhaustive matrix:

| Dimension | MiniMax Coding Plan Max | Alibaba Qwen Coding Plan Pro | Winner |
|---|---|---|---|
| Price | $50/mo ($500/yr saves $100) | $50/mo (promo: $15 m1, $25 m2) | Qwen (promo) |
| Quota / 5h | 1,000–4,500 prompts | **6,000 requests** | Qwen |
| Weekly | ~10,000 | **45,000** | Qwen (4.5×) |
| Monthly | ~40,000 | **90,000** | Qwen (2.25×) |
| Model families | 1 (MiniMax M2.x only) | **6** — Qwen3.6-plus, Qwen3-Max, Coder variants + **Kimi-K2.5, GLM-5, MiniMax-M2.5 bundled** | **Qwen** |
| Context window | 200K | **1M** (Qwen3.6-plus) | Qwen (5×) |
| SWE-bench | 53.7 (M2.7) | **64.8** (Qwen3.6-plus) | Qwen (+20%) |
| Terminal-Bench 2.0 | 57% | **61.6%** | Qwen |
| Vendor stability | Startup (IPO'd 2025) | **Alibaba Cloud** enterprise | Qwen |
| Automated use (batch/cron) | **Allowed** | **Prohibited** (interactive only) | MiniMax |
| Yearly lock-in option | Yes ($500) | Monthly only | MiniMax |
| Tool support | 20+ (Claude Code, Cursor, Cline, Kilo, Roo…) | Claude Code, Cursor, Cline, Qwen Code, Kilo | Functional tie |

**Qwen Pro wins on 7 dimensions, MiniMax on 2 (batch permission, yearly
option).**

### Why the "interactive only" ToS is acceptable

Qwen Pro's restriction against automated/batch/backend use would disqualify
it if our overflow target included:
- Cron-scheduled LLM evaluators
- Nightly SDD pipelines running unattended
- Webhook handlers invoking LLM
- Application backends

**Our actual overflow target is the opposite**: sub-agents spawned during
an interactive Claude Code session when the user has hit rate-limit. That
IS interactive coding — the user is present, typing, triaging agent output.
This is exactly what Qwen Pro's ToS permits.

If we later need a batch-capable provider (e.g. weekly audit hook that
calls LLM), we add MiniMax pay-per-use (`$0.30/$1.20 per 1M`, no
subscription, ToS-unrestricted) as a Tier 3 addition — estimated
$2-5/mo real usage. Not needed now.

### Why not Z.AI GLM

Earlier drafts of this ADR selected Z.AI Pro Quarterly at $64.80/mo as
the primary overflow. Superseded by Qwen Pro for these reasons:

- **Cheaper** ($50 vs $64.80 = $14.80/mo save)
- **More models per dollar** — Qwen Pro bundles Kimi + GLM + MiniMax IN
  ADDITION to Qwen family. Z.AI bundles only GLM family.
- **Larger context** — Qwen3.6-plus 1M vs GLM-5.1 200K.
- **Higher code quality** — Qwen3.6-plus SWE-bench 64.8 vs GLM-5.1 ~45.
- **More stable vendor** — Alibaba. Z.AI raised prices 2× in 2 months
  (Feb + Apr 2026) — quarterly lock doesn't help if they hike again.

Z.AI remains a viable alternative if user prefers the interface or has a
specific preference for GLM models. Documented here as an analyzed-but-
rejected option.

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
- Z.AI evaluated but superseded by Qwen Pro (see comparison above) — $50
  vs $64.80, larger context, more model families bundled, more stable
  vendor.
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

## Implementation — Feature Flag Pattern (NORMATIVE)

All providers are implemented as stubs in `lib/model_router.py` from the
start, but enabled individually via `cognitive-os.yaml` feature flags.
This decouples "we support provider X" from "provider X is active in this
session." Users opt in to each provider by obtaining the API key and
flipping `enabled: true`.

### Canonical schema

```yaml
# cognitive-os.yaml
providers:
  claude_max:
    enabled: true                       # STATUS: implemented
    priority: 1                         # native Agent tool, always primary
    notes: "Claude Code Max subscription, used via native Agent tool"

  alibaba_qwen:                         # SELECTED as single overflow provider
    enabled: true                       # STATUS: implemented
    priority: 2
    api_key_env: ALIBABA_QWEN_API_KEY
    default_model: qwen3.6-plus         # 1M context, SWE-bench 64.8
    base_url: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    fallback_models: [qwen3-max, qwen3-coder-plus, qwen3-coder-next, kimi-k2.5, glm-5, minimax-m2.5]
    quota_per_month: 90000
    quota_per_5h: 6000
    tos_interactive_only: true          # no batch/cron/backend use

  zai_glm:                              # EVALUATED, not selected — alternative
    enabled: false                      # STATUS: implemented
    priority: 6                         # lowered to fallback tier
    api_key_env: ZAI_API_KEY
    default_model: glm-5.1
    base_url: https://open.bigmodel.cn/api/paas/v4/
    fallback_models: [glm-5-turbo, glm-5v-turbo, glm-4.7]

  qwen:
    enabled: false                      # STATUS: implemented
    priority: 3
    api_key_env: OPENROUTER_API_KEY     # simplest path (no Alibaba Cloud signup)
    default_model: qwen/qwen3.6-plus
    base_url: https://openrouter.ai/api/v1

  minimax:
    enabled: false                      # STATUS: implemented
    priority: 4
    api_key_env: MINIMAX_API_KEY
    default_model: minimax-m2.7
    base_url: https://api.minimax.io/v1

  openrouter_free:
    enabled: false                      # STATUS: implemented
    priority: 5
    api_key_env: OPENROUTER_API_KEY
    default_model: nvidia/llama-3.1-nemotron-ultra-253b:free
    base_url: https://openrouter.ai/api/v1
    notes: "Emergency free tier — 50 req/day or 1000 with $10 balance"

  anthropic_api_direct:
    enabled: false                      # STATUS: implemented — opt-in for critical only
    priority: 6
    api_key_env: ANTHROPIC_API_KEY
    default_model: claude-opus-4-7
    notes: "Reserved for critical tasks — $15/$75 per 1M tokens"
```

### Dispatch algorithm

`lib/model_router.py::dispatch(task, budget_remaining_usd)` iterates only
the providers with `enabled: true`, sorted by `priority` ascending:

```python
def dispatch(task, budget_remaining_usd):
    for provider in sorted_enabled_providers():
        if not provider_budget_ok(provider, task, budget_remaining_usd):
            continue
        try:
            return call_direct_sdk(provider, task)
        except RateLimitError:
            log_rate_limit(provider); continue
        except ProviderUnavailable:
            log_outage(provider); continue
    raise NoProvidersAvailable("all enabled providers exhausted or budgeted out")
```

Each `call_direct_sdk(provider, task)` uses the appropriate SDK:
- `claude_max` → Claude Code native Agent tool (NOT direct SDK — special path)
- `anthropic_api_direct` → `anthropic` SDK
- everything else → `openai` SDK with `base_url` override

### Minimum viable setup (1 provider)

User wants to start with ONE provider (Z.AI Lite). Steps:

1. `zai_glm.enabled: true` in `cognitive-os.yaml`
2. `ZAI_API_KEY=...` in `.env`
3. Leave all others at `enabled: false`

Router works end-to-end with a single overflow provider. No code changes.

When user decides to add MiniMax later:

1. `minimax.enabled: true`
2. `MINIMAX_API_KEY=...` in `.env`
3. Done. Router picks it up on next invocation.

**Adding a NEW provider not in the list** (e.g. DeepSeek):

1. Add row to `providers:` block in yaml
2. Add `call_deepseek(...)` stub in `lib/model_router.py` (~15 lines,
   OpenAI-compatible via `base_url`)
3. Add test covering the dispatch path
4. PR review

**Disabling a provider temporarily** (e.g. provider has an outage):

1. `enabled: false` in yaml
2. Next dispatch skips it
3. No code changes, no restart

### Validator contract

`scripts/cos-config-audit.sh` gains contract `meta.llm_providers_reachable`:

- For each `enabled: true` provider, ping a cheap endpoint (model list /
  health check) with the configured API key.
- Reports IMPL if all enabled providers respond; PARTIAL if key missing;
  ASPIR if endpoint unreachable or 401/403.

Prevents the "enabled but misconfigured" drift (similar gap to
`meta.settings_freshness`).

### Zero-provider fallback

If all providers fail or are disabled, the router raises
`NoProvidersAvailable`. The orchestrator logs this and falls back to the
native Agent tool even if it's rate-limited — user sees the original
"You're out of extra usage" error rather than silent hang.

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

1. **Dedicated `providers.yaml` file vs expanding `cognitive-os.yaml`**.
   Provider tuning is high-churn (prices move monthly); main config is
   stable. Separation would scope reviews better. Argument against: one
   more config surface to track. **Deferred — revisit after 3 months of
   real usage.**

2. **OpenRouter BYOK mode** — if we hold our own Anthropic API key,
   routing via OpenRouter BYOK gives us unified observability + 1M free
   requests/mo. Worth evaluating once direct-SDK baseline is shipped.
   **Deferred — revisit after Milestone 2 (3+ providers active).**

3. **Semantic cache** — if we find ourselves re-sending similar prompts
   (e.g. SDD phase templates), a thin cache layer in `lib/model_router.py`
   (Python dict + TTL) would help. Bifrost would have given this for
   free. **Keep under observation — add if repeat-prompt rate > 20% in
   metrics.**

4. **Automatic rate-limit detection accuracy** — step 7 of rollout adds
   `hooks/rate-limit-detector.sh` that greps stderr for "out of extra
   usage". Claude's error wording may change. Mitigation: maintain a
   regex pattern list in the hook, update on observed new wording, log
   unmatched errors for manual review.

5. **Claude Max subscription recovery signal** — currently no automated
   way to detect when the subscription cooldown ends (reset hour known
   in user's local TZ but not broadcast to the hook). Router will keep
   fallback-routing until user manually re-enables. Future: parse the
   "resets Xpm (America/Buenos_Aires)" message, schedule a re-check
   hook at that time.

## Architecture Correction (2026-04-21)

Original ADR-049 wrote "Claude primary + Qwen reactive fallback." That
direction was wrong for our actual use case:

- **Main chat (user↔Claude Code) cannot be redirected** — Claude Code
  is a proprietary app; no plugin/hook intercepts the primary chat.
- **Sub-agents via `scripts/orchestrator.py`** can be redirected.

Corrected architecture (Option B, implemented as mega-plan C1-C7):

- **Qwen is PRIMARY** for sub-agents dispatched via our orchestrator.
  This preserves Claude Max quota for the main chat.
- **Claude is FALLBACK** — only invoked when Qwen fails.
- **Asymmetric cascade advance rules**:
  - Qwen failure → always advance to Claude (Qwen is overflow)
  - Claude failure → only advance if rate-limit (don't mask non-quota
    errors behind a cheaper provider)

## Implementation checkpoints (mega-plan)

| Checkpoint | Deliverable | Status |
|---|---|---|
| C0 | `.cognitive-os/plans/roadmaps/adr-049-050-051-mega-plan.md` persisted | ✅ |
| C1 | `--providers` CLI (Option B cascade) + kill-switches | ✅ |
| C2 | `lib/dispatch.py` abstract router + JSONL metrics foundation | ✅ |
| C3 | `rules/llm-dispatch.md` + gotcha + ref-key | ✅ |
| C4 | `/llm-status` skill (`scripts/llm_status.py`) | ✅ |
| C5 | `docs/runbooks/llm-dispatch.md` operational guide | ✅ |
| C6 | ADR-049 update (this section) + ADR-050/052/053 stubs | ✅ |
| C6.5 | `claude-code-router` research (NO-GO verdict) | ✅ |
| C7 | ADR-051 Phase 1 Qwen agent loop (Read/Edit/Bash tools) | ✅ |
| C8 | ADR-051 Phase 2/3/4 (remaining tools, hooks injection, parity) | DEFERRED |

## Future Extensibility

Reserved ADR slots:

- **ADR-050** Per-Skill Routing Policy — `routing:` frontmatter schema,
  `skill_requirements` parameter already reserved in
  `lib/dispatch.dispatch()`.
- **ADR-051** Qwen Agent Loop — Phase 1 shipped (`lib/qwen_agent_loop.py`),
  Phases 2-4 deferred.
- **ADR-052** Provider Benchmark Harness — quality signal producer,
  feeds ADR-053.
- **ADR-053** Dispatch Auto-Optimizer — consumes `llm-dispatch.jsonl`
  + benchmark data to re-tune routing per `(skill, task_type)`.

None of these are required for the current Qwen+Claude cascade to
function. They unlock multi-provider + per-skill + adaptive routing
when/if that complexity is justified by observed usage patterns.

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
