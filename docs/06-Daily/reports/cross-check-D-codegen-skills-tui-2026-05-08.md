# Cross-check Part D: Codegen, Skills, TUI (2026-05-08)

Working dir: `luum-agent-os` (repo root)
Phase: reconstruction. Blast radius: 0 (research-only).

---

## 🔍9 Aider edit-block + repo-map (Apache-2.0)

**Veredicto:** **MEJOR_EXTERNO (parcial) — repo-map vale portar como pattern.**

### Aider unique value
- **Repo-map**: graph-ranking algorithm sobre dependency graph (nodos=archivos, edges=imports/calls) que extrae "most important classes/functions with type signatures" dentro de un **token budget configurable** (`--map-tokens`, default 1k). Tree-sitter para extracción simbólica selectiva — filtra ruido que grep no filtra.
- **Edit-block diff format**: SEARCH/REPLACE blocks (format `<<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE`) that the LLM emits as an applicable diff. Claude Code already has native `Edit` that covers this — **NO_COMPARABLE** on that axis (functional parity).

### Nuestro equivalente
- `lib/context_diet.py` — selección **por task_type** (implementation/review/debug/etc.) con allowlist istica de rules. Token estimation char/4. **No usa graph ranking ni dependency graph.**
- `lib/context_budget.py`, `lib/context_budget_monitor.py`, `lib/context_compressor.py`, `lib/context_estimator.py` — budget enforcement y compresión, pero ninguno hace **ranking por importancia simbólica**.
- `lib/context_optimization` — no existe como módulo separado (sólo aparece como rule key `[context-optimization]` en RULES-COMPACT §9).

### Gap real
| Eje | Aider | Nuestro |
|---|---|---|
| Selección de archivos | Graph rank por dependencias | Allowlist por task_type |
| Símbolos | Tree-sitter, top-N por uso | N/A |
| Token budget dinámico | Sí (`--map-tokens`) | Sí (`context_budget.py`) |
| Edit application | SEARCH/REPLACE blocks | Native `Edit` tool |

### Is repo-map worth porting?
**Sí, como `lib/repo_map.py`** — pattern-only port (Apache-2.0 permite hasta copy-code). Valor concreto: cuando un sub-agente recibe el prompt SDD, en vez de leer rules isticas + grep ad-hoc, recibiría un mapa simbólico priorizado del subgrafo relevante. Reduciría context waste en `sdd-apply` sobre repos grandes (luum-agent-os ya tiene >500 archivos Python).

**Trabajo estimado:** medium — necesita tree-sitter (Python ya tiene `tree_sitter_languages`), graph builder, ranker (PageRank-style). 2-3 días para MVP.

**Referencia externa:** https://aider.chat/docs/repomap.html · https://github.com/Aider-AI/aider (Apache-2.0).

---

## 🔍13 Skill schemas: obra/superpowers vs nuestro

**Veredicto:** **MEJOR_NUESTRO** (significativamente). Schema superpowers es minimalists por diseño cross-agent; el nuestro modela governance.

### Comparación de schema

| Campo | obra/superpowers | luum-agent-os |
|---|---|---|
| `name` | required (kebab) | required (kebab) |
| `description` | required, "Use when…", ≤1024 chars | required (multilínea OK) |
| `command` | — | opcional (`/sdd-explore`) |
| `trigger` | — | opcional (texto narrativo) |
| `version` | — | `1.0.0` semver |
| `audience` | — | `project`/`personal` |
| `effort` | — | `opus`/`sonnet`/`haiku` (model routing) |
| `summary_line` | — | one-line preview |
| `platforms` | implícito (cross-agent) | `["claude-code"]` explícito |
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
- **Superpowers schema = mínimo viable cross-agent** (sólo `name` + `description`). Spec deferida a agentskills.io. Gana en portabilidad, pierde en governance.
- **Nuestro schema = governance-rich**: model routing (effort+routing.tier), cost ceiling (budget_max_usd_per_call), pattern-based invocation (regex+confidence), ADR provenance, scope discrimination. Atado a Claude Code pero con `platforms` explícito = upgrade path.
- "455 SKILL.md vs 90" es métrica de cantidad, no de schema. Nuestras 90 son densas (governance, model directives, routing); muchas de las 455 de everything-claude-code son mirrors de Anthropic specs.

### Migrate / maintain / hybridize?
**Hybridize (low-cost):** keep current schema + adopt the convention `description: "Use when…"` de superpowers. The "Use when" pattern improves **trigger discoverability** del skill_router because it aligns description with invocation conditions. Mechanical change: update `skill-creator` to force prefix "Use when" en `description`. Do not touch the 90 existing ones in bulk; only new ones and natural refresh.

**Referencia externa:** https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md · agentskills.io/specification.

**Archivos consultados:**
- `skills/code-review/SKILL.md` (rich governance schema, GGA-inspired)
- `skills/sdd-explore/SKILL.md` (inputs/outputs + routing.tier=frontier)
- `skills/CATALOG-COMPACT.md` / `skills/REGISTRY.lock`

---

## 🔍8 TUI substrate SURFACE-5

**Verdict:** **NO_COMPARABLE — research is closed, decision made (Bubble Tea), proof shipped.**

### Estado de ADR-187 / ADR-192
ADR-187 (`ADR-187-surface-5-adoption-proof-contract.md`) **established the proof contract** y ADR-192 (`ADR-192-surface-5-adopt-bubbletea.md`, status=Accepted 2026-05-06) **resolved the decision: adopt Bubble Tea**. Complete chain:

1. ADR-172 — Multi-Surface UI Architecture (deja Surface 5 abierto)
2. ADR-173 — Surface 5 Research Gate
3. ADR-187 — Adoption Proof Contract (7 evidence rows: source compat, license, runtime boundary, operator value, reversibility, failure mode, testability)
4. **ADR-192 — Adopt Bubble Tea** (proof shipped en `cmd/cos/internal/tui/proof.go` + `proof_test.go`)
5. ADR-195 — Operable TUI Contract
6. ADR-197 — Operable Actions

### Recomendación de framework
**Bubble Tea (Go)** — ya adoptado, ya vendored en `cmd/cos/go.mod`, proof slice compilando. Razones documentadas en ADR-192 + report `surface-5-tui-ui-candidates-2026-05-05.md`:
- COS ya tiene módulos Go (`cmd/cos`, `cmd/cos-test` per ADR-131) — composición natural.
- MIT (vs Charm crush FSL-1.1-MIT bloqueado por ~2 años).
- Battle-tested (lazygit, k9s, gh-dash, soft-serve).
- Elm-architecture (Model/Update/View) mapea limpio a lifecycle states COS como fields y transiciones como messages.
- Bubbles + Lipgloss completan stack (table, viewport, list, styling).

### Why NOT Textual / ratatui / huh / gum?
- **Textual (Python)**: discarded in proof — heavier, startup time, does not leverage the existing Go investment. It would have been valid if COS were Python-only, but Go already exists.
- **ratatui (Rust)**: añadiría tercer lenguaje al toolchain (Python+Go+Rust). Sin pre-existing Rust surface.
- **huh** y **gum**: son **componentes** sobre Bubble Tea (formularios y shell-scriptables), no substratos. Complementarios, no alternativos.
- **bubbletea** ganó por ya-vendored + Go-native + composabilidad con `cmd/cos`.

### Reason fundamental
La premisa "cero imports TUI, todo bash" del audit es **outdated**: el proof slice Go ya importa Bubble Tea (`cmd/cos/internal/tui/proof.go`). El bash `scripts/cos-tui` se mantiene como bridge legacy mientras Surface 5 nace en Go. **No hay gap abierto.**

**Archivos consultados:**
- `docs/02-Decisions/adrs/ADR-187-surface-5-adoption-proof-contract.md`
- `docs/02-Decisions/adrs/ADR-192-surface-5-adopt-bubbletea.md`
- `docs/02-Decisions/adrs/ADR-195-surface-5-operable-tui-contract.md`
- `docs/02-Decisions/adrs/ADR-197-surface-5-operable-actions.md`
- `docs/06-Daily/reports/surface-5-tui-ui-candidates-2026-05-05.md` (526 líneas, 60+ repos auditados)
- `cmd/cos/internal/tui/proof.go` (referenciado en ADR-192)

**Referencia externa:** https://github.com/charmbracelet/bubbletea (MIT, 42k stars).

---

## Resumen ejecutivo

| Item | Veredicto | Acción recomendada |
|---|---|---|
| 🔍9 Aider repo-map | MEJOR_EXTERNO (parcial) | Portar repo-map como `lib/repo_map.py` (pattern-port, Apache-2.0). Edit-block ya cubierto por `Edit` nativo. |
| 🔍13 Skill schemas | MEJOR_NUESTRO | Keep. Hibridizar adoptando convención `description: "Use when…"` de superpowers en skill-creator. |
| 🔍8 TUI Surface-5 | NO_COMPARABLE | Cerrado: ADR-192 adopta Bubble Tea, proof en `cmd/cos/internal/tui/`. No reabrir. |

**Confianza:** alta en 🔍8 (ADRs concretos), alta en 🔍13 (schema diff directo), media-alta en 🔍9 (repo-map docs cubiertos, edit-block sólo descrito superficialmente via web).

**Gaps flagueados:** ninguno respecto a TUI (research cerrado). El unique trabajo accionable es repo-map port — candidato a `/sdd-new repo-map-context-selector`.
