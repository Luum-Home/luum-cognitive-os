#!/usr/bin/env bash
# SCOPE: both
# common.sh — Shared utility functions for Cognitive OS hooks
#
# Usage: source "$(dirname "$0")/_lib/common.sh"
#
# Provides:
#   require_tool <tool_name>        — exit 0 if TOOL_NAME doesn't match (gate)
#   cos_session_id                  — echo this hook process session id (or empty)
#   resolve_session_dir             — echo session-scoped metrics directory path
#   get_phase                       — echo current project phase from cognitive-os.yaml
#   check_private_mode              — exit 0 if private mode is active
#   read_stdin_json                 — read and cache stdin JSON (sets $_STDIN_JSON)
#   stdin_field <jq_path> [default] — extract a field from cached stdin JSON

# Guard: only load once
[ "${_COMMON_SH_LOADED:-}" = "true" ] && return 0
_COMMON_SH_LOADED="true"

# ─── Core paths ─────────────────────────────────────────────────────────────

if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
  _PROJECT_DIR="$COGNITIVE_OS_PROJECT_DIR"
elif [ -n "${CODEX_PROJECT_DIR:-}" ]; then
  _PROJECT_DIR="$CODEX_PROJECT_DIR"
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  _PROJECT_DIR="$CLAUDE_PROJECT_DIR"
else
  _PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
_CONFIG_FILE="$_PROJECT_DIR/.cognitive-os/cognitive-os.yaml"

# Alternate config path for projects that use cognitive-os.yaml at root
[ ! -f "$_CONFIG_FILE" ] && [ -f "$_PROJECT_DIR/cognitive-os.yaml" ] && _CONFIG_FILE="$_PROJECT_DIR/cognitive-os.yaml"

# ─── require_tool ────────────────────────────────────────────────────────────
# Usage: require_tool "Agent"
# Usage: require_tool "Bash"
# Usage: require_tool "Agent" "task" "delegate"   (multiple allowed)
# Exits 0 (skip hook) if the tool doesn't match any of the provided names.
# Reads TOOL_NAME from cached stdin JSON if not set as env var.

require_tool() {
  local tool_name="${TOOL_NAME:-}"

  # If TOOL_NAME not in env, try to extract from stdin JSON
  if [ -z "$tool_name" ]; then
    read_stdin_json
    tool_name=$(echo "$_STDIN_JSON" | jq -r '.tool_name // empty' 2>/dev/null)
  fi

  for allowed in "$@"; do
    [ "$tool_name" = "$allowed" ] && return 0
  done

  exit 0
}

# ─── cos_session_id ──────────────────────────────────────────────────────────
# Echoes the id of the session this hook process belongs to, or the empty
# string when it cannot be established. NEVER consumes stdin.
#
# 2026-08-19 — por que existe esta funcion. La resolucion de identidad vivia
# inline dentro de resolve_session_dir() y su unico fallback era leer
# `.current-session-$$`, un archivo que escribe hooks/session-init.sh:223 con
# SU PROPIO PID. Como el PID del lector nunca es el del escritor, ningun
# proceso distinto de session-init podia resolver la sesion: medido, 8.887
# eventos de hooks que creen segregar cayeron al directorio global el
# 2026-08-19 y 0 a los seis .cognitive-os/sessions/*/metrics/ (que existen
# vacios solo porque session-init.sh:21 los crea con mkdir -p al abrir la
# sesion). Mismo defecto y mismo dia que hooks/concurrent-write-guard.sh
# (fix 82969b80f, 1.062 invocaciones sin tomar un lock).
#
# El orden replica scripts/_lib/session-id.sh —la primitiva que ya existia para
# los locks de edicion— y le agrega el idioma del payload del harness, que ya
# estaba en hooks/orchestrator-skill-invocation-gate.sh:36. No se inventa
# mecanismo nuevo.
#
# Restriccion dura: los pasos 2 y 3 leen payload YA leido. resolve_session_dir
# se llama ANTES del `cat` de stdin en packages/prompt-quality-gate/hooks/
# prompt-quality.sh:27 y packages/verification-audit/hooks/result-truncator.sh:27;
# si esta funcion llamara a read_stdin_json les vaciaria stdin y los romperia.
cos_session_id() {
  local sid=""

  # 1. Env explicito: override canonico COS primero, despues cada harness.
  #
  # CLAUDE_CODE_SESSION_ID es la variable REAL y documentada del arnes
  # (env-vars.md:339): "Set automatically to the current session ID in Bash and
  # PowerShell tool subprocesses, hook command subprocesses ... this matches the
  # session_id field in the hook JSON input". Verificada presente en el entorno:
  #   env | grep CLAUDE_CODE_SESSION_ID   ->   93e6e34f-...  (2026-08-19)
  #
  # CLAUDE_SESSION_ID -sin CODE- NO EXISTE: 0 ocurrencias en env-vars.md. Se
  # conserva ultima en la cadena solo porque el repo la nombra en ~101 lugares y
  # sacarla de aca no arregla ninguno; nunca resuelve nada.
  if [ -n "${COGNITIVE_OS_SESSION_ID:-}" ]; then printf '%s' "$COGNITIVE_OS_SESSION_ID"; return 0; fi
  if [ -n "${CLAUDE_CODE_SESSION_ID:-}" ];  then printf '%s' "$CLAUDE_CODE_SESSION_ID";  return 0; fi
  if [ -n "${CODEX_SESSION_ID:-}" ];        then printf '%s' "$CODEX_SESSION_ID";        return 0; fi
  if [ -n "${CLAUDE_SESSION_ID:-}" ];       then printf '%s' "$CLAUDE_SESSION_ID";       return 0; fi

  if command -v jq >/dev/null 2>&1; then
    # 2. Payload del harness ya cacheado por read_stdin_json (no consume stdin).
    if [ "${_STDIN_READ:-false}" = "true" ] && [ -n "${_STDIN_JSON:-}" ]; then
      sid=$(printf '%s' "$_STDIN_JSON" | jq -r '.session_id // empty' 2>/dev/null)
      if [ -n "$sid" ]; then printf '%s' "$sid"; return 0; fi
    fi
    # 3. Hooks que hacen su propio INPUT="$(cat)" antes de llamar.
    if [ -n "${INPUT:-}" ]; then
      sid=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
      if [ -n "$sid" ]; then printf '%s' "$sid"; return 0; fi
    fi
  fi

  # 4. Marcador legacy por PID. Solo resuelve dentro de session-init; se
  #    conserva porque scripts/commit_provenance.py todavia lo lee.
  local session_file="$_PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  if [ -f "$session_file" ]; then
    sid=$(tr -d '\n' < "$session_file" 2>/dev/null)
    if [ -n "$sid" ]; then printf '%s' "$sid"; return 0; fi
  fi

  printf ''
  return 0
}

# ─── resolve_session_dir ─────────────────────────────────────────────────────
# Echoes the session-scoped metrics directory if a session is active AND
# per-session metrics are enabled, otherwise echoes the global metrics
# directory. Creates the directory if it doesn't exist.
#
# COS_SESSION_SCOPED_METRICS=1 habilita la rama por sesion. Esta APAGADA por
# defecto a proposito, y el motivo no es cautela generica: encender la
# segregacion hoy pierde datos.
#
#   a) La ruta de merge esta muerta. hooks/session-cleanup.sh es quien devuelve
#      las metricas de sesion al global (Step 1, merge_metrics_on_exit: true) y
#      resuelve la sesion con el MISMO `.current-session-$$` imposible
#      (session-cleanup.sh:18). Metricas por sesion + merge que nunca corre =
#      13 archivos .jsonl que los consumidores del global dejan de ver
#      (skill-metrics.jsonl tiene 45 referencias en el repo; truncation-events
#      12; aci-observations 14).
#   b) Arreglar ese merge tampoco es libre: session-cleanup esta registrado en
#      Stop, que dispara UNA VEZ POR TURNO, y con cleanup_on_exit: true termina
#      borrando el directorio de sesion (session-cleanup.sh:125) y soltando los
#      locks de la sesion (:118). Hoy no destruye nada solo porque el mismo bug
#      de identidad lo hace salir en el `exit 0` de la linea 26.
#
# Es decir: la identidad ya se resuelve bien (cos_session_id), y el redirect
# queda detras del switch hasta que Stop-vs-SessionEnd este resuelto.
#
#   c) Hay DOS espacios de nombres de sesion conviviendo en
#      .cognitive-os/sessions/. hooks/session-init.sh:17 se INVENTA un id
#      (`$(date +%s)-$$-<rand>`, p.ej. 1787183298-51467-3fe05b4a) en vez de
#      adoptar el del arnes, y por eso hacia falta un archivo marcador. Al lado,
#      con el id real del arnes (CLAUDE_CODE_SESSION_ID), hay un directorio vivo
#      -93e6e34f-a5b1-4921-a480-a36496b3c566, 209 entradas, escrito ahora mismo-
#      que otro componente si usa. cos_session_id devuelve el del ARNES, que es
#      el unico que todo proceso puede derivar solo. Reconciliar session-init
#      con ese id es la continuacion natural de este arreglo y NO se hizo aca:
#      mueve active-sessions.json, session-cleanup y commit_provenance.
#
# Compatibilidad: cuando COGNITIVE_OS_SESSION_ID viene seteado explicitamente
# —la unica via que funcionaba antes de este cambio— la rama por sesion sigue
# activa sin necesidad del switch, para no alterar comportamiento existente.
#
# COS_METRICS_DIR gana sobre TODO lo anterior, incluida la rama por sesion. No es
# una tercera politica de ruteo: es el override explicito de quien corre el
# proceso —la suite lo apunta a un sandbox en `conftest.py::pytest_configure`— y
# ya es la convencion del repo (`bypass-resolver.sh:82`, `tuning.sh:31`,
# `circuit-breaker.sh:27`, `remediation.sh:40`, `pre-commit-gate.sh:32`).
# Va PRIMERO, no dentro del `else`: como fallback del global solo taparia el caso
# con la segregacion apagada, y un test corriendo con COS_SESSION_SCOPED_METRICS=1
# seguiria escribiendo bajo el `.cognitive-os/sessions/` del operador — el mismo
# agujero, un nivel mas abajo. Sin la variable esta funcion se comporta
# exactamente igual que antes: lo sostiene el control B de
# `scripts/verify-metrics-dir-override.sh`.
resolve_session_dir() {
  if [ -n "${COS_METRICS_DIR:-}" ]; then
    mkdir -p "$COS_METRICS_DIR" 2>/dev/null
    echo "$COS_METRICS_DIR"
    return 0
  fi

  local metrics_dir="$_PROJECT_DIR/.cognitive-os/metrics"
  local session_id
  session_id="$(cos_session_id)"

  local scoped="${COS_SESSION_SCOPED_METRICS:-}"
  if [ -z "$scoped" ] && [ -n "${COGNITIVE_OS_SESSION_ID:-}" ]; then
    scoped="1"
  fi

  if [ "$scoped" = "1" ] && [ -n "$session_id" ] \
     && [ -d "$_PROJECT_DIR/.cognitive-os/sessions/$session_id" ]; then
    local session_metrics="$_PROJECT_DIR/.cognitive-os/sessions/$session_id/metrics"
    mkdir -p "$session_metrics" 2>/dev/null
    echo "$session_metrics"
  else
    mkdir -p "$metrics_dir" 2>/dev/null
    echo "$metrics_dir"
  fi
}

# ─── get_phase ───────────────────────────────────────────────────────────────
# Echoes the current project phase from cognitive-os.yaml.
# Falls back to "reconstruction" if not found.

get_phase() {
  local default="${1:-reconstruction}"

  if [ -f "$_CONFIG_FILE" ]; then
    local parsed
    parsed=$(grep -E '^\s*phase:' "$_CONFIG_FILE" 2>/dev/null | head -1 \
      | sed 's/.*phase:[[:space:]]*//' | sed 's/[[:space:]]*#.*//' | tr -d '[:space:]' || true)
    [ -n "$parsed" ] && echo "$parsed" && return 0
  fi

  echo "$default"
}

# ─── check_private_mode ──────────────────────────────────────────────────────
# Exits 0 (skip hook) if private mode is active.

check_private_mode() {
  if [ -f "/tmp/claude-private-mode-active" ]; then
    exit 0
  fi
}

# ─── read_stdin_json / stdin_field ───────────────────────────────────────────
# Reads stdin once and caches it in $_STDIN_JSON.
# Subsequent calls return the cached value.
# stdin_field extracts a jq path from the cached JSON.

# ─── check_capability_level ─────────────────────────────────────────────────
# Checks if the current hook should run based on the model capability level.
# If the hook's name is in the auto_disable list for the current level, exit 0.
#
# Usage: check_capability_level "clarification-gate"
# Call this at the top of any hook that should respect capability levels.

check_capability_level() {
  local component_name="$1"
  [ -z "$component_name" ] && return 0

  # Read capability level from config
  local level=""
  if [ -f "$_CONFIG_FILE" ]; then
    level=$(grep -A1 'model_capability:' "$_CONFIG_FILE" 2>/dev/null \
      | grep 'level:' | head -1 \
      | sed 's/.*level:[[:space:]]*//' | sed 's/[[:space:]]*#.*//' | tr -d '[:space:]' || true)
  fi
  [ -z "$level" ] && level="3"

  # Use the Python module if available, otherwise use inline logic
  local disabled=""
  if command -v python3 >/dev/null 2>&1; then
    disabled=$(python3 -c "
import sys
sys.path.insert(0, '$_PROJECT_DIR')
try:
    from cos_lib.capability_levels import should_component_run
    if not should_component_run('$component_name', $level, '$_CONFIG_FILE'):
        print('disabled')
except Exception:
    pass
" 2>/dev/null)
  else
    # Fallback: hardcoded check for common disabled components
    case "$level" in
      5)
        case "$component_name" in
          context-management|clarification-gate|assumption-tracking|confidence-gate|model-routing|blast-radius|\
epic-task-detector|scope-proportionality|trust-score-validator|\
claim-validator|tool-loop-detector|consequence-evaluator|infra-intent-detector|\
pre-cleanup-snapshot|architecture-compliance|auto-skill-generator)
            disabled="disabled"
            ;;
        esac
        ;;
      4)
        case "$component_name" in
          context-management|clarification-gate|assumption-tracking|confidence-gate|model-routing|blast-radius)
            disabled="disabled"
            ;;
        esac
        ;;
      3)
        case "$component_name" in
          context-management)
            disabled="disabled"
            ;;
        esac
        ;;
    esac
  fi

  if [ "$disabled" = "disabled" ]; then
    exit 0
  fi
}

# ─── check_disabled_env ──────────────────────────────────────────────────────
# Exits 0 (skip hook silently) if the DISABLE_HOOK_<UPPERCASE_NAME> env var is
# set to "true" or "1" for the current session.
#
# Usage: check_disabled_env "blast-radius"
#   Checks: DISABLE_HOOK_BLAST_RADIUS=true
#
# Name transformation: hyphens → underscores, all uppercase.
# This function must be called near the top of each hook that supports it.
# Always exits 0 (never blocks), so it is safe for security-critical hooks too
# (operator responsibility to not disable safety-critical hooks).
#
# Example:
#   check_disabled_env "blast-radius"    # checks DISABLE_HOOK_BLAST_RADIUS
#   check_disabled_env "clarification-gate"  # checks DISABLE_HOOK_CLARIFICATION_GATE

check_disabled_env() {
  local hook_name="${1:-}"
  [ -z "$hook_name" ] && return 0

  # Transform name: hyphens to underscores, uppercase
  local env_key
  env_key="DISABLE_HOOK_$(echo "$hook_name" | tr '[:lower:]-' '[:upper:]_')"

  local env_val
  env_val="${!env_key:-}"

  if [ "$env_val" = "true" ] || [ "$env_val" = "1" ]; then
    exit 0
  fi
}

_STDIN_JSON=""
_STDIN_READ="false"

read_stdin_json() {
  if [ "$_STDIN_READ" = "false" ]; then
    _STDIN_JSON=$(cat)
    _STDIN_READ="true"
  fi
}

# Usage: stdin_field '.tool_input.command' 'default_value'
stdin_field() {
  local path="$1"
  local default="${2:-}"

  read_stdin_json

  local val
  val=$(echo "$_STDIN_JSON" | jq -r "$path // empty" 2>/dev/null)
  if [ -z "$val" ] || [ "$val" = "null" ]; then
    echo "$default"
  else
    echo "$val"
  fi
}
