---
title: "holaOS Annex C — Auto-Evolution, Skill Governance, Session TODOs"
date: 2026-05-10
annex: C
parent: holaos-comparison-2026-05-10.md
author: research-agent
status: draft
source-repo: "/tmp/holaOS-investigation"
license-classification: "BSL-like / BLOCK for code adoption — pattern-only, clean-room"
scope:
  - evolve loop post-run (skill candidate review + task proposals)
  - skill widening policy (per-run capability grants)
  - session-todo state machine + scratchpad
---

# Annex C — Auto-Evolución, Gobernanza de Skills y TODOs Persistentes

> Continuación de `docs/research/holaos-comparison-2026-05-10.md`. Compara código-a-código tres ejes de holaOS contra superficie equivalente en luum-agent-os. **Sin adopción de código**: clean-room, pattern-only. Estilo TS de holaOS NO debe filtrarse a bash/Python luum.

---

## 0. Inventario de archivos relevantes

### holaOS (fuente — lectura only)

| Path | LOC | Rol |
|---|---:|---|
| `runtime/api-server/src/evolve.ts` | 210 | Job `evolve` (enqueue/process post-run); orquesta writeback de memoria + review de skill candidate + propuesta de tarea |
| `runtime/api-server/src/evolve-worker.ts` | 196 | Worker con claim-lease, retry (max 3, 5s backoff), concurrencia configurable via `HB_EVOLVE_WORKER_CONCURRENCY` |
| `runtime/api-server/src/evolve-skill-review.ts` | 737 | LLM-driven extraction de skill candidate (kind=skill_create|skill_patch), promoción de draft a `skills/<slug>/SKILL.md`, deduplicación, fingerprint sha256 |
| `runtime/api-server/src/evolve-tasks.ts` | 68 | Registry de tasks que corren post-turn (`turn_memory_evolve` default); planificación via `setImmediate` |
| `runtime/harnesses/src/skill-policy.ts` | 162 | `HarnessSkillWideningState`: cada skill declara `grantedTools` + `grantedCommands`; tools/comandos quedan **bloqueados** hasta que la skill se invoca, momento en que se "ensancha" el grant |
| `runtime/harnesses/src/todo-policy.ts` | 1134 | Tool `todowrite` con ops tipadas (`replace`, `add_phase`, `add_task`, `update`, `remove_task`), schema JSON estricto, persistencia versionada en `<workspace>/state/todos/<session>.json` |
| `runtime/api-server/src/session-todo.ts` | (>300) | API server: lectura/escritura del estado todo + migración de paths legados (`.holaboss/todos`, `.holaboss/pi-agent/todos`) |
| `runtime/api-server/src/session-scratchpad.ts` | (>80) | Scratchpad markdown libre por sesión (`<workspace>/state/scratchpads/<session>.md`) con append/replace/clear |

### luum-agent-os (superficie actual)

| Path | Rol |
|---|---|
| `hooks/auto-skill-generator.sh` | PostToolUse hook sobre `Agent`: detecta tareas complejas (≥10 tool uses o ≥8000 chars) y genera SKILL.md draft heurístico (regex `created\|updated\|fixed…`) en `.cognitive-os/skills/auto-generated/<slug>/` |
| `rules/auto-skill-generation.md` | Documenta el ciclo Act/Learn/Reuse, opt-out via `NO_AUTO_SKILL` |
| `rules/self-improvement-protocol.md` | Política `/self-improve` semanal: KPI trigger, blocklist, comparative promotion gate, skill archive |
| `lib/skill_archive.py` + `lib/skill_efficacy.py` + `lib/skill_lifecycle_promoter.py` + `lib/self_improvement.py` | Fitness landscape (snapshot por ejecución), best-of registry, rollback signal |
| `rules/skill-invocation-mandatory.md` (ADR-188) + `hooks/orchestrator-skill-invocation-gate.sh` | Gate: si router sugiere skill con conf≥0.90 hay que invocarla o anotar `SKILL_BYPASS:` |
| `rules/skill-management.md`, `rules/skill-rewrite.md` | Prioridad project>global>auto; promoción gobernada |
| `hooks/work-queue-sync.sh` | PostToolUse para `TodoWrite` + `Agent` → `.cognitive-os/work-queue.jsonl` (event log canónico ADR-033) |
| `skills/resume-tasks/SKILL.md` | Recovery basado en `.claude/tasks/active-tasks.json` (no state machine tipado) |
| `lib/agent_runner.py` (comentario L19) | "No TodoWrite semantics" — el agent loop Qwen NO emite TodoWrite |

---

## 1. Feature 1 — Evolve loop post-run

### 1.1 holaOS — anatomía

**Disparo.** Cada turno completado encola un job `evolve` (idempotency key `evolve:<inputId>`, con migración de claves legacy `reinforce_memory_writeback`/`durable_memory_writeback`):

```ts
// evolve.ts:91-131
export function enqueueEvolveJob(params: { … }): PostRunJobRecord {
  const evolveIdempotencyKey = `${EVOLVE_JOB_TYPE}:${params.inputId}`;
  …
  const record = params.store.enqueuePostRunJob({
    jobType: EVOLVE_JOB_TYPE,
    workspaceId: params.workspaceId,
    sessionId: params.sessionId,
    inputId: params.inputId,
    payload: { instruction: trimmedInstruction(params.instruction) },
    idempotencyKey: evolveIdempotencyKey,
  });
  params.wakeWorker?.();
  return record;
}
```

**Procesado.** `processEvolveJob` (`evolve.ts:133-210`) hace dos cosas:
1. `writeTurnDurableMemory(...)` — pipeline de memoria durable (delegado).
2. `reviewTurnForSkillCandidate(...)` (`evolve-skill-review.ts:524-606`):
   - **Cadencia**: solo cada `SKILL_REVIEW_INTERVAL_TURNS = 3` turnos completados (`shouldReviewSkillsOnTurn`).
   - Requiere `modelClient`; corre un prompt JSON estricto pidiendo `{kind, target_skill_id, title, summary, slug, when_to_use, workflow[], verification[], confidence, evaluation_notes}` (`evolve-skill-review.ts:444-487`).
   - Filtros: `MIN_SKILL_CONFIDENCE = 0.72`, workflow mínimo 2 pasos, deduplicación contra skills resueltos y workspace-owned.
   - Si pasa: `persistSkillCandidate(...)` (L608-655) escribe draft en `workspace/<id>/evolve/skills/<candidateId>/SKILL.md`, calcula `sha256` fingerprint, valida que no haya duplicado activo.
3. **Promotion via task proposal**: si el candidato no está ya promovido/aceptado/propuesto, `createEvolveTaskProposal` genera una `TaskProposalRecord` con `proposalSource: "evolve"` y un prompt human-review explícito ("Review and promote the candidate skill … If you promote it, write the live workspace skill to `skills/<slug>/SKILL.md`"). El estado del candidate pasa a `proposed`. La **promoción real** la hace `promoteAcceptedSkillCandidate` (`evolve-skill-review.ts:657-737`) — solo si el status es `accepted` (decisión humana), copiando draft de memoria a `<workspaceDir>/skills/<slug>/SKILL.md`.

**Worker.** `RuntimeEvolveWorker` (`evolve-worker.ts:50-196`):
- Loop `claim → execute → requeueOrFail`.
- `leaseSeconds=300`, `maxAttempts=3`, `retryDelayMs=5000`, `distinctSessions: true` (evita serializar dos turnos de la misma sesión).
- `processAvailableJobsOnce` también recupera leases expirados (`listExpiredClaimedPostRunJobs`) — patrón ADR-073-style.

**Task registry** (`evolve-tasks.ts`): `turnMemoryEvolveTask` es el único default; el shape `EvolveTask = {name, shouldRun, run}` permite extensiones (writeback adicional, gardening de memoria, etc.). Ejecutado por `setImmediate` para no bloquear el turn loop.

### 1.2 luum — equivalente

| Capa holaOS | luum equivalente | Estado |
|---|---|---|
| Job queue `evolve` | `hooks/auto-skill-generator.sh` (PostToolUse `Agent`) | **Síncrono**, dentro del hook (5s budget) |
| Disparo cada N turnos | Disparo en **cada Agent completion** (no cadencia) | Más ruidoso |
| LLM JSON extraction de skill candidate | Regex shell (`grep -cEi "(created\|wrote\|generated)…"` en `auto-skill-generator.sh:85-91`) | Mucho más débil |
| `MIN_SKILL_CONFIDENCE=0.72` | No hay puntuación; binario sí/no por threshold de tool_uses≥10 ó chars≥8000 | Sin signal de confianza |
| Deduplicación por `sha256(skillMarkdown)` + slug + `activeCandidate` | Solo evita overwrite por mismo slug (append timestamp) | Sin fingerprint |
| Task proposal "Review and promote …" | No existe (no hay tablero de proposals); skill cae directo en `auto-generated/` | **Gap** |
| `accepted → promoted` con copia draft → live | `/optimize-skill <slug>` manual + `lib/skill_lifecycle_promoter.py` + comparative promotion gate (`rules/self-improvement-protocol.md` §"Comparative Promotion Evaluation") | Promoción gobernada existe, pero desconectada del trigger automático |
| Worker async, `leaseSeconds`, retries | `hooks/work-queue-sync.sh` solo emite eventos a JSONL; no hay consumer | Sin worker |

luum tiene **mejor** evaluación post-promoción (skill_archive trend, baseline-vs-candidate fitness en `cos_governed_self_improvement.py`, blocklist) pero **peor** detección automática y peor calidad de draft inicial.

### 1.3 Delta y nuevos workflows

luum carece de:
- **Cadencia de review** (every-N-turns) — actualmente puede generar N skills por sesión, desperdiciando tokens.
- **Skill-patch kind**: holaOS distingue `skill_create` vs `skill_patch` (mejorar skill workspace-owned existente). luum solo crea skills nuevos; las mejoras necesitan `/optimize-skill` manual.
- **Task proposal queue como puente humano**: hoy el flow es "auto-genero → user descubre por casualidad → `/optimize-skill`". holaOS publica un to-do explícito ("Review and promote skill X") que llega al inbox del operador.
- **Fingerprint dedup**: dos sesiones que hacen tareas similares generan dos skills duplicados en luum.

### 1.4 Plan de adopción clean-room

**Archivos NUEVOS (Python, no portar TS):**
1. `lib/evolve_skill_review.py` — extractor LLM (vía `lib/dispatch.py`, providers `qwen,claude`), prompt JSON estricto, normalización slug/confidence (esquema **propio**, no copiar nombres ni el prompt literal de holaOS). Salida: `SkillCandidate` dataclass.
2. `lib/evolve_task_queue.py` — tabla SQLite o JSONL (`.cognitive-os/state/evolve-candidates.jsonl`) con fingerprint sha256, estado `{draft, proposed, accepted, dismissed, promoted}`.
3. `scripts/cos-evolve-tick.py` — entry point invocable desde hook o cron.

**Archivos MODIFICADOS:**
4. `hooks/auto-skill-generator.sh` — reemplazar lógica regex por dispatch a `scripts/cos-evolve-tick.py --turn-input <id>` con **cadencia cada 3 turnos** (contador en `.cognitive-os/runtime/evolve-turn-counter`). Mantener killswitch + `NO_AUTO_SKILL`.
5. `rules/auto-skill-generation.md` — documentar nuevo flow: candidate → proposal → operator review → `lib/skill_lifecycle_promoter.py`.
6. Inbox/orquestador: extender `skills/resume-tasks/` (o crear `skills/evolve-inbox/`) para listar candidates pendientes al inicio de sesión.

**Enganche:**
- **Disparo**: PostToolUse `Agent` (no PostStop, porque holaOS dispara por turn, no por session-end; equivalente claude-code es post-tool).
- **Cron opcional**: si queremos batch nocturno cuando hay muchos turnos acumulados, agregar entrada en `scripts/cron-runner.sh` (precedente: `lib/cron_runner.py`).
- **Skill**: nuevo `/evolve-review` para que el operador vea pending proposals.

**Esfuerzo**: ~600-800 LOC Python + ~80 bash + ~150 docs. **3-4 días** (1 día spec, 1-2 días impl, 1 día tests + integración con skill_lifecycle_promoter).

---

## 2. Feature 2 — Skill Widening Policy

### 2.1 holaOS — anatomía

`skill-policy.ts` modela **least-privilege-by-skill**:

```ts
// skill-policy.ts:1-18
export interface HarnessSkillMetadata {
  skillId: string;
  skillName: string;
  filePath: string;
  baseDir: string;
  grantedTools: string[];    // e.g. ["browser_navigate", "form_input"]
  grantedCommands: string[]; // e.g. ["screenshot"]
}

export interface HarnessSkillWideningState {
  scope: "run";
  managedToolNames: Set<string>;        // tools controlled by skill widening
  grantedToolNames: Set<string>;        // currently active grants
  skillIdsByManagedTool: ReadonlyMap<string, ReadonlySet<string>>;
  managedCommandIds: Set<string>;
  grantedCommandIds: Set<string>;
  skillIdsByManagedCommand: ReadonlyMap<string, ReadonlySet<string>>;
}
```

Flujo:
1. **Pre-skill-invoke**: los tools listados en alguna skill (`createHarnessSkillWideningState` L64-109) están en `managedToolNames` pero NO en `grantedToolNames`. Si el modelo intenta llamar al tool, el harness lo bloquea y devuelve `requiredHarnessSkillIdsForTool` (L111-119) — efectivamente diciendo "para usar `browser_navigate` invocá primero la skill `webapp-testing`".
2. **Skill invocation**: `applyHarnessSkillWideningGrants` (L121-154) mueve los tools/comandos declarados desde managed → granted, *para el resto del run*.
3. **Scope**: `"run"` (no persiste entre sesiones), idempotente, alfabéticamente ordenado para output determinístico.

**Insight clave**: la skill no es solo documentación — es la **llave** que habilita el tool. Reduce drásticamente el blast radius de prompt injection (un agente que no invocó `webapp-testing` no puede tocar `browser_*`).

### 2.2 luum — equivalente

luum tiene una mecánica **conceptualmente similar** pero implementada distinto:

- `rules/skill-invocation-mandatory.md` (ADR-188) + `hooks/orchestrator-skill-invocation-gate.sh`: gate **soft** (WARN→WARN→BLOCK) cuando router sugiere skill ≥0.90 pero el agente lanza work bespoke.
- `.claude/settings.json` permissions: lista plana de tools permitidos por sesión (independiente de skill invocación).
- `lib/skill_routing.py`, `lib/skill_router.py`: detección de mismatch.

**Diferencia fundamental**: en holaOS el harness **bloquea hard** el tool hasta que se invoca la skill que lo "abre"; en luum el gate es **observacional + advisory** y depende de que el orquestador respete la sugerencia.

Tampoco hay un campo `grantedTools: [...]` en el frontmatter YAML de los SKILL.md de luum (revisado `skills/resume-tasks/SKILL.md` L11: `platforms: ["claude-code"]`, `prerequisites: []` — sin tool grants).

### 2.3 Delta y workflows nuevos

luum NO tiene:
- **Tool gating por skill invocation** (least-privilege automático).
- Capacidad de declarar en `SKILL.md` qué tools "ensancha" (analogía a Linux capabilities).
- Estado per-run de grants acumulados, observable.

Adopción habilitaría:
- Reducir matriz de permissions globales en `.claude/settings.json` (hoy las permissions están abiertas y el gate ADR-188 es la única defensa).
- Mejor defense-in-depth contra prompt injection: un attacker que logre que el modelo llame `Bash("rm -rf …")` sin invocar la skill correspondiente sería bloqueado por el harness (no solo audited).
- Auditoría más limpia: log "tool X granted because skill Y invoked at turn Z".

### 2.4 Plan de adopción clean-room

luum corre sobre Claude Code, que **no expone** un primitive de tool-gating dinámico en `.claude/settings.json` (las permissions son estáticas por sesión, no condicionadas a Skill tool calls). Adopción real requeriría:

**Camino A — Wrapper hook:**
1. Frontmatter nuevo en SKILL.md: `widens_tools: [Bash, WebFetch]`, `widens_commands: [gh, kubectl]`.
2. `hooks/skill-widening-gate.sh` PreToolUse: lee estado runtime `.cognitive-os/runtime/skill-widening-<session>.json`. Si tool ∈ managed AND tool ∉ granted → BLOCK con mensaje "Invoke skill <X> first".
3. `hooks/skill-widening-grant.sh` PostToolUse `Skill`: cuando se invoca una skill, parsea su frontmatter y agrega tools/commands a granted-set.
4. `lib/skill_widening.py` — librería que computa managedSet desde escaneo de `skills/**/SKILL.md` + frontmatter parsing (clean-room: nombres propios, no `HarnessSkillWideningState`).

**Camino B — pure-policy:** sin bloqueo hard, solo extender ADR-188 con campo `widens` y subir el contador BLOCK a la primera violación si el tool está marcado como widened-only. Más liviano, menos garantía.

**Recomendación**: Camino A para tools sensibles (Bash, WebFetch, mcp__*) y Camino B (advisory) para el resto.

**Esfuerzo**:
- Camino A: ~400 LOC Python + ~150 bash + tests + migración de frontmatter en ~10 skills críticas. **3 días.**
- Camino B: ~150 LOC + extensión del gate existente. **1 día.**

**Riesgo**: si el frontmatter está mal, una skill recién creada bloquea ejecuciones legítimas → hace falta `COS_DISABLE_SKILL_WIDENING=1` killswitch + test contract.

---

## 3. Feature 3 — Session-TODO State Machine + Scratchpad

### 3.1 holaOS — anatomía

`todo-policy.ts` (1134 LOC) define el **tool `todowrite`** del harness con un schema JSON discriminado por `op`:

```ts
// todo-policy.ts:6-13
export const HARNESS_TODO_STATUSES = [
  "pending", "in_progress", "blocked", "completed", "abandoned",
] as const;
export const HARNESS_TODO_WRITE_OPS = [
  "replace", "add_phase", "add_task", "update", "remove_task",
] as const;
```

Ops (cada una con su rama JSON Schema estricta):
- `replace` — reemplaza todo el árbol phases→tasks (L800-880 aprox).
- `add_phase` — agrega fase con `name` y opcional `tasks[]`.
- `add_task` — agrega task a fase existente (`phase: "phase-2"`).
- `update` — modifica task por `id` (status, content, notes, details). L926-959.
- `remove_task` — borra por id. L960-975.

**Invariantes** (de `normalizeInProgressHarnessTodoTask` L245-270):
- A lo sumo un task con `status="in_progress"` por sesión; si hay >1, los extras se degradan a `pending`.
- Si no hay in_progress y no hay blocked, el primer pending se auto-promueve a in_progress (forward progress automático).

**Persistencia** (`session-todo.ts:8-112`):
- Path: `<workspaceRoot>/<workspaceId>/state/todos/<sessionId>.json`.
- Versionado: `version: 2`, migración desde paths legacy (`.holaboss/todos`, `.holaboss/pi-agent/todos`).
- Sanitización de `sessionId` a segmento de filesystem seguro (regex `[^A-Za-z0-9._-]` → `_`).
- IDs estables: `task-N`, `phase-N`, donde N es monotónico (no UUID).

**Anti-alias warning** (L16-17):
```ts
export const HARNESS_TODO_WRITE_ALIAS_WARNING =
  "Do not invent alias op names such as `replace_all`, `update_task`, or `set_status`.";
```
Excelente defensa contra alucinación de op-names — el modelo se equivoca seguido y el tool devuelve repair hint en lugar de fallar silenciosamente (fallback validation branch L976-1018).

**Scratchpad** (`session-scratchpad.ts:1-80`): markdown libre por sesión con ops `append`/`replace`/`clear`, preview de 280 chars, normalización de line endings. Path `<workspace>/<id>/state/scratchpads/<sessionId>.md`. Complementa todos para notas libres que no encajan en task model.

### 3.2 luum — equivalente

luum **no implementa** un state machine de todos — usa el TodoWrite nativo de Claude Code:

- `hooks/work-queue-sync.sh` solo **observa** TodoWrite y `Agent` PostToolUse, escribe a `.cognitive-os/work-queue.jsonl`. Es event log, no state machine.
- No hay invariantes "máximo un in_progress" en luum (Claude Code los enforce client-side, pero no es introspectable desde hooks).
- `skills/resume-tasks/SKILL.md` lee `.claude/tasks/active-tasks.json` — un blob diferente, sin fases, sin status enum tipado, sin IDs estables.
- `lib/request_queue.py` (mencionado en `~/.claude/CLAUDE.md` global) — orientado a user requests, no a sub-tasks del orquestador.
- `lib/agent_runner.py:19` deja claro: "No TodoWrite semantics" en Qwen agent loop.

Faltan:
- **Persistencia gobernada cross-session** (active-tasks.json existe pero no versionado, sin migración).
- **Fases agrupando tasks** (luum es flat).
- **Schema repair hints**: en luum si el modelo escribe un TodoWrite mal, falla silenciosamente o se trunca; no hay "did you mean `update`?" como en holaOS.
- **Scratchpad markdown per-session** — no existe; los workings notes hoy van a Engram (mem_save) o a `docs/work/*.md` ad-hoc.

### 3.3 Delta y workflows nuevos

Adoptar el patrón habilita:
- **Resume confiable**: hoy `resume-tasks` adivina por `checkCommand`/`expectedOutputs`; con state machine tipado + fases, el resume es determinístico ("phase-2 está en in_progress, retomar tarea task-7").
- **Multi-fase explícita**: SDD pipeline (`/sdd-apply`) genera muchas tareas; sin fases el TodoWrite se vuelve una lista de 30 ítems ilegible. Con phases (`phase-1: design`, `phase-2: implement`, `phase-3: verify`) la UX de operador mejora mucho.
- **Scratchpad markdown**: lugar canónico para notas inter-turno de un mismo agente, separado de Engram (que es para conocimiento durable, no working notes).
- **Anti-aliasing repair hints**: reduce la pérdida de tokens cuando el modelo confunde op-names (problema observado en `tests/integration/test_stash_lock.py` y otros).

### 3.4 Plan de adopción clean-room

**No reemplazar TodoWrite nativo** — Claude Code lo provee y el operador ya tiene mental model. **Sí extender**:

**Archivos NUEVOS:**
1. `lib/session_todo_state.py` — modelo Python con `Phase`, `Task`, status enum `[pending, in_progress, blocked, completed, abandoned]`, invariante "≤1 in_progress" + autoforward.
2. `lib/session_scratchpad.py` — append/replace/clear sobre `.cognitive-os/state/scratchpads/<session_id>.md`.
3. `scripts/cos-session-todo` CLI — wraps lib para Bash/hook consumo.
4. `hooks/session-todo-sync.sh` — PostToolUse `TodoWrite` traduce el TodoWrite plano de Claude Code a `phases` (heurística: prefijos `Phase N:` o tags `[design]`/`[impl]`/`[verify]` en content) y persiste a `.cognitive-os/state/todos/<session>.json`.
5. `skills/scratchpad/SKILL.md` — skill nueva para que el agente escriba working notes durante un turn largo.

**Archivos MODIFICADOS:**
6. `skills/resume-tasks/SKILL.md` — reemplazar lectura de `.claude/tasks/active-tasks.json` por `lib/session_todo_state.load()`.
7. `hooks/work-queue-sync.sh` — agregar emisión de evento `phase_complete` cuando cierra una fase.
8. `rules/RULES-COMPACT.md` — registrar nueva regla `[session-todo-state-machine]`.

**Enganche:**
- PostToolUse `TodoWrite` para sync.
- SessionStart → `resume-tasks` lee state.
- `/sdd-apply` puede leer state para reportar progreso por fase.

**Esfuerzo**: ~500 LOC Python + ~200 bash/docs. **2-3 días.**

**Decisión a tomar con el operador**: ¿persistencia en `.cognitive-os/state/` (project-local) o en Engram (durable cross-machine)? holaOS usa filesystem; luum tiene Engram disponible. Recomiendo **filesystem para state machine** (transaccional, rápido) + **Engram para post-session summary** (consultable cross-session).

---

## 4. Integración con SDD

¿El evolve loop debe generar `sdd-new` changes automáticamente?

**holaOS no lo hace** — su task proposal es human-review-required ("Review and promote …"). El operador decide si aceptar.

**Recomendación para luum**: NO acoplar evolve → sdd-new automático. Razones:
1. El comparative-promotion gate (`rules/self-improvement-protocol.md` §6) ya exige baseline-vs-candidate con `required_delta`; un sdd-new auto-generado eludiría este gate.
2. SDD es para changes substantiales; un skill draft de evolve es ~50 líneas — demasiado liviano para el overhead de explore→propose→spec→design→tasks.
3. Riesgo de cascada: un evolve tick podría disparar 5 sdd-new por sesión, saturando la cola.

**SÍ integrar de estas formas:**
- `/sdd-explore` consulta `lib/evolve_task_queue` para ver candidates pendientes que podrían informar el scope.
- `/sdd-archive` emite señal a evolve queue para revisar si surgió un skill reusable durante el change.
- `sdd-apply` con phases mapeables al state machine de §3 (fase = SDD phase).
- Evolve **patch candidates** (skill_patch) podrían convertirse en sdd-propose si afectan skills core (no auto-generated). Solo el `skill_patch` kind, no `skill_create`.

---

## 5. Riesgos específicos

### 5.1 Auto-evolución que degrada skills

**Riesgo**: el LLM puede proponer un patch que reemplaza un workflow correcto por uno alucinado. Sin gate humano, la siguiente sesión usa una skill rota.

**Cómo lo mitiga holaOS**:
1. `MIN_SKILL_CONFIDENCE = 0.72` filtra candidatos débiles.
2. Cadencia (cada 3 turnos) reduce frecuencia.
3. **Promoción requiere status `accepted` por humano** (`promoteAcceptedSkillCandidate` chequea `candidate.status !== "accepted"` → `not_ready`).
4. Draft vive en `evolve/skills/` (zona staging), separado de `skills/` (live).
5. Fingerprint sha256 evita re-procesar el mismo draft.

**Cómo lo mitigaríamos**:
- Mantener el comparative-promotion gate existente (luum ya es **más estricto** que holaOS aquí — exige métricas de baseline/candidate, no solo OK humano).
- Reusar `lib/skill_archive.py` para detectar degradación post-promoción y auto-rollback (ya existe).
- Frontmatter `lifecycle_state: sandbox` (ya se aplica en `auto-skill-generator.sh:185`) → never auto-loaded por skill-router.
- Killswitch: `DISABLE_HOOK_AUTO_SKILL_GENERATOR=true` + `NO_AUTO_SKILL=true`.
- **Nuevo**: agregar test contract `tests/contracts/test_evolve_promotion_gate.py` — un candidate con score < baseline DEBE rechazarse aunque el humano apruebe.

### 5.2 Skill widening que rompe sesiones existentes

**Riesgo**: si migramos a Camino A (§2.4), una skill mal-marcada bloquea Bash y la sesión se traba.

**Mitigación**:
- Roll-out gradual: empezar solo con tools sensibles (`Bash`, `WebFetch`, `mcp__Claude_in_Chrome__*`).
- Killswitch `COS_DISABLE_SKILL_WIDENING=1`.
- Test contract: cada skill con frontmatter `widens_tools` debe tener un test que prueba que el grant funciona.

### 5.3 Session-todo state corruption

**Riesgo**: dos hooks concurrentes escribiendo `state/todos/<session>.json` causan estado inconsistente.

**Mitigación**:
- Reusar `safe_jsonl_append` (precedente: `hooks/_lib/safe-jsonl.sh`) o adaptar `lib/file_locking.py` para JSON.
- Versionado: si version mismatch, migrar; nunca sobre-escribir un v2 con un v1.
- Backup automático antes de `replace` op (precedente: `lib/snapshot_manager.py`).

---

## 6. Recomendación final por feature

### Feature 1 — Evolve loop post-run

**Adoptar parcialmente.** Específicamente:
- **Sí**: cadencia (cada 3 turnos), confidence threshold (≥0.72), fingerprint dedup, task proposal queue, kind=skill_patch.
- **No**: el worker async con leases (overkill para nuestro volumen; hook síncrono basta hasta que metamos cron).
- **Reusar**: `lib/skill_archive.py`, `lib/skill_lifecycle_promoter.py`, comparative-promotion gate.

**Prioridad**: ALTA. Cierra gap "auto-skills de baja calidad" que ya fue señalado en `docs/research/multi-agent-orchestration-prior-art-2026-05-06.md`.

**Esfuerzo**: 3-4 días. Crear `lib/evolve_skill_review.py` + `lib/evolve_task_queue.py` + `scripts/cos-evolve-tick.py` + modificar `hooks/auto-skill-generator.sh` + extender `skills/resume-tasks/` o crear `skills/evolve-inbox/`.

### Feature 2 — Skill Widening Policy

**Adoptar Camino B primero (advisory), evaluar Camino A después.**
- Camino B reutiliza `hooks/orchestrator-skill-invocation-gate.sh` extendiendo `widens` en SKILL.md frontmatter.
- Camino A (hard block) solo si tras 1 mes de Camino B vemos casos reales de prompt injection o tool misuse que hubieran sido bloqueados.

**Prioridad**: MEDIA. ADR-188 ya da el 70% del valor; el resto es defense-in-depth.

**Esfuerzo**: B=1 día, A=3 días adicionales si decidimos escalar.

### Feature 3 — Session-TODO State Machine + Scratchpad

**Adoptar.** El gap es real y se siente en sesiones largas con SDD. Conviene:
- State machine tipado en `lib/session_todo_state.py` con invariante "≤1 in_progress".
- Phases mapeadas a SDD phases.
- Scratchpad como skill nueva.
- Anti-aliasing repair hints (port del concepto, no del código).

**Prioridad**: ALTA — habilita resume confiable, mejora UX de SDD multi-fase, base para el inbox de evolve (§1).

**Esfuerzo**: 2-3 días.

---

## 7. Resumen ejecutivo (annex C)

| Feature | luum tiene | luum carece de | Esfuerzo adopción | Prioridad |
|---|---|---|---:|---|
| Evolve loop | regex shell auto-gen + skill_archive post-promo | LLM extraction, cadencia, dedup sha256, task proposal queue, skill_patch kind | 3-4 d | **ALTA** |
| Skill widening | ADR-188 advisory gate | tool-gating hard por skill invocation | 1-3 d | MEDIA |
| Session TODO | TodoWrite nativo + work-queue.jsonl observacional | state machine tipado, phases, scratchpad markdown, repair hints | 2-3 d | **ALTA** |

**Orden de implementación sugerido**:
1. Feature 3 (state machine) — baja dependencia, habilita Feature 1.
2. Feature 1 (evolve loop) — depende del task queue/inbox de Feature 3.
3. Feature 2 — opcional refinamiento, ya cubierto en 70% por ADR-188.

**Total estimado**: 7-10 días de trabajo focused (1 ingeniero) o 2-3 sprints SDD.

**License compliance**: ningún archivo holaOS se copia. Toda implementación es Python/bash clean-room con nombres propios (`EvolveSkillCandidate` ≠ `EvolveSkillCandidateRecord`, `widens_tools` ≠ `grantedTools`, `SessionTodoState` ≠ `HarnessTodoState`). Los prompts JSON al LLM son reescritos desde cero — no copiar el system prompt literal de `evolve-skill-review.ts:445-451`.

---

## 8. Apéndice — Referencias cruzadas

- Parent: `docs/research/holaos-comparison-2026-05-10.md`
- ADR-188 (Mandatory Skill Invocation): `docs/adrs/ADR-188-mandatory-skill-invocation-at-high-confidence.md`
- ADR-033 (Canonical event format): work-queue.jsonl
- ADR-073-style claim-lease (precedente luum para worker pattern si lo necesitamos)
- `lib/skill_archive.py`, `lib/skill_efficacy.py`, `lib/skill_lifecycle_promoter.py`, `lib/self_improvement.py`
- `scripts/cos_governed_self_improvement.py` (comparative promotion evaluator)
- holaOS source paths citados (lectura only, no copiar):
  - `runtime/api-server/src/evolve.ts:27-210`
  - `runtime/api-server/src/evolve-worker.ts:50-196`
  - `runtime/api-server/src/evolve-skill-review.ts:23-737`
  - `runtime/api-server/src/evolve-tasks.ts:29-68`
  - `runtime/harnesses/src/skill-policy.ts:1-162`
  - `runtime/harnesses/src/todo-policy.ts:1-1134`
  - `runtime/api-server/src/session-todo.ts:1-300+`
  - `runtime/api-server/src/session-scratchpad.ts:1-80+`
