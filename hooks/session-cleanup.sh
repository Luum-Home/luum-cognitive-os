#!/usr/bin/env bash
# SCOPE: both
# Stop hook: Clean up session on exit
# Removes session from active-sessions.json, merges metrics, optionally cleans up directory.
# Must complete in <10 seconds.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions"
ACTIVE_FILE="$SESSIONS_DIR/active-sessions.json"
GLOBAL_METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"

# Resolve session ID: env var > file-based discovery
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  # Try to find session file for this PID
  SESSION_FILE="$SESSIONS_DIR/.current-session-$$"
  if [ -f "$SESSION_FILE" ]; then
    SESSION_ID=$(cat "$SESSION_FILE" 2>/dev/null)
  fi
fi

# If no session, nothing to clean up
if [ -z "$SESSION_ID" ]; then
  exit 0
fi

SESSION_DIR="$SESSIONS_DIR/$SESSION_ID"

# --- Las dos perillas de este hook, y por que estaban muertas ---------------
# El default vive aca, no en un archivo: si ninguna config existe, esto es lo
# que rige. Escrito ARRIBA de la lectura para que se lea como default y no como
# resultado de parsear algo.
CLEANUP_ON_EXIT=true
MERGE_METRICS=true

# Se leia UN solo archivo, .cognitive-os/cognitive-os.yaml, que no existe en
# ningun checkout de este repo. Consecuencia medida el 2026-08-19: las dos
# perillas eran decorativas — poner `cleanup_on_exit: false` en el
# cognitive-os.yaml de la raiz (linea 181, el canonico de ADR-064) no
# desactivaba nada, y el `true` que regia salia del default de aca arriba.
#
# El segundo defecto vivia en el parseo, y solo se ve con el archivo presente:
# la linea canonica es `cleanup_on_exit: true  # Remove session directory...`,
# y el sed no cortaba el comentario. Con `false` escrito ahi, el valor parseado
# habria sido `false#Removesessiondirectoryonexit`, que no compara igual a
# `false`. O sea que conectar el archivo sin arreglar el parseo dejaba la
# perilla igual de muerta, solo que mas dificil de ver.
_read_knob() {
  local key="$1" file raw value=""
  # Orden de precedencia: canonico primero, override local despues — gana el
  # ultimo valor no vacio.
  for file in "$PROJECT_DIR/cognitive-os.yaml" "$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"; do
    [ -f "$file" ] || continue
    raw=$(grep -E "^[[:space:]]*${key}:" "$file" 2>/dev/null | head -1 \
      | sed -E "s/^[[:space:]]*${key}:[[:space:]]*//; s/#.*$//" | tr -d '[:space:]')
    [ -n "$raw" ] && value="$raw"
  done
  printf '%s' "$value"
}

[ "$(_read_knob cleanup_on_exit)" = "false" ] && CLEANUP_ON_EXIT=false
[ "$(_read_knob merge_metrics_on_exit)" = "false" ] && MERGE_METRICS=false

# --- _session_owner_alive ---------------------------------------------------
# Devuelve 0 (viva) cuando el proceso duenio de la sesion sigue corriendo, o
# cuando no hay evidencia para afirmar lo contrario. Conservador por diseno: sin
# prueba de muerte, la sesion se considera viva y no se toca nada suyo.
#
# Existe porque este hook esta registrado en Stop, y Stop dispara UNA VEZ POR
# TURNO, no al cerrar la sesion. Medido sobre 286.163 filas de telemetria
# (.cognitive-os/metrics/hook-timing.jsonl mas .archive/hook-timing-*.jsonl.gz):
# 335 disparos de session-cleanup contra 75 aperturas de sesion, con hasta 41
# disparos DENTRO de una misma ventana SessionStart->SessionStart. "El turno
# termino" no es evidencia de que "la sesion termino", y de esa confusion colgaba
# todo el paso destructivo.
_session_owner_alive() {
  local meta="$SESSION_DIR/meta.json"
  local pid=""
  [ -f "$meta" ] || return 0
  command -v jq >/dev/null 2>&1 || return 0
  pid=$(jq -r '.pid' "$meta" 2>/dev/null)
  case "$pid" in ''|null|*[!0-9]*) return 0 ;; esac
  [ "$pid" -eq 0 ] && return 0
  ps -p "$pid" >/dev/null 2>&1 && return 0
  kill -0 "$pid" 2>/dev/null && return 0
  return 1
}

# --- Step 1: Merge session metrics into global metrics ---
# Merge INCREMENTAL. Antes era `cat "$metric_file" >> "$global_file"`: con Stop
# disparando por turno, cada turno reapendaba el archivo ENTERO y el global
# terminaba con N copias de las mismas filas. El offset por archivo hace el merge
# idempotente, y reejecutarlo sin filas nuevas no cuesta nada.
if [ "$MERGE_METRICS" = true ] && [ -d "$SESSION_DIR/metrics" ]; then
  mkdir -p "$GLOBAL_METRICS_DIR"

  MERGE_LOCK_DIR="$PROJECT_DIR/.cognitive-os/runtime/locks"
  mkdir -p "$MERGE_LOCK_DIR" 2>/dev/null || true
  MERGE_OFFSET_DIR="$SESSION_DIR/.merge-offsets"
  mkdir -p "$MERGE_OFFSET_DIR" 2>/dev/null || true

  for metric_file in "$SESSION_DIR/metrics"/*.jsonl; do
    [ ! -f "$metric_file" ] && continue
    basename_file=$(basename "$metric_file")
    global_file="$GLOBAL_METRICS_DIR/$basename_file"
    lockfile="$MERGE_LOCK_DIR/merge-${basename_file}.lock"
    offset_file="$MERGE_OFFSET_DIR/$basename_file"

    merged_bytes=0
    if [ -f "$offset_file" ]; then
      merged_bytes=$(tr -d '[:space:]' < "$offset_file" 2>/dev/null)
      case "$merged_bytes" in ''|*[!0-9]*) merged_bytes=0 ;; esac
    fi
    current_bytes=$(wc -c < "$metric_file" 2>/dev/null | tr -d '[:space:]')
    case "$current_bytes" in ''|*[!0-9]*) current_bytes=0 ;; esac
    # Rotacion o truncado del archivo de sesion: el offset viejo ya no aplica.
    [ "$current_bytes" -lt "$merged_bytes" ] && merged_bytes=0
    [ "$current_bytes" -le "$merged_bytes" ] && continue

    # Acquire per-file exclusive lock with 30s timeout; fail-open on timeout
    if command -v flock >/dev/null 2>&1; then
      if ! (
        flock -w 30 9 || {
          echo "[session-cleanup] WARN: lock timeout for $basename_file — skipping merge" >&2
          exit 1
        }
        tail -c "+$((merged_bytes + 1))" "$metric_file" >> "$global_file"
        printf '%s' "$current_bytes" > "$offset_file"
      ) 9>"$lockfile"; then
        continue
      fi
    else
      # Fallback: mkdir-based advisory lock (atomic on POSIX, no flock needed)
      # ADR-028 D4 fix (2026-04-20): moved deadline check to the while condition
      # (was in the loop body, allowing overshoot under slow `date` — CONCERN unbounded_loop).
      _lock_dir="${lockfile}.d"
      _lock_acquired=false
      _lock_deadline=$(( $(date +%s) + 30 ))
      while [ "$(date +%s)" -lt "$_lock_deadline" ]; do
        if mkdir "$_lock_dir" 2>/dev/null; then
          _lock_acquired=true
          break
        fi
        sleep 0.2 2>/dev/null || sleep 1
      done
      if [ "$_lock_acquired" = false ]; then
        echo "[session-cleanup] WARN: lock timeout (mkdir) for $basename_file — skipping merge" >&2
      fi
      if [ "$_lock_acquired" = true ]; then
        tail -c "+$((merged_bytes + 1))" "$metric_file" >> "$global_file"
        printf '%s' "$current_bytes" > "$offset_file"
        rmdir "$_lock_dir" 2>/dev/null || true
      else
        continue
      fi
    fi
  done
fi

# --- Step 2: Remove session from active-sessions.json ---
_deregister_session() {
  local lockfile="$SESSIONS_DIR/.active-sessions.lock"

  (
    flock -w 5 200 || { echo "WARN: Could not acquire lock for session deregistration" >&2; return 1; }

    if [ -f "$ACTIVE_FILE" ] && jq empty "$ACTIVE_FILE" 2>/dev/null; then
      jq --arg id "$SESSION_ID" \
         '.sessions = [.sessions[] | select(.id != $id)]' \
         "$ACTIVE_FILE" > "$ACTIVE_FILE.tmp" && mv "$ACTIVE_FILE.tmp" "$ACTIVE_FILE"
    fi

  ) 200>"$lockfile"
}

_deregister_session

# --- Step 3: Release locks whose OWNING PROCESS is gone ---
# Antes soltaba todo lock con el session_id de esta sesion. En un hook que
# dispara por turno eso significa arrancarle el lock a un escritor VIVO de la
# misma sesion: hooks/concurrent-write-guard.sh empezo a tomar locks reales el
# 2026-08-19 (commit 82969b80f) tras 1.062 invocaciones sin tomar ninguno, asi
# que a partir de hoy hay locks vivos que arrancar.
#
# Criterio nuevo: se suelta un lock solo cuando su .pid ya no existe. Es el mismo
# test de obsolescencia que el guard aplica sobre si mismo
# (hooks/concurrent-write-guard.sh: LOCK_AGE > LOCK_TIMEOUT o PID muerto), de
# modo que este paso ya no puede quitar un lock que su duenio siga usando; en el
# peor caso el guard lo recicla solo a los 300s.
LOCKS_DIR="$SESSIONS_DIR/locks"
if [ -d "$LOCKS_DIR" ] && command -v jq >/dev/null 2>&1; then
  for lockfile in "$LOCKS_DIR"/*.lock; do
    [ ! -f "$lockfile" ] && continue
    LOCK_SESSION=$(jq -r '.session_id' "$lockfile" 2>/dev/null)
    [ "$LOCK_SESSION" = "$SESSION_ID" ] || continue
    LOCK_PID=$(jq -r '.pid' "$lockfile" 2>/dev/null)
    case "$LOCK_PID" in ''|null|*[!0-9]*) continue ;; esac
    [ "$LOCK_PID" -eq 0 ] && continue
    ps -p "$LOCK_PID" >/dev/null 2>&1 && continue
    kill -0 "$LOCK_PID" 2>/dev/null && continue
    rm -f "$lockfile"
  done
fi

# --- Step 4: Retire the session directory (archive-first, never rm -rf) ---
# Aca vivia `rm -rf "$SESSION_DIR"`, incondicional salvo por cleanup_on_exit. Dos
# cosas lo hacian inaceptable:
#
#   1. Stop dispara por turno (ver _session_owner_alive), asi que el borrado caia
#      sobre una sesion VIVA. Con la identidad resuelta al id del arnes, el
#      objetivo habria sido .cognitive-os/sessions/$CLAUDE_CODE_SESSION_ID/, el
#      directorio que hooks/subagent-budget-enforcer.sh:106 usa como estado vivo
#      de presupuesto (210 contadores subagent-tool-calls-* al momento de medir).
#   2. Contradice ADR-119 (Session Filesystem Reaper, status: implemented), que
#      es el contrato escrito para este mismo directorio: archive-first, con
#      estados KEEP_ACTIVE / KEEP_PENDING_CONTENT / KEEP_RECENT_GRACE y borrado
#      recien en RM_ARCHIVED pasada la retencion. El reaper vive en
#      hooks/_lib/session-fs-reap.sh, lo invoca scripts/so-reaper.sh:305 y su
#      destino .cognitive-os/archive/sessions/ ya tenia 405 entradas.
#
# Un hook de Stop no puede decidir lo que ADR-119 decide con evidencia de PID,
# contenido pendiente y ventana de gracia. Lo unico que puede afirmar barato es
# "el duenio murio". Con eso: mueve el directorio al archivo del reaper, que se
# encarga de la retencion. Sin eso: no toca nada.
if [ "$CLEANUP_ON_EXIT" = true ] && [ -d "$SESSION_DIR" ] && ! _session_owner_alive; then
  ARCHIVE_DIR="$PROJECT_DIR/.cognitive-os/archive/sessions"
  mkdir -p "$ARCHIVE_DIR" 2>/dev/null || true
  ARCHIVE_TARGET="$ARCHIVE_DIR/$SESSION_ID"
  [ -e "$ARCHIVE_TARGET" ] && ARCHIVE_TARGET="$ARCHIVE_TARGET.$(date +%s)"
  mv "$SESSION_DIR" "$ARCHIVE_TARGET" 2>/dev/null || true
fi

# Clean up PID-based session file
rm -f "$SESSIONS_DIR/.current-session-$$" 2>/dev/null

# --- Step 5: Mark lost agents and log them ---
# Any task still in_progress when the session ends is considered lost.
TASKS_FILE="$PROJECT_DIR/.cognitive-os/tasks/active-tasks.json"
if [ -f "$TASKS_FILE" ] && command -v jq &>/dev/null && command -v python3 &>/dev/null; then
  LOST_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  METRICS_DIR="$GLOBAL_METRICS_DIR"
  mkdir -p "$METRICS_DIR" 2>/dev/null

  # Collect in_progress tasks before marking them lost
  LOST_TASKS=$(jq -c \
    '.tasks[] | select(.status == "in_progress")' \
    "$TASKS_FILE" 2>/dev/null || true)

  if [ -n "$LOST_TASKS" ]; then
    # Write one log entry per lost task
    while IFS= read -r task; do
      TASK_ID=$(echo "$task" | jq -r '.id // ""' 2>/dev/null)
      TASK_DESC=$(echo "$task" | jq -r '.description // ""' 2>/dev/null | head -c 200)
      LAUNCHED_AT=$(echo "$task" | jq -r '.launchedAt // ""' 2>/dev/null)

      # Calculate how long it was running (best effort)
      DURATION=0
      if [ -n "$LAUNCHED_AT" ]; then
        DURATION=$(python3 -c "
import sys
from datetime import datetime, timezone

def parse_iso(s):
    s = s.rstrip('Z')
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)

try:
    launched = parse_iso('$LAUNCHED_AT')
    from datetime import datetime as dt
    now = datetime.fromisoformat('$LOST_TIMESTAMP'.rstrip('Z')).replace(tzinfo=timezone.utc)
    print(int((now - launched).total_seconds()))
except Exception:
    print(0)
" 2>/dev/null || echo "0")
      fi

      printf '{"timestamp":"%s","task_id":"%s","duration_secs":%s,"status":"lost","description":"%s"}\n' \
        "$LOST_TIMESTAMP" "$TASK_ID" "$DURATION" \
        "$(echo "$TASK_DESC" | sed 's/"/\\"/g')" \
        >> "$METRICS_DIR/agent-timeouts.jsonl" 2>/dev/null || true
    done <<< "$LOST_TASKS"

    # Mark all in_progress tasks as lost in the file
    LOCK_FILE="$PROJECT_DIR/.cognitive-os/tasks/.active-tasks.lock"
    (
      flock -w 5 200 2>/dev/null || true
      MARKED=$(jq \
        --arg ts "$LOST_TIMESTAMP" \
        '(.tasks[] | select(.status == "in_progress")) |= . + {"status": "lost", "completedAt": $ts}' \
        "$TASKS_FILE" 2>/dev/null)
      [ -n "$MARKED" ] && echo "$MARKED" > "$TASKS_FILE"
    ) 200>"$LOCK_FILE" || true
  fi
fi

# --- Step 5b: Self-improve KPI flag ---
# Check last KPI snapshot. If first_pass_success_rate < 0.70 OR
# avg_trust_score < 60, write a flag so session-init warns next session.
SELF_IMPROVE_FLAG="$GLOBAL_METRICS_DIR/.self-improve-recommended"
KPI_FILE="$GLOBAL_METRICS_DIR/kpi-history.jsonl"

if [ -f "$KPI_FILE" ] && command -v python3 >/dev/null 2>&1; then
  KPI_VERDICT=$(python3 -c "
import json, sys

kpi_file = '$KPI_FILE'
flag_file = '$SELF_IMPROVE_FLAG'

try:
    with open(kpi_file, 'r') as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines:
        sys.exit(0)
    last = json.loads(lines[-1])
    first_pass = float(last.get('first_pass_success_rate', 1.0))
    avg_trust  = float(last.get('avg_trust_score', 100.0))
    if first_pass < 0.70 or avg_trust < 60.0:
        with open(flag_file, 'w') as fh:
            json.dump({'reason': 'first_pass_success_rate={:.2f} avg_trust_score={:.1f}'.format(first_pass, avg_trust),
                       'timestamp': last.get('timestamp', '')}, fh)
        print('RECOMMENDED')
    else:
        # Clear stale flag if KPIs recovered
        import os
        if os.path.exists(flag_file):
            os.remove(flag_file)
        print('OK')
except Exception as ex:
    print('ERROR:' + str(ex))
" 2>/dev/null || echo "SKIP")

  if [ "$KPI_VERDICT" = "RECOMMENDED" ]; then
    echo "SELF-IMPROVE RECOMMENDED: KPIs below threshold — run /self-improve at next session start." >&2
  fi
fi

# --- Step 6: Symbiosis Check (organism health) ---
# Measure overhead-to-value ratio. Alert if parasitic.
if command -v python3 >/dev/null 2>&1; then
  _symbiosis=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR/lib')
try:
    from symbiosis_monitor import SymbiosisMonitor
    m = SymbiosisMonitor('$PROJECT_DIR')
    r = m.generate_report()
    m.log_report(r)
    if r.health == 'parasitic':
        print('SYMBIOSIS WARNING: COS overhead ratio is {:.0%} (parasitic). {}'.format(r.overhead_ratio, r.recommendation or ''))
except Exception:
    pass
" 2>/dev/null)
  [ -n "$_symbiosis" ] && echo "$_symbiosis" >&2
fi

# --- Advisory: suggest session wrapup ---
# Non-blocking advisory so the user knows /session-wrapup is available.
echo "TIP: Run /session-wrapup before closing to inventory pending work and save session state to engram." >&2

exit 0
