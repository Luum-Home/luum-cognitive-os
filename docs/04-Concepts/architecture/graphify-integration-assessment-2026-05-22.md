# Graphify Integration Assessment — 2026-05-22

## Decision

Adopt Graphify as an **optional graph-indexing and query-optimization tool** for Cognitive OS maintainer workflows. Do not make it a core runtime dependency, a mandatory hook, or an unfiltered whole-repository scan.

Graphify is useful as a repository navigation layer: it turns selected code and documentation into `graphify-out/graph.json`, then supports lower-token queries such as `graphify query`, impact checks such as `graphify affected`, graph paths, benchmarks, and optional visual exports.

## Current Verdict

**Status:** `TRIAL-CONTROLLED`

Graphify should enter a controlled trial behind explicit maintainer commands and a curated `.graphifyignore`. It should not be enabled by default for consumer projects and should not be installed through `graphify codex install` without reviewing the generated instruction changes.

## Why This Reassessment Exists

A prior May 2026 repo-scout monitor follow-up rejected `safishamsi/graphify` because of signal-integrity concerns around an anomalous star count and limited available evidence at that time.

This reassessment uses a direct local clone, package inspection, upstream tests, and a real Cognitive OS probe. The earlier signal concern remains a caution for dependency governance, but it is no longer sufficient to block a **local optional trial** because the tool is MIT licensed, installable, testable, and useful in a bounded code-only slice.

## Source Snapshot

- Repository: `https://github.com/safishamsi/graphify`
- Local clone path used for investigation: `/tmp/graphify-investigation`
- Cloned HEAD: `6efd06c`
- Commit date: `2026-05-22`
- Commit subject: `add YC S26 badge to README`
- PyPI package: `graphifyy`
- CLI command: `graphify`
- Version inspected: `0.8.15`
- PyPI release date: `2026-05-22`
- Python requirement: `>=3.10`
- License: `MIT`

## Upstream Capability Summary

Graphify provides a Python CLI and assistant skill that can map supported files into a knowledge graph.

Core pipeline described by upstream:

```text
detect() -> extract() -> build_graph() -> cluster() -> analyze() -> report() -> export()
```

Important local capabilities:

- Tree-sitter structural extraction for code.
- NetworkX graph construction and clustering.
- Query commands over existing `graphify-out/graph.json`.
- Path and explanation commands for known nodes.
- Affected-node traversal for impact-style questions.
- Optional HTML, SVG, GraphML, Neo4j, MCP, watch, and hook integrations.
- Optional semantic extraction for docs, papers, images, office files, Google Workspace files, audio, and video.

Supported code surfaces overlap well with Cognitive OS: Python, Bash, Go, JavaScript/TypeScript, JSON, YAML-like docs, SQL, Rust, and other languages.

## Local Verification Performed

### Upstream Clone and Metadata

The repository was cloned to `/tmp/graphify-investigation` and inspected directly. Package metadata from `pyproject.toml` reported:

- Package name: `graphifyy`
- Version: `0.8.15`
- Required Python: `>=3.10`
- Base dependencies include `networkx`, `datasketch`, `rapidfuzz`, `tree-sitter`, and language grammars.
- Optional extras include `mcp`, `neo4j`, `pdf`, `watch`, `svg`, `leiden`, `office`, `google`, `video`, `openai`, `ollama`, `gemini`, `bedrock`, and `sql`.

### Upstream Test Smoke

A temporary venv was created at `/tmp/graphify-venv`, Graphify was installed editable from the clone, and a targeted upstream test slice was run:

```bash
/tmp/graphify-venv/bin/python -m pytest \
  tests/test_detect.py \
  tests/test_extract.py \
  tests/test_build.py \
  tests/test_cli_export.py \
  -q
```

Result:

```text
218 passed in 32.20s
```

### Cognitive OS Probe: `lib/`

A code-only clustered extraction was run against Cognitive OS `lib/`:

```bash
OLLAMA_BASE_URL=http://127.0.0.1:9 \
/tmp/graphify-venv/bin/graphify extract \
  <repo-root>/lib \
  --backend ollama \
  --out /tmp/luum-graphify-lib-cluster \
  --max-workers 8 \
  --exclude '*.md' \
  --exclude '*.txt' \
  --exclude '*.yaml' \
  --exclude '*.yml'
```

The local Ollama endpoint was intentionally pointed at an unavailable loopback port. Because the corpus was code-only, Graphify used deterministic AST extraction and did not need semantic LLM calls.

Result:

```text
found 383 code, 0 docs, 0 papers, 0 images
wrote graph.json: 7956 nodes, 12984 edges, 511 communities
```

Benchmark result:

```text
Corpus:          397,800 words -> ~530,400 tokens (naive)
Graph:           7,956 nodes, 12,984 edges
Avg query cost:  ~5,252 tokens
Reduction:       101.0x fewer tokens per query
```

This is the strongest practical signal from the investigation: a scoped graph over `lib/` can materially reduce repeated context loading for architecture questions.

## Important Gotchas

### Whole-Repo Scan Is Unsafe Without Scoping

The local working tree contains large directories that should not be scanned by default:

```text
reference/      ~77,461 files
dashboard/      ~14,991 files
.venv/          ~7,301 files
.cognitive-os/  ~5,040 files
.git/           ~4,863 files
.claude/        ~3,084 files
```

A first uncurated repository-level scan produced no useful output for an extended period before being stopped. The correct path is to scope Graphify before any full-repo attempt.

### Clustered vs Raw Output

`graphify extract --no-cluster` writes a raw `nodes`/`edges` extraction schema. Some commands, including `graphify benchmark`, expect clustered NetworkX node-link JSON with `links`. For benchmarkable and query-friendly output, use clustered extraction unless a raw extraction artifact is explicitly needed.

### Semantic Extraction Has Cost

Docs, PDFs, images, office files, audio, and video require semantic extraction through an LLM backend or assistant subagents. For Cognitive OS, start with code-only deterministic extraction before expanding to documentation.

### Codex Install Is Not a Safe Blind Step

Upstream supports Codex with `graphify codex install`, but that command writes persistent assistant instructions. The upstream Codex skill also expects `multi_agent = true` in `~/.codex/config.toml` for parallel semantic extraction.

For this repository, do not run `graphify codex install` blindly. If Codex integration is desired, port a controlled instruction block into a repo-owned skill or rule so it remains compatible with Cognitive OS governance.

### Git Hooks Should Not Be Enabled Initially

Graphify can install post-commit and post-checkout hooks that rebuild graphs in the background. Cognitive OS already has a substantial hook governance layer. Do not enable Graphify hooks until a specific compatibility review proves they will not interfere with existing hook metrics, protected paths, merge workflows, or test lanes.

## Recommended Adoption Plan

### Phase 1 — Add a Curated Ignore File

Create a repo-owned `.graphifyignore` before any repository-level run. Initial candidate:

```gitignore
.git/
.venv/
.ruff_cache/
.pytest_cache/
target/
dist/
dashboard/
reference/
graphify-out/
.cognitive-os/metrics/
.cognitive-os/cache/
```

Candidate included surfaces for the first maintainer graph:

```text
lib/
hooks/
cmd/
internal/
pkg/
packages/agent-service/
scripts/
rules/
skills/
templates/
docs/04-Concepts/
docs/02-Decisions/
```

### Phase 2 — Add a Maintainer Wrapper

Add a reproducible command such as `scripts/cos-graphify-build` rather than depending on ad hoc CLI invocations. The wrapper should:

1. Refuse to run without `.graphifyignore`.
2. Default to deterministic code extraction.
3. Write outputs under `graphify-out/`.
4. Print node, edge, community, and token-reduction evidence.
5. Avoid semantic document extraction unless explicitly requested.

Candidate first command shape:

```bash
uvx --from graphifyy graphify extract . \
  --out . \
  --max-workers 8 \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'reference/' \
  --exclude 'dashboard/' \
  --exclude 'target/' \
  --exclude 'dist/' \
  --exclude 'graphify-out/'
```

If upstream adds or confirms an `--exclude-from` flag, prefer passing `.graphifyignore` directly.

### Phase 3 — Trial Query Workflow

After generating a graph, maintainers can use it for scoped questions before broad grep or multi-file reads:

```bash
graphify query "Which modules handle memory, routing, and governance?" \
  --graph graphify-out/graph.json \
  --budget 1600
```

```bash
graphify affected "CanonicalEvent" \
  --graph graphify-out/graph.json \
  --depth 2
```

```bash
graphify benchmark graphify-out/graph.json
```

### Phase 4 — Optional Docs Expansion

Only after code extraction proves stable, add a separate semantic-docs lane for a curated documentation subset:

```text
docs/04-Concepts/architecture/
docs/02-Decisions/adrs/
rules/
skills/
```

This lane must be opt-in because semantic extraction can spend model tokens.

### Phase 5 — Optional Codex Instruction

If the graph proves useful across multiple sessions, add a repo-owned instruction that says:

- Prefer `graphify query` when `graphify-out/graph.json` exists and the user asks a repository-structure question.
- Do not treat Graphify output as authoritative for tests or release claims.
- Regenerate or update the graph after large refactors before relying on it.
- Use Graphify as context selection, not as proof of correctness.

## Relationship to Existing Cognitive OS Primitives

Graphify should be treated as an external tool adapter wrapped by an OS-owned context optimization agentic primitive, not as a core runtime primitive or upstream IDE installer.

It complements existing systems:

- **Engram:** stores durable decisions, discoveries, and session memory. Graphify indexes current repository structure.
- **Repo-map skills:** provide curated human-maintained orientation. Graphify provides generated graph traversal.
- **ACC and audits:** verify claims and primitive coverage. Graphify can guide where to inspect, but does not verify correctness.
- **Test lanes:** remain the source of runtime confidence. Graphify does not replace tests.

## Acceptance Criteria for Adoption

Before promoting Graphify beyond a local maintainer trial:

1. `.graphifyignore` exists and excludes known large/noisy local directories.
2. `scripts/cos-graphify-build` or equivalent wrapper exists.
3. A code-only graph can be generated for the curated repo slice.
4. The wrapper reports node count, edge count, community count, and benchmark output.
5. No Graphify hook is installed by default.
6. No Codex/AGENTS.md mutation happens through upstream install commands without review.
7. Documentation clearly labels Graphify output as navigation context, not verification evidence.
8. A targeted validation lane proves the wrapper does not touch blocked paths or credentials.

## Current Recommendation

Proceed with the controlled trial.

Do not vendor Graphify into the repository. Install it as an operator tool with `uvx --from graphifyy graphify` or a local venv. Keep any Cognitive OS integration as thin wrapper scripts and documentation until repeated maintainer use proves value.

## Trust Report

```text
TRUST_REPORT: SCORE=84 STATUS=HIGH EVIDENCE=5 UNCERTAINTIES=2
```

Evidence:

1. Upstream repository cloned locally.
2. Package metadata and MIT license inspected.
3. Targeted upstream tests passed.
4. Cognitive OS `lib/` graph generated successfully.
5. Graphify benchmark reported 101.0x lower average query-token cost for the scoped graph.

Uncertainties:

1. Full semantic extraction over Cognitive OS docs was not run because it can consume model tokens.
2. Codex install and Graphify hook install were intentionally not executed, so integration side effects remain to be reviewed.

## Implementation Status

Initial controlled-trial wiring has started:

1. `.graphifyignore` guards noisy local roots and sensitive/private areas.
2. `.gitignore` ignores local `graphify-out/` outputs so default repo-root builds do not create trackable artifacts.
3. `scripts/cos-graphify-build` provides a maintainer wrapper for code-only Graphify builds by default.
4. `docs/09-Quality/manual-tests/graphify-controlled-trial.md` defines the manual proof path.
5. `docs/06-Daily/reports/graphify-controlled-trial-receipt-2026-05-22.md` records the first wrapper-run receipt for a bounded `lib/` graph.

The wrapper still keeps Graphify outside the core runtime: it uses an operator-installed `graphify` binary or `uvx --from graphifyy graphify`, does not vendor the dependency, does not install hooks, and does not mutate assistant instruction files.

## Next Slice

Use the maintainer-only `graphify-query` skill and ADR-331 as the next operating path. Do not add persistent Codex instructions yet. Run a scoped semantic-docs extraction only if token budget and backend are explicitly approved.

## Portable Primitive Update — 2026-05-22

Graphify is being incorporated as an OS-owned context optimization primitive, not as an upstream IDE installer. The canonical follow-up artifacts are ADR-331, `skills/graphify-query/SKILL.md`, and `scripts/cos-graphify-build`.
