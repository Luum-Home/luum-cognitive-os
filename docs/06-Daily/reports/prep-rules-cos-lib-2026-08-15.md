# Preparación: migrar `lib/*.py` → `cos_lib/*.py` en `rules/`

**Fecha:** 2026-08-15 · **Modo:** preparación (no se aplicó nada) · **Alcance:** `rules/` únicamente

---

## 1. Veredicto

**De 104 referencias a `lib/*.py` en `rules/`, 96 son sustitución mecánica segura
(57 módulos distintos, 48 archivos). Las 8 restantes NO se tocan: 7 son excepciones
con motivo escrito y 1 es un módulo fantasma que necesita decisión del operador.**

`lib/` no existe en el repo. Las 104 referencias resuelven a nada, y `rules/` se
inyecta en el contexto de todo agente que trabaje acá.

---

## 2. El censo, con el comando

```bash
find -L rules -type f -name '*.md' -print0 \
  | xargs -0 perl -nle 'while (/(?<![\w\/.-])lib\/([\w\/-]+\.py)/g) { print "$ARGV:$.:lib/$1" } close ARGV if eof;'
```

| Métrica | Valor |
|---|---|
| Referencias `lib/*.py` (bare) | **104** |
| Archivos afectados | **48** |
| Módulos distintos | **63** |
| Sustituibles mecánicamente | **96** refs / **57** módulos |
| Excepciones aceptadas (no tocar) | **7** refs / **5** módulos |
| Bloqueadas (decisión pendiente) | **1** ref / **1** módulo |

Tres detalles del comando que no son cosméticos:

- **`find -L`, no `grep -r`.** `rules/` tiene 17 symlinks a `packages/*/rules/`, y
  `grep -r` en macOS no los sigue. Mi primer censo dio **96/46** por eso; el número
  real es **104/48**. Los 10 que faltaban están en `rules/agent-communication.md` (8)
  y `rules/skill-management.md` (2).
- **`perl`, no `grep -P`.** El `grep` de macOS es BSD y no tiene `-P`. Un script que
  use `grep -P` bajo `bash` devuelve **vacío en silencio** (rc=2 tragado por `2>/dev/null`),
  o sea reporta "nada pendiente" cuando hay 104. Pasó en la primera versión de este script.
- **Lookbehind `(?<![\w/.-])`.** Excluye `packages/*/lib/x.py` y `~/.claude/lib/x.py`,
  que son rutas correctas.

---

## 3. Clasificación por módulo

### 3.1 RENOMBRE DIRECTO — 57 módulos, 96 referencias

Existe `cos_lib/<mod>.py` con el nombre exacto. Sustitución segura.

Comando que lo decide (por módulo):

```bash
[ -e "cos_lib/$mod" ] && echo DIRECTO || echo NO-EXISTE   # -e sigue symlinks
```

| Módulo | Refs | Resolución en `cos_lib/` |
|---|---:|---|
| `agent_bus.py` | 2 | symlink → `packages/agent-coordination/lib/agent_bus.py` |
| `agent_dashboard.py` | 3 | symlink → `packages/agent-coordination/lib/agent_dashboard.py` |
| `agent_message_bus.py` | 1 | archivo |
| `agent_output_extractor.py` | 2 | archivo |
| `agent_permissions.py` | 1 | symlink → `packages/agent-lifecycle/lib/agent_permissions.py` |
| `ai_provider_identity_guard.py` | 1 | archivo |
| `capability_levels.py` | 1 | symlink → `packages/context-optimization/lib/capability_levels.py` |
| `checkpoint_manager.py` | 1 | archivo |
| `claude_executor.py` | 1 | archivo |
| `cognitive_load_monitor.py` | 1 | archivo |
| `completeness_checker.py` | 1 | archivo |
| `confidentiality_scanner.py` | 1 | archivo |
| `consequence_engine.py` | 4 | archivo |
| `cost_dashboard.py` | 2 | archivo |
| `cost_predictor.py` | 4 | symlink → `packages/scope-governance/lib/cost_predictor.py` |
| `cross_verifier.py` | 1 | symlink → `packages/verification-audit/lib/cross_verifier.py` |
| `dispatch.py` | 4 | archivo |
| `dispatch_helper.py` | 1 | archivo |
| `dispatch_model_advisor.py` | 1 | archivo |
| `dogfood_scorer.py` | 1 | archivo |
| `engram_http_client.py` | 3 | archivo |
| `engram_lifecycle.py` | 3 | archivo |
| `escalation_detector.py` | 2 | archivo |
| `estimation_calibrator.py` | 1 | symlink → `packages/scope-governance/lib/estimation_calibrator.py` |
| `file_mutation_queue.py` | 1 | archivo |
| `goal_budget.py` | 1 | archivo |
| `goal_evaluator.py` | 1 | archivo |
| `goal_evidence.py` | 1 | archivo |
| `goal_state.py` | 1 | archivo |
| `ground_truth.py` | 1 | symlink → `packages/verification-audit/lib/ground_truth.py` |
| `impact_analysis.py` | 1 | symlink → `packages/sdd-compound/lib/impact_analysis.py` |
| `memory_governance.py` | 3 | archivo |
| `memory_retriever.py` | 1 | archivo |
| `model_router.py` | 3 | archivo |
| `orchestrator_mode.py` | 1 | symlink → `packages/agent-lifecycle/lib/orchestrator_mode.py` |
| `prompt_classifier.py` | 3 | archivo |
| `queue_drainer.py` | 1 | archivo |
| `qwen_agent_loop.py` | 2 | archivo |
| `qwen_provider.py` | 1 | archivo |
| `rate_limit_protection.py` | 1 | symlink → `packages/adaptive-workflow/lib/rate_limit_protection.py` |
| `rate_limiter.py` | 2 | archivo |
| `record_completion.py` | 2 | archivo |
| `retry_scheduler.py` | 2 | archivo |
| `scheduled_drain.py` | 1 | archivo |
| `sdd_pipeline.py` | 1 | archivo |
| `secret_ref.py` | 2 | symlink → `packages/ecosystem-tools/lib/secret_ref.py` |
| `semantic_skill_matcher.py` | 2 | archivo |
| `session_state.py` | 1 | symlink → `packages/context-optimization/lib/session_state.py` |
| `singularity.py` | 3 | archivo |
| `skill_archive.py` | 2 | archivo |
| `skill_router.py` | 4 | archivo |
| `smart_infra.py` | 1 | archivo |
| `smart_reader.py` | 1 | archivo |
| `staged_verification.py` | 1 | symlink → `packages/verification-audit/lib/staged_verification.py` |
| `state_heartbeat.py` | 2 | archivo |
| `token_budget_monitor.py` | 2 | symlink → `packages/adaptive-workflow/lib/token_budget_monitor.py` |
| `trust_report_parser.py` | 1 | archivo |

**15 de los 57 son symlinks** de `cos_lib/` hacia `packages/*/lib/`. Sustituir a
`cos_lib/<mod>.py` es correcto igual: el enlace resuelve. Si en algún caso se prefiere
la ruta canónica del package, es una decisión de estilo aparte, no un bloqueo.

### 3.2 NO ES UNA REFERENCIA — 5 refs

Un `sed` a ciegas las rompe. Cada una con el motivo:

| Archivo:línea | Texto | Por qué no se toca |
|---|---|---|
| `rules/response-compression.md:27` | `` `lib/foo.py` `` | Ejemplo de formato de path dentro de una regla de estilo ("inline code for paths"). No nombra un módulo. |
| `rules/reinvention-prevention.md:40` | `our_file: lib/thing.py` | Placeholder de una plantilla YAML, junto a `source_file: agent/thing.py`. |
| `rules/task-dag.md:5` | `` **REMOVED 2026-04-20**: `lib/task_dag.py` was deleted `` | Tumba. La ruta vieja **es** el dato histórico: se borró de `lib/`, no de `cos_lib/`. Reescribirla inventa un archivo que nunca existió ahí. |
| `rules/workload-scheduling.md:5` | `` **REMOVED 2026-04-20**: `lib/workload_scheduler.py` was deleted `` | Ídem. |
| `rules/orchestrator-mode.md:60` | `` `lib/file_lock_registry.py` `` | El módulo existe, pero en `packages/agent-coordination/lib/file_lock_registry.py`. **No hay** `cos_lib/file_lock_registry.py`. Sustituir apuntaría a nada. La corrección correcta es la ruta completa del package, y eso es una edición a mano. |

Además, dos rutas del propio `rules/agent-communication.md` (L115 `packages/agent-coordination/lib/agent_bus.py`, L117 `packages/agent-lifecycle/lib/harness_adapter/base.py`) **ya son correctas** y un regex sin lookbehind las convertiría en `packages/.../cos_lib/...`. El patrón del script las excluye.

### 3.3 NO EXISTE EN NINGÚN LADO — 3 refs, 2 módulos

Necesitan decisión, no sustitución.

| Archivo:línea | Módulo | Estado |
|---|---|---|
| `rules/so-slo.md:35` y `:76` | `agent_heartbeat.py` | No existe en el árbol trackeado (`git ls-files \| grep agent_heartbeat.py` → vacío; solo aparece `tests/integration/test_native_agent_heartbeat.py`). La regla lo describe **como componente vivo**: "stamps `agent-heartbeat.jsonl`; watchdog checks staleness", y sostiene el SLO 9. O el mecanismo cambió de nombre, o el SLO mide algo que ya no tiene dueño. |
| `rules/non-blocking-retry.md:63` | `workload_scheduler.py` | El módulo **está declarado borrado** en `rules/workload-scheduling.md:5` (2026-04-20, "0 production callers"). Pero acá se lo cita en una tabla como componente vigente, con método y todo: `` `next_slot_available_in()` estimates wait time ``. Es una regla que le promete a los agentes una API que no existe. |

El script marca ambos y **no los toca** (`agent_heartbeat.py` como excepción escrita,
`workload_scheduler.py:non-blocking-retry` como `BLOCK` que hace fallar la verificación
hasta que se decida). Las opciones son las mismas para los dos: borrar la fila, o
reemplazarla por el mecanismo real si alguien sabe cuál es.

### 3.4 AMBIGUO

**Ninguno.** No hay módulo con dos candidatos: la búsqueda de colisiones
`packages/*/lib/<mod>.py` devolvió 15 casos, y los 15 son exactamente el destino del
symlink que ya está en `cos_lib/`. O sea, un solo archivo con dos rutas, no dos archivos.

```bash
while read -r m; do git ls-files "packages/*/lib/$m"; done < <(lista de módulos)
```

---

## 4. Deuda adyacente (fuera del alcance de este script)

12 referencias a `lib/<algo>` **sin** `.py` en `rules/`, que el patrón no toca por diseño:

```
rules/RULES-COMPACT.md:28            lib/harness_adapter
rules/RULES-COMPACT.md:43            lib/decision_tracker
rules/cosd-secure-api.md:28,38       lib/cosd_grant, lib/cosd_grant_store
rules/llm-dispatch.md:36,44,110,169  lib/qwen_agent_loop, lib/qwen_provider ×3
rules/orchestrator-mode.md:19        lib/file_lock_registry
rules/reinvention-prevention.md:49   lib/hook/skill
rules/skill-invocation-mandatory.md:11,23  lib/skill_router, lib/harness_adapter
```

Son la misma familia y se arreglan con una segunda pasada, pero el patrón sin `.py`
tiene mucho más riesgo de falso positivo (`lib/` genérico, `settings.json/lib/`), así que
no lo metí en este script.

---

## 5. Hallazgo colateral: el aviso de trampas es él mismo una trampa

`templates/project-gotchas.md` le dice a todo agente de este repo, en la tabla
"Before modifying":

| Si tocás… | Leé primero… | Porque… |
|---|---|---|
| `lib/*.py` | `ls -la lib/<file>` | Puede ser un symlink a packages/ |
| `packages/*/lib/*.py` | `ls -la lib/` | los symlinks de lib/ apuntan acá |
| `scripts/orchestrator.py` o `lib/dispatch.py` | `rules/llm-dispatch.md` + ADR-049 | … |

Las tres instrucciones son contra `lib/`, que no existe. `ls -la lib/<file>` falla
siempre, y el agente que la corre aprende que el chequeo "no da nada" en vez de aprender
que la ruta cambió. El mecanismo que avisa sobre trampas se volvió una.

Es el arreglo más barato de todos los de este informe (3 celdas de una tabla) y el de
mayor alcance, porque ese template lo consumen `scripts/compose_agent_prompt.py` y una
decena de ADRs. Va aparte de la migración de `rules/` y no lo incluí en el script porque
no es una sustitución mecánica: `ls -la lib/<file>` tiene que pasar a
`ls -la cos_lib/<file>` **y** el "porque" sigue siendo verdadero (los symlinks ahora
viven en `cos_lib/`).

---

## 6. El script

Vive en el scratchpad de la sesión (`.../scratchpad/migrate-rules-cos-lib.sh`) y va
pegado entero acá porque `/tmp` se limpia sola.

Modos: sin argumentos = plan (no escribe); `--apply` = escribe; `--verify` = solo veredicto,
para usar como gate. Exit: `0` limpio, `1` pendientes o aplicado, `2` error.

```bash
#!/usr/bin/env bash
# migrate-rules-cos-lib.sh — migra `lib/<mod>.py` -> `cos_lib/<mod>.py` en rules/.
# Read-only por default. Escribe solo con --apply. Idempotente.
#
#   ./migrate-rules-cos-lib.sh            # censo + plan, no toca nada
#   ./migrate-rules-cos-lib.sh --apply    # aplica el plan
#   ./migrate-rules-cos-lib.sh --verify   # solo el veredicto (para CI/gate)
#
# Exit: 0 = limpio | 1 = hay pendientes (o se aplicaron) | 2 = error de uso/entorno
#
# Por que NO es un `sed -i s|lib/|cos_lib/|g`:
#   1. `grep -r` en macOS NO sigue symlinks y rules/ tiene 17. Se recorre con
#      `find -L`.
#   2. `grep -P` no existe en el grep de macOS (BSD). Toda la deteccion va en
#      perl, que si esta siempre.
#   3. Hay rutas `packages/*/lib/<mod>.py` que son CORRECTAS: el patron usa
#      lookbehind negativo para no tocarlas.
#   4. Seis ocurrencias son ejemplos, placeholders, tumbas historicas o modulos
#      inexistentes: lista EXCLUDE, abajo, cada una con su motivo.
#   5. Dos archivos de rules/ son symlinks a packages/*/rules/: se escribe sobre
#      el destino real, nunca reemplazando el enlace.

set -uo pipefail

MODE="plan"
case "${1:-}" in
  "")        MODE="plan" ;;
  --apply)   MODE="apply" ;;
  --verify)  MODE="verify" ;;
  *) echo "uso: $0 [--apply|--verify]" >&2; exit 2 ;;
esac

REPO="${COS_REPO:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$REPO" ] && [ -d "$REPO/rules" ] && [ -d "$REPO/cos_lib" ] || {
  echo "ERROR: correr dentro del repo (rules/ y cos_lib/ deben existir)" >&2; exit 2; }
cd "$REPO" || exit 2
command -v perl >/dev/null || { echo "ERROR: falta perl" >&2; exit 2; }

# --------------------------------------------------------------------------
# EXCLUDE — pares "<ruta>:<modulo>|<motivo>" que NO se sustituyen.
# Sustituirlas empeoraria el texto en vez de arreglarlo.
# --------------------------------------------------------------------------
read -r -d '' EXCLUDE <<'EOF'
rules/response-compression.md:foo.py|ejemplo de formato de path, no nombra un modulo
rules/reinvention-prevention.md:thing.py|placeholder de una plantilla YAML
rules/task-dag.md:task_dag.py|tumba: el modulo se borro de lib/ el 2026-04-20; la ruta vieja es el dato historico
rules/workload-scheduling.md:workload_scheduler.py|tumba: idem, borrado 2026-04-20
rules/orchestrator-mode.md:file_lock_registry.py|vive en packages/agent-coordination/lib/, no en cos_lib/
rules/so-slo.md:agent_heartbeat.py|no existe en ningun lado: decision de operador pendiente
EOF
export COS_EXCLUDE="$EXCLUDE"
export COS_REPO_ABS="$REPO"

is_excluded() { printf '%s\n' "$EXCLUDE" | grep -qF -- "$1:$2|"; }
excl_reason() { printf '%s\n' "$EXCLUDE" | grep -F -- "$1:$2|" | head -1 | cut -d'|' -f2-; }
resolve() { readlink -f "$1" 2>/dev/null \
            || python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$1"; }

# Censo: "<archivo>:<linea>:lib/<mod>". find -L sigue los symlinks de rules/.
scan() {
  find -L rules -type f -name '*.md' -print0 \
    | xargs -0 perl -nle 'while (/(?<![\w\/.-])lib\/([\w\/-]+\.py)/g) { print "$ARGV:$.:lib/$1" } close ARGV if eof;' \
    | sort -t: -k1,1 -k2,2n
}

n_fix=0; n_skip=0; n_block=0
declare -a PLAN_FILES=()
PLAN_OUT=""

while IFS= read -r hit; do
  [ -z "$hit" ] && continue
  file="${hit%%:*}"; rest="${hit#*:}"; line="${rest%%:*}"; mod="${rest##*:lib/}"

  if is_excluded "$file" "$mod"; then
    PLAN_OUT+=$(printf 'SKIP   %-40s L%-4s lib/%-26s  %s\n' \
      "$file" "$line" "$mod" "$(excl_reason "$file" "$mod")")$'\n'
    n_skip=$((n_skip+1)); continue
  fi
  if [ ! -e "cos_lib/$mod" ]; then
    PLAN_OUT+=$(printf 'BLOCK  %-40s L%-4s lib/%-26s  cos_lib/%s no existe -> decidir a mano\n' \
      "$file" "$line" "$mod" "$mod")$'\n'
    n_block=$((n_block+1)); continue
  fi
  real="$(resolve "cos_lib/$mod")"; real="${real#"$REPO"/}"
  note=""; [ "$real" != "cos_lib/$mod" ] && note="  (symlink -> $real)"
  PLAN_OUT+=$(printf 'FIX    %-40s L%-4s lib/%-26s -> cos_lib/%s%s\n' \
    "$file" "$line" "$mod" "$mod" "$note")$'\n'
  n_fix=$((n_fix+1)); PLAN_FILES+=("$file")
done < <(scan)

if [ "$MODE" = "verify" ]; then
  if [ "$n_fix" -eq 0 ] && [ "$n_block" -eq 0 ]; then
    echo "OK: rules/ sin referencias colgadas a lib/*.py ($n_skip excepciones aceptadas)"
    exit 0
  fi
  echo "PENDIENTE: $n_fix sustituibles + $n_block bloqueadas en rules/ ($n_skip excepciones aceptadas)"
  exit 1
fi

echo "== PLAN ($(basename "$REPO"), modo: $MODE) =="
echo
printf '%s' "$PLAN_OUT"
echo
echo "-- $n_fix a sustituir | $n_skip excluidas | $n_block bloqueadas --"

[ "$n_fix" -eq 0 ] && [ "$n_block" -eq 0 ] && { echo "nada pendiente"; exit 0; }

if [ "$MODE" = "plan" ]; then
  echo; echo "dry-run: no se escribio nada. Volve a correr con --apply."
  exit 1
fi

# --- aplicar --------------------------------------------------------------
echo
declare -A SEEN=()
for f in "${PLAN_FILES[@]}"; do
  [ -n "${SEEN[$f]:-}" ] && continue
  SEEN[$f]=1
  target="$(resolve "$f")"
  [ "$target" != "$REPO/$f" ] && echo "nota: $f es symlink -> ${target#"$REPO"/} (se escribe el destino)"

  COS_FILE="$f" perl -i -pe '
    BEGIN { %ex = map { (split /\|/, $_, 2)[0] => 1 }
                  grep { /\S/ } split /\n/, $ENV{COS_EXCLUDE}; }
    s{(?<![\w/.-])lib/([\w/-]+\.py)}{
       my $m = $1;
       ( exists $ex{"$ENV{COS_FILE}:$m"} || ! -e "$ENV{COS_REPO_ABS}/cos_lib/$m" )
         ? "lib/$m" : "cos_lib/$m";
    }ge;
  ' "$target" || { echo "ERROR escribiendo $f" >&2; exit 2; }
  echo "escrito: ${target#"$REPO"/}"
done

echo
echo "-- re-verificacion --"
left=$(scan | wc -l | tr -d ' ')
echo "quedan $left refs lib/*.py en rules/ (esperado $((n_skip + n_block)) = excluidas + bloqueadas)"
[ "$left" -eq "$((n_skip + n_block))" ] || { echo "INESPERADO: revisar" >&2; exit 2; }
exit 1
```

### Qué se probó del script (sandbox aislado, sin tocar el repo)

Se armó un repo de mentira en el scratchpad con un módulo real, uno detrás de symlink,
una ruta de package, un módulo fantasma, un path `~/.claude/lib/` y un archivo de reglas
que es symlink a `packages/`. Resultado:

- La ruta `packages/p/lib/agent_bus.py` quedó **intacta**.
- `~/.claude/lib/otro.py` quedó **intacto**.
- El módulo inexistente quedó **intacto** y se reportó `BLOCK`.
- El archivo symlinkeado: se escribió el destino en `packages/`, y **el symlink siguió
  siendo symlink** (un `sed -i` lo habría reemplazado por un archivo regular, rompiendo
  la sincronización con el package).
- Segunda corrida de `--apply`: **0 a sustituir**. Idempotente.

### Dos archivos escriben fuera de `rules/`

`rules/agent-communication.md` y `rules/skill-management.md` son symlinks. Sus ediciones
aterrizan en `packages/agent-coordination/rules/agent-communication.md` y
`packages/skill-governance/rules/skill-management.md`. El script lo anuncia por línea
antes de escribir. Tenerlo en cuenta para el `git add` (paths acotados, nunca `-A`).

---

## 7. Correcciones a las premisas del encargo

| Premisa recibida | Medición | Corrección |
|---|---|---|
| "`rules/` tendría ~96 referencias" | 104 | El 96 es el resultado de `grep -r`, que **no sigue los 17 symlinks** de `rules/`. Faltaban 10 (8 en `agent-communication.md`, 2 en `skill-management.md`). Casualmente 96 es también el número de refs sustituibles, pero por coincidencia. |
| "ninguna resolviendo" | Correcto | `lib/` no existe. Las 104 apuntan a nada. |
| "un juez reportó 60+ módulos fantasma en `rules/`" | **2** | Módulos distintos referenciados: 63. De esos, **57 existen** en `cos_lib/` con nombre exacto. Fantasmas de verdad (no están en ningún lado): `agent_heartbeat.py` y `workload_scheduler.py`. El juez confundió "63 módulos referenciados por una ruta que no resuelve" con "63 módulos que no existen". |
| "otro juez, 433 refs en docs y reglas; no reprodujo" | **5.474** (104 en `rules/` + 5.370 en `docs/*.md`) | No reprodujo porque el 433 no corresponde a nada medible con este patrón. El número real es un orden de magnitud mayor, pero **no es comparable**: 3.225 de las 5.370 de `docs/` están en `docs/06-Daily/`, o sea reportes fechados — instantáneas históricas que no hay que reescribir (los 8 archivos más cargados son `aspirational-audit-*.md`, entre 216 y 368 refs cada uno). La migración de `docs/` es otro problema, con otra clasificación. |
| "el repo usa symlinks masivamente; `readlink -f` antes de declarar que algo falta" | Confirmado, y con un giro | Los symlinks que importan están en **`cos_lib/`** (15 de los 57 módulos apuntan a `packages/*/lib/`) y en **`rules/`** (17 archivos apuntan a `packages/*/rules/`). Los de `rules/` son los que rompen tanto el censo (`grep -r`) como la escritura (`sed -i`). |
| Trampa inyectada por el hook: "SOME `lib/*.py` (~22%, 68 of 314) are SYMLINKS… verify with `ls -la lib/<file>.py`" | `ls -d lib` → no existe; `git ls-files 'lib/*'` → 0 | Vencida. Texto en `templates/project-gotchas.md:22,25`. Ver §5. |

---

## 8. Verificación (rojo hoy → verde después)

**Gate, en una línea:**

```bash
bash <ruta-al-script>/migrate-rules-cos-lib.sh --verify
```

Hoy:
```
PENDIENTE: 96 sustituibles + 1 bloqueadas en rules/ (7 excepciones aceptadas)   # exit 1
```

Después de `--apply` **y** de resolver a mano `rules/non-blocking-retry.md:63`:
```
OK: rules/ sin referencias colgadas a lib/*.py (8 excepciones aceptadas)        # exit 0
```

**Sin el script** (por si se quiere el chequeo crudo): cuenta de referencias que
resuelven a nada, descontando las 8 excepciones documentadas.

```bash
find -L rules -type f -name '*.md' -print0 \
  | xargs -0 perl -nle 'while (/(?<![\w\/.-])lib\/([\w\/-]+\.py)/g) { print $1 } close ARGV if eof;' \
  | sort | uniq -c | sort -rn
```

Hoy imprime 63 módulos / 104 líneas. Después tiene que imprimir solo estos cinco:
`foo.py`, `thing.py`, `task_dag.py`, `workload_scheduler.py`, `file_lock_registry.py`
(más `agent_heartbeat.py` si el operador decide dejar la referencia mientras se investiga).

**Orden sugerido:** correr el plan, aplicar, resolver `non-blocking-retry.md:63` y
`so-slo.md:35,76` a mano, y por último las 3 celdas de `templates/project-gotchas.md`.
