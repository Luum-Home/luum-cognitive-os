#!/usr/bin/env bash
# SCOPE: os-only
#
# Prueba por EFECTO EN DISCO del camino de retiro de sesion de
# hooks/session-cleanup.sh. Nunca por exit code: el hook sale 0 tanto cuando
# hace lo correcto como cuando destruye una sesion viva, y esa es exactamente
# la razon por la que el defecto sobrevivio un dia entero.
#
#   RUN A  sesion VIVA (la propia del proceso)  -> no se toca nada
#   RUN B  duenio PROBADAMENTE MUERTO           -> archivado ADR-119 + merge x1
#   RUN C  contrafactico: identidad arreglada + el borrado que desarmo el paso 1
#          -> el danio vuelve. Si C no reproduce, el modelo del defecto es falso.
#
# RUN C opera sobre una COPIA del hook en un temporal. El arbol del repo no se
# modifica en ningun momento; el script lo verifica por sha256 al terminar.
#
# Uso: bash scripts/session-cleanup-counterfactual.sh <dir-temporal>
set -uo pipefail

REPO="${COS_REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HOOK="$REPO/hooks/session-cleanup.sh"
TP="${1:?uso: $0 <dir-temporal>}"
SID="fake-session-abc123"
OTRA="sesion-de-otro-proceso"

HOOK_SHA_ANTES="$(shasum -a 256 "$HOOK" | awk '{print $1}')"

# Un PID libre de verdad: se arranca un proceso, se espera a que muera y se
# confirma con ps que ya no esta. Nada de inventar un numero grande.
_pid_muerto() {
  local p i=0
  p=$(sh -c 'echo $$')
  while ps -p "$p" >/dev/null 2>&1 && [ "$i" -lt 50 ]; do sleep 0.1; i=$((i+1)); done
  ps -p "$p" >/dev/null 2>&1 && { echo "no pude conseguir un PID muerto" >&2; exit 2; }
  printf '%s' "$p"
}
PID_MUERTO="$(_pid_muerto)"

setup() {
  find "$TP" -mindepth 1 -delete 2>/dev/null || true
  mkdir -p "$TP/.cognitive-os/sessions/locks" "$TP/.cognitive-os/metrics"
  mkdir -p "$TP/.cognitive-os/sessions/$SID/metrics"
  printf '{"m":1}\n{"m":2}\n' > "$TP/.cognitive-os/sessions/$SID/metrics/skill-metrics.jsonl"
  echo 'LIVE' > "$TP/.cognitive-os/sessions/$SID/subagent-tool-calls-agentX"
  printf '{"session_id":"%s","pid":%s,"start_time":"x","working_directory":"%s"}\n' \
    "$SID" "$1" "$TP" > "$TP/.cognitive-os/sessions/$SID/meta.json"
  printf '{"session_id":"%s","pid":%s,"file_path":"/x"}\n' "$SID" "$PID_MUERTO" \
    > "$TP/.cognitive-os/sessions/locks/aaa.lock"
  printf '{"session_id":"otra","pid":2,"file_path":"/y"}\n' \
    > "$TP/.cognitive-os/sessions/locks/bbb.lock"
  printf '{"sessions":[{"id":"%s"}]}\n' "$SID" > "$TP/.cognitive-os/sessions/active-sessions.json"
}

report() {
  local d="$TP/.cognitive-os/sessions/$SID"
  local arch="$TP/.cognitive-os/archive/sessions/$SID"
  echo "  session dir  : $([ -d "$d" ] && echo EXISTE || echo BORRADO)"
  if [ -f "$d/subagent-tool-calls-agentX" ]; then
    echo "  contenido    : INTACTO en su lugar"
  elif [ -f "$arch/subagent-tool-calls-agentX" ]; then
    echo "  contenido    : INTACTO en el archivo (nada se destruyo)"
  else
    echo "  contenido    : DESTRUIDO"
  fi
  echo "  archivado    : $([ -d "$arch" ] && echo "SI -> archive/sessions/$SID" || echo NO)"
  echo "  registrada   : $(jq -c '.sessions | map(.id)' "$TP/.cognitive-os/sessions/active-sessions.json" 2>/dev/null)"
  echo "  merge global : $([ -f "$TP/.cognitive-os/metrics/skill-metrics.jsonl" ] \
      && echo "SI ($(wc -l < "$TP/.cognitive-os/metrics/skill-metrics.jsonl" | tr -d ' ') lineas)" || echo NO)"
}

echo "### RUN A - la sesion esta VIVA (es la del propio proceso)"
echo "# La identidad resuelve, y aun asi no se toca nada: Stop corre DENTRO de"
echo "# la sesion, o sea que esta viva por construccion."
setup "$PID_MUERTO"
CLAUDE_PROJECT_DIR="$TP" CLAUDE_CODE_SESSION_ID="$SID" \
  "$HOOK" </dev/null >/dev/null 2>&1
report
echo

echo "### RUN B - duenio PROBADAMENTE MUERTO (sesion ajena, PID $PID_MUERTO, fuera de gracia)"
echo "# Se dispara DOS veces para probar que el merge es incremental por offset."
setup "$PID_MUERTO"
touch -t 202601010000 "$TP/.cognitive-os/sessions/$SID"
CLAUDE_PROJECT_DIR="$TP" CLAUDE_CODE_SESSION_ID="$OTRA" COGNITIVE_OS_SESSION_ID="$SID" \
  "$HOOK" </dev/null >/dev/null 2>&1
echo "  -- despues del disparo 1 --"; report
CLAUDE_PROJECT_DIR="$TP" CLAUDE_CODE_SESSION_ID="$OTRA" COGNITIVE_OS_SESSION_ID="$SID" \
  "$HOOK" </dev/null >/dev/null 2>&1
echo "  -- despues del disparo 2 (el merge NO debe duplicar) --"; report
echo

echo "### RUN C - CONTRAFACTICO: identidad arreglada + el borrado que desarmo el paso 1"
echo "# Copia mutada del hook en un temporal. El repo no se toca."
MUT_DIR="${TP}-mutante"
mkdir -p "$MUT_DIR"
MUT="$MUT_DIR/session-cleanup-MUTADO.sh"
python3 - "$HOOK" "$MUT" <<'PYMUT'
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
# 1. Reintroduce el borrado incondicional que el paso 1 (4d9bec980) desarmo.
guard = 'if [ "$CLEANUP_ON_EXIT" = true ] && [ -d "$SESSION_DIR" ] && [ "$SESSION_OWNER_ALIVE" = false ]; then'
assert guard in s, "no encontre el guard del paso 4"
s = s.replace(guard, 'if [ "$CLEANUP_ON_EXIT" = true ] && [ -d "$SESSION_DIR" ]; then\n  rm -rf "$SESSION_DIR"', 1)
# 2. Y el deregistro incondicional que este cambio guardo.
s = s.replace('if [ "$SESSION_OWNER_ALIVE" = false ]; then\n  _deregister_session\nfi', '_deregister_session', 1)
assert 'rm -rf "$SESSION_DIR"' in s
open(dst, "w").write(s)
PYMUT
setup "$PID_MUERTO"
bash -n "$MUT" || { echo "  ERROR: el mutante no compila" >&2; exit 2; }
CLAUDE_PROJECT_DIR="$TP" CLAUDE_CODE_SESSION_ID="$SID" \
  bash "$MUT" </dev/null >/dev/null 2>&1
report
echo

HOOK_SHA_DESPUES="$(shasum -a 256 "$HOOK" | awk '{print $1}')"
echo "### Integridad del arbol"
echo "  hooks/session-cleanup.sh sha256 antes  : $HOOK_SHA_ANTES"
echo "  hooks/session-cleanup.sh sha256 despues: $HOOK_SHA_DESPUES"
if [ "$HOOK_SHA_ANTES" = "$HOOK_SHA_DESPUES" ]; then
  echo "  -> IDENTICO (el contrafactico nunca toco el repo)"
else
  echo "  -> EL ARBOL CAMBIO"; exit 1
fi
exit 0
