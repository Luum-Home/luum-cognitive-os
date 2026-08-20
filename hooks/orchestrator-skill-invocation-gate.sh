#!/usr/bin/env bash
# SCOPE: both
# orchestrator-skill-invocation-gate.sh — ADR-188
#
# PreToolUse hook (matcher: Agent, Bash). Enforces that when the skill router
# emits a high-confidence (>=0.90) suggestion since the most recent user
# prompt, the orchestrator does ONE of:
#   1. invoke the suggested (or strictly stronger) skill, OR
#   2. include a `SKILL_BYPASS: <skill> confidence=<N> reason=<short>` line in
#      the tool input (e.g. inside the agent prompt or bash command), OR
#   3. set COS_ALLOW_SKILL_BYPASS=1 + COS_SKILL_BYPASS_REASON=<text> for an
#      emergency env-override.
#
# Killswitch:  DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE=1
# Exit codes: 0=allow, 2=BLOCK.

set -uo pipefail

if [ "${DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE:-0}" = "1" ]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}}"

INPUT="$(cat)"
[ -z "$INPUT" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)"
case "$TOOL_NAME" in
  Agent|Bash|task|delegate) ;;
  *) exit 0 ;;
esac

# Identidad: UN solo resolvedor, compartido con el productor.
#
# Esta linea era una cadena propia —COGNITIVE_OS_SESSION_ID, CLAUDE_SESSION_ID,
# payload— y tenia un agujero medido: `CLAUDE_SESSION_ID` (sin CODE) no existe
# (0 ocurrencias en env-vars.md), y la variable que el arnes SI exporta,
# `CLAUDE_CODE_SESSION_ID`, no estaba en la cadena. Que hoy coincidan es
# casualidad del arnes (la doc dice que esa variable "matches the session_id
# field in the hook JSON input"), no una garantia.
#
# Un gate que resuelve la identidad distinto que el productor de la evidencia es
# el mismo bug de fondo que se esta arreglando: dos puntas que creen hablar de la
# misma sesion. cos_session_id() (hooks/_lib/common.sh) es la primitiva unica, y
# su paso 3 lee justamente el `INPUT="$(cat)"` que este hook ya hizo.
# shellcheck source=_lib/common.sh
. "$(dirname "${BASH_SOURCE[0]}")/_lib/common.sh" 2>/dev/null || true
if command -v cos_session_id >/dev/null 2>&1; then
  SESSION_ID="$(cos_session_id 2>/dev/null || true)"
else
  SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_CODE_SESSION_ID:-$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null)}}"
fi

# ─── Sin identidad probada, el gate NO decide ────────────────────────────────
# Antes esta linea decia `[ -z "$SESSION_ID" ] && SESSION_ID="unknown"`, y esa
# fabricacion era el bug: `unknown` no es "sin identidad", es una CLAVE, y una
# clave compartida por todo el que no dijo quien era. El contador vive en
# `$RUNTIME_DIR/skill-bypass-counter-$SESSION_ID`, asi que cualquier payload sin
# `session_id` —un test, una sonda de portabilidad, un replay— leia y escribia
# el mismo bucket. Consecuencias medidas el 2026-08-20:
#   - el contador `-unknown` acumulaba desde 2026-05-18 y llego a 143 con umbral
#     3, o sea que TODO payload anonimo quedaba bloqueado para siempre;
#   - las 11 filas de skill-bypass.jsonl decian "BLOCK tras N bypasses en la
#     sesion" con N=132..142 y el MISMO prompt_hash: N contaba replays, no
#     comportamiento;
#   - el veredicto de un test dependia del estado del operador y lo movia.
#
# Un veredicto sin sujeto no es un veredicto: el gate se abstiene. No bloquea
# (no puede probar que haya habido un bypass) y no aprueba en silencio (una
# guarda que evalua y no registra es indistinguible de una guarda rota): deja la
# fila en un bucket anonimo EXPLICITO que ningun gate lee para decidir.
#
# No se sintetiza un id falso a proposito. Ponerle nombre a la herencia no la
# corta: la vuelve mas dificil de ver.
if [ -z "$SESSION_ID" ]; then
  ANON_DIR="${COS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}/anonymous"
  mkdir -p "$ANON_DIR" 2>/dev/null || true
  python3 - "$ANON_DIR/skill-bypass-anonymous.jsonl" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$TOOL_NAME" <<'PYEOF' 2>/dev/null || true
import json, sys
path, ts, tool = sys.argv[1:]
with open(path, "a") as fh:
    fh.write(json.dumps({
        "ts": ts, "session_id": None, "tool_name": tool,
        "actor": "gate", "outcome": "abstained",
        "reason": "sin identidad de sesion probada: el gate no decide",
    }) + "\n")
PYEOF
  exit 0
fi

LS_OUT="$(PROJECT_DIR="$PROJECT_DIR" SESSION_ID="$SESSION_ID" python3 - <<'PYEOF' 2>/dev/null || true
import os, sys, json
project = os.environ.get("PROJECT_DIR", ".")
sys.path.insert(0, project)
try:
    from cos_lib.skill_router import last_suggestion
except Exception:
    print("")
    sys.exit(0)
sid = os.environ.get("SESSION_ID", "")
res = last_suggestion(sid, project_root=project)
print(json.dumps(res) if res else "")
PYEOF
)"

[ -z "$LS_OUT" ] && exit 0

CONF="$(printf '%s' "$LS_OUT" | jq -r '.confidence // 0' 2>/dev/null)"
SKILL="$(printf '%s' "$LS_OUT" | jq -r '.skill // ""' 2>/dev/null)"
PROMPT_HASH="$(printf '%s' "$LS_OUT" | jq -r '.prompt_hash // ""' 2>/dev/null)"
# Marca de tiempo de la fila de skill-suggestion.jsonl que gano. El productor
# escribe UNA fila por UserPromptSubmit, asi que este ts identifica el ENVIO del
# prompt, no la herramienta que se esta por correr. Es la unidad que cuenta la
# politica de insistencia mas abajo.
SUGGESTION_TS="$(printf '%s' "$LS_OUT" | jq -r '.timestamp // ""' 2>/dev/null)"

HIGH_CONF="$(awk -v c="$CONF" 'BEGIN { print (c+0 >= 0.90) ? "1" : "0" }')"
if [ "$HIGH_CONF" != "1" ]; then
  exit 0
fi
[ -z "$SKILL" ] && exit 0

EVENTS_FILE="$PROJECT_DIR/.cognitive-os/sessions/events.jsonl"
TOOL_BLOB="$(printf '%s' "$INPUT" | jq -r '
  [ (.tool_input // {} | tostring),
    (.tool_input.prompt // ""),
    (.tool_input.command // ""),
    (.tool_input.cmd // ""),
    (.tool_input.description // "") ] | join("\n")' 2>/dev/null || true)"

INVOKED=0
if printf '%s' "$TOOL_BLOB" | grep -qE "(Load[[:space:]]+\`?skills/${SKILL}/SKILL\.md|/${SKILL}([[:space:]]|\$|\`)|skill:[[:space:]]*\"?${SKILL}\"?)"; then
  INVOKED=1
fi

if [ "$INVOKED" = "0" ] && [ -f "$EVENTS_FILE" ]; then
  if python3 - "$EVENTS_FILE" "$SESSION_ID" "$SKILL" <<'PYEOF' >/dev/null 2>&1
import json, sys
path, sid, skill = sys.argv[1], sys.argv[2], sys.argv[3]
anchor = None
try:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
except Exception:
    sys.exit(1)
for line in lines:
    try:
        e = json.loads(line)
    except Exception:
        continue
    if e.get("session_id") != sid: continue
    et = (e.get("event_type") or "").lower()
    if et in ("user_prompt_submit", "userpromptsubmit", "user_prompt"):
        ts = e.get("ts") or ""
        if anchor is None or ts > anchor: anchor = ts
for line in lines:
    try:
        e = json.loads(line)
    except Exception:
        continue
    if e.get("session_id") != sid: continue
    et = (e.get("event_type") or "").lower()
    if et not in ("skill-invoked", "skill_invoked"): continue
    ts = e.get("ts") or ""
    if anchor and ts < anchor: continue
    payload = e.get("payload") or {}
    name = payload.get("skill") or payload.get("skill_name") or ""
    if name == skill: sys.exit(0)
sys.exit(1)
PYEOF
  then
    INVOKED=1
  fi
fi

ANNOTATED=0
BYPASS_REASON=""
if printf '%s' "$TOOL_BLOB" | grep -qE "SKILL_BYPASS:[[:space:]]*${SKILL}([[:space:]]|\$)"; then
  ANNOTATED=1
  BYPASS_REASON="$(printf '%s' "$TOOL_BLOB" | grep -oE "SKILL_BYPASS:[[:space:]]*${SKILL}[^\"]*" | head -1)"
fi

# COS_METRICS_DIR redirige la escritura sin tocar PROJECT_DIR. Es la convencion
# que ya honran plan-claim-validator.sh y scope-marker-portability-gate.sh, y la
# que el conftest de la raiz exporta para toda la suite.
METRICS_DIR="${COS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
mkdir -p "$METRICS_DIR" "$RUNTIME_DIR" 2>/dev/null || true
AUDIT_FILE="$METRICS_DIR/skill-bypass.jsonl"

# Barrido acotado del estado propio. La politica nueva crea un archivo por
# (sesion, prompt_hash, skill) en vez de uno por sesion, asi que sin poda el
# directorio crece con cada prompt de alta confianza (~1/dia medido sobre 94
# dias: 104 hashes distintos con confianza >=0.90). Solo toca el prefijo que
# este hook escribe. NO toca skill-bypass-counter-*: ese contador es estado del
# operador y su existencia es la evidencia de que el diseno viejo latcheaba;
# se deja en disco y ningun camino de codigo lo vuelve a leer.
find "$RUNTIME_DIR" -maxdepth 1 -type f -name 'skill-gate-*' -mtime +7 -delete 2>/dev/null || true

# Emite UNA fila de auditoria por decision evaluada. Una guarda que evalua y no
# emite nada es indistinguible de una guarda rota: el consumidor
# (scripts/skill_adherence_loop.py) no puede distinguir "nadie bypasseo" de "el
# productor nunca escribio". Por eso escriben TODAS las ramas, incluida la
# positiva.
#
# Contrato que consume load_bypasses() en scripts/skill_adherence_loop.py:
#   ts | timestamp  -> ISO8601 parseable (si falta, la fila se descarta)
#   suggested_skill -> nombre de la skill (si falta, la fila se descarta)
#   reason          -> NO VACIO => audited=True  => aparea y cuenta BYPASSED
#                      VACIO    => audited=False => la fila NO se aparea
#   prompt_hash     -> aparea con la sugerencia sin depender de la ventana
#   confidence, session_id, actor, outcome -> contexto
_emit_audit() {
  local reason="$1" actor="$2" outcome="$3"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "$AUDIT_FILE" "$ts" "$SESSION_ID" "$PROMPT_HASH" "$SKILL" "$CONF" "$reason" "$actor" "$outcome" <<'PYEOF' 2>/dev/null || true
import json, sys
path, ts, sid, ph, skill, conf, reason, actor, outcome = sys.argv[1:]
entry = {"ts": ts, "session_id": sid, "prompt_hash": ph,
         "suggested_skill": skill, "confidence": float(conf or 0.0),
         "reason": reason, "actor": actor, "outcome": outcome}
with open(path, "a") as fh:
    fh.write(json.dumps(entry) + "\n")
PYEOF
}

# La rama positiva dispara en CADA tool call mientras la sugerencia siga viva.
# Se deduplica por (sesion, prompt_hash, skill) para que el log registre la
# decision una vez y no una por herramienta.
# Clave de la decision: (sesion, prompt de origen, skill exigida). La misma
# terna identifica el marcador de "ya paso" y el contador de insistencia, para
# que las dos mitades hablen del mismo hecho.
_gate_key() {
  local ph="${PROMPT_HASH:-nohash}"
  printf '%s-%s-%s' "$SESSION_ID" "$ph" "$SKILL" | tr -c 'A-Za-z0-9._-' '_'
}

_pass_marker_path() {
  printf '%s/skill-gate-pass-%s' "$RUNTIME_DIR" "$(_gate_key)"
}

if [ "$INVOKED" = "1" ]; then
  # Caso positivo: reason VACIO a proposito. El consumidor solo aparea filas
  # con razon escrita, asi que un `pass` nunca se puede leer como un bypass.
  PASS_MARKER="$(_pass_marker_path)"
  if [ ! -f "$PASS_MARKER" ]; then
    : > "$PASS_MARKER" 2>/dev/null || true
    _emit_audit "" "gate" "invoked"
  fi
  exit 0
fi

if [ "$ANNOTATED" = "1" ]; then
  _emit_audit "${BYPASS_REASON:-annotated}" "orchestrator-annotation" "bypass-annotated"
  exit 0
fi

if [ "${COS_ALLOW_SKILL_BYPASS:-0}" = "1" ]; then
  reason="${COS_SKILL_BYPASS_REASON:-}"
  if [ -z "$reason" ]; then
    printf 'orchestrator-skill-invocation-gate: COS_ALLOW_SKILL_BYPASS=1 requires COS_SKILL_BYPASS_REASON=<text>\n' >&2
    exit 2
  fi
  _emit_audit "env-override: $reason" "env-override" "env-override"
  exit 0
fi

# ─── Politica de insistencia (reemplaza el acumulado de por vida) ────────────
# Lo que habia: un contador por SESION en skill-bypass-counter-<sesion>, +1 por
# cada tool call, sin ningun camino de reset en el repo. Estado real medido el
# 2026-08-20: el archivo `-unknown` nacio el 2026-05-18 y marcaba 143 contra un
# umbral de 3, o sea latcheado en BLOCK desde su cuarta lectura. Ese numero no
# describia conducta, describia antiguedad: contaba herramientas a lo largo de
# 94 dias, no insistencia.
#
# Lo que cuenta ahora: cuantas veces se re-envio EL MISMO prompt (mismo
# prompt_hash) recibiendo LA MISMA sugerencia de alta confianza sin invocarla ni
# anotarla. Eso si es conducta — el operador vio el aviso, mando de nuevo lo
# mismo, y volvio a ignorarlo.
#
# La unidad es el ENVIO, no la herramienta: el contador solo avanza cuando
# cambia el ts de la fila de sugerencia, que el productor escribe una vez por
# UserPromptSubmit. Veinte tool calls dentro de un mismo turno cuentan uno.
#
# El reset es estructural, no un barrido: cambiar de prompt cambia el hash, y el
# hash es parte del nombre del archivo. No hay contador que limpiar para volver
# a cero, ni estado que pueda quedar latcheado como el de mayo.
#
# El umbral: 3 envios. Medido sobre las 584 filas de skill-suggestion.jsonl
# (94 dias), de 104 prompt_hash distintos con confianza >=0.90, 4 se repitieron
# alguna vez, 3 llegaron a 3 envios y 2 a 5 o mas. Entre N=2 y N=3 la diferencia
# medida es UN prompt en 94 dias, asi que se elige el mas indulgente, que ademas
# es la constante que ADR-188 ya documenta.
INSIST_THRESHOLD="${COS_SKILL_GATE_INSIST_THRESHOLD:-3}"
INSIST_FILE="$RUNTIME_DIR/skill-gate-insist-$(_gate_key)"

count=0
last_ts=""
if [ -f "$INSIST_FILE" ]; then
  IFS="$(printf '\t')" read -r count last_ts < "$INSIST_FILE" 2>/dev/null || true
  case "$count" in ''|*[!0-9]*) count=0 ;; esac
fi

ADVANCED=0
if [ "$SUGGESTION_TS" != "$last_ts" ]; then
  count=$((count + 1))
  ADVANCED=1
  printf '%s\t%s' "$count" "$SUGGESTION_TS" > "$INSIST_FILE" 2>/dev/null || true
fi

if [ "$count" -ge "$INSIST_THRESHOLD" ]; then
  # La fila de auditoria sale una vez por ENVIO, igual que el contador. Bloquear
  # sale en cada tool call: el veredicto vale para el turno entero.
  if [ "$ADVANCED" = "1" ]; then
    _emit_audit "unannotated: BLOCK tras $count envios del mismo prompt (hash ${PROMPT_HASH:-nohash}) sin invocar ni anotar SKILL_BYPASS" \
      "gate" "blocked"
  fi
  printf 'orchestrator-skill-invocation-gate: BLOCK — high-confidence skill `%s` (conf=%s) was suggested for this same prompt %s times and still not invoked. Either invoke the skill, add `SKILL_BYPASS: %s confidence=%s reason=<short>` to the tool input, or set COS_ALLOW_SKILL_BYPASS=1 + COS_SKILL_BYPASS_REASON=<text>. Rewording the request clears the count.\n' "$SKILL" "$CONF" "$count" "$SKILL" "$CONF" >&2
  exit 2
fi

if [ "$ADVANCED" = "1" ]; then
  _emit_audit "unannotated: skill de alta confianza no invocada y sin anotacion SKILL_BYPASS (envio $count/$INSIST_THRESHOLD de este prompt, tool permitido)" \
    "gate" "bypass-unannotated"
fi
printf 'orchestrator-skill-invocation-gate: WARN — high-confidence skill `%s` (conf=%s) was suggested for this prompt but not invoked. (%s/%s repeats of this prompt before BLOCK)\n' "$SKILL" "$CONF" "$count" "$INSIST_THRESHOLD" >&2
exit 0
