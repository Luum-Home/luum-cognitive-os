# Cross-check Part D: Codegen, Skills, TUI (2026-05-08)

Working dir: `luum-agent-os` (repo root)
Phase: reconstruction. Blast radius: 0 (research-only).

---

## 🔍9 Aider edit-block + repo-map (Apache-2.0)

**Veredicto:** **MEJOR_EXTERNO (parcial) — repo-map vale portar como pattern.**

### Aider unique value
- **Repo-map**: graph-ranking algorithm sobre dependency graph (nodos=archivos, edges=imports/calls) que extrae "most important classes/functions with type signatures" dentro de un **token budget configurable** (`--map-tokens`, default 1k). Tree-sitter para extracción simbólica selectiva — filtra ruido que grep no filtra.
- **Edit-block diff format**: SEARCH/REPLACE bloques (formato `<<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE`) que el LLM emite como diff aplicable. Claude Code ya tiene `Edit` nativo que cubre esto — **NO_COMPARABLE** en ese eje (paridad funcional).

### Nuestro equivalente
- `lib/context_diet.py` — selección **por task_type** (implementation/review/debug/etc.) con allowlist estática de rules. Token estimation char/4. **No usa graph ranking ni dependency graph.**
- `lib/context_budget.py`, `lib/context_budget_monitor.py`, `lib/context_compressor.py`, `lib/context_estimator.py` — budget enforcement y compresión, pero ninguno hace **ranking por importancia simbólica**.
- `lib/context_optimization` — no existe como módulo separado (sólo aparece como rule key `[context-optimization]` en RULES-COMPACT §9).

### Gap real
| Eje | Aider | Nuestro |
|---|---|---|
| Selección de archivos | Graph rank por dependencias | Allowlist por task_type |
| Símbolos | Tree-sitter, top-N por uso | N/A |
| Token budget dinámico | Sí (`--map-tokens`) | Sí (`context_budget.py`) |
| Edit application | SEARCH/REPLACE blocks | Native `Edit` tool |

### ¿Vale portar repo-map?
**Sí, como `lib/repo_map.py`** — pattern-only port (Apache-2.0 permite hasta copy-code). Valor concreto: cuando un sub-agente recibe el prompt SDD, en vez de leer rules estáticas + grep ad-hoc, recibiría un mapa simbólico priorizado del subgrafo relevante. Reduciría context waste en `sdd-apply` sobre repos grandes (luum-agent-os ya tiene >500 archivos Python).

**Trabajo estimado:** medium — necesita tree-sitter (Python ya tiene `tree_sitter_languages`), graph builder, ranker (PageRank-style). 2-3 días para MVP.

**Referencia externa:** https://aider.chat/docs/repomap.html · https://github.com/Aider-AI/aider (Apache-2.0).

---

## 🔍13 Skill schemas: obra/superpowers vs nuestro

**Veredicto:** **MEJOR_NUESTRO** (significativamente). Schema superpowers es minimalista por diseño cross-agent; el nuestro modela governance.

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
| `prerequisites` | — | lista |
| `inputs`/`outputs` | — | estructurados (sdd-explore) |
| `routing_patterns` | — | regex + confidence (skill_router) |
| `routing` (LLM) | — | tier/providers/budget_max_usd (ADR-049) |
| `user-invocable` | — | bool |
| `auto-generated` | — | bool |
| `last-updated` | — | fecha |
| `license` | — | MIT/etc. |
| `context info` | — | author/pattern/inspired-by |
| `<!-- SCOPE: both -->` | — | pre-frontmatter scope marker (os/project/both) |

### Análisis
- **Superpowers schema = mínimo viable cross-agent** (sólo `name` + `description`). Spec deferida a agentskills.io. Gana en portabilidad, pierde en governance.
- **Nuestro schema = governance-rich**: model routing (effort+routing.tier), cost ceiling (budget_max_usd_per_call), pattern-based invocation (regex+confidence), ADR provenance, scope discrimination. Atado a Claude Code pero con `platforms` explícito = upgrade path.
- "455 SKILL.md vs 90" es métrica de cantidad, no de schema. Nuestras 90 son densas (governance, model directives, routing); muchas de las 455 de everything-claude-code son mirrors de Anthropic specs.

### ¿Migrar / mantener / hibridizar?
**Hibridizar (low-cost):** mantener schema actual + adoptar la convención `description: "Use when…"` de superpowers. El "Use when" pattern mejora **trigger discoverability** del skill_router porque alinea descripción con condiciones de invocación. Cambio mecánico: actualizar `skill-creator` para forzar prefijo "Use when" en `description`. No tocar las 90 existentes en bulk — sólo nuevas y refresh natural.

**Referencia externa:** https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md · agentskills.io/specification.

**Archivos consultados:**
- `skills/code-review/SKILL.md` (rich governance schema, GGA-inspired)
- `skills/sdd-explore/SKILL.md` (inputs/outputs + routing.tier=frontier)
- `skills/CATALOG-COMPACT.md` / `skills/REGISTRY.lock`

---

## 🔍8 TUI substrate SURFACE-5

**Veredicto:** **NO_COMPARABLE — research está cerrado, decisión tomada (Bubble Tea), proof shipped.**

### Estado de ADR-187 / ADR-192
ADR-187 (`ADR-187-surface-5-adoption-proof-contract.md`) **estableció el proof contract** y ADR-192 (`ADR-192-surface-5-adopt-bubbletea.md`, status=Accepted 2026-05-06) **resolvió la decisión: adoptar Bubble Tea**. Cadena completa:

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

### ¿Por qué NO Textual / ratatui / huh / gum?
- **Textual (Python)**: descartado en proof — más pesado, startup time, no aprovecha la inversión Go existente. Habría sido válido si COS fuera Python-only, pero ya hay Go.
- **ratatui (Rust)**: añadiría tercer lenguaje al toolchain (Python+Go+Rust). Sin pre-existing Rust surface.
- **huh** y **gum**: son **componentes** sobre Bubble Tea (formularios y shell-scriptables), no substratos. Complementarios, no alternativos.
- **bubbletea** ganó por ya-vendored + Go-native + composabilidad con `cmd/cos`.

### Razón fundamental
La premisa "cero imports TUI, todo bash" del audit es **outdated**: el proof slice Go ya importa Bubble Tea (`cmd/cos/internal/tui/proof.go`). El bash `scripts/cos-tui` se mantiene como bridge legacy mientras Surface 5 nace en Go. **No hay gap abierto.**

**Archivos consultados:**
- `docs/adrs/ADR-187-surface-5-adoption-proof-contract.md`
- `docs/adrs/ADR-192-surface-5-adopt-bubbletea.md`
- `docs/adrs/ADR-195-surface-5-operable-tui-contract.md`
- `docs/adrs/ADR-197-surface-5-operable-actions.md`
- `docs/reports/surface-5-tui-ui-candidates-2026-05-05.md` (526 líneas, 60+ repos auditados)
- `cmd/cos/internal/tui/proof.go` (referenciado en ADR-192)

**Referencia externa:** https://github.com/charmbracelet/bubbletea (MIT, 42k stars).

---

## Resumen ejecutivo

| Item | Veredicto | Acción recomendada |
|---|---|---|
| 🔍9 Aider repo-map | MEJOR_EXTERNO (parcial) | Portar repo-map como `lib/repo_map.py` (pattern-port, Apache-2.0). Edit-block ya cubierto por `Edit` nativo. |
| 🔍13 Skill schemas | MEJOR_NUESTRO | Mantener. Hibridizar adoptando convención `description: "Use when…"` de superpowers en skill-creator. |
| 🔍8 TUI Surface-5 | NO_COMPARABLE | Cerrado: ADR-192 adopta Bubble Tea, proof en `cmd/cos/internal/tui/`. No reabrir. |

**Confianza:** alta en 🔍8 (ADRs concretos), alta en 🔍13 (schema diff directo), media-alta en 🔍9 (repo-map docs cubiertos, edit-block sólo descrito superficialmente vía web).

**Gaps flagueados:** ninguno respecto a TUI (research cerrado). El único trabajo accionable es repo-map port — candidato a `/sdd-new repo-map-context-selector`.
