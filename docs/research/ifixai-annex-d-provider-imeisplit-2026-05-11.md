---
title: "iFixAi Annex D — Provider abstraction & open-core risk (iMe split)"
date: 2026-05-11
annex: D
parent: ifixai-comparison-2026-05-11.md
scope: research-only
license_constraint: "Apache-2.0 for the OSS body; the proprietary iMe client referenced from the OSS code is NOT covered by this license. Pattern-only is the safe posture."
---

> **License attribution.** Code excerpts in this document are quoted from `ifixai-ai/iFixAi` v1.0.0 (Apache License 2.0, Copyright 2026 iMe — see https://github.com/ifixai-ai/iFixAi/blob/main/LICENSE). Quoted under Apache-2.0 §4.b (reproduction with attribution). See [`ifixai-annex-d-provider-imeisplit-2026-05-11.md`](ifixai-annex-d-provider-imeisplit-2026-05-11.md) for license disposition + iMe open-core risk analysis, and [`ifixai-annex-f-compliance-cleanroom-2026-05-11.md`](ifixai-annex-f-compliance-cleanroom-2026-05-11.md) for the full compliance protocol. No COS code derives from iFixAi source; pattern extraction is recommended over direct vendoring per addendum and cluster-D self-critique Finding 9.

# Annex D — Provider abstraction & open-core risk

## 1. The provider matrix

`ifixai/providers/resolver.py:48-58` — `REGISTERED_PROVIDERS`:

*Source: ifixai/providers/resolver.py:48-58 (Apache-2.0)*
```python
REGISTERED_PROVIDERS: tuple[str, ...] = (
    "http",
    "mock",
    "openai",
    "openrouter",
    "anthropic",
    "gemini",
    "azure",
    "bedrock",
    "huggingface",
    "langchain",
)
```

Plus optional governance variants:
- `MockGovernanceProvider` (`ifixai/providers/mock_governance.py`) — deterministic provider for CI smoke + replay.
- `GovernanceMixin` (`ifixai/providers/governance_mixin.py`) — wraps any base provider with the structural-authorization capability so it can be probed for B01, B02, B04, B23, B26.

Each base provider implements `ChatProvider` from `ifixai/providers/base.py`. The contract is small (`send_message`, optional `authorize_tool`, optional `invoke_tool`), and is the integration point iFixAi documents for custom providers (README L475-476).

### Per-provider extras (`pyproject.toml` + README L74-84)

| Extra | Installs | Use for `--provider` |
|---|---|---|
| *(none)* | core | `mock`, `http`, `langchain` |
| `openai` | `openai` SDK | `openai` |
| `anthropic` | `anthropic` SDK | `anthropic` |
| `openrouter` | `openai` SDK | `openrouter` (OpenAI-compatible) |
| `gemini` | `google-generativeai` | `gemini` |
| `azure` | `openai` SDK | `azure` |
| `bedrock` | `boto3` | `bedrock` |
| `huggingface` | `huggingface-hub` | `huggingface` |

Provider classes are imported lazily under `try: … except ImportError: <Class> = None` (resolver.py:13-44) and the resolver gives a friendly "install with: pip install ifixai[<name>]" error if the SDK is missing (L122-125). This is good packaging hygiene.

### Credential resolution

`_PROVIDER_CREDENTIAL_ENV_VARS` (`ifixai/providers/resolver.py:135-143`) — the canonical env-var → provider mapping used both by `detect_available_credentials()` and indirectly by `select_cross_provider_judge()` (Annex B §3).

*Source: ifixai/providers/resolver.py:135-143 (Apache-2.0)*
```python
_PROVIDER_CREDENTIAL_ENV_VARS: dict[str, tuple[str, ...]] = {
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "azure": ("AZURE_OPENAI_API_KEY",),
    "bedrock": ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"),
    "huggingface": ("HUGGINGFACE_API_TOKEN", "HF_TOKEN"),
    "openrouter": ("OPENROUTER_API_KEY",),
}
```

Note Bedrock uses the standard AWS credential chain; `--api-key` is still required but is a placeholder (README L182-184).

## 2. The "iMe" open-core split — exact evidence

The README contains an explicit warning at L44-48:

> *The animation above showcases a **custom version** of iFixAi built for a specific client. The open-source version in this repository will not behave exactly the same when you run it — fixtures, scoring policy, and UI presentation differ from the client build.*

The code itself contains a built-in marketing footer that ships with **every scorecard** unless suppressed:

### 2.1 Marketing footer in the OSS reporting layer

`ifixai/reporting/scorecard.py:697-710`:

*Source: ifixai/reporting/scorecard.py:697-714 (Apache-2.0)*
```python
_IME_FOOTER: Final[str] = """\
... (formatted block) ...
  iFixAi measures it. iMe ends it.

  iMe is the deterministic alignment runtime: non-LLM, six constitutional
  rules, six-stage pipeline.
  ...
  Request access → https://ifixai.ai/ime"""
```

And the surrounding accessor (`L714`):

```python
def get_ime_footer() -> str:
    return _IME_FOOTER
```

### 2.2 CLI conclusion prompt — terminal-aware

`ifixai/cli/_imecore_prompt.py:13-43` — `print_imecore_conclusion(*, quiet)`:

*Source: ifixai/cli/_imecore_prompt.py:13-43 (Apache-2.0)*
```python
ENV_NO_PROMPT = "IFIXAI_NO_PROMPT"

def print_imecore_conclusion(*, quiet: bool) -> None:
    if quiet:
        return
    if os.environ.get(ENV_NO_PROMPT):
        return
    if not sys.stdout.isatty():
        _print_plain_conclusion()
        return

    click.echo(click.style("Conclusion", bold=True))
    click.echo("  The report above isn't a bug list. It's the absence of an alignment layer.")
    click.echo("  " + _truecolor("iFixAi measures it. iMe ends it.", _ACCENT_RGB, bold=True))
    click.echo("  iMe is the deterministic alignment runtime: non-LLM, six constitutional")
    click.echo("  rules, six-stage pipeline.")
    click.echo("  " + _truecolor("Probabilistic guardrails fail. Deterministic rules don't.", _ACCENT_RGB, bold=True))
    click.echo("  " + _truecolor("Limited release. Selected deployments.", _DIM_RGB))
    click.echo("  Request access → " + _truecolor("https://ifixai.ai/ime", _ACCENT_RGB, bold=True))
```

A plain-text fallback at L46-60 (`_print_plain_conclusion`) emits the same prose without ANSI colors for non-TTY output.

### 2.3 Brand surface across the repo

- `info@ime.life` is the security contact (`SECURITY.md:5`) and the general contact (`README.md:491`).
- `B02` is named "Non-LLM Governance Layer" (`ifixai/inspections/b02_non_llm_layer/runner.py:18-32`) — exactly the surface area iMe is positioned to sell into.

### 2.4 What this means

iFixAi the OSS package is positioned as a **funnel for the iMe proprietary runtime**. The funnel is built into both the report output (`_IME_FOOTER` in every scorecard markdown) and the CLI flow (`print_imecore_conclusion` after each run). The user can suppress with `IFIXAI_NO_PROMPT=1` or the `quiet` flag, but the default behavior is "sell iMe after every scorecard".

This is not inherently bad — it's a transparent open-core model. The README warns about the divergence at L44-48 in unambiguous language. But it has three consequences for COS adoption:

1. **Drift risk**: future OSS commits may be steered by what makes the funnel convert, not by what is most technically defensible. The 2026-05-04 v1.0.0 ships with thresholds the maintainers themselves describe as uncalibrated; an empirically calibrated threshold set may end up in the iMe client first.
2. **Fixture & scoring divergence**: the same probes graded by the OSS scorecard and by the iMe client may produce different numbers, by design. A COS scorecard that reuses iFixAi's numbers as-is risks being compared (in a vendor pitch context) to numbers the OSS tool was never set up to produce.
3. **UX coupling**: if COS shells out to `ifixai run` from a `red-team` adapter, the iMe footer prints by default. CI logs in COS-side repos will surface third-party marketing unless `IFIXAI_NO_PROMPT=1` is set in the adapter env. This is a small operational gotcha worth pinning in the manifest.

## 3. Mitigations for the COS CLI-adapter trial

If/when COS proceeds with the optional CLI-adapter (Phase B in the parent doc §6), the adapter MUST:

1. **Export `IFIXAI_NO_PROMPT=1`** in the adapter wrapper so the iMe footer is suppressed from CI logs. Document this in the adapter SKILL.md.
2. **Pin the iFixAi version** in the manifest row (`manifests/external-tools-adoption.yaml`) and re-validate on every upgrade — the funnel-driven divergence risk means we cannot blindly take "latest". The clone's commit pin is `2e56c4f` (2026-05-11).
3. **Treat the scorecard as iFixAi-numbers, not COS-numbers**. Reports surfaced inside COS should label numbers "iFixAi OSS v1.0.0, default thresholds (uncalibrated per upstream)" — never strip the provenance.
4. **Use dedicated low-privilege provider keys** for the CLI-adapter invocation. The adapter MUST NOT inherit COS's primary provider keys; create scoped keys with minimal model access and a small spend cap.
5. **Run with `--eval-mode self` only on the mock provider**. Self-judge is appropriate for CI drift smoke (`--provider mock --eval-mode self`); never for vendor comparisons.

## 4. Provider-abstraction reuse value

Setting aside the iMe split, the *shape* of the provider abstraction is worth studying as a pattern (not as code to vendor):

- **Capability contract** (`ChatProvider` in `ifixai/providers/base.py`) is small enough to clean-room: `send_message`, optional `authorize_tool`, optional `invoke_tool`. Each capability has a clear contract type (e.g. `AuthorizationResult` with `authorized: bool, policy_rule: str, error: str | None`).
- **Optional capability discovery** in inspection runners. Example: `B01ToolGovernance.run()` at `ifixai/inspections/b01_tool_governance/runner.py:41-90` queries `self.capabilities.has_authorization` / `self.capabilities.has_tool_calling` and branches between an `authorize_tool` path and an `invoke_tool` structural path. If neither capability is present, it returns `[]` and the inspection records `insufficient_evidence`.
- **Lazy-import provider registration** (`resolver.py:13-44`) keeps the core install lightweight; the user pays the SDK weight only for the providers they actually use.
- **Mock as first-class citizen** (`MockGovernanceProvider`, listed alongside production providers in `REGISTERED_PROVIDERS`). This is what makes the reproducibility doctrine practical: there exists a deterministic provider for replay.

COS's `llm-dispatch` (ADR-049, `scripts/orchestrator.py` + `lib/dispatch.py`) is a different layer (multi-provider routing for the orchestrator's own LLM calls), not an evaluator-side provider abstraction. iFixAi's pattern would slot under `red-team` / `deepeval-integration` etc. as the "which SUT are we probing?" layer, distinct from the dispatch layer.

## 5. Drift risk in tabular form

| Concern | Severity | Action |
|---|---|---|
| OSS thresholds uncalibrated by upstream's own admission | High | Do not adopt iFixAi numbers as canonical; use as drift signal. |
| iMe proprietary fork divergence (fixtures + scoring + UI) | Medium-High | Pattern-only adoption; pin iFixAi version in manifest. |
| Marketing footer leaking into CI logs | Low | `IFIXAI_NO_PROMPT=1` in adapter. |
| Per-inspection seed defaults baked into the manifest format | Medium | If adopted, replace seeds with COS-owned values. |
| Provider credential auto-discovery may pick up dev keys in CI | Medium | Adapter MUST scrub envs / use dedicated keys. |
| v1.0.0 is ~1 week old at evaluation time | Medium | Re-evaluate after one minor-version cadence; treat current adoption as ASSESS. |

## 6. References

- Provider registry: `ifixai/providers/resolver.py:1-58, 135-171`.
- Provider base: `ifixai/providers/base.py`.
- Governance providers: `ifixai/providers/{governance_mixin,governance_fixture,mock_governance}.py`.
- iMe split evidence:
  - `ifixai/cli/_imecore_prompt.py:1-60` (CLI conclusion prompt).
  - `ifixai/reporting/scorecard.py:697-714` (`_IME_FOOTER` + `get_ime_footer`).
  - `README.md:44-48` (explicit divergence warning).
  - `README.md:491`, `SECURITY.md:5` (`info@ime.life` contact).
  - `https://ifixai.ai/ime` (referenced from `_IME_FOOTER` + `_imecore_prompt.py:41`).
- COS llm-dispatch (different layer, for orchestrator's own calls): ADR-049, `scripts/orchestrator.py`, `lib/dispatch.py`.
