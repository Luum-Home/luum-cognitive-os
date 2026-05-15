---
adr: 288
title: Web-Automation Adapter for Dispatch (browser-use)
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: []
superseded_by: null
implementation_files:
  - pyproject.toml
  - lib/browser_use_adapter.py
  - lib/web_automation_router.py
  - skills/browser-task/SKILL.md
  - tests/unit/test_browser_use_adapter.py
  - tests/integration/test_dispatch_web_automation_routing.py
tier: maintainer
tags:
  - web-automation
  - dispatch
  - browser-use
classification_basis: optional browser-use dependency, adapter, router, skill, and dispatch-routing tests implemented as the accepted Slice A integration; no remaining in-scope work for this ADR, and dispatch.py caller expansion is separate/out-of-scope follow-up
---

# ADR-288: Web-Automation Adapter for Dispatch (browser-use)

## Status

Accepted

- **Status:** Accepted
- **Date:** 2026-05-13
- **Deciders:** platform-safety, agent-runtime
- **Related:** ADR-049 (LLM dispatch), ADR-228 (retry contract + budget gate),
  ADR-232 (sandbox preflight), ADR-236 (deferred tool loading),
  ADR-259 (external pattern adoption posture), ADR-267 (license compliance)
- **Supersedes:** None
- **Blast radius (intended):** 12 files

## Context

`luum-cognitive-os` has no first-class web-automation capability. Agent workflows
that need to navigate, click, extract, or fill web forms currently shell out to
ad-hoc Bash + `curl` flows or punt to the operator. Research recorded on
2026-05-13 (`docs/06-Daily/reports/web-automation-tooling-2026-05-13.md` —
follow-up) identified this as a recurring gap for product-answer and
research-protocol workflows that need live-page evidence rather than static
fetches.

The dispatch surface (`lib/dispatch.py`, 1069 lines) already enforces a strict
four-phase ordering contract (ADR-236 → 232 → 228 → 226). It is **not** safe to
shoehorn a new modality directly into `dispatch()` without an explicit phase
amendment. This ADR therefore adopts a *sidecar* integration: a dedicated
adapter and intent router, wired into `dispatch.py` in a follow-up that updates
the ordering test.

## Alternatives rejected

| Option | License | Verdict | Reason |
|---|---|---|---|
| **Playwright direct** | Apache-2.0 | Rejected | Low-level. No LLM loop, no accessibility-tree extraction, no built-in step planner. We would re-implement what browser-use already provides. |
| **UI-TARS desktop** | Apache-2.0 | Rejected | Target is native-GUI control. Overlap with web is partial and the runtime ships a desktop binary we do not want in our deps. |
| **Selenium / WebDriver** | Apache-2.0 | Rejected | Legacy, no LLM-native abstractions, weaker async story, brittle locators. |
| **Roll our own (Chrome DevTools Protocol + own loop)** | n/a | Rejected | Reinvention. ADR-259 explicitly prefers external pattern adoption when license allows. |
| **browser-use** | MIT | **Accepted** | 93.7k★, MIT, LLM-native loop, accessibility-tree based DOM extraction, provider-agnostic chat models (`ChatOpenAI`, `ChatAnthropic`, `ChatBrowserUse`, …), Python ≥ 3.11 matches our floor, lazy `__getattr__` imports keep cold-start cheap. |

## License Compatibility

`browser-use` is MIT (verified against upstream `pyproject.toml`, v0.12.6 as of
2026-05-13). Per ADR-267 the `license-policy` rule allows MIT for both adoption
of upstream code *and* linking. We adopt the runtime as a declared optional
dependency and import its public API; we do **not** copy source. Attribution
lives in this ADR and in the adapter docstring.

## Decision

1. **Adopt `browser-use>=0.12.6` as an optional runtime dependency** under a new
   `web-automation` extra in `pyproject.toml`. It is **not** part of the
   default install — operators opt in with `uv sync --extra web-automation`.
2. **Introduce `lib/browser_use_adapter.py`**, an adapter that wraps
   `browser_use.Agent`, exposes a `BrowserUseAdapter.run_task(...)` coroutine
   returning a typed `WebAutomationResult`, and emits structured events to the
   existing `AgentPublisher` (`packages/agent-coordination/lib/agent_bus.py`).
3. **Introduce `lib/web_automation_router.py`**, a thin intent classifier with
   `is_web_automation_intent(task: str) -> bool` and a `route(...)` entry that
   either returns a constructed `BrowserUseAdapter` or raises a clear
   `WebAutomationUnavailable` if the package is missing or the kill switch is
   set. This is the integration seam that `lib/dispatch.py` will call from a
   future ADR (see "Follow-up" below).
4. **Add kill switch `COS_DISABLE_WEB_AUTOMATION=1`**, modelled on
   `COS_DISABLE_LLM_FALLBACK` and `COS_FORCE_CLAUDE_PRIMARY`. When set, the
   router refuses to construct the adapter and the dispatch caller MUST handle
   the unavailable case (no silent fallback to a non-browser provider).
5. **Expose `/browser-task` skill** at `skills/browser-task/SKILL.md` for direct
   operator and sub-agent invocation. The skill body documents required env,
   the kill switch, and the cost-tracking model.
6. **Wire cost tracking through `lib.dispatch_cost_predictor.predict_call_cost`**.
   Each browser-use step records observed `tokens_in`/`tokens_out` against the
   selected provider so the existing session budget gate (ADR-228) sees web
   automation as a normal cost source.

## Integration Boundary

```
caller (skill or sub-agent)
    │
    ▼
lib/web_automation_router.py        ← intent detection + kill switch
    │   route()
    ▼
lib/browser_use_adapter.py          ← our code; emits agent_bus events
    │   BrowserUseAdapter.run_task()
    ▼
browser_use.Agent                   ← external (MIT, vendored as dep)
    │
    ▼
ChatAnthropic / ChatOpenAI / ChatBrowserUse  ← provider chosen by adapter
```

The adapter is the **only** module allowed to import from `browser_use`. All
other code paths consume `WebAutomationResult` or the router's facade. This
keeps the blast radius bounded if upstream changes its public API.

## Cost Model

- When the caller selects an **owned provider** (Anthropic / OpenAI key in env),
  cost is computed via the standard `predict_call_cost(provider, …)` flow with
  per-step token counts returned by `browser_use.Agent`'s history.
- When the caller selects **`ChatBrowserUse`** (browser-use's hosted endpoint),
  cost uses upstream's published pricing: **$0.20 / 1M input, $2.00 / 1M output**
  (verified 2026-05-13). The predictor falls through to the `unknown_provider`
  branch and the adapter computes the figure directly, tagging the metric
  `source="adr288_chat_browser_use_pricing"`.
- A failed step still records its consumed tokens; partial cost is honest cost.

## Kill Switch

`COS_DISABLE_WEB_AUTOMATION=1` blocks `web_automation_router.route()` from
returning an adapter. Behaviour:

- The router raises `WebAutomationUnavailable("kill_switch")`.
- The caller is responsible for translating that to a user-visible error;
  there is no silent fallback to a non-browser tool.
- The kill switch is checked **at route time**, so a long-running adapter
  already in flight is not interrupted — consistent with how
  `COS_DISABLE_LLM_FALLBACK` is evaluated only at cascade-advance time.

## Follow-up (deferred from this ADR)

Direct integration into `lib/dispatch.py` is deliberately deferred. `dispatch()`
holds a phase-ordering contract (ADR-236 → 232 → 228 → 226) validated by
`tests/architecture/test_dispatch_ordering_contract.py`. Inserting a new
modality without amending the contract docstring and the architecture test
would be a contract violation. A follow-up ADR will:

1. Reserve a phase number for "modality routing" (proposed: ADR-289).
2. Update the dispatch ordering test.
3. Call `web_automation_router.route(...)` from inside `dispatch()` before the
   ADR-228 cost gate so a browser run debits the session budget correctly.

Until then, `/browser-task` and direct adapter calls are the supported entry
points.

## Consequences

### Positive
- First-class web-automation capability without reinventing a browser loop.
- MIT license keeps us inside ADR-267 allow-list.
- Optional dependency: operators that do not need it pay zero install cost.
- Cost is honest: token usage flows through the same predictor as LLM dispatch.
- Kill switch matches existing operator vocabulary
  (`COS_DISABLE_*`, `COS_FORCE_*`).

### Negative
- We inherit a transitive dependency surface (anthropic, openai, google-genai,
  browser-use-sdk). Mitigated by the `web-automation` extra so it is opt-in.
- `browser_use.Agent` is the upstream's public API but it is still a moving
  target at v0.12.x. We pin `>=0.12.6,<0.13` and rely on the adapter as the
  single import site.
- Headful browser runs are expensive. The skill documents `headless=True` as
  default and recommends caching evidence to `docs/06-Daily/reports/`.

### Risks
- **Upstream API drift.** Mitigation: the adapter is the only import site, and
  a smoke test exercises the constructor and `run_task` signature.
- **Cost runaway on long pages.** Mitigation: `max_steps` defaults to 50; the
  cost predictor records each step so the session budget gate (ADR-228) trips
  before the wallet does.
- **Sandbox escape from a hostile page.** Mitigation: web automation is a
  network-touching capability. When the caller passes
  `skill_requirements.require_sandbox`, the future dispatch integration will
  run the adapter inside the existing sandbox plan (ADR-232). Until then,
  `/browser-task` documents that hostile-URL workflows MUST set the env var
  `COS_BROWSER_USE_TRUSTED_ONLY=1` and gate the URL list at the call site.

## Verification

```bash
python3 -m pytest tests/unit/test_browser_use_adapter.py tests/integration/test_dispatch_web_automation_routing.py -q
```

- `tests/unit/test_browser_use_adapter.py` — mocks `browser_use.Agent`,
  validates event emission, cost tracking, and kill-switch behaviour.
- `tests/integration/test_dispatch_web_automation_routing.py` — exercises
  router intent detection, fallback when the package is missing, and the
  unavailable error envelope.
- No real browser is launched in CI. The smoke test mocks
  `browser_use.Agent.run` to return a synthetic `AgentHistoryList`.

## References

- Upstream: <https://github.com/browser-use/browser-use> (MIT, 93.7k★).
- Public API verified 2026-05-13:
  `Agent`, `BrowserSession`, `BrowserProfile`, `Tools`, `Controller`,
  `ChatAnthropic`, `ChatOpenAI`, `ChatBrowserUse`, …
- Pricing for `ChatBrowserUse` verified 2026-05-13: $0.20/$2.00 per million
  input/output tokens.
