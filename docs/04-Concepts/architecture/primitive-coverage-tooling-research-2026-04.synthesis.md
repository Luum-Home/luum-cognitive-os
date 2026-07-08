---
type: concept-synthesis
source: docs/04-Concepts/architecture/primitive-coverage-tooling-research-2026-04.md
provenance: "Cognitive OS needs a 'test coverage'-equivalent for agentic/operational primitives (skills, hooks, rules, workflows, configs, docs, APIs, scripts, prompts, runtime signals), not an agent that reads the whole repo into context."
---

## What it is
Research (2026-04-30) concluding no tool provides turnkey "coverage for agentic primitives" out of the box; COS should build a thin Primitive Coverage Layer on existing building blocks (code intelligence indexes, static analysis, docs-as-code, API governance, coverage infra, emerging MCP/code-graph servers) rather than inventing scanners from scratch. Agents query a compact evidence store, not the repo.

## Key mechanics
- Primitive Coverage Schema: each row normalizes a repo object with fields `declared`, `registered`, `referenced_by`, `runtime_seen`, `tested`, `documented`, `owner`, `claims`, `proof_links`, `status` (`real|partial|dormant|aspirational|orphan|deprecated`), `next_action`.
- Tooling landscape by category: code intelligence (Tree-sitter recommended starting point, optional SCIP import; Kythe/Joern only if semantic precision needed); static analysis (Semgrep/ast-grep for fast custom rules, CodeQL for language-specific semantic queries); coverage/CI reporting patterns (Codecov PR deltas, SARIF); docs coverage (Vale, markdownlint-cli2, lychee, Sphinx coverage, pytest-codeblock); API governance (Spectral, Redocly CLI, oasdiff); emerging agent/MCP code-graph tools (jcodemunch-mcp, tree-sitter-analyzer, mcp-server-tree-sitter, code-graph-rag).
- Scoring proposal: 20% declaration + 20% wiring + 15% behavior tests + 15% runtime evidence + 10% docs discoverability + 10% claim proof + 5% ownership + 5% DX/runbook evidence; reported as global score, per-family score, and PR regression score.
- Existing COS scripts mapped as early domain-specific versions: `scripts/primitive_gap_snapshot.py`, `scripts/primitive_row_audit.py`, `scripts/claim_proof_audit.py`, `scripts/docs_duplicate_audit.py`, `scripts/reduction_backlog.py`, `scripts/primitive_usage_map.py`, `scripts/primitive_surface_reduce.py`.
- 4-phase implementation plan: Phase 1 local deterministic scanner (adapter manifest schema, normalized `primitive-coverage.json` + Markdown + SARIF, gate on "no new high gaps"); Phase 2 structural backend (Tree-sitter extraction, Semgrep/ast-grep rules, docs graph, runtime log importer); Phase 3 agent query surface (CLI query commands, MCP server, compact evidence rows, "why partial?" explanations); Phase 4 multi-repo/org mode (Backstage catalog, OpenAPI/Spectral/oasdiff adapter, per-team trends, PR comments).
- Immediate recommended stack: Tree-sitter + Semgrep/ast-grep + SARIF + (Vale + lychee + markdownlint-cli2 + pytest-codeblock) + (Spectral + oasdiff) + SQLite/JSONL storage.

## Relations & where used
Proposed CLI surface: `primitive-coverage scan .`, `report --format markdown`, `ci --fail-new-gaps`, `query --family hooks --status partial`, `query --docs --claims-without-proof`, `explain hook:pre-commit-gate`.

## Status / caveats
Research/decision-recommendation document, not yet a shipped package — open questions remain: which primitive families are first-class outside COS, LLM vs rules classification for docs claims, minimum evidence threshold for "real," blocking vs advisory findings, runtime evidence expiry, generated/vendor file exclusion, default graph backend.
