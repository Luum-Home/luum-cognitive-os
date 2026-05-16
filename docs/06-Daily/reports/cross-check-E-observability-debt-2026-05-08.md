# Cross-check Part E: Observability + Claims Debt (2026-05-08)

> Phase: reconstruction. Brutal mode. Each verdict cites a concrete path/grep.

## 🔍11 Phoenix vs Langfuse vs MLflow

**Verdict:** RESOLVED AND PARTIALLY IMPLEMENTED. The decision is not MLflow-vs-Phoenix; it is **MLflow + Phoenix coexist**, with separate roles, and Langfuse deprecated.

**Documented decision:**
- ADR primario: **ADR-058** (`docs/02-Decisions/adrs/ADR-058-observability-migration-langfuse-to-phoenix.md`), fecha 2026-04-24, status **Accepted**.
- ADR-067 NO trata observability — es `ADR-067-frontmatter-defense-in-depth.md` (otro tema). El research mental que sugería ADR-067 era erróneo.
- Eval base: `docs/04-Concepts/architecture/observability-backend-evaluation-2026-04-24.md` con sección §Decision pinneada al final apuntando a ADR-058.

**Roles según ADR-058:**
| Backend | Rol | Estado | Evidencia |
|---|---|---|---|
| JSONL | source of truth local | Core, always-on | `.cognitive-os/metrics/*.jsonl` |
| MLflow | exporter de outcome/cost metrics | DEFAULT (`mode: pip`) | `lib/mlflow_bridge.py` (273L) |
| Phoenix | trace UI LLM-native (OTel) | OPCIONAL (`mode: pip`) | `lib/record_completion.py` L38-47 (`from phoenix.otel import register`); `skills/phoenix-trace-ui/SKILL.md` existe |
| Langfuse | DEPRECATED | Phase 0 done; Phase 2-4 pendientes | Aún 9 hits OTel/phoenix en `record_completion.py`, **0 hits langfuse** → trace sink ya migrado |

**Is the decision correct?**

Pros:
- MLflow para outcome metrics + Phoenix para LLM traces resuelve la objeción legítima ("MLflow no entiende prompts/tools/spans").
- Phoenix es OTel-native → portabilidad a Grafana/Jaeger sin reinstrumentar.
- 1.34 GiB RAM liberados (audit del 2026-04-24 documentado en ADR-058).
- License posture corrected 2026-05-06: ELv2 server (operator-installed) + Apache-2.0 SDK packages. The rule §10 [`license-policy`] BLOCKS ELv2, pero ADR-058 states explicitly que Phoenix es operator-installed runtime (no bundled), which is within del ELv2 allowed scope. **Edge case:** if someone tries to package Phoenix en un release de COS, el license-gate should fire. I did not see a test enforcing it: minor gap.

Cons / riesgos abiertos:
- Phase 3 (remover Langfuse de `docker-compose.cognitive-os.yml`) target 2026-06-15 — pendiente.
- Phase 4 (volume cleanup) target 2026-06-30 — pendiente.
- README aún publicita "Phoenix sólo mencionado" (lo verifiqué: README L64 menciona Phoenix como una de 4 surfaces, sin profundidad). El claim de `docs/09-Quality/manual-tests/proof-paths.md` no fue auditado aquí.

**Recommendation:** KEEP current decision. Phoenix + MLflow is the correct combination. Action: close Phase 3/4 before 2026-06-30 and add a test verifying that the COS bundle does not embed the Phoenix ELv2 server.

---

## DEBT-1 blast-radius advisory vs blocking

**Decision:** INTENTIONAL ADVISORY — not real debt.

**Evidencia (`packages/task-management/hooks/blast-radius.sh`):**
- Comentario L4-5: `Advisory only (exit 0) — does NOT block, but warns for HIGH/CRITICAL`.
- L216: `# Advisory only — always exit 0`.
- L160-171: thresholds **explicitly raised** because "the old rules flagged every doc/test agent as CRITICAL because 'migration' or 'auth' keyword alone triggered it. Noise > signal."
- L192-205: usa `hookSpecificOutput.additionalContext` con `permissionDecision: "allow"` (ADR-023). El propio diseño dice "no quiero bloquear, quiero inyectar contexto al orquestador."
- L144-158: integra con `clarification-gate` via hook-pipe — si ambigüedad ≥ 30, baja umbral HIGH a 20. Este es el mecanismo **correcto** para escalar selectivamente.

**Reason documentada:** estimación por keywords sobre el prompt es heurística — bloquear por heurística generaría falsos positivos masivos. El docs/04-Concepts/root/safety-mesh.md L23 confirma: "Layer 2: blocks: 0 (WARN only)".

**README discrepancy:** README L34 says `blast-radius.sh` "warns before a task touches more than a safe scope" — this is **correct**, not an overclaim. The discrepancy the user suggested ("warns" vs actually blocks) does not exist. The README claim is precise.

**Acción:** MANTENER advisory. Considerar add un modo opt-in `BLAST_RADIUS_BLOCKING=true` para producción si surge demanda, pero NO default. El diseño actual es correcto.

---

## DEBT-2 Tombstone convention

**Estado:** EXISTE convención formal, pero NO se aplicó a squads archivados.

**Convención existente:**
- `skills/adr-tombstone/SKILL.md` define el patrón.
- `scripts/adr_tombstone.py` + `tests/unit/test_adr_tombstone.py` lo implementan (visto en frontmatter de `ADR-085-tombstone.md`).
- 8 ADRs ya usan el patrón: `ADR-003, 004, 005, 043, 046, 085, 214, 229`.
- Frontmatter canónico: `status: tombstone`, `superseded_by: <ADR-X>`, `tier: maintainer`, `tags: [adr, tombstone, governance]`.
- Uso típico (ADR-229): consolidación, slot reservado, no reusable.

**Gap squads archivados:**
- `packages/_archived/squads/` contiene 4 YAML archivados (infra/platform/mobile/payments) + README explicativo del 2026-04-16 (Sprint 2A).
- README cita `docs/04-Concepts/architecture/functional-audit/scorecard-packages-squads-agents.md` como justificación.
- **No ADR tombstone formally records the decision to archive squads.** `grep -ril squad docs/02-Decisions/adrs/` only returns `ADR-075-stage2-selective-expansion.md` (related, not a tombstone).
- The rule §10 [`license-policy`] y los KPIs no fuerzan tombstone para componentes archivados, pero la convención implícita (ver ADR-229) es que **decisiones revertidas/consolidadas → ADR tombstone**.

**It is real debt.** Archiving 4 squads + neutralizing the loader is an architecture decision with public surface (affected `.cognitive-os/squads/` symlinks, health reports, KPIs). It deserves a formal record.

**Acción propuesta:**
1. Crear `docs/02-Decisions/adrs/ADR-NNN-squad-templates-archival.md` (próximo slot disponible) con frontmatter `status: tombstone-of-feature` o `status: superseded` (NO tombstone-of-slot — ese patrón es para ADRs vacíos). Status correcto sugerido: **`status: superseded` con `supersedes: []` y body que tombstonea la *feature*, no el slot ADR**.
2. Alternativa: extender `skills/adr-tombstone/` con un sub-tipo "feature-tombstone" diferente del actual "slot-tombstone".
3. El README de `packages/_archived/squads/` debe linkear al nuevo ADR.

---

## Auditoría de claims README/AGENTS.md

> No existe `CLAUDE.md` raíz en este repo (verificado: `ls CLAUDE.md` → no such file). El equivalente es `AGENTS.md` + `rules/RULES-COMPACT.md`. Auditados ambos.

| # | Claim | Status | Evidencia | Acción |
|---|---|---|---|---|
| 1 | "14-layer safety mesh" (README L26, docs/04-Concepts/root/safety-mesh.md) | **VERIFIED** | `docs/04-Concepts/root/safety-mesh.md` enumera las 14 capas con hook + exit code. 11 son hooks PreTool/PostTool, 3 son library/conditional. Todos los hooks citados existen: `clarification-gate.sh`, `blast-radius.sh`, `dry-run-preview.sh`, `rate-limiter.sh` (`hooks/rate-limiter.sh`), `scope-proportionality.sh`, `claim-validator.sh`, `assumption-tracker.sh`, `trust-score-validator.sh`, `confidence-gate.sh`, `clarification-interceptor.sh`, `auto-rollback-trigger.sh`. Libraries: `lib/cross_verifier.py`, `reinvention-check.sh`, `lib/memory_scanner.py`. README es honesto al desglosar 11+3. | Keep. |
| 2 | "claim-validator.sh blocks agents that report test results without running tests (Layer 6, blocks in production mode)" | **VERIFIED** | Hook exists en `hooks/claim-validator.sh` y `packages/quality-gates/hooks/claim-validator.sh`. Bloqueo condicional al modo producción is alineado con el patrón advisory-vs-blocking del resto. | Keep. |
| 3 | "auto-rollback reverts on retry exhaustion (Layer 11)" | **VERIFIED** | `hooks/auto-rollback-trigger.sh` existe; safety-mesh L11 "exit 2 + revert"; rule §6 [`auto-rollback`] hook-enforced. | Keep. |
| 4 | "blast-radius warns before a task touches more than a safe scope" | **VERIFIED** | Ver DEBT-1. Advisory consciente, no overclaim. | Keep. |
| 5 | "trust-score-validator requires a scored Trust Report with evidence" (Layer 8) | **PARTIAL** | Hook exists (`hooks/trust-score-validator.sh`). BUT safety-mesh L8 says exit code "0 (LOG only)" — that is, does NOT block, only logs. README L37 dice "requires" which suggests enforcement; in reality es advisory en el hook actual. The rule §3 [`trust-score`] dice "mandatory" pero I do not see blocking enforcement in code. | Soften language a "logs and surfaces missing Trust Reports" or document where effective blocking occurs. |
| 6 | "rate-limiter caps tool calls, agent spawns, and hourly spend" (Layer 4) | **VERIFIED** | Existen 5 archivos: `rate-limiter.sh`, `rate-limit-detector.sh`, `rate-limit-drain.sh`, `rate-limit-precheck.sh`, `rate-limit-protection.sh`. Cobertura amplia coincide con el claim. | Keep. |
| 7 | "Phoenix traces, Engram Cloud memory, Obsidian/markdown reader" como 4 surfaces operator-facing (README L62-64, ADR-172) | **PARTIAL** | Phoenix: lib/record_completion.py L38 lo importa; skill `phoenix-trace-ui` existe. Engram: tools `mcp__plugin_engram_engram__*` activos. Obsidian: NO verifiqué binding concreto en este audit — claim no cubierto. ADR-172 referenciado existe (no leí). | Verificar surface Obsidian en otro pase. |
| 8 | "Cognitive OS maps to a traditional OS: kernel, scheduler, memory, drivers, syscalls, networking, MAPE-K" (README L124-127) | **PARTIAL/ASPIRATIONAL** | Mapping is metaphor. `cognitive-os.yaml` (65KB) is kernel-config. Engram is memoria. Hooks sí son scheduler. BUT "MAPE-K-inspired loop" — el README mismo dice "advisory self-healing patterns... not autonomous production mutation". Rule §10 lists [`singularity`] como "MAPE-K(inactive)". The architecture claim is real as design; the live implementation is partial. README already labels this correctly con la nota "(MAPE-K-inspired loop, not autonomous production mutation)". | Keep — el README ya califica el claim. |
| 9 | "self-improvement / self-healing... propose-only and human-gated" (README L172-174) | **VERIFIED as an honest caveat** | El README EXPLICITLY dice "autonomous production mutation is not claimed". This is NOT an overclaim; it is deliberate underclaiming. Rule §10 [`singularity`] confirma `(inactive)`. | Keep. It is an example of an honest claim. |
| 10 | "REAL/DORMANT/ASPIRATIONAL feature status legend" (README L166-174) | **VERIFIED** | `scripts/aspirational_audit.py` existe (referenciado en RULES-COMPACT). Skill `component-reality-check` listsdo. Doc `docs/09-Quality/legal/h1-feature-status-audit.md` referenciado (no leí en este pase). Rule §"Change Safety" cita el patrón. | Keep. Es auto-auditoría sana. |
| 11 | "Squads y teams son experimental layers, not the adoption path" (README L57-58) | **VERIFIED + reconociendo gap DEBT-2** | `packages/_archived/squads/README.md` confirma "0% runtime integration, no loader, no parser." `squads/organization.yaml` se mantiene como template. README es honesto. | Cerrar con ADR tombstone (DEBT-2). |
| 12 | "FSL-1.1-MIT" license badge (README L8) | **VERIFIED** | `LICENSE` archivo presente; rule §10 license-policy bloquea AGPL/SSPL/BSL pero permite FSL/MIT. Coherente. | Keep. |
| 13 | "11 that fire as hooks PreTool/PostTool, 3 son library/conditional" (README L26) | **VERIFIED** | safety-mesh L1-L11 has Type=PreToolUse/PostToolUse; L12, L14 Type=Library; L13 PostToolUse. **Minor discrepancy:** L13 (`reinvention-check.sh`) es PostToolUse per the doc, no library. Correct count should be **12 hooks + 2 libraries**, no 11+3. | Correct README L26 a "12 fire as PreTool/PostTool hooks, 2 are library calls". |

---

## Resumen ejecutivo

- **Observability:** Phoenix+MLflow decision (ADR-058) is correct, NOT ADR-067. Migration is in Phase 0/1/2; Phase 3-4 pending for 2026-06-30. Trace sink is already zero-Langfuse in `lib/record_completion.py`.
- **DEBT-1 (blast-radius):** false alarm. Advisory is an intentional and well documented in-code decision. Keep.
- **DEBT-2 (tombstone squads):** debt real. Existe convención (8 ADR-tombstones precedentes), no se aplicó a `packages/_archived/squads/`. Crear ADR formal.
- **Claims README/AGENTS:** 8 VERIFIED, 3 PARTIAL, 0 pure ASPIRATIONAL, 1 trivial numeric correction (11+3 → 12+2). README is notably honest: it already qualifies MAPE-K como "inspired/not autonomous" y lists REAL/DORMANT/ASPIRATIONAL legend. **Only overclaim:** Trust Report "requires" suggests blocking where the current hook only logs (Layer 8, exit 0).
- **Acciones priorizadas:**
  1. Crear ADR tombstone para squad archival (DEBT-2).
  2. Correct conteo 11+3 → 12+2 en README L26.
  3. Suavizar claim de Trust Report "requires" o add enforcement bloqueante donde el README lo promete.
  4. Cerrar ADR-058 Phase 3 (remover langfuse de docker-compose) antes de 2026-06-15.
