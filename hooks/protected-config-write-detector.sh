#!/usr/bin/env bash
# SCOPE: os-only
# SPDX-License-Identifier: MIT
#
# PostToolUse: caza las escrituras a rutas protegidas que el guard de PreToolUse no
# puede ver, porque aquel inspecciona el TEXTO DEL COMANDO y una escritura hecha
# desde un script no aparece ahi. Medido 2026-08-20: `echo x >> rules/X.md` bloquea,
# `python3 scripts/escritor.py` que escribe lo mismo PASA.
#
# Envoltorio fino: la logica y su documentacion viven en el script de Python, que se
# puede correr y testear sin arnes.
#
# Sale 2 sobre un hallazgo porque el dispatcher DESCARTA stdout y stderr del hijo
# cuando sale 0: un aviso silencioso no existe para el operador.

set -uo pipefail
[ "${DISABLE_HOOK_PROTECTED_CONFIG_WRITE_DETECTOR:-}" = "true" ] && exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
DETECTOR="$PROJECT_DIR/scripts/detect_protected_config_writes.py"
[ -f "$DETECTOR" ] || exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -n "$INPUT" ] || exit 0

RESULT="$(printf '%s' "$INPUT" | python3 "$DETECTOR" 2>/dev/null)"
[ -n "$RESULT" ] || exit 0

STATE_DIR="${COS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
mkdir -p "$STATE_DIR" 2>/dev/null || true
printf '{"ts":"%s","hook":"protected-config-write-detector","result":%s}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$RESULT" \
  >> "$STATE_DIR/protected-config-writes.jsonl" 2>/dev/null || true

case "$RESULT" in
  *'"SIN_APROBAR"'*)
    {
      echo "=== PROTECTED CONFIG WRITE: DETECTADA SIN APROBACION ==="
      printf '%s\n' "$RESULT"
      echo
      echo "El guard de PreToolUse no pudo verlo: mira el TEXTO del comando, y una"
      echo "escritura hecha desde un script no aparece ahi."
      echo "La escritura YA OCURRIO -- esto no la impide, la hace visible."
      echo "Escape: DISABLE_HOOK_PROTECTED_CONFIG_WRITE_DETECTOR=true"
    } >&2
    exit 2 ;;
  *'"unknown"'*)
    {
      echo "=== DETECTOR: NO PUDO VERIFICAR ==="
      printf '%s\n' "$RESULT"
      echo "'No pude verificar' NO es 'no hubo cambios'. Se reporta en vez de callar."
    } >&2
    exit 2 ;;
esac
exit 0
