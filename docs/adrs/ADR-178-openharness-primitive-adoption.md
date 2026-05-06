# ADR-178 — OpenHarness Primitive Adoption (HttpHookDefinition, PromptHookDefinition, ProviderProfile)

**Status**: Accepted
**Date**: 2026-05-05
**Deciders**: Matias Nahuel Améndola
**Cross-refs**:
  - ADR-171 (removed-integration lesson — verify upstream source before adopting)
  - ADR-049 (multi-provider agent loop, LLM dispatch)
  - ADR-062 (provider cascade: qwen → openrouter → gemini → ollama → claude)
  - `docs/reports/openharness-opus-deep-audit-2026-05-05.md` (Opus symmetric audit)

---

## Context

The Opus deep audit of HKUDS/OpenHarness (2026-05-05, commit
`7873f0d109174a57b3b1af7aa5397a6b3b0bd551`) identified three primitives with
HIGH-confidence adoption value, while rejecting full substrate migration:

1. **Hook type diversity** — OpenHarness supports 4 hook types
   (Command/Http/Prompt/Agent). COS supports 1 (shell command only). This is a
   real structural gap: operators cannot wire an HTTP callback or an inline prompt
   as a hook without writing a shell wrapper.

2. **ProviderProfile credential-slot pattern** — OpenHarness's `ProviderProfile`
   (settings.py, lines 109–131, same commit) separates named provider profiles
   from per-machine credential resolution. COS uses ad-hoc `os.environ.get(...)`
   calls scattered across `lib/providers/*.py` with no unified named-profile layer.

The removed-integration lesson (ADR-171) requires verifying upstream before adopting. All
field definitions in this ADR were read from the upstream source via
`gh api repos/HKUDS/OpenHarness/contents/...` at the exact commit cited.

---

## Decision

Cherry-pick 3 primitives from OpenHarness. This is **not a substrate migration**.
The 227 unique shell hooks, settings driver, skill router, and dispatch layer are
untouched.

### Primitive 1 — HttpHookDefinition

**Upstream source**: `src/openharness/hooks/schemas.py` at commit
`7873f0d109174a57b3b1af7aa5397a6b3b0bd551`

Upstream fields (verbatim):
```python
class HttpHookDefinition(BaseModel):
    type: Literal["http"] = "http"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=600)
    matcher: str | None = None
    block_on_failure: bool = False
```

COS adaptation (`lib/hook_types.py`):
- `timeout_ms` replaces `timeout_seconds` as the primary field (5000ms default
  vs upstream's 30s; COS favours faster webhook timeouts). `timeout_seconds` is
  a derived property for interface compatibility.
- Added: `method` (POST default), `body_template` (str.Template), `expected_status`
  (set defaulting to {200,201,202,204}).
- Inherits from `HookDefinition(ABC)` rather than Pydantic `BaseModel` to avoid
  a new dependency.

### Primitive 2 — PromptHookDefinition

**Upstream source**: `src/openharness/hooks/schemas.py` at commit
`7873f0d109174a57b3b1af7aa5397a6b3b0bd551`

Upstream fields (verbatim):
```python
class PromptHookDefinition(BaseModel):
    type: Literal["prompt"] = "prompt"
    prompt: str
    model: str | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=600)
    matcher: str | None = None
    block_on_failure: bool = True
```

COS adaptation (`lib/hook_types.py`):
- `prompt_template` replaces `prompt` as the primary field (supports
  `str.Template` substitution of `$event_json` at dispatch time).
- `model_hint` replaces `model` (accepts haiku/sonnet/opus tier names matching
  COS MODEL_MAP convention; maps to provider-native names at dispatch).
- Added: `inline_agent_subagent_type`, `max_tokens`.
- `prompt` preserved as a property alias for upstream interface compat.
- `block_on_failure=True` default preserved (matches upstream conservative stance).

### Primitive 3 — ProviderProfile credential-slot pattern

**Upstream source**: `src/openharness/config/settings.py` at commit
`7873f0d109174a57b3b1af7aa5397a6b3b0bd551`

Upstream fields (verbatim):
```python
class ProviderProfile(BaseModel):
    label: str
    provider: str
    api_format: str
    auth_source: str
    default_model: str
    base_url: str | None = None
    last_model: str | None = None
    credential_slot: str | None = None
    allowed_models: list[str] = Field(default_factory=list)
    context_window_tokens: int | None = None
    auto_compact_threshold_tokens: int | None = None
```

COS adaptation (`lib/provider_profile.py`):
- `auth_slots: dict[str, str]` replaces the single `credential_slot`. COS needs
  multiple slots per provider (e.g. api_key + org_id for OpenAI).
- Slot spec format: `"ENV:<VAR_NAME>"` for env-var indirection (explicit, auditable,
  avoids shell injection). Literal values accepted but discouraged for secrets.
- `model_aliases: dict[str, str]` replaces `default_model` + `allowed_models`
  with the opus/sonnet/haiku tier mapping already used throughout COS.
- `resolve_auth()` method is self-contained on the dataclass (upstream delegates
  to a separate `ResolvedAuth` flow in settings.py).
- Loaded from `manifests/provider-profiles.yaml`; absent file = no-op (backward
  compatible with existing `lib/providers/REGISTRY`).

---

## Consequences

### Positive
- Operators can declare an HTTP-callback hook in `cognitive-os.yaml` without
  writing a shell script (once the dispatcher is wired — see §Future Work).
- Operators can declare an inline prompt-validation hook (same gating).
- Provider credential configuration is centralised in one YAML file; switching
  API keys per machine no longer requires scattered env-var changes in multiple
  provider modules.
- `lib/providers/__init__.py` gains `get_provider_profiles()` shim; existing
  `REGISTRY`, `is_configured()`, `get_client()`, etc. are unaffected.

### Negative / Risks
- **Execution not wired**: `HttpHookDefinition` and `PromptHookDefinition` are
  declared types only. The hook dispatcher (settings driver + `_cc_hook_group`)
  does not yet dispatch them natively. Operators must use the shell shim examples
  (`hooks/example-http-callback.sh.disabled`, `hooks/example-prompt-hook.sh.disabled`)
  until a follow-up ADR wires the dispatcher.
- **ProviderProfile schema may need extension** if upstream OpenHarness adds fields
  COS missed (e.g. `last_model`, `auto_compact_threshold_tokens`). The `from_dict`
  factory ignores unknown keys, making forward extension backward-compatible.
- **Cherry-pick risk**: the 3 primitives may have hidden dependencies on each
  other's full subsystem in OpenHarness (e.g. `PromptHookDefinition` there depends
  on `HookExecutor` which calls a fully managed loop). COS's ports are standalone
  dataclasses; no transitive OH dependency is imported.

---

## Implementation

| Artifact | Status |
|---|---|
| `lib/hook_types.py` | Created — `HookDefinition`, `ShellHookDefinition`, `HttpHookDefinition`, `PromptHookDefinition`, `hook_from_dict` |
| `lib/provider_profile.py` | Created — `ProviderProfile`, `load_profiles`, `get_profile` |
| `manifests/provider-profiles.yaml` | Created — 5 seeded profiles (claude_sdk, qwen, openrouter, openai, gemini) |
| `lib/providers/__init__.py` | Extended — `get_provider_profiles()` shim added; no existing symbols changed |
| `hooks/example-http-callback.sh.disabled` | Created — shell shim + future YAML block docs |
| `hooks/example-prompt-hook.sh.disabled` | Created — shell shim + future YAML block docs |
| `tests/unit/test_hook_types.py` | Created — 26 tests, all passing |
| `tests/unit/test_provider_profile.py` | Created — 17 tests, all passing |

---

## Future Work

- **Wire HttpHookDefinition into hook dispatcher**: `scripts/_lib/settings-driver-claude-code.sh`
  and/or a new `lib/hook_dispatcher.py` should handle `type: http` entries in
  `cognitive-os.yaml > harness.hooks.<event>` natively (currently falls through
  to unknown-type skip).
- **Wire PromptHookDefinition into hook dispatcher**: similar path; requires
  deciding whether to spawn a subagent or call a provider directly.
- **AgentHookDefinition**: intentionally deferred (not in scope for ADR-178);
  would require full subagent lifecycle management.

---

## Examples

### HTTP callback hook (cognitive-os.yaml — future native syntax)

```yaml
harness:
  hooks:
    Stop:
      - type: http
        url: "${WEBHOOK_URL}"
        method: POST
        headers:
          Content-Type: application/json
          Authorization: "Bearer ${WEBHOOK_TOKEN}"
        timeout_ms: 5000
        expected_status: [200, 201, 202, 204]
        block_on_failure: false
```

Until the dispatcher supports `type: http` natively, use the shell shim:

```yaml
harness:
  hooks:
    Stop:
      - command: hooks/example-http-callback.sh
```

### Prompt validation hook (cognitive-os.yaml — future native syntax)

```yaml
harness:
  hooks:
    PreToolUse:
      - type: prompt
        prompt_template: |
          Inspect this event and respond ALLOW or BLOCK: $event_json
        model_hint: haiku
        max_tokens: 10
        block_on_failure: true
```

### ProviderProfile usage (Python)

```python
from lib.provider_profile import get_profile

p = get_profile("openai")
auth = p.resolve_auth()   # {"api_key": "sk-...", "org_id": "org-..."}
model = p.get_model("sonnet")  # "gpt-5.4"
```

---

## Trust Report

**Confidence**: 0.87

**Honest uncertainties**:
1. `HttpHookDefinition` execution path is not wired into the hook dispatcher —
   that is a follow-up; ADR-178 declares the type; activation is gated.
2. `ProviderProfile` schema may need extension if upstream OpenHarness adds fields
   COS missed (e.g. `last_model`, `auto_compact_threshold_tokens`). The from_dict
   factory ignores unknown keys to stay forward-compatible.
3. Cherry-pick risk: the 3 primitives may have hidden dependencies on each other's
   full subsystem in OpenHarness. COS ports are standalone dataclasses with no
   transitive OpenHarness import — verified by import analysis.
4. OpenHarness is 35 days old (created 2026-04-01) with no observable canonical
   test-suite run (CI dominated by Autopilot scans). Field definitions were read
   directly from source at commit `7873f0d`; semantic behaviour of their executor
   was not verified end-to-end.

## Status

Accepted.


## Alternatives rejected

- **Leave the decision implicit** — rejected because ADR slots must remain self-describing and audit-safe after multi-agent collision recovery.


## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

