#!/usr/bin/env bash
# SCOPE: os-only
# verify-metrics-dir-override.sh — COS_METRICS_DIR gana; la segregacion sobrevive.
#
# Read-only sobre el repo. Todo lo que escribe cae en un directorio temporal
# propio: el "directorio del operador" de esta prueba es un proyecto FALSO
# (COGNITIVE_OS_PROJECT_DIR), nunca `.cognitive-os/metrics` del repo real.
#
# Exit: 0 sin hallazgos | 1 hallazgos | 2 error
set -uo pipefail

# SCRIPT_HOME es SIEMPRE el repo real: de ahi salen el detector y el conftest,
# que son el gate y no el codigo bajo prueba. REPO es el arbol a ejercitar y
# puede apuntarse a una copia parchada con COS_VERIFY_REPO.
SCRIPT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${COS_VERIFY_REPO:-$SCRIPT_HOME}"
HOOK="$REPO/hooks/lethal-trifecta-gate.sh"
[ -x "$HOOK" ] || { echo "ERROR: no ejecutable: $HOOK" >&2; exit 2; }

FINDINGS=0
WORK="$(mktemp -d "${TMPDIR:-/tmp}/cos-metrics-override.XXXXXX")" || exit 2
trap 'rm -rf "$WORK"' EXIT

PAYLOAD='{"session_id":"probe-session","tool_name":"Bash","tool_input":{"command":"echo hola"}}'

# Entorno limpio: sin bypasses heredados, sin identidad de la sesion viva.
unset COS_ALLOW_PROTECTED_CONFIG_WRITE COS_BYPASS 2>/dev/null || true
unset COGNITIVE_OS_SESSION_ID CLAUDE_CODE_SESSION_ID CODEX_SESSION_ID CLAUDE_SESSION_ID 2>/dev/null || true
unset COS_SESSION_SCOPED_METRICS COS_METRICS_DIR 2>/dev/null || true

# Corre el hook en un proyecto falso. $1 = etiqueta; el resto son VAR=VAL extra.
run_case() {
  local label="$1"; shift
  local proj="$WORK/$label/proj"
  mkdir -p "$proj/.cognitive-os/metrics" || return 2
  env -i \
    PATH="$PATH" HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" \
    COGNITIVE_OS_PROJECT_DIR="$proj" \
    COGNITIVE_OS_HOOK_HEARTBEAT=false \
    "$@" \
    bash "$HOOK" <<<"$PAYLOAD" >"$WORK/$label.out" 2>"$WORK/$label.err"
  echo "$proj"
}

# ─── Control A: COS_METRICS_DIR gana ─────────────────────────────────────────
SANDBOX="$WORK/a/sandbox"; mkdir -p "$SANDBOX"
PROJ_A="$(run_case a COS_METRICS_DIR="$SANDBOX")"
A_SANDBOX=$(ls -1 "$SANDBOX" 2>/dev/null | grep -c '\.jsonl$' || true)
A_OPERADOR=$(ls -1 "$PROJ_A/.cognitive-os/metrics" 2>/dev/null | grep -c '\.jsonl$' || true)
echo "A  COS_METRICS_DIR seteada -> sandbox:${A_SANDBOX}  operador-falso:${A_OPERADOR}"
if [ "$A_SANDBOX" -lt 1 ]; then
  echo "   HALLAZGO: con COS_METRICS_DIR seteada, el sandbox quedo VACIO"; FINDINGS=1
fi
if [ "$A_OPERADOR" -ne 0 ]; then
  echo "   HALLAZGO: escribio en la ruta del operador pese al override:"
  ls -l "$PROJ_A/.cognitive-os/metrics"; FINDINGS=1
fi

# ─── Control B: sin COS_METRICS_DIR, la segregacion por sesion sigue viva ────
SID="segregacion-viva-42"
PROJ_B_PRE="$WORK/b/proj"; mkdir -p "$PROJ_B_PRE/.cognitive-os/sessions/$SID"
PROJ_B="$(run_case b COS_SESSION_SCOPED_METRICS=1 CLAUDE_CODE_SESSION_ID="$SID")"
B_SESION=$(ls -1 "$PROJ_B/.cognitive-os/sessions/$SID/metrics" 2>/dev/null | grep -c '\.jsonl$' || true)
B_GLOBAL=$(ls -1 "$PROJ_B/.cognitive-os/metrics" 2>/dev/null | grep -c '\.jsonl$' || true)
echo "B  sin override, scoped=1  -> sesion:${B_SESION}  global:${B_GLOBAL}"
if [ "$B_SESION" -lt 1 ]; then
  echo "   HALLAZGO: la segregacion por sesion se rompio (nada en sessions/$SID/metrics)"; FINDINGS=1
fi
if [ "$B_GLOBAL" -ne 0 ]; then
  echo "   HALLAZGO: con scoped=1 igual cayo al global"; FINDINGS=1
fi

# ─── Control C: sin override y sin scoped -> global (comportamiento previo) ──
PROJ_C="$(run_case c)"
C_GLOBAL=$(ls -1 "$PROJ_C/.cognitive-os/metrics" 2>/dev/null | grep -c '\.jsonl$' || true)
echo "C  sin override, sin scoped -> global:${C_GLOBAL}"
if [ "$C_GLOBAL" -lt 1 ]; then
  echo "   HALLAZGO: el default (global) dejo de escribir"; FINDINGS=1
fi

# ─── Control D: safe-jsonl.sh (_resolve_metrics_dir / heartbeat) ─────────────
SANDBOX_D="$WORK/d/sandbox"; PROJ_D="$WORK/d/proj"
mkdir -p "$SANDBOX_D" "$PROJ_D/.cognitive-os/metrics"
D_ECHO=$(env -i PATH="$PATH" HOME="$HOME" \
  COGNITIVE_OS_PROJECT_DIR="$PROJ_D" COS_METRICS_DIR="$SANDBOX_D" \
  bash -c 'source "'"$REPO"'/hooks/_lib/safe-jsonl.sh"; _resolve_metrics_dir' 2>/dev/null)
env -i PATH="$PATH" HOME="$HOME" \
  COGNITIVE_OS_PROJECT_DIR="$PROJ_D" COS_METRICS_DIR="$SANDBOX_D" \
  bash -c 'source "'"$REPO"'/hooks/_lib/safe-jsonl.sh"; _emit_heartbeat' >/dev/null 2>&1
D_HB_SANDBOX=$([ -f "$SANDBOX_D/hook-health.jsonl" ] && echo 1 || echo 0)
D_HB_OPERADOR=$([ -f "$PROJ_D/.cognitive-os/metrics/hook-health.jsonl" ] && echo 1 || echo 0)
echo "D  safe-jsonl: _resolve_metrics_dir='${D_ECHO}'  heartbeat sandbox:${D_HB_SANDBOX} operador-falso:${D_HB_OPERADOR}"
if [ "$D_ECHO" != "$SANDBOX_D" ]; then
  echo "   HALLAZGO: safe-jsonl no honra COS_METRICS_DIR (esperaba $SANDBOX_D)"; FINDINGS=1
fi
if [ "$D_HB_OPERADOR" -ne 0 ]; then
  echo "   HALLAZGO: el heartbeat escribio en la ruta del operador"; FINDINGS=1
fi

# ─── Control E: el gate sigue cazando a un escritor que IGNORA la variable ───
# Arreglar el tronco no puede volver invisible a una hoja que hardcodea la ruta.
# La deteccion de la capa 2 mira el FILESYSTEM, no el resolver, asi que se
# ejercita con las funciones reales de `conftest.py` sobre un operador falso.
SEEDED="$WORK/e/proj"; mkdir -p "$SEEDED/.cognitive-os/metrics"
cat > "$WORK/e/escritor-sembrado.sh" <<'SEED'
#!/usr/bin/env bash
# Escritor sembrado A PROPOSITO: hardcodea la ruta, no consulta COS_METRICS_DIR.
echo '{"sembrado":true}' >> "$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/sembrado.jsonl"
SEED
chmod +x "$WORK/e/escritor-sembrado.sh"
E_OUT=$(COS_VERIFY_SEEDED_HOOK="$WORK/e/escritor-sembrado.sh" \
        COS_VERIFY_SEEDED_PROJ="$SEEDED" \
        COS_VERIFY_SANDBOX="$WORK/e/sandbox" \
        python3 "$SCRIPT_HOME/scripts/verify_seeded_writer_detected.py" 2>&1) || true
echo "E  $E_OUT"
case "$E_OUT" in
  DETECTADO*) : ;;
  *) echo "   HALLAZGO: el gate dejo de cazar al escritor sembrado"; FINDINGS=1 ;;
esac

echo "---"
if [ "$FINDINGS" -eq 0 ]; then echo "OK: sin hallazgos"; else echo "HALLAZGOS presentes"; fi
exit "$FINDINGS"
