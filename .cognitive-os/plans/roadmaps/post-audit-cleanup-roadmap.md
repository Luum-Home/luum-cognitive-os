# Post-Audit Cleanup Roadmap

> Generated 2026-05-18 after multi-agent audit of pending checkboxes, ADR
> partials, plans, and SDD state. Baseline observed:
> ~300 plan-checkboxes pending + 125 ADRs partial + 90-item backlog.
> Audit verified against code, not against markdown declarations.

## Already shipped in this session

- [x] `feat(cos-status): expose per-distribution primitive counts` (verified: git log -1 e90981ed)
- [x] `docs(plans): reconcile 8 op-stability checkboxes` (verified: git log -1 702dd977)
- [x] Wave 0 in flight (background agents): claim ledger merge (A), `lib/stash_ops.py` (B). Verified 2026-05-20: `lib/task_claim_ledger.py` is a compatibility shim over `scripts/cos_task_claims.py` (commit 0bbd0980), `lib/stash_ops.py` exists as a symlink to `packages/agent-coordination/lib/stash_ops.py` with tests in `tests/unit/test_stash_ops.py` (commit 5dac1a33).

## Wave 0 — In flight (do not relaunch)

| Item | Status |
|---|---|
| Unify `lib/task_claim_ledger.py` + `scripts/cos_task_claims.py` | done — `lib/task_claim_ledger.py` delegates to canonical `scripts/cos_task_claims.py` store (0bbd0980) |
| Create `lib/stash_ops.py` covering ADR-117 invariants 3/4/1 | done — symlinked package implementation plus `tests/unit/test_stash_ops.py` (5dac1a33) |

Wave 0 returned and was verified from git/code evidence on 2026-05-20; proceed to Wave 1.

## Wave 1 — Quick wins (~3-4 sessions, low risk)

Cierra 4 planes con poco trabajo restante. Bajo riesgo. Ningún diseño nuevo.

| # | Task | Plan / ADR | Effort | Notes |
|---|---|---|---|---|
| 1.1 | Scheduled propose-only runner | headless-self-improvement-proposer (19/23 → 23/23) | 1 sesión | Gated en ADR-201 PromoteFromTelemetry. Verificar primero. |
| 1.2 | `/install-skill` + `/install-hook` skills | so-existential-validation Phase 3 | 1 sesión | Crear 2 archivos en `.claude/skills/`. |
| 1.3 | Migrar `hooks/secret-detector.sh` a `updatedInput` | stabilization-roadmap Gap 2 | 0.5 sesión | Cambia exit-2 → mutar tool_input. |
| 1.4 | Migrar 3 hooks a native `additionalContext` | stabilization-roadmap Gap 3 | 0.5 sesión | `inject-phase-context.sh`, `context-diet.sh`, `subagent-context-injector.sh`. |
| 1.5 | External Review Readiness: 8 items restantes (10/18 → 18/18) | external-review-readiness-plan | 1 sesión | Lean/Core surface trim + scenario list automation + 5-min proof script. |
| 1.6 | Marcar checkboxes drift en 9 planes reconciliados | reconciliador output (67 items) | 1 sesión | Aplicar las marcas que tienen evidencia clara, archivar 2 planes (`headless-self-improvement-proposer`, `runtime-comparison-benchmark`). |

**Output esperado**: 4 planes archivados, ~75 checkboxes marcados, 4 hooks migrados, 2 skills nuevos. Reducción de "ruido aparente" del ~40%.

## Wave 2 — ADR-278 dedicated (1 sesión)

Un solo agente focused. Mecánico pero alto impacto.

- 984 `subprocess.run()` calls sin timeout → agregar `timeout=N` por call
- Usar `manifests/subprocess-timeout-allowlist.yaml` para excepciones reales
- Cierra ~8.5k findings del control-plane de un solo saque
- Tests: `tests/audit/test_subprocess_timeout.py` confirma cobertura

**Riesgo**: medio. Algunos timeouts pueden ser legítimamente largos. Tener fallback de allowlist.

## Wave 3 — Human decisions (sin agentes)

Sentarse 30 min, decidir, aplicar.

| # | Decisión | Contexto |
|---|---|---|
| 3.1 | **ADR-275**: ¿activar staged hooks o seguir en stage? | Slice A completo, hook wiring listo en `docs/05-Methodology/runbooks/adr-275-session-start-hook-staging`. |
| 3.2 | **ADR-008**: ¿cerrar como "policy accepted" o partial permanente? | Política multi-tool no es una feature cerrable. |
| 3.3 | **multilingual-corpus-expansion**: ¿`/sdd-continue` o congelar? | Solo proposal. 5h estimadas si se activa. |
| 3.4 | **dormant ratio threshold** (so-existential Phase 1) | Está en ~0.35, target 0.25. Requiere DELETIONS reales de primitives ASPIRATIONAL. ¿Qué archivar? |
| 3.5 | **5 ADRs cerrables (179, 252, 013, 015, 322)** | Cerrar con `scripts/cos-adr-close` o seguir partial. |

## Wave 4 — Medium plans casi terminados (~4-5 sesiones)

Cada plan tiene <20 items restantes, no requiere diseño nuevo.

| # | Plan | Progreso actual | Items restantes | Effort |
|---|---|---|---|---|
| 4.1 | ADR-200+ Closure | 24/32 | 8 | 1-2 sesiones |
| 4.2 | Maintainer Telemetry Loop | 23/40 | 17 (varios doc-sync) | 2 sesiones |
| 4.3 | Hook Architecture v2 | 22/36 | 14 (mayoría doc-sync, código existe) | 1 sesión |

## Wave 5 — Big plans (multi-week)

NO atacar sin operator sign-off explícito. Diseño-heavy o blast-radius alto.

| Plan | Phases abiertas | Effort estimado |
|---|---|---|
| **ADR-121 Foundation Hardening** | phases 2-6 (single-writer, WIP ownership, guard maturity, chaos N=10/20/50) | Multi-semana, ~10 sesiones |
| **ADR-325 Cost Governance** | Phases 2-5 (taximeter, ingestion, anti-loop, language token economy) | 3-5 sesiones |
| **ADR-291** | Phase 2: 23 endpoints en 501 → implementar | 4-5 sesiones |
| **Operational Stability** | Phases 2,3,7,8 (guard maturity metadata, adaptive profiles, distribution boundary, productization) | 4-5 sesiones |
| **DX Tax Reduction** | 23 items (después de Wave 1 closing C, queda mucho) | 3-4 sesiones |
| **Governance Tools Consolidation** | 5 items net-new (después de archive trial decision) | 2-3 sesiones |
| **ADR-319/324** | Hook obligatorio para EAS en review surfaces | 1-2 sesiones, requiere diseño |

## Wave 6 — Sequential ADR backlog (036→041)

Estos están en `.cognitive-os/pending-tasks/`. Dependientes entre sí.

```
ADR-036 (sprint orchestration primitives) ← Foundation, ningún dep
  ↓
ADR-037 (self-knowledge base) ← needs 036 events
  ↓
ADR-040 (query-tailored context injection) ← needs 037 + 039
ADR-039 (reinvention phase B-β embeddings) ← independent (~1h deps install)
ADR-038 (preamble v2 industry-aligned) ← 4 waves, ~8h
ADR-041 (exercised coverage pipeline) ← independent, MVP 2h
```

**Order recomendado**: 036 → 037 → 039 || 041 || 038 → 040. Total ~8-12 sesiones.

## Wave 7 — Cleanup zombies (no implementation)

| # | Acción |
|---|---|
| 7.1 | Borrar sprint demo `sprint-b37c1353.json` |
| 7.2 | Purgar 7 active-tasks `cancelled-stale` de `active-tasks.json` |
| 7.3 | Truncar `work-queue.jsonl` (últimas entradas son ruido `unknown_tool`) |
| 7.4 | Archivar `handoffs/unknown.jsonl` + improvements del 2026-05-03 |
| 7.5 | Tombstonear formalmente `agent-escalation-capabilities` y `workflow-engine` con ADR-tombstone slot |

## Cost estimate (mix opus/sonnet/haiku)

| Wave | Sesiones | Cost rango |
|---|---|---|
| Wave 0 (in flight) | 2 | $5-15 |
| Wave 1 | 4 | $15-40 |
| Wave 2 | 1 | $10-25 |
| Wave 3 | 0 (decisiones) | $0 |
| Wave 4 | 5 | $20-50 |
| Wave 5 | 25+ | $100-300 |
| Wave 6 | 10 | $40-100 |
| Wave 7 | 1 | $3-8 |
| **Total** | **~48 sesiones** | **~$200-540** |

## Recommended order

1. **Esperar Wave 0** (A y B en vuelo)
2. **Wave 3** (decisiones humanas — 30 min sin agentes, desbloquea Waves siguientes)
3. **Wave 1** (quick wins, 1-2 días)
4. **Wave 7** (cleanup, mismo día)
5. **Wave 2** (ADR-278 batch dedicado)
6. **Wave 4** (medium plans casi terminados)
7. **Wave 6** (ADR 036-041 secuencial)
8. **Wave 5** (big plans, requiere planning explícito y posiblemente SDD per plan)

## End state target

| Métrica | Antes | Después de Waves 1-4+7 | Después de todo |
|---|---|---|---|
| Plan-checkboxes "pendientes" | 300 | ~150 | ~50 |
| ADRs partial | 125 | ~115 | ~95 |
| Backlog items | 90 | ~40 | <20 |
| Planes activos | 21 | ~12 | ~6 |
| Control-plane open findings | 8814 | <500 | <100 |

## Decision log (este roadmap)

- **2026-05-18**: Roadmap creado tras audit consolidado. Pending operator sign-off por wave antes de lanzar agentes.
