---
report_type: external-tools-radar-full-reassessment
scope: all-third-party-tools-found-in-git-docs-manifests-deps
source_index: docs/06-Daily/reports/external-tools-radar-INDEX.md
generated_at: 2026-05-08
status: documentation-before-implementation
source_artifacts:
  - docs/06-Daily/reports/external-tools-master-inventory-2026-05-08.md
  - docs/06-Daily/reports/external-tools-master-inventory-2026-05-08.json
  - docs/06-Daily/reports/external-tools-reassessment-scope-2026-05-08.md
  - docs/06-Daily/reports/external-tools-reassessment-scope-2026-05-08.json
related_docs:
  - docs/04-Concepts/architecture/external-tool-adoption-doctrine.md
  - docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md
---

# External Tools Radar — Full Reassessment 2026-05-08

## Executive summary

This reassessment restarts from the current review index
`docs/06-Daily/reports/external-tools-radar-INDEX.md` and expands the scope from the
curated 2026-05-08 radar to the broadest repository-derived tool corpus from
this review wave. "Current review index" means authoritative for this
2026-05-08 analysis pass, not a permanent or exhaustive claim that no external
tool exists outside the scanned corpus.

The operator concern is valid: COS should be excellent at integrating and
governing external tools, not at rebuilding every interesting framework. The
new rule is:

> Build COS governance semantics; adopt or integrate commodity mechanisms.

The sweep found three categories:

1. **Good adoptions already aligned with the doctrine**: FastMCP, Bubble Tea,
   Syft+Grype, RAGAS/DeepEval lanes, Phoenix/OTel, MLflow, Aider repo-map as
   pattern, agentapi testdata, Bubblewrap as host-native backend.
2. **Adoptions that should remain optional/adapter-only**: Graphiti, LightRAG,
   HippoRAG, MIRIX, DSPy, Cognee, E2B, LangGraph/AutoGen/CrewAI/MS Agent
   Framework, Jupyter, NeMo Guardrails, Phoenix server, Opik.
3. **Cleanup candidates / contradictions**: LiteLLM remains in requirements
   despite ADR-049 direct-SDK posture; Langfuse remains as dependency/docs
   residue despite ADR-058 Phoenix/OTel migration; `memu` likely points to the
   wrong PyPI package; `pytest-smell` appears declared but not wired.

## Methodology

### Step 1 — Automatic inventory

Generated from:

- `docs/03-PoCs/research/repo-scout/**/*`;
- `docs/06-Daily/reports/**/*external-tools*` and cross-check reports;
- ADRs, architecture docs, and manifests containing GitHub/tool references;
- `requirements.txt`, `requirements/dependency-lanes/*.txt`, `pyproject.toml`,
  package requirements, `go.mod`, and package install commands.

Outputs:

- `docs/06-Daily/reports/external-tools-master-inventory-2026-05-08.json`
- `docs/06-Daily/reports/external-tools-master-inventory-2026-05-08.md`

Counts:

- Raw mentions: **1762**
- Unique normalized raw items: **822**

The raw inventory intentionally includes false positives. It is evidence input,
not a decision ledger.

### Step 2 — Deduplication and normalization

Generated a high/medium-confidence reassessment scope by keeping:

- repo-scout file entries;
- actual dependency/package/module entries;
- explicit radar tool terms;
- high-confidence repository references.

Outputs:

- `docs/06-Daily/reports/external-tools-reassessment-scope-2026-05-08.json`
- `docs/06-Daily/reports/external-tools-reassessment-scope-2026-05-08.md`

Deduplicated scope:

- **184** tools/packages/repos.

### Step 3 — Domain grouping

Grouped the 184-item scope into:

| Domain | Count |
|---|---:|
| agents-orchestration-routing | 45 |
| tui-cli-devtools | 41 |
| memory-rag | 31 |
| foundation-dependencies | 23 |
| uncategorized | 18 |
| mcp-integration | 9 |
| observability-eval-optimization | 8 |
| security-supply-chain-guardrails | 5 |
| sandbox-runtime-testing | 4 |

### Step 4 — Batch re-investigation

Five read-only agents reviewed the scope:

| Batch | Domains | Result |
|---|---|---|
| Memory/RAG + Observability/Eval | `memory-rag`, `observability-eval-optimization` | Engram remains core; adopt/integrate patterns and eval lanes; remove Langfuse residue. |
| Agents/Orchestration/Routing | `agents-orchestration-routing` | Keep COS governance core; treat frameworks as adapters/lab; remove LiteLLM residue. |
| TUI/CLI/DevTools | `tui-cli-devtools` | Bubble Tea remains adopted; integrate existing terminal primitives instead of custom UI utilities. |
| Security/Supply/Foundation | `security-supply-chain-guardrails`, `foundation-dependencies` | Syft+Grype stay primary; heavy lanes remain optional; pytest-smell candidate remove. |
| MCP/Sandbox/Uncategorized | `mcp-integration`, `sandbox-runtime-testing`, `uncategorized` | FastMCP and Bubblewrap are correct integrations; `memu` likely package-name collision. |

### Step 5 — Canonical reports

This report is the consolidation layer. Raw and deduped inventories remain the
machine-readable backing evidence.

## Recommendation taxonomy

| Recommendation | Meaning |
|---|---|
| ADOPT | Use as the selected mechanism/pattern for this layer, with clear tests and a rollback path. |
| INTEGRATE | Keep behind adapter/provider/policy wrapper. |
| KEEP | Current dependency/tool is justified as-is. |
| MONITOR | Watch or harvest patterns; no implementation now. |
| DEFER | Plausible later, blocked by scope/weight/maturity. |
| REJECT | Do not pursue under current constraints. |
| REMOVE | Current repo dependency/reference contradicts doctrine or appears wrong/dead. |

## Cross-domain decision ledger

### P0 cleanup / contradiction findings

These are documentation-first findings now, not yet implementation changes.
They should become follow-up issues/ADRs or targeted commits.

| Tool/package | Recommendation | Why | Next action |
|---|---:|---|---|
| LiteLLM / `BerriAI/litellm` | REMOVE | ADR-049 chooses direct SDK/provider routing; LiteLLM remains in `requirements.txt`/lane docs and adds proxy/supply-chain surface. | Audit imports/usages, then remove or move to explicit legacy/monitor lane. |
| Langfuse | REMOVE from runtime/default | ADR-058 migrates tracing to Phoenix/OTel; Langfuse remains in `requirements.txt` and legacy docs/tests. | Confirm no active imports, then remove or quarantine in legacy lane. |
| `memu` | REMOVE / VERIFY | Requirements likely point to wrong PyPI package; intended memU memory framework appears to use `memu-py`. | Verify API/package, then replace with correct package or remove lane. |
| `pytest-smell` | REMOVE unless wired | Declared in testing extra but no visible gate/config usage. | Add actual CI/audit consumer or drop dependency. |
| NeMo Guardrails | DEFER / optional only | Heavy dependency; PyPI metadata includes proprietary classifier alongside Apache docs. | Keep outside default; audit extras/model licenses before any integration. |
| Jupyter / Notebook | DEFER / optional only | Large execution surface; docs/lanes mark optional/dormant/partial. | Keep in heavy lane only; do not advertise as default adoption. |
| Phoenix server | INTEGRATE with license boundary | Server is ELv2/operator-installed; wrapper/OTel path is safe. | Keep server out of core bundle; document self-host constraints. |

### High-confidence ADOPT / INTEGRATE targets

| Tool/pattern | Recommendation | Adoption kind | Reason | Next action |
|---|---:|---|---|---|
| FastMCP | INTEGRATE | dependency | COS should not reimplement MCP transport; existing server imports FastMCP. | Pin version range and test compatibility. |
| Bubble Tea | ADOPT | dependency | Surface-5 TUI decision is closed; Go TUI framework already used. | Do not reopen TUI framework search. |
| Bubbles / Huh / Lipgloss | INTEGRATE | dependency | Avoid custom terminal widgets/forms/styling. | Use when `cos tui` expands. |
| Glamour / Rich | INTEGRATE | dependency | Avoid custom Markdown/rich terminal rendering. | Use per Go/Python surface. |
| Syft + Grype | KEEP | CLI adapter | Correct primary SBOM/CVE toolchain. | Record versions in release audits. |
| Semgrep | KEEP | CLI adapter | Useful scanner, but rules licensing differs from engine. | Keep tool-only; do not bundle registry rules unreviewed. |
| RAGAS | ADOPT | eval dependency | Good fit for Engram/Cognee retrieval quality evaluation. | Create opt-in eval lane with fixtures. |
| DeepEval | ADOPT | eval dependency | Pytest-style LLM/agent/RAG metrics. | Convert dormant skill into smoke/eval suite. |
| arize-phoenix-otel / OTel | ADOPT | telemetry standard | Portable tracing layer; Phoenix can remain a sink. | Prefer OTLP abstraction. |
| MLflow | INTEGRATE | optional backend | Good outcome/experiment tracking, not trace replacement. | Wire opt-in Stop hook with timeout/idempotency. |
| Aider repo-map | ADOPT pattern | algorithm-port | Avoid static/custom context selection; repo-map pattern is mature. | Implement SDD from `repo-map-context-selector`. |
| coder/agentapi | ADOPT | testdata-vendor first | Golden multi-harness fixtures prevent parser reinvention. | Vendor `msgfmt/testdata` with MIT provenance. |
| Graphiti | INTEGRATE | schema-port/optional backend | Bi-temporal memory model closes Engram history gap. | Add schema proposal/benchmark before code. |
| LightRAG | INTEGRATE | algorithm-port/provider | Dual-level retrieval can improve Engram/Cognee retrieval. | Benchmark before default switch. |
| HippoRAG | INTEGRATE | algorithm-port | PPR fits memory graph multi-hop traversal. | Add experimental strategy behind flag. |
| MIRIX | INTEGRATE | schema/taxonomy-port | Memory class split cleans free-form Engram type semantics. | Add enum/taxonomy design. |
| DSPy / GEPA | INTEGRATE | dependency-pilot | Useful for structured-I/O skill optimization, not router replacement. | Pilot on confidence-check/sdd-verify after dataset. |
| agents.md | INTEGRATE | standard/spec | Cross-harness repo instruction convention. | Ensure init/projection emits compatible AGENTS.md. |
| Simon Willison `llm` | ADOPT patterns | provider/cassette pattern | Mature plugin/provider/cassette ideas avoid dispatch-test reinvention. | Port cassette testing pattern, not CLI wholesale. |
| Snyk agent-scan / Augustus | INTEGRATE | security lane | Useful for malicious skill/MCP/agent probes. | Add opt-in security corpus/scanner lane. |
| Qwen code/provider path | INTEGRATE | provider/harness reference | Aligns with existing ADR-049 Qwen provider path. | Keep OpenAI-compatible provider; no local weights. |
| fzf / fx / VHS | INTEGRATE | optional CLI adapters | Avoid custom fuzzy selector, JSON viewer, demo recorder. | Add only as optional tool probes. |

### Frameworks to keep as adapters/lab, not core

| Tool/framework | Recommendation | Reason |
|---|---:|---|
| LangGraph | DEFER / adapter-lab | Strong ecosystem, but COS owns governance semantics. |
| AutoGen | DEFER | Heavy framework; license/subpackage posture needs review. |
| CrewAI | DEFER | Mature framework, but would replace COS semantics if core. |
| Microsoft Agent Framework | MONITOR | Candidate adapter only. |
| Agentscope | MONITOR | Framework complete; harvest observability/state ideas. |
| OpenHands | MONITOR | Strong external baseline; use for benchmark/ACI. |
| Continue / Roo-Code / OpenCode / Claude Agent SDK | MONITOR | Harness references; adapters only if demand/evidence. |
| E2B | DEFER | Cloud sandbox opt-in; not default local-first runtime. |
| Firecracker | DEFER | Strong isolation but too high ops cost for default. |
| NATS | DEFER | Multi-machine bus later; file IPC covers MVP. |
| OPA | DEFER | Overkill until multi-tenant/ABAC policy is real. |
| Temporal | DEFER | Durable workflow engine, not local-first core. |

### Rejections / no-pursue

| Tool | Recommendation | Why |
|---|---:|---|
| awslabs/agent-squad | REJECT runtime | Squads runtime was archived; ADR-251 is redesign. |
| Bifrost | REJECT default | Proxy/credential surface not justified for local-first. |
| OpenClaw | REJECT pending deep manual verification | Signal/stars anomaly; low unique value vs risk. |
| Hyper-Extract | REJECT until license clear | GitHub license `NOASSERTION`; KG extraction not worth unclear license. |
| File managers/system monitors/K8s/Docker TUIs | REJECT core | Off-theme; useful at most as UX references. |

## Domain summaries

### Memory / RAG

Decision: **Engram remains the selected in-repo memory substrate for this wave**. Adopt patterns and benchmarks rather
than replacing it with a framework.

Recommended staged work:

1. Benchmark Engram FTS5/BFS vs LightRAG-style dual retrieval vs HippoRAG PPR
   vs Cognee optional path.
2. Design Graphiti-style bi-temporal schema and MIRIX memory-class enum as an
   additive migration.
3. Keep Cognee optional; do not make a KG/RAG service default.
4. Use RAGAS/DeepEval to measure retrieval quality before public claims.

### Agents / Orchestration / Routing

Decision: **do not replace COS orchestration core with a framework**. ADR-251
is the right boundary: external frameworks are adapters/lab, while COS owns
worktree/branch ownership, dispatch budgets, release freeze, handoff receipts,
and capability truth.

Highest value adoptions are low-risk artifacts:

- agentapi test fixtures;
- agents.md convention;
- Aider repo-map pattern;
- Simon Willison `llm` cassette/provider patterns;
- DSPy/GEPA for structured skill optimization;
- Snyk/Augustus security probe corpus.

### TUI / CLI / DevTools

Decision: **Surface-5 remains Bubble Tea**. Do not rebuild terminal rendering,
widgets, forms, fuzzy finding, JSON viewing, or demo recording.

Adopt/integrate as needed:

- Bubble Tea, Bubbles, Huh, Lipgloss;
- Glamour/Rich for Markdown/rich terminal output;
- fzf for fuzzy selection;
- fx for JSON/JSONL viewing;
- VHS for demos.

### MCP / Sandbox / Foundation

Decision: **delegate mechanisms, own policy**.

- FastMCP: correct MCP mechanism.
- Bubblewrap/Seatbelt: correct host-native sandbox backend, but hardening
  remains.
- Testcontainers: correct test-only Docker fixture dependency.
- Provider SDKs (`openai`, `anthropic`, `google-generativeai`) are provider
  dependencies, not MCP features.

### Security / Supply Chain

Decision: **Syft+Grype stay primary**. Semgrep stays CLI/tool-only because rule
licensing can differ from engine licensing. Heavy lanes (`jupyter`,
`notebook`, `nemoguardrails`) remain optional.

## Required documentation follow-ups

1. **Machine-readable adoption manifest** — `manifests/external-tools-adoption.yaml`.
   Fields: tool, stable_id, source reports, adoption kind, license, status,
   consumer proof, implementation paths, tests, owner, next action.
2. **License appendix** — Phoenix ELv2 boundary, Langfuse mixed/MIT posture,
   Semgrep engine-vs-rules, MPL test-only deps, FSL self-package note.
3. **Dependency cleanup ADR or issue** — LiteLLM, Langfuse, memu, pytest-smell,
   NeMo/Jupyter lane posture.
4. **Memory benchmark spec** — Engram baseline vs LightRAG/HippoRAG/Cognee and
   RAGAS/DeepEval metrics.
5. **Harness fixtures plan** — agentapi testdata vendoring with MIT provenance.
6. **Provider/cassette testing plan** — Simon Willison `llm` patterns applied to
   COS dispatch tests.

## Implementation hold

No runtime adoption should start from this report until the target tool has:

- adoption kind;
- license and footprint posture;
- default/optional lane decision;
- consumer proof target;
- test plan;
- rollback/deprecation plan;
- claim wording boundary.

## Validation notes

This was a mixed automated/manual reassessment over the repository-derived corpus.
It was not a fresh internet-wide validation of every tool, release, license,
star count, or maintenance status. Some upstream currentness checks were limited
by API rate limits, and some licenses require subpackage-level verification
before copying code or vendoring data. This report is sufficient to prioritize
documentation and cleanup work; it is not sufficient to vendor code, add a
runtime dependency, or make public claims without a targeted source check.
