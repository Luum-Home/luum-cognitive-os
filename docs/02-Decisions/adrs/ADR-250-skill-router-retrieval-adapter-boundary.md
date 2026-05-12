---

adr: 250
title: Skill Router Retrieval Adapter Boundary
status: accepted
implementation_status: implemented
classification_basis: 'boundary manifest, audit, benchmark fixtures, and tests implement the retrieval adapter boundary scope'
relationship_chain_exempt: true
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-174, ADR-201, ADR-216, ADR-236, ADR-248, ADR-249]
implementation_files:
  - manifests/skill-router-retrieval.yaml
  - scripts/skill-router-retrieval-audit.py
  - scripts/skill-router-benchmark.py
  - tests/unit/test_skill_router_retrieval_audit.py
  - tests/unit/test_skill_router_benchmark.py
tier: maintainer
tags: [skill-router, retrieval, adapters, toolsearch, anti-reinvention, benchmark]
---

<!-- ADR_RELATION_CHAIN_EXEMPT: part of the 2026-05-08 implementation-ledger ADR burst; relationship depth is tracked by control-plane audits rather than new transitive ADR scope. -->

# ADR-250: Skill Router Retrieval Adapter Boundary

## Status

Accepted — Slice A implemented.

## Context

The operator asked whether COS is reinventing the wheel with its custom skill
router. This concern is connected to the ADR-239+ primitive-coherence incidents:
custom primitives can look locally correct while duplicating community tooling,
missing mature failure modes, or hardcoding policy into ranking code.

A repo search on 2026-05-08 found related but incomplete prior art:

- ADR-174 makes skills self-describing via `routing_patterns:` frontmatter.
- ADR-216/236 adopt ToolSearch/deferred tool-loading patterns.
- ADR-201 intends to consume router telemetry.
- ADR-249 now requires behavioral proof for critical primitives.

No existing ADR defined the precise boundary for skill-router retrieval:

> COS owns policy and governance. Retrieval/ranking may be custom only behind an
> adapter boundary and should adopt community patterns when footprint allows.

External prior art confirms this is not a novel problem:

- OpenAI Agents SDK supports deferred tool loading with Tool Search so large tool
  surfaces can be searched and loaded on demand instead of sent eagerly.
- LlamaIndex documents router/query-engine/retriever patterns, including
  retrieval-augmented routing when the set of choices is large.
- Haystack and LangChain both expose retriever abstractions for keyword, vector,
  hybrid, and remote retrieval.

## Decision

Split the skill router into an explicit conceptual pipeline:

```text
Skill catalog
  -> Candidate retriever adapter
  -> COS policy / intent guard
  -> Telemetry and feedback ledger
  -> Suggest / block / no-op
```

Hard rules:

1. `lib/skill_router.py` may keep the zero-dependency frontmatter-regex adapter
   as the default hot-path implementation.
2. Optional community retrieval stacks must not be imported directly by
   `lib/skill_router.py`; they must live behind declared adapters.
3. COS policy guards remain first-party: dangerous-skill rejection, negative
   context, profile/harness scope, bypass rules, and telemetry are not delegated
   to community retrievers.
4. Any new retrieval adapter requires:
   - manifest declaration;
   - license/footprint classification;
   - benchmark fixtures;
   - ADR-249 style behavioral proof.
5. Router confidence changes require measurement, not intuition.

Introduce:

```text
manifests/skill-router-retrieval.yaml
scripts/skill-router-retrieval-audit.py
scripts/skill-router-benchmark.py
```

## Adapter posture

| Adapter | Default | Status | Rationale |
|---|---:|---|---|
| `regex_frontmatter` | yes | active | Zero dependency, hot-path safe, already implemented by ADR-174 |
| `bm25_local` | no | candidate | Lightweight local retrieval candidate before adding heavy stacks |
| `provider_toolsearch` | no | candidate | Aligns with ADR-236 and provider-native deferred loading when available |
| `llamaindex_router` | no | lab only | Mature routing abstractions but too heavy for default COS install |
| `haystack_retriever` | no | lab only | Mature retrieval stack but not appropriate as default hook-path dependency |
| `langchain_retriever` | no | lab only | Ecosystem-wide retrievers but dependency footprint is too large for core |

## Benchmark doctrine

Router changes must be evaluated against historical dogfood prompts before
confidence thresholds are changed. Slice A includes fixtures for:

- false-positive mentions of `/auto-rollback`, `/deep-research`, `/auto-refine`,
  and `/self-improve`;
- positive routing for repo forensics, security audit, and code review;
- known gaps such as “crear una nueva skill” currently routing to `/sdd-new`
  instead of `/add-skill`.

Known gaps may be reported as warnings, but they must be explicit; they must not
be silently hidden by a green coverage number.

## Consequences

Positive:

- Prevents `skill_router.py` from becoming an unbounded custom retrieval stack.
- Makes community adoption possible without importing large dependencies into
  hook-fast paths.
- Creates a measurable path from regex routing to BM25/ToolSearch/provider-native
  retrieval.
- Separates governance policy from candidate retrieval.

Negative:

- Adds another manifest and audit surface.
- Static import audits cannot prove semantic quality; benchmark fixtures and
  telemetry are still required.
- Community adapters remain candidates until footprint and benchmark evidence
  justify adoption.

## Operational Guide

### What changes for the operator

Before this ADR, `lib/skill_router.py` mixed retrieval logic, ranking, and
COS-specific policy (dangerous-skill rejection, negative context, profile/harness
scope, bypass rules) in one file, with no formal boundary between them. Community
retrieval stacks (BM25, vector search, provider-native ToolSearch) could only be
adopted by importing them directly — which would bloat hook-fast paths.

After this ADR:

- `lib/skill_router.py` may keep the zero-dependency `regex_frontmatter` adapter
  as the default hot-path implementation. No change to existing behavior.
- Any new retrieval adapter (BM25, provider ToolSearch, LlamaIndex, etc.) must
  be declared in `manifests/skill-router-retrieval.yaml` with license, footprint
  classification, and benchmark fixtures — and must NOT be imported directly by
  `lib/skill_router.py`.
- COS policy guards (dangerous-skill rejection, negative context, profile/harness
  scope, bypass rules, telemetry) remain first-party and are not delegated to any
  community retriever.
- Known routing gaps (e.g., "crear una nueva skill" routed to `/sdd-new` instead
  of `/add-skill`) must be declared as explicit warnings, not hidden.

### What this answers (and what it doesn't)

**Answers:**
- "Can I adopt BM25 or provider ToolSearch for skill routing?" — Yes, but only
  as a declared adapter behind the boundary. Declare it in the manifest, provide
  benchmark fixtures, verify license/footprint. The `regex_frontmatter` adapter
  remains default until evidence justifies switching.
- "How do I know if the router boundary is respected?" — Run
  `python3 scripts/skill-router-retrieval-audit.py --json`. It checks that
  optional community stacks are not imported directly by core router files.
- "Are known routing gaps acceptable?" — Yes, if declared as warnings in the
  benchmark. Hidden gaps (green coverage with silent failures) are not.

**Does not answer:**
- Whether the `regex_frontmatter` adapter produces semantically correct routing
  for all prompts. Benchmark fixtures (`scripts/skill-router-benchmark.py`) must
  be extended to cover new routing failure modes.
- Whether adopting a candidate adapter will improve quality. Telemetry and
  benchmark comparison are required before a candidate becomes default.

### Daily operational pattern

1. Verify the retrieval boundary and benchmark on any change to `lib/skill_router.py`:
   ```bash
   python3 scripts/skill-router-retrieval-audit.py --json
   python3 scripts/skill-router-benchmark.py --json
   ```
2. To propose a new retrieval adapter:
   - Add an entry to `manifests/skill-router-retrieval.yaml` with
     `status: candidate` and the required fields.
   - Add benchmark fixtures that prove the adapter handles historical failure modes.
   - Keep `lib/skill_router.py` imports unchanged until the adapter graduates
     from candidate to active.
3. Full verification:
   ```bash
   python3 -m pytest tests/unit/test_skill_router_retrieval_audit.py tests/unit/test_skill_router_benchmark.py -q
   scripts/cos-control-plane-audit --lane hook-fast --json
   ```

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Replace the router with LangChain/LlamaIndex/Haystack immediately | Violates footprint discipline for hook-fast paths and delegates COS-specific policy to generic retrieval frameworks. |
| Keep adding regexes directly to `lib/skill_router.py` | Continues the reinvention risk and makes ranking/policy inseparable. |
| Use provider-native ToolSearch only | Provider-native support is not universally available across harnesses and does not cover local-first/offline COS. |
| Let the LLM choose skills from the full catalog | Reintroduces token bloat and makes routing non-deterministic, harder to test, and harder to audit. |

## Verification

```bash
python3 scripts/skill-router-retrieval-audit.py --json
python3 scripts/skill-router-benchmark.py --json
python3 -m pytest tests/unit/test_skill_router_retrieval_audit.py tests/unit/test_skill_router_benchmark.py -q
scripts/cos-control-plane-audit --lane hook-fast --json
```

Expected current result: the retrieval-boundary audit passes, the benchmark has
zero required failures, and hook-fast includes the boundary audit without
findings.
