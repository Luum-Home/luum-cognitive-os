---
report_type: external-tools-radar
date: 2026-05-08
prior_edition: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
new_axis: bidirectional-implementation-cross-check
source_audits:
  - docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md
  - docs/06-Daily/reports/cross-check-B-sandbox-mcp-2026-05-08.md
  - docs/06-Daily/reports/cross-check-C-orchestration-2026-05-08.md
  - docs/06-Daily/reports/cross-check-D-codegen-skills-tui-2026-05-08.md
  - docs/06-Daily/reports/cross-check-E-observability-debt-2026-05-08.md
related_adrs: [ADR-065, ADR-058, ADR-187, ADR-192, ADR-227, ADR-231, ADR-232, ADR-236, ADR-251, ADR-253]
budget_used_tool_calls: ~80
---

# External Tools Radar — 2026-05-08

Iteration of the radar pipeline (ADR-065). Adds a new axis the prior editions
lacked: **bidirectional cross-check between research recommendation and our
implementation**. The 2026-05-06 edition ranked candidates by extractable
primitive value; this edition re-ranks them by **delta against shipped
code** — i.e. *would adopting this actually improve over what we already do?*

The 2026-05-06 priority list was mostly correct. This edition keeps it but
collapses items where our code already ships parity, and promotes items
where the research narrative was correct but our implementation has a real
gap.

## 1. Executive Summary

**Re-rank vs 2026-05-06:**

| Tool / pattern | 2026-05-06 | 2026-05-08 | Reason |
|---|---|---|---|
| graphiti bi-temporal schema | trial | **adopt-schema** | `memory_relations` is mono-temporal; clean port, no framework |
| LightRAG dual-level retrieval | trial | **adopt-algorithm** | Engram FTS5 + graph walk has no dual-level scoring |
| HippoRAG personalized PageRank | trial | **adopt-algorithm** | `engram_graph_walker.py` does flat BFS (depth=2) — no PPR |
| MIRIX taxonomy | (not on prior radar) | **adopt-overlay** | 1-2d add-on, combinable with the above |
| Aider repo-map | trial | **adopt-algorithm** | `lib/context_diet.py` uses static allowlist; repo-map graph-rank superior for codegen context |
| DSPy | trial (foundational) | **adopt-selective** | Use for skills with structured I/O (sdd-verify, confidence-check). Do **not** rewrite skill router — categories are orthogonal |
| agentapi | trial | **adopt-testdata-only** | Different problem (interactive I/O vs observability events). Vendor the 11-harness golden corpus, skip the Go sidecar |
| obra/superpowers schema | trial | **hybrid** | Our schema (governance + routing + ADR provenance) is richer; only adopt their `description: "Use when…"` convention |
| TUI (Textual / ratatui / bubbletea) | tier-2 assess | **closed** | ADR-192 already adopted Bubble Tea; proof shipped in `cmd/cos/internal/tui/proof.go` |
| Phoenix vs Langfuse vs MLflow | (architecture eval) | **closed** | ADR-058 (2026-04-24) makes MLflow + Phoenix coexist; Langfuse deprecated |
| Cline shadow-git pattern | trial | **already-shipped** | ADR-227 `lib/shadow_git.py` ships parity + atomic file+conversation restore (better than upstream pattern) |
| fastmcp | trial | **already-shipped** | Genuine import in `mcp-server/cos_mcp.py` (870L) and `packages/advisor-mcp/`. Not a casero reimplementation |
| Bubblewrap / sandbox-exec | trial | **already-shipped (hardening pending)** | `packages/agent-lifecycle/lib/sandbox_adapter.py` wires bwrap + sandbox-exec; bwrap policy laxa needs `--die-with-parent` + seccomp |
| Squad coordination (awslabs/agent-squad) | monitor | **rejected (ADR-253)** | Intentional dormancy; ADR-251 is the redesign |
| NATS, Firecracker, OPA, Temporal | tier-4 reject | **tier-4 confirmed** | Local-first positioning; not a gap |

## 2. Adoption Plan (ranked by leverage / effort)

Three waves. Each item cites the cross-check audit that justifies it.

### Wave 1 — Housekeeping (1 day total)
Pure honesty + trivial hardening. No risk.

| # | Action | Source | Effort |
|---|---|---|---|
| H1 | Create ADR-253 tombstone for squads (`packages/_archived/squads/`) | C §🔍3 | 30 min |
| H2 | Fix README L26: "11 PreTool/PostTool + 3 library" → "12 + 2" (L13 reinvention-check is PostToolUse) | E auditoría | 5 min |
| H3 | Reconcile Trust Report claim ("requires") with hook L8 (exit 0, log only) — decide enforce or soften wording | E DEBT-1 | 30 min – 1 d |
| H4 | Bubblewrap policy hardening: add `--die-with-parent`, seccomp, drop `--ro-bind /` | B §🔍4 | 1-2 h |
| H5 | "85% token reduction" claim from research — measure or remove from docs | B §🔍7 | 1-2 h |
| H6 | Skill schema convention: adopt `description: "Use when…"` across `skills/*/SKILL.md` for trigger discoverability | D §🔍13 | 1-2 d |

### Wave 2 — Memory bundle (10–14 days, single SDD change)
Highest leverage cluster. Combine four memory gaps into one schema migration.
Candidate: `/sdd-new memory-layer-evolution`.

| # | Action | License | Approach |
|---|---|---|---|
| M1 | Adopt graphiti bi-temporal schema (`valid_from`/`valid_to`) in `memory_relations` | Apache-2.0 | Schema only, no framework |
| M2 | Port LightRAG dual-level (entity + topic) retrieval scoring into `engram_lifecycle.py` | MIT | Algorithm port |
| M3 | Add HippoRAG personalized PageRank as alternative mode in `engram_graph_walker.py` (alongside current BFS) | MIT | Algorithm port |
| M4 | Add `memory_class` enum overlay (`semantic`/`episodic`/`procedural`/`working`) — couple `memory_decay` to `working` | MIT (MIRIX) | Overlay field |

Source: cross-check A.

### Wave 3 — Codegen + selective integrations (3 weeks, parallelizable)

| # | Action | License | Effort |
|---|---|---|---|
| W3-1 | `lib/repo_map.py`: graph-rank + tree-sitter + token budget. Replaces static allowlist in `lib/context_diet.py` for codegen context selection | Apache-2.0 (Aider) | 5-7 d |
| W3-2 | DSPy pilot: integrate as dependency for one structured-I/O skill (start with `sdd-verify`). Do **not** touch `lib/skill_router.py` | MIT | 3-7 d pilot |
| W3-3 | Vendor `lib/msgfmt/testdata/` from agentapi (11-harness golden fixtures) under `lib/harness_adapter/testdata/`. No Go sidecar | MIT | 1 d vendor + 3-5 d parser port |

## 3. Tier-4 Confirmed (no-pursue, with rationale)

Carried forward from 2026-05-06; this edition revalidates each:

- **NATS JetStream as default cross-session bus** — heavy external dep; file-IPC in ADR-233 covers MVP. Confirmed.
- **Firecracker / hypervisor sandboxes as primary** — operationally expensive; Bubblewrap (Wave 1 H4) closes 80% at zero cost. E2B remains opt-in tier-3.
- **OPA / Rego policy engine** — single-operator OS doesn't need ABAC. Approval policies stay YAML (ADR-234).
- **Temporal / Cadence durable workflows** — `@event_wrap` + ADR-226 event-sourced bus covers MVP need.
- **Multi-machine cloud orchestration** — local-first is positioning, not a gap.

## 4. Already-Shipped Verifications (do **not** re-audit)

This radar edition verified these are real in code, not aspirational:

- **ADR-227 shadow-git**: `lib/shadow_git.py`, `manifests/shadow-git.yaml`, `hooks/auto-checkpoint.sh`, `hooks/pre-agent-snapshot.sh`. Atomic file + conversation restore. Source: cross-check C §🔍6.
- **ADR-231 fastmcp**: `from fastmcp import FastMCP` in `mcp-server/cos_mcp.py` (870L) and `packages/advisor-mcp/advisor_server.py`. `requirements.txt` declares `fastmcp>=2.0.0`. The 15-LOC `_FastMCPCompat` is a test seam, not a reimplementation. Source: cross-check B §🔍5.
- **ADR-232 sandbox tiers**: `packages/agent-lifecycle/lib/sandbox_adapter.py` (146 LOC) wires bwrap + sandbox-exec via subprocess. microvm/contree are adapter_contract scaffolds, declared as such. Source: cross-check B §🔍4.
- **ADR-251 orchestration boundary**: Status `accepted`, Slice A implemented. Squads tombstone ADR-253 closes the convention gap. Source: cross-check C §🔍3.
- **ADR-058 observability**: MLflow (outcome) + Phoenix (LLM traces via OTel) coexist; Langfuse deprecated (`grep -c langfuse lib/record_completion.py` = 0). Source: cross-check E §🔍11.
- **ADR-192 TUI**: Bubble Tea adopted, proof in `cmd/cos/internal/tui/proof.go`. SURFACE-5 closed. Source: cross-check D §🔍8.

## 5. Methodology Note (for next edition)

The bidirectional cross-check axis (verdicts MEJOR_NUESTRO / IGUAL /
MEJOR_EXTERNO / NO_COMPARABLE) caught two classes of error the prior radar
missed:

1. **Recommendations that are categorically wrong** — e.g. research framed
   our skill router as a DSPy peer; in fact they operate on different
   abstraction layers. Adopting DSPy to "replace" the router would have
   been waste. Verdict: NO_COMPARABLE. Selective adoption only.
2. **Recommendations that miss already-shipped code** — e.g. shadow-git,
   fastmcp, Bubblewrap, MLflow/Phoenix, TUI, squads. Re-running these
   audits without the bidirectional check would have re-spawned
   already-decided work.

Recommendation for next radar edition: keep the bidirectional axis as a
required column. Add a **claim-debt audit** column that flags every
adoption recommendation against `aspirational-audit-*.md` to prevent
overclaim drift.
