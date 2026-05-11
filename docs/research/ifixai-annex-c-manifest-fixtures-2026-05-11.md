---
title: "iFixAi Annex C — Reproducibility manifest & fixtures"
date: 2026-05-11
annex: C
parent: ifixai-comparison-2026-05-11.md
scope: research-only
license_constraint: "Apache-2.0 — manifest schema is small enough to clean-room re-implement under attribution."
---

> **License attribution.** Code excerpts in this document are quoted from `ifixai-ai/iFixAi` v1.0.0 (Apache License 2.0, Copyright 2026 iMe — see https://github.com/ifixai-ai/iFixAi/blob/main/LICENSE). Quoted under Apache-2.0 §4.b (reproduction with attribution). See [`ifixai-annex-d-provider-imeisplit-2026-05-11.md`](ifixai-annex-d-provider-imeisplit-2026-05-11.md) for license disposition + iMe open-core risk analysis, and [`ifixai-annex-f-compliance-cleanroom-2026-05-11.md`](ifixai-annex-f-compliance-cleanroom-2026-05-11.md) for the full compliance protocol. No COS code derives from iFixAi source; pattern extraction is recommended over direct vendoring per addendum and cluster-D self-critique Finding 9.

# Annex C — Reproducibility manifest & fixtures

## 1. The artifact

Every iFixAi run writes a single JSON file at `runs/<run_id>/manifest.json`. The schema is the `RunManifest` Pydantic model at `ifixai/evaluation/manifest.py:19-61`.

*Source: ifixai/evaluation/manifest.py:19-43 (Apache-2.0)*
```python
class RunManifest(BaseModel):
    run_id: str
    timestamp: str
    mode: RunMode
    model_under_test: ModelDescriptor
    judge_models: list[ModelDescriptor]
    judge_temperature: float = 0.0
    judge_identity: ModelDescriptor | None = None
    normalizer_version: str
    test_versions: dict[str, str]
    rubric_hashes: dict[str, str]
    fixture_digest: str                       # 64-hex sha256
    governance_fixture_digest: str | None
    governance_source: str | None
    seed: int | None
    mode_filter: list[str]
    strict_structured: bool = False
    b12_seed: int = 20260422                  # per-inspection seeds
    b14_seed: int = 20260422
    b28_seed: int = 20260422
    b30_seed: int = 20260422
    sut_temperature: float = 0.0
    sut_seed: int | None
    effective_sut_temperature: float = 0.0
    effective_sut_seed: int | None
    seed_supported_by_provider: bool = True
```

A field-validator (`L49-61`) rejects:
- any `fixture_digest` that isn't a 64-char lowercase sha256 hex,
- the all-zero sentinel `"0" * 64`.

## 2. What goes into the digest, what doesn't

### 2.1 Fixture digest — `ifixai/utils/fixture_digest.py:19-30`

*Source: ifixai/utils/fixture_digest.py:19-30 (Apache-2.0)*
```python
def compute_fixture_digest(fixture_path):
    raw = path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw)
    canonical = _canonicalise(parsed)
    serialised = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()
```

Algorithm:
1. Read fixture as UTF-8.
2. `yaml.safe_load` — discards comments, normalises whitespace.
3. `_canonicalise()` (L11-16) recursively sorts dict keys at every nesting depth; list order is preserved.
4. JSON-serialise with `sort_keys=True, separators=(",", ":"), ensure_ascii=False`.
5. `sha256`.

**Stable across**: YAML comment edits, whitespace edits, dict-key reordering, scalar formatting equivalences captured by `yaml.safe_load`.
**Sensitive to**: list-order changes (lists are semantically ordered in iFixAi fixtures — e.g. step sequences), any value change, scalar type changes (e.g. `1` vs `1.0` are distinct after `yaml.safe_load`).

The algorithm is **pinned** — `docs/reproducibility.md` in the clone explicitly states "any future change is a breaking change to the manifest format and requires a new schema version."

### 2.2 Run ID — `ifixai/evaluation/manifest.py:68-74`

*Source: ifixai/evaluation/manifest.py:68-74 (Apache-2.0)*
```python
def compute_run_id(manifest_fields):
    payload = {k: v for k, v in manifest_fields.items() if k != "timestamp" and k != "run_id"}
    canonical = _canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
```

A 16-char sha256 prefix of the canonicalised payload, **excluding `run_id` itself and `timestamp`**. Two runs with identical inputs produce the same `run_id`. This is what makes the manifest content-addressed.

### 2.3 Verification — `ifixai/evaluation/manifest.py:163-166`

*Source: ifixai/evaluation/manifest.py:163-166 (Apache-2.0)*
```python
def verify_run_id(manifest: RunManifest) -> bool:
    payload = manifest.model_dump(mode="json", exclude={"run_id", "timestamp"})
    expected = compute_run_id(payload)
    return manifest.run_id == expected
```

Plus `verify_fixture_digest()` at `ifixai/utils/fixture_digest.py:33-34`. Tamper detection is a 2-line replay check.

### 2.4 Self-judge ban built into the manifest

`build_manifest()` at `L103-107`:

*Source: ifixai/evaluation/manifest.py:103-107 (Apache-2.0)*
```python
if judge_models and model_under_test.model_id in {j.model_id for j in judge_models}:
    raise ValueError(
        "model_under_test must not appear in judge_models — "
        "self-judging is signaled by an empty judge_models list."
    )
```

This is Annex B's Layer 3. A self-judged run has `judge_models = []`; a cross-judged run has the judge model IDs listed; a manifest where the SUT *also* appears in `judge_models` is rejected at build time.

## 3. Masked non-deterministic fields

Per `docs/reproducibility.md` in the clone, byte-identity across replay assertions **excludes**:
- `manifest.timestamp`
- `scorecard.generated_at`, `scorecard.runtime_seconds`
- Per-inspection `latency_ms`, `started_at`, `completed_at`

These are recorded but not load-bearing for the score. Two replays produce different timestamps and latencies but the same `run_id`.

## 4. What reproducibility does NOT promise

Quoting the clone's reproducibility doc verbatim:

> - **Network-dependent scores are not reproducible against live providers.** LLMs are non-deterministic; two runs against the same provider with the same inputs produce different outputs. To verify bit-identical replay you need a deterministic provider that returns a pre-recorded response table.
> - **Reproducibility is conditional on the judge set.** Changing the judge provider or judge model changes the manifest and therefore the `run_id`, even if the model-under-test's outputs are identical.
> - **Rubric hashes, test versions, and the normaliser version are all pinned.** Any upgrade of any of these produces a new `run_id`; this is intentional — it forces auditors to notice the upgrade.

This is honest disclosure: the manifest provides **input-content addressability**, not output replay. To get bit-identical replay one needs a deterministic provider with a pre-recorded response table. iFixAi ships `--provider mock` and a `MockGovernanceProvider` (`ifixai/providers/mock_governance.py`) for exactly this.

## 5. CI integration

Two hooks are designed in:

1. **Per-inspection seeds** (`b12_seed`, `b14_seed`, `b28_seed`, `b30_seed` — `manifest.py:39-42`). The corpora-driven inspections (prompt injection, covert side-task, RAG poisoning, malicious deployer) sample from their YAML corpora using these seeds, so the same seed reproduces the same sub-sample.
2. **`ifixai validate`** (CLI in `ifixai/cli/validate.py`) checks fixtures against the schema before a run — designed to be the pre-commit / CI gate.

The clone's `.github/workflows/ci.yml` runs ruff, bandit, and pytest plus the validate command.

## 6. Comparison with ADR-247 manifest doctrine

COS already has a manifest doctrine: ADR-247 (`docs/adrs/ADR-247-manifest-driven-postmortem-regression-audits.md`) plus `manifests/postmortem-regression-audit.yaml`. The relevant points:

| Property | ADR-247 manifest | iFixAi `RunManifest` |
|---|---|---|
| Purpose | Postmortem regression audit — "did the fix stay fixed?" Checks `required_paths`, `required_tokens`, `forbidden_pattern` against the repo state. | Reproducibility of a single eval run — "did the SUT see exactly these inputs?" |
| Layer | Repo-level / cross-session. One manifest at `manifests/postmortem-regression-audit.yaml`. | Per-run. One manifest per eval execution at `runs/<run_id>/manifest.json`. |
| Content-addressed? | No — referenced by stable filename. | Yes — `run_id` is sha256(payload)[:16], `fixture_digest` is sha256(canonical YAML). |
| What's pinned | ADR linkage, severity, required tokens / forbidden patterns. | Fixture digest, rubric hashes, test versions, normalizer version, seeds, SUT and judge model IDs, temperatures. |
| Tamper-evident at replay? | Indirect — the audit script re-scans. | Directly: `verify_run_id()` + `verify_fixture_digest()` are 2-line checks. |
| Per-judge attribution | n/a | Yes — `judge_models: list[ModelDescriptor]`; empty list = self-judge (declared, not inferred). |
| Audit philosophy match | "Detect-first, repair-second" | "Treat absolute scores as informative, not authoritative; CI drift signal." |

### Where iFixAi's manifest **adds** value to COS

COS has manifest-driven **audits** of the repo state (ADR-247) and manifest-driven **adoption** of external tools (`manifests/external-tools-adoption.yaml`). It does **not** have manifest-driven **eval-run reproducibility**. The two doctrines are orthogonal — ADR-247 is "did the system regress?", iFixAi's manifest is "given an eval run, can we re-derive its inputs from its outputs?"

Concrete extraction: a clean-room manifest format for `red-team`, `deepeval-integration`, `promptfoo-integration`, `ragas-integration` runs. The 5-line `compute_fixture_digest` and the 2-line `verify_run_id` are the irreducible primitives. Pinning rubric/test versions is the harder cultural change — it means each eval skill needs a versioned rubric file rather than ad-hoc inline scoring.

### Where COS's ADR-247 manifest **adds** value to iFixAi-shape thinking

iFixAi assumes the auditor will read the manifest manually. ADR-247 wires manifest checks into hooks (`hooks/_lib/bypass-resolver.sh`, `hooks/destructive-git-blocker.sh`, etc.) so policy violations *block* at the source. If COS adopts an eval-run manifest, it should integrate with the same hook discipline — e.g. a pre-commit check that no eval-run manifest in the tree has SUT==judge.

## 7. Fixture format

Schema source of truth: `ifixai/fixtures/schema.json` in the clone.

Minimum-valid template: `ifixai/fixtures/smoke_tiny.yaml` (3 KB).
Default fixture (used when `--fixture` is omitted): `ifixai/fixtures/default/fixture.yaml`, which **includes an inline `governance:` block** (README L320-326) so any provider produces a full 32-inspection scorecard out of the box (with a `warnings[]` entry naming the synthesized vs. measured fields).

Examples ship under `ifixai/fixtures/examples/`:
- `acme_legal.yaml` (illustrative legal)
- `customer_support.yaml`
- `healthcare.yaml`
- `helio_finance.yaml`
- `software_engineering.yaml`

Each is a real fixture exercising all the schema fields.

**Governance wiring** has three options (README L318-361, decreasing friction):
1. `--governance <path>` flag → CLI wraps the resolved provider with `GovernanceMixin` (`ifixai/providers/governance_mixin.py`). No subclassing required.
2. Inline `governance:` block on the diagnostic fixture → loader hydrates a `GovernanceFixture` (`ifixai/providers/governance_fixture.py`) and the CLI wraps the provider.
3. `governance: { synthesize: true }` → iFixAi derives a structural policy bundle from `tools`, `permissions`, and `roles`; the scorecard records the bundle as synthesized rather than measured.

The governance fixture has its own digest (`governance_fixture_digest`) recorded in the manifest, separate from the diagnostic fixture digest — so an auditor can tell whether governance was inlined, externally supplied, or synthesized.

## 8. Concrete COS recommendations

1. **Adopt the digest algorithm verbatim** for any new eval-run manifest in COS. It is 12 lines of pure-Python under Apache-2.0; clean-room re-implement under attribution and pin the algorithm to a versioned constant (matching iFixAi's "any change is a breaking change" stance).
2. **Adopt the manifest assertion `SUT not in judge_models`** as a separate rule from the cross-judge contract; the assertion alone catches a class of regressions that runtime checks may miss (e.g. an SDK upgrade silently renaming a model ID).
3. **Adopt the `warnings[]` discipline** for any COS evaluator that excludes scores when evidence is insufficient. Today, `deepeval-integration` / `ragas-integration` etc. silently skip metrics they can't compute. The iFixAi pattern is to scorecard the exclusion explicitly so the operator sees coverage, not just score.
4. **Do not adopt the per-inspection seeds verbatim** (`b12_seed=20260422`, etc.). Those numbers are policy defaults tuned to upstream's corpora and should be replaced with COS-owned seeds tied to the COS-owned corpora.
5. **Treat fixture digest stability as a contract** — list-order is semantic, comments are not. This is the right call (matches how COS already thinks about settings.json / hooks ordering).

## 9. References

- Manifest model: `ifixai/evaluation/manifest.py:19-178`.
- Fixture digest: `ifixai/utils/fixture_digest.py:1-34`.
- Reproducibility doc: `docs/reproducibility.md` in the clone (L1-62).
- Fixture schema: `ifixai/fixtures/schema.json`, `ifixai/fixtures/smoke_tiny.yaml`, `ifixai/fixtures/default/fixture.yaml`, `ifixai/fixtures/examples/*.yaml`.
- Governance fixture: `ifixai/providers/governance_fixture.py`, `ifixai/providers/governance_mixin.py`.
- COS comparison: `docs/adrs/ADR-247-manifest-driven-postmortem-regression-audits.md`, `manifests/postmortem-regression-audit.yaml`.
