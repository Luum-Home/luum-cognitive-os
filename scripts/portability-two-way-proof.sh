#!/usr/bin/env bash
# SCOPE: both
# portability-two-way-proof.sh — que el arreglo portable ande en LAS DOS
# direcciones: en BSD/bash-3.2 (donde estaba roto) y en GNU/bash-5 (donde ya
# andaba, y donde un "arreglo" podria romperlo).
#
# Un arreglo probado solo en macOS no es portable, es macOS-especifico con otro
# nombre. Por eso este script corre las MISMAS aserciones dos veces:
#
#   local   -> /bin/bash 3.2.57 + userland BSD (la maquina del operador)
#   linux   -> debian:stable-slim en docker  + userland GNU (lo que corre CI)
#
# Si docker no esta, la direccion GNU se reporta SKIP — no se da por buena.
# Un SKIP silencioso seria justamente el "verde barato" que esto busca evitar.
#
# Uso:  bash scripts/portability-two-way-proof.sh
# Exit: 0 las dos direcciones OK (o linux SKIP explicito), 1 alguna fallo.

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Las aserciones, en un solo lugar ─────────────────────────────────────────
# Se escriben una vez y se ejecutan en los dos userlands. Cada una imprime
# `ok:` o `FALLA:`; el runner cuenta.
ASERCIONES=$(cat <<'ASSERT'
fallas=0
chk() { # chk NOMBRE ESPERADO OBTENIDO
  if [ "$2" = "$3" ]; then echo "  ok: $1"; else
    echo "  FALLA: $1 -- esperaba [$2] obtuvo [$3]"; fallas=$((fallas+1)); fi
}

# --- 1..3: extraccion de agent_name en subagent-context-injector.sh ---------
# Antes usaba `grep -oP` (PCRE). BSD grep no lo tiene: devolvia vacio SIN error
# y agent_name quedaba "" en cada spawn.
p='Identity: mi-agente-de-prueba'
chk "Identity: -> nombre" "mi-agente-de-prueba" \
  "$(echo "$p" | sed -nE 's/.*Identity:[[:space:]]*([^[:space:]]+).*/\1/p' | head -1)"

p='Cargar skills/sdd-apply/SKILL.md antes de nada'
chk "skills/<x>/ -> nombre" "sdd-apply" \
  "$(echo "$p" | sed -nE 's|.*skills/([^/]+)/.*|\1|p' | head -1)"

p='corre la fase sdd-verify sobre el change'
chk "fase sdd-*" "sdd-verify" \
  "$(echo "$p" | grep -oE 'sdd-(explore|propose|spec|design|tasks|apply|verify|archive|improve)' | head -1)"

# --- 4: control anti-falso-positivo -----------------------------------------
# Un prompt SIN ninguno de los tres patrones tiene que dar vacio. Sin esto, una
# expresion que matchea cualquier cosa pasaria las tres de arriba.
p='un prompt cualquiera sin marcas'
chk "prompt sin marcas -> vacio" "" \
  "$(echo "$p" | sed -nE 's/.*Identity:[[:space:]]*([^[:space:]]+).*/\1/p' | head -1)"

# --- 5: mayusculas en rule-md-routing-validator.sh --------------------------
# Antes `${base^^}` (bash 4). /bin/bash 3.2 corta con "bad substitution" y el
# hook entero muere en esa linea.
base="Roadmap.md"
chk "base -> MAYUSCULAS" "ROADMAP.MD" \
  "$(printf '%s' "$base" | tr '[:lower:]' '[:upper:]')"

# --- 6..7: portable_timeout --------------------------------------------------
source "$REPO_IN/hooks/_lib/portable.sh"
chk "portable_timeout deja pasar el rc" "7" \
  "$(portable_timeout 5 sh -c 'exit 7' >/dev/null 2>&1; echo $?)"
chk "portable_timeout corta y devuelve 124" "124" \
  "$(portable_timeout 1 sh -c 'sleep 5' >/dev/null 2>&1; echo $?)"

# --- 8: control -- el bug ORIGINAL sigue siendo un bug ----------------------
# Sin esto, si algun dia el userland cambiara y `grep -oP` anduviera en todos
# lados, las aserciones de arriba pasarian sin decir que ya no hay nada que
# arreglar. Aca solo se afirma que el instrumento distingue los dos mundos.
if echo 'Identity: x' | grep -oP 'Identity:\s*(\S+)' >/dev/null 2>&1; then
  echo "  info: este userland SI tiene grep -P (GNU)"
else
  echo "  info: este userland NO tiene grep -P (BSD) <- la falla original"
fi

echo "fallas=$fallas"
[ "$fallas" -eq 0 ]
ASSERT
)

fallo_global=0

# ── Direccion 1: BSD / bash 3.2 (la maquina del operador) ────────────────────
echo "=== direccion BSD: /bin/bash $(/bin/bash -c 'echo $BASH_VERSION') ==="
REPO_IN="$REPO" /bin/bash -c "REPO_IN='$REPO'; $ASERCIONES" || fallo_global=1

# ── Direccion 2: GNU / bash 5 (lo que corre CI) ──────────────────────────────
echo
if [ "${COS_PROOF_SKIP_LINUX:-0}" = "1" ]; then
  # Salida deliberada para el proof pareado, que corre este script tres veces y
  # no puede pagar un pull de imagen. Se dice en voz alta: un SKIP callado seria
  # el verde barato que este script existe para no dar.
  echo "=== direccion GNU: SKIP por COS_PROOF_SKIP_LINUX=1 ==="
  echo "    NO se afirma portabilidad: falta la mitad de la prueba."
elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  echo "=== direccion GNU: debian:stable-slim en docker ==="
  docker run --rm -i \
    -v "$REPO:/repo:ro" -e REPO_IN=/repo \
    debian:stable-slim bash -c "
      set -e
      command -v python3 >/dev/null 2>&1 || {
        apt-get -qq update >/dev/null 2>&1 && apt-get -qq install -y python3 >/dev/null 2>&1
      }
      echo \"  bash: \$BASH_VERSION\"
      $ASERCIONES
    " || fallo_global=1
else
  echo "=== direccion GNU: SKIP (docker ausente o daemon caido) ==="
  echo "    NO se afirma portabilidad: falta la mitad de la prueba."
fi

exit "$fallo_global"
