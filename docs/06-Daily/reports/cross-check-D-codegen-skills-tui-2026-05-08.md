# Cross-check Part D: Codegen, Skills, TUI (2026-05-08)

Working dir: `luum-agent-os` (repo root)
Phase: reconstruction. Blast radius: 0 (research-only).

---

## 🔍9 Aider edit-block + repo-map (Apache-2.0)

**Verdict:** **EXTERNAL_BETTER (parcial) — repo-map worth porting as pattern.**

### Aider unique value
- **Repo-map**: graph-ranking algorithm over the dependency graph (nodes=files, edges=imports/calls) that extracts "most important classes/functions with type signatures" inside a **configurable token budget** (`--map-tokens`, default 1k). Tree-sitter for selective symbolic extraction — filters noise that grep does not filter.
- **Edit-block diff format**: SEARCH/REPLACE blocks (format `<<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE`) that the LLM emits as an applicable diff. Claude Code already has native `Edit` that covers this — **NOT_COMPARABLE** on that axis (functional parity).

### Local equivalent
- `lib/context_diet.py` — selection **by task_type** (implementation/review/debug/etc.) with heuristic allowlist of rules. Token estimation char/4. **Does not use graph ranking or dependency graph.**
- `lib/context_budget.py`, `lib/context_budget_monitor.py`, `lib/context_compressor.py`, `lib/context_estimator.py` — budget enforcement and compression, but none performs **ranking by symbolic importance**.
- `lib/context_optimization` — does not exist as a separate module (only appears as rule key `[context-optimization]` in RULES-COMPACT §9).

### Gap real
| Axis | Aider | Ours |
|---|---|---|
| File selection | Graph rank by dependencies | Allowlist by task_type |
| Symbols | Tree-sitter, top-N by usage | N/A |
| Dynamic token budget | Yes (`--map-tokens`) | Yes (`context_budget.py`) |
| Edit application | SEARCH/REPLACE blocks | Native `Edit` tool |

### Is repo-map worth porting?
**Yes, as `lib/repo_map.py`** — pattern-only port (Apache-2.0 allows even copy-code). Concrete value: when a sub-agent receives the SDD prompt, instead of reading heuristic rules + grep ad-hoc, would receive a prioritized symbolic map of the relevant subgraph. Would reduce context waste in `sdd-apply` on large repos (luum-agent-os already has >500 Python files).

**Estimated work:** medium — needs tree-sitter (Python already has `tree_sitter_languages`), graph builder, ranker (PageRank-style). 2-3 days for MVP.

**Referencia externa:** https://aider.chat/docs/repomap.html · https://github.com/Aider-AI/aider (Apache-2.0).

---

## 🔍13 Skill schemas: obra/superpowers vs ours

**Verdict:** **OURS_BETTER** (significantly). Schema superpowers is minimalist by cross-agent design; ours models governance.

### Schema comparison

| Campo | obra/superpowers | luum-agent-os |
|---|---|---|
| `name` | required (kebab) | required (kebab) |
| `description` | required, "Use when…", ≤1024 chars | required (multiline OK) |
| `command` | — | optional (`/sdd-explore`) |
| `trigger` | — | optional (texto narrativo) |
| `version` | — | `1.0.0` semver |
| `audience` | — | `project`/`personal` |
| `effort` | — | `opus`/`sonnet`/`haiku` (model routing) |
| `summary_line` | — | one-line preview |
| `platforms` | implicit (cross-agent) | `["claude-code"]` explicit |
| `prerequisites` | — | lists |
| `inputs`/`outputs` | — | estructurados (sdd-explore) |
| `routing_patterns` | — | regex + confidence (skill_router) |
| `routing` (LLM) | — | tier/providers/budget_max_usd (ADR-049) |
| `user-invocable` | — | bool |
| `auto-generated` | — | bool |
| `last-updated` | — | fecha |
| `license` | — | MIT/etc. |
| `context info` | — | author/pattern/inspired-by |
| `<!-- SCOPE: both -->` | — | pre-frontmatter scope marker (os/project/both) |

### Analysis
- **Superpowers schema = minimum viable cross-agent** (only `name` + `description`). Spec deferred a agentskills.io. Gains portability, loses governance.
- **Our schema = governance-rich**: model routing (effort+routing.tier), cost ceiling (budget_max_usd_per_call), pattern-based invocation (regex+confidence), ADR provenance, scope discrimination. Tied to Claude Code but with `platforms` explicit = upgrade path.
- "455 SKILL.md vs 90" is a quantity metric, not a schema metric. Our 90 are dense (governance, modthe directives, routing); many of the 455 in everything-claude-code are mirrors of Anthropic specs.

### Migrate / maintain / hybridize?
**Hybridize (low-cost):** keep current schema + adopt the convention `description: "Use when…"` from superpowers. The "Use when" pattern improves **trigger discoverability** of skill_router because it aligns description with invocation conditions. Mechanical change: update `skill-creator` to force prefix "Use when" in `description`. Do not touch the 90 existing ones in bulk; only new ones and natural refresh.

**Referencia externa:** https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md · agentskills.io/specification.

**Files consulted:**
- `skills/code-review/SKILL.md` (rich governance schema, GGA-inspired)
- `skills/sdd-explore/SKILL.md` (inputs/outputs + routing.tier=frontier)
- `skills/CATALOG-COMPACT.md` / `skills/REGISTRY.lock`

---

## 🔍8 TUI substrate SURFACE-5

**Verdict:** **NOT_COMPARABLE — research is closed, decision made (Bubble Tea), proof shipped.**

### Status of ADR-187 / ADR-192
ADR-187 (`ADR-187-surface-5-adoption-proof-contract.md`) **established the proof contract** and ADR-192 (`ADR-192-surface-5-adopt-bubbletea.md`, status=Accepted 2026-05-06) **resolved the decision: adopt Bubble Tea**. Complete chain:

1. ADR-172 — Multi-Surface UI Architecture (deja Surface 5 abierto)
2. ADR-173 — Surface 5 Research Gate
3. ADR-187 — Adoption Proof Conct (7 evidence rows: source compat, license, runtime boundary, operator value, reversibility, failure mode, testability)
4. **ADR-192 — Adopt Bubble Tea** (proof shipped in `cmd/cos/internal/tui/proof.go` + `proof_test.go`)
5. ADR-195 — Operable TUI Conct
6. ADR-197 — Operable Actions

### Framework recommendation
**Bubble Tea (Go)** — already adopted, already vendored in `cmd/cos/go.mod`, proof slice compiling. Reasons documented in ADR-192 + report `surface-5-tui-ui-candidates-2026-05-05.md`:
- COS already has Go modules (`cmd/cos`, `cmd/cos-test` per ADR-131) — natural composition.
- MIT (vs Charm crush FSL-1.1-MIT blocked for ~2 years).
- Battle-tested (lazygit, k9s, gh-dash, soft-serve).
- Elm-architecture (Model/Update/View) maps cleanly a lifecycle states COS as fields and transitions as messages.
- Bubbles + Lipgloss complete the stack (table, viewport, list, styling).

### Why NOT Textual / ratatui / huh / gum?
- **Textual (Python)**: discarded in proof — heavier, startup time, does not leverage the existing Go investment. It would have been valid if COS were Python-only, but Go already exists.
- **ratatui (Rust)**: would add a third language to the toolchain (Python+Go+Rust). No pre-existing Rust surface.
- **huh** and **gum** are **components** on top of Bubble Tea (forms and shell-scriptable prompts), not substrates. They are complementary, not alternatives.
- **bubbletea** won because of already vendored + Go-native + composability with `cmd/cos`.

### Fundamental reason
The premise "zero TUI imports, all Bash" of the audit is **outdated**: the Go proof slice already imports Bubble Tea (`cmd/cos/internal/tui/proof.go`). The Bash `scripts/cos-tui` is kept as a legacy bridge while Surface 5 is born in Go. **There is no open gap.**

**Files consulted:**
- `docs/02-Decisions/adrs/ADR-187-surface-5-adoption-proof-contract.md`
- `docs/02-Decisions/adrs/ADR-192-surface-5-adopt-bubbletea.md`
- `docs/02-Decisions/adrs/ADR-195-surface-5-operable-tui-contract.md`
- `docs/02-Decisions/adrs/ADR-197-surface-5-operable-actions.md`
- `docs/06-Daily/reports/surface-5-tui-ui-candidates-2026-05-05.md` (526 lines, 60+ repos auditados)
- `cmd/cos/internal/tui/proof.go` (referenced in ADR-192)

**Referencia externa:** https://github.com/charmbracelet/bubbletea (MIT, 42k stars).

---

## Resumen ejecutivo

| Item | Verdict | Recommended action |
|---|---|---|
| 🔍9 Aider repo-map | EXTERNAL_BETTER (parcial) | Port repo-map as `lib/repo_map.py` (pattern-port, Apache-2.0). Edit-block already covered por `Edit` native. |
| 🔍13 Skill schemas | OURS_BETTER | Keep. Hybridize by adopting the convention `description: "Use when…"` from superpowers in skill-creator. |
| 🔍8 TUI Surface-5 | NOT_COMPARABLE | Closed: ADR-192 adopts Bubble Tea, proof in `cmd/cos/internal/tui/`. Do not reopen. |

**Confidence:** alta in 🔍8 (concrete ADRs), alta in 🔍13 (direct schema diff), media-alta in 🔍9 (repo-map docs covered, edit-block only described superficially via web).

**Flagged gaps:** none for TUI (research closed). The only actionable work es repo-map port — candidate a `/sdd-new repo-map-context-selector`.
