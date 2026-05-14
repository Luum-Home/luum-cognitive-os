---
name: browser-task
description: Use when an agent or operator needs to drive a real web browser - navigate
  to a URL, click elements, fill forms, scrape live page content, or extract evidence
  from a site that static HTTP fetches cannot reach. Backed by browser-use (MIT) per
  ADR-288.
version: 0.1.0
audience: both
tags:
- web-automation
- browser
- scraping
- evidence
- browser-use
platforms:
- claude-code
prerequisites:
- uv sync --extra web-automation
routing_patterns:
- pattern: \bbrowser[-\s]?task\b
  confidence: 0.95
- pattern: \bweb[-\s]?automation\b
  confidence: 0.82
- pattern: \b(navigate|browse|scrape|extract|click|fill).+(url|website|page|form)\b
  confidence: 0.78
related_adr: ADR-288
routing_intents:
- intent: interactive_browser_task
  description: User needs a real browser to navigate pages, click elements, fill forms,
    scrape dynamic content, or extract evidence from a live website.
  confidence: 0.86
triggers:
- browser-task
- /browser-task
- Browser Task
- 'Use when an agent or operator needs to drive a real web browser - navigate to a
  URL, click elements, fill forms, scrape '
---
<!-- SCOPE: os-only -->
# Browser Task

> Drive a real browser for navigation, extraction, and form-fill workflows.

## Trigger

Use this skill when the work needs a live browser - not a plain HTTP fetch.
Typical cases:

- "Navigate to a URL and extract the price table."
- "Fill out a form and record the confirmation page."
- "Scrape a dashboard after logging in."

If a plain HTTP fetch (no JS, no auth, no interaction) suffices, prefer
`WebFetch` - it is cheaper and faster.

## Prerequisites

1. The `web-automation` optional dependency must be installed via:
   `uv sync --extra web-automation`.
2. One of the supported LLM credentials must be available in env, OR the
   hosted `ChatBrowserUse` endpoint will be used (pricing: $0.20 / $2.00 per
   million input / output tokens).
3. The kill switch `COS_DISABLE_WEB_AUTOMATION=1` MUST NOT be set. If it is,
   the router will refuse and you must escalate to the operator.

## How to invoke

### From Python (a skill or sub-agent)

```python
from lib.web_automation_router import route, WebAutomationUnavailable
from lib.dispatch_cost_predictor import predict_call_cost

try:
    adapter = route(
        "Navigate to the target URL and extract the headline.",
        llm_provider="browser_use",
        cost_predictor=predict_call_cost,
    )
    result = await adapter.run_task(
        "Navigate to the target URL and extract the headline.",
        max_steps=20,
        headless=True,
    )
except WebAutomationUnavailable as exc:
    # Surface to operator; do NOT silently fall back to a non-browser tool.
    raise
```

### From a synchronous context

```python
result = adapter.run_task_sync(task, max_steps=20)
```

### Result shape

`WebAutomationResult` has:
- `success: bool`
- `final_url: str`
- `screenshots_paths: list[str]`
- `extracted_data: dict`
- `error: str` (empty on success)
- `token_usage: {"input": int, "output": int}`
- `cost_usd: float`
- `steps: int`

## Kill switch

Set the env var `COS_DISABLE_WEB_AUTOMATION=1`.

When set, both `lib.web_automation_router.route()` and
`lib.browser_use_adapter.BrowserUseAdapter(...)` raise
`WebAutomationUnavailable`. This is the operator-level off switch - there is
no silent fallback.

## Cost model

- **Owned providers** (`anthropic`, `openai`): cost flows through
  `lib.dispatch_cost_predictor.predict_call_cost(provider, ...)` exactly like
  any other LLM dispatch. The ADR-228 session budget gate sees web automation
  as a normal cost source.
- **`ChatBrowserUse`** (hosted): $0.20 / $2.00 per million input / output
  tokens, computed directly by the adapter.

A failed run still records the tokens it consumed. Partial cost is honest
cost.

## Defaults and limits

- `headless=True` by default. Override only when an operator is watching.
- `max_steps=50` by default. Raise only after a cost prediction shows it is
  worth it; a runaway loop is the most likely way to overspend.
- Untrusted URLs: set `COS_BROWSER_USE_TRUSTED_ONLY=1` and gate the URL at
  the call site until the future dispatch-integration ADR lands sandbox
  preflight (ADR-232) for browser runs.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `browser_use is not installed` | Missing optional extra | `uv sync --extra web-automation` |
| Kill switch error | `COS_DISABLE_WEB_AUTOMATION=1` set | Unset after operator approval |
| `task does not match ...` | Router intent filter | Re-invoke with `force=True` or rewrite the task |
| `success=False` with error | Page failed (timeout, captcha, blocked) | Inspect screenshots; reduce scope; do not retry blindly |

## References

- ADR-288 - Web-Automation Adapter for Dispatch.
- Upstream: `browser-use` (MIT).
- Cost flow: `lib/dispatch_cost_predictor.py`.
- Event emission: `packages/agent-coordination/lib/agent_bus.py::AgentPublisher`.
