---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/llm-dispatch.md
provenance: "Operator runbook for ADR-049's sub-agent LLM dispatch system (Qwen primary, Claude fallback) covering activation, dispatch patterns, kill-switches, troubleshooting, security, and cost monitoring."
---

## What it is

An operator-audience runbook for the daily operation of the LLM dispatch system (ADR-049), which cascades sub-agent tasks through a Qwen-primary / Claude-fallback provider chain to preserve Claude Max usage.

## Key mechanics

- **Quick start**: verify wiring with `bash scripts/smoke-qwen-fallback.sh` (expect `ALL 4 CHECKS PASS`), check provider state with `python3 scripts/llm_status.py`, dispatch a test task via `scripts/orchestrator.py --task "..." --providers qwen,claude`.
- **Fresh activation**: subscribe to Alibaba Qwen Coding Plan Pro ($50/mo, 90K req/mo, first-month $15 promo — plans release in daily batches and may show "out of stock, restocking at HH:MM"), generate an API key in Model Studio, add `ALIBABA_QWEN_API_KEY` and `ALIBABA_QWEN_BASE_URL` to gitignored `.env` (never pasted in chat/commit/PR/issue — rotate immediately if exposed), install the SDK via `uv sync --extra direct_providers`.
- **Dispatch patterns**: default cascade `--providers qwen,claude` (Qwen primary, Claude fallback on failure); single-provider pinning; inverted priority `--providers claude,qwen` reserved for when quality is critical; programmatic dispatch via `cos_lib.dispatch.dispatch()`; multi-step tool-use tasks via `cos_lib.qwen_agent_loop.run_agent()` — Phase 1 tool whitelist is limited to Read/Edit/Bash, with Grep/WebFetch arriving in a stated future Phase 2.
- **Kill-switches**: remove the API key (soft), `COS_DISABLE_QWEN=1` (skip Qwen this session), `COS_FORCE_CLAUDE_PRIMARY=1` (rewrites `--providers` to `["claude"]`), `COS_DISABLE_LLM_FALLBACK=1` (primary fires, error surfaces immediately on failure — for debugging/strict single-provider policy), `COS_SKIP_DOTENV=1` (agent-safe smoke test using only already-exported env vars, avoids indirectly loading repo `.env`).
- **Credential-safe smoke wrapper**: `scripts/cos-credential-safe-run qwen-fallback-smoke --approve` reads only the three Qwen-specific `.env` keys, forces `COS_SKIP_DOTENV=1` for the child process, verifies a pinned script hash, sanitizes the environment, redacts output, and logs to `.cognitive-os/metrics/credential-safe-runs.jsonl` without secret values — the documented path for letting an agent run the live smoke using repo credentials.
- **Important limitation called out explicitly**: a Claude Max rate-limit that blocks the primary chat interface is NOT solved by ADR-049 — Claude Code's native chat can't be redirected through this dispatch system. Documented workarounds: wait for reset, use a dual-IDE (Cline/Cursor/Qwen Code) configured with the Qwen key, or use CLI dispatch from a terminal for batch work in the meantime.
- **Troubleshooting table** covers: SDK-not-installed (`meta.llm_providers_reachable = ASPIR`), Qwen 401 (check key format/whitespace, 37-char length including newline, Active status in Alibaba panel, possible "out of stock" subscription state), base-URL 404 (workspace-scoped endpoint format), cascade-skip message causes, and a live-probe snippet for when unit tests pass but the live API fails.
- **Security**: API key exposure response (revoke → regenerate → update `.env` everywhere → search/redact from transcripts/logs → rotate quarterly); `.env` hygiene checks; audit via `tail .cognitive-os/metrics/llm-dispatch.jsonl`.
- **Cost monitoring**: `llm_status.py --days 1|30` for daily/monthly totals by provider, plus a raw JSONL aggregation snippet for custom date-range cost queries.
- **Expected healthy-state matrix** ties together: `meta.llm_providers_reachable` = IMPL, smoke script 4/4, `llm_status.py` shows ≥1 configured provider with no kill-switches, the metrics JSONL is actively writing, and `pytest tests/unit/test_dispatch.py` passes.

## Relations & where used

Normative counterpart is `rules/llm-dispatch.md`; decision record is ADR-049; implementation lives in `lib/dispatch.py` (dispatch), `lib/qwen_provider.py` (direct SDK), `lib/qwen_agent_loop.py` (ADR-051 Phase 1 tool-use loop); operator-facing entry point is the `llm-status` skill; roadmap tracked in `.cognitive-os/plans/roadmaps/adr-049-050-051-mega-plan.md`.

## Status / caveats

No dated point-in-time claims beyond illustrative example output (agent IDs, costs, timestamps) which are clearly examples, not live state. The Qwen agent-loop tool whitelist is explicitly marked as a partial/Phase-1 capability with a stated future Phase 2 — this is a forward-looking roadmap note, not a completed feature, and should be read as such. No internal inconsistencies found.
