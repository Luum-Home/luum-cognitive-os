#!/usr/bin/env bash
# SCOPE: os-only
# Prueba pareada del gate de cadencia: tests/contracts/test_hook_event_cadence.py.
#
# Un gate que exige un campo y acepta cualquier texto no sirve. Este script no
# demuestra que el gate "pasa"; demuestra QUE RECHAZA, y en las dos direcciones:
# el mismo evento sin cadencia da rojo y con cadencia da verde; y una cadencia
# con forma perfecta pero clase FALSA tambien da rojo, que es el caso que habria
# atajado el defecto de 2026-08-19 ("Stop = fin de sesion").
#
# Read-only sobre el repo en el neto: respalda los manifiestos bajo /tmp, los
# muta, corre el gate, y RESTAURA SIEMPRE via trap — incluso si pytest se cae o
# si alguien manda Ctrl-C. Correr dos veces seguidas da identico, y
# `git status manifests/` queda igual que antes de correrlo.
#
# Salida: 0 si los seis chequeos dieron el veredicto esperado, 1 si alguno no, 2 error.
#
# Uso:  bash scripts/proof-event-cadence-gate.sh
set -uo pipefail

# Raiz por ubicacion del propio script: el gate corre igual en un checkout git,
# en un worktree o en una instalacion desempaquetada de un tarball. Depender de
# Resolver la raiz preguntandole a git hacia que el script muriera con exit 2
# fuera de un checkout, que es exactamente lo que prohibe
# tests/contracts/test_script_root_portability.py.
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || exit 2
REPO="${COGNITIVE_OS_PROJECT_DIR:-$(cd "$_SCRIPT_DIR/.." && pwd)}"
[ -d "$REPO/manifests" ] || { echo "no encuentro la raiz del OS desde $_SCRIPT_DIR" >&2; exit 2; }
cd "$REPO" || exit 2
PY="$REPO/.venv/bin/python3"
[ -x "$PY" ] || { echo "falta .venv/bin/python3" >&2; exit 2; }

CC="manifests/claude-code-hooks-schema.yaml"
CX="manifests/codex-hooks-schema.yaml"
BK="$(mktemp -d /tmp/cadence-proof.XXXXXX)" || exit 2
cp "$CC" "$BK/cc.yaml"
cp "$CX" "$BK/cx.yaml"
# El respaldo queda bajo /tmp a proposito: restaurar es la parte que no puede
# fallar, y borrar el respaldo antes de que el trap corra seria la unica forma
# de que este script deje el repo mutado.
restore() {
  cp "$BK/cc.yaml" "$CC"
  cp "$BK/cx.yaml" "$CX"
}
trap restore EXIT INT TERM

FAILED=0
check() {  # $1 esperado(rojo|verde)  $2 etiqueta  $3 filtro -k
  local esperado="$1" etiqueta="$2" filtro="$3" out rc real
  out="$("$PY" -m pytest tests/contracts/test_hook_event_cadence.py -q -k "$filtro" 2>&1)"
  rc=$?
  real="verde"; [ "$rc" -ne 0 ] && real="rojo"
  if [ "$real" = "$esperado" ]; then
    printf '  OK    %-50s esperado=%-5s real=%s\n' "$etiqueta" "$esperado" "$real"
  else
    printf '  FALLA %-50s esperado=%-5s real=%s\n' "$etiqueta" "$esperado" "$real"
    echo "$out" | tail -4 | sed 's/^/         /'
    FAILED=1
  fi
}

echo "== [0] linea base: el repo tal como esta"
check verde "manifiestos actuales" "cadence or telemetry or agrees or absence"

echo "== [1] evento NUEVO en el esquema, sin fires_when"
"$PY" - <<'PY'
import pathlib
p = pathlib.Path("manifests/codex-hooks-schema.yaml"); s = p.read_text()
p.write_text(s.replace("  Stop:\n",
  "  SessionEnd:\n    matcher: unsupported\n    can_block: false\n\n  Stop:\n", 1))
PY
check rojo "evento nuevo SIN cadence" "declares_a_cadence"

echo "== [2] el MISMO evento, ahora con cadence completa"
"$PY" - <<'PY'
import pathlib
p = pathlib.Path("manifests/codex-hooks-schema.yaml"); s = p.read_text()
p.write_text(s.replace("  SessionEnd:\n    matcher: unsupported\n",
"""  SessionEnd:
    cadence:
      fires_when: >-
        Cuando termina el hilo principal de la sesion. Una vez por SESION, y no
        corre para subagentes. Es exactamente lo que Stop no es.
      per_session: exactly-1-per-session
      evidence: documented
      basis: [https://learn.chatgpt.com/docs/hooks]
      doc_quote: >-
        When the main thread ends SessionEnd (doesn't run for subagents)
      how: "curl -sSL https://learn.chatgpt.com/docs/hooks | grep -c SessionEnd"
    matcher: unsupported
""", 1))
PY
check verde "el mismo evento CON cadence" "declares_a_cadence or shape"

echo "== [3] cadence presente pero con prosa vaga"
"$PY" - <<'PY'
import pathlib
p = pathlib.Path("manifests/codex-hooks-schema.yaml"); s = p.read_text()
p.write_text(s.replace(
  "        Cuando termina el hilo principal de la sesion. Una vez por SESION, y no\n"
  "        corre para subagentes. Es exactamente lo que Stop no es.",
  "        Dispara cuando corresponde, segun el caso del turno de la sesion.", 1))
PY
check rojo "fires_when vago ('cuando corresponde')" "shape"

echo "== [4] forma VALIDA, clase FALSA: Stop declarado una-vez-por-sesion"
cp "$BK/cx.yaml" "$CX"
"$PY" - <<'PY'
import pathlib
p = pathlib.Path("manifests/claude-code-hooks-schema.yaml"); s = p.read_text()
i = s.index("  Stop:\n"); j = s.index("per_session: 0-N-per-turn", i)
p.write_text(s[:j] + "per_session: exactly-1-per-session" + s[j+len("per_session: 0-N-per-turn"):])
PY
check verde "la MENTIRA pasa las capas de forma"    "shape"
check rojo  "y muere contra la telemetria del repo" "agrees_with_todays_telemetry"

echo
if [ "$FAILED" -eq 0 ]; then
  echo "seis chequeos, seis veredictos esperados."
else
  echo "hay chequeos fuera de lo esperado."
fi
exit "$FAILED"
