#!/usr/bin/env bash
# SCOPE: both
# ADR-241 shared bypass resolver.
# Usage: source this file, then call `cos_bypass_allows <stable-key>`.
# Stable keys are read from COS_BYPASS (comma-separated) and from the optional
# runtime file .cognitive-os/runtime/bypass.env. Legacy env aliases remain for
# one release and are centralized here.

_cos_bypass_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

_cos_bypass_project_dir() {
  printf '%s' "${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
}

# Identidad del agente que esta pidiendo el bypass, si la hay. El sub-agente la
# recibe por entorno; la sesion del operador no tiene ninguna y eso es correcto:
# el operador SI puede desactivar un guard para todo su proyecto, un sub-agente no.
_cos_bypass_agent_id() {
  printf '%s' "${COS_AGENT_ID:-${CLAUDE_AGENT_ID:-${CODEX_AGENT_ID:-}}}"
}

# Archivo de bypass, POR AGENTE cuando hay agente.
#
# Antes esto devolvia siempre `bypass.env` a secas, de alcance PROYECTO. El
# agujero, medido el 2026-08-20: el bypass que escribia UN sub-agente destrababa
# a TODOS los concurrentes, con el motivo de otro encargo. Un agente cansado de
# que un guard le estorbe apagaba, sin saberlo, la misma defensa para sus cinco
# hermanos -- y el motivo escrito en el archivo pertenecia a un trabajo que nada
# tenia que ver con el de ellos.
#
# Ahora: si hay agente, su bypass vive en `bypass-<agente>.env` y no toca a
# nadie mas. Si NO hay agente --sesion del operador-- se usa `bypass.env` como
# siempre, porque desactivar un guard en tu propia maquina para tu propia sesion
# es una decision legitima y con dueno visible.
#
# Compatibilidad: un `bypass.env` preexistente sigue funcionando para la sesion
# del operador. Lo que deja de funcionar es que un sub-agente lo escriba y le
# valga al vecino, que es exactamente el comportamiento que se quiere perder.
_cos_bypass_runtime_file() {
  local dir agent
  dir="$(_cos_bypass_project_dir)/.cognitive-os/runtime"
  agent="$(_cos_bypass_agent_id)"
  if [ -n "$agent" ]; then
    printf '%s/bypass-%s.env' "$dir" "$agent"
  else
    printf '%s/bypass.env' "$dir"
  fi
}

# Lee UNA variable del runtime file. Antes esto sabía leer solamente COS_BYPASS,
# y esa limitación era el agujero: todo bypass que exige una variable compañera
# --los `*_REASON` de direct_main, direct_push, skill y subagent-budget-- tenía
# su clave en el resolvedor y aun así no había forma de activarlo a mitad de
# sesión, porque la compañera no tenía por dónde viajar. El hook es hijo del
# arnés: un prefijo `VAR=1 <cmd>` se lo come el shell del comando y el hook ya
# decidió. Con el archivo transportando cualquier COS_*, la vía existe.
#
# Sólo se aceptan nombres COS_*: el archivo es una vía de activación de bypass,
# no un mecanismo genérico para inyectar entorno en los hooks.
_cos_bypass_runtime_var() {
  local name="$1" runtime_file
  case "$name" in
    COS_*) ;;
    *) return 1 ;;
  esac
  runtime_file="$(_cos_bypass_runtime_file)"
  [ -f "$runtime_file" ] || return 1
  grep -E "^${name}=" "$runtime_file" 2>/dev/null \
    | tail -1 \
    | sed "s/^${name}=//" \
    | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'\$//"
}

_cos_bypass_combined_list() {
  printf '%s,%s' "${COS_BYPASS:-}" "$(_cos_bypass_runtime_var COS_BYPASS || true)"
}

# cos_bypass_var <NOMBRE>  -> imprime el valor, entorno primero, archivo después.
#
# El entorno gana porque `export VAR=... ` antes de lanzar el arnés es la vía
# deliberada del operador; el archivo es la vía de quien YA está bloqueado y no
# puede relanzar nada. Devuelve 1 si no hay valor en ninguna de las dos.
cos_bypass_var() {
  local name="$1" value
  [ -n "$name" ] || return 1
  eval "value=\${$name:-}"
  if [ -n "$value" ]; then
    printf '%s' "$value"
    return 0
  fi
  value="$(_cos_bypass_runtime_var "$name" 2>/dev/null || true)"
  [ -n "$value" ] || return 1
  printf '%s' "$value"
}

# cos_bypass_audit <clave> <hook> <motivo>
# Un escape sin constancia es un agujero; con constancia es una decisión con
# dueño. Se registra SIEMPRE que un bypass destraba algo, venga del entorno o
# del archivo. Fail-silent: la auditoría no puede ser el motivo de un bloqueo.
cos_bypass_audit() {
  local key="$1" hook="$2" reason="$3" dir
  # COS_METRICS_DIR primero: sin esto, cualquier test que ejercite un bypass
  # (con COS_METRICS_DIR apuntado a un temporal, como hace tests/conftest.py)
  # igual escribia en la telemetria REAL del operador -- medido 2026-08-20,
  # +231 bytes deterministas en .cognitive-os/metrics/bypass-activation.jsonl
  # por cada invocacion, sin ninguna forma de redirigirlo. Ver
  # tests/audit/test_metrics_isolation.py::test_bypass_audit_honors_cos_metrics_dir.
  dir="${COS_METRICS_DIR:-$(_cos_bypass_project_dir)/.cognitive-os/metrics}"
  mkdir -p "$dir" 2>/dev/null || true
  python3 - "$dir/bypass-activation.jsonl" "$key" "$hook" "$reason" \
    "${COS_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}" <<'PY_AUDIT' 2>/dev/null || true
import json, os, sys, time
path, key, hook, reason, session = sys.argv[1:6]
row = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "bypass_key": key,
    "hook": hook,
    "reason": reason,
    "session_id": session,
    "pid": os.getpid(),
    "source": "env" if os.environ.get(key.upper()) else "bypass.env",
}
with open(path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, sort_keys=True) + "\n")
PY_AUDIT
}

_cos_bypass_list_contains() {
  local key="$1" item list
  list="$(_cos_bypass_combined_list)"
  IFS=',' read -r -a _cos_bypass_items <<< "$list"
  for item in "${_cos_bypass_items[@]}"; do
    item="$(printf '%s' "$item" | xargs 2>/dev/null || printf '%s' "$item")"
    [ "$item" = "$key" ] && return 0
  done
  return 1
}

_cos_bypass_legacy_alias_allows() {
  local key="$1"
  case "$key" in
    destructive_git)
      [ "${COS_ALLOW_DESTRUCTIVE_GIT:-}" = "1" ] || _cos_bypass_truthy "${COS_GIT_BYPASS:-}"
      ;;
    main_branch_write)
      _cos_bypass_truthy "${COS_ALLOW_MAIN_BRANCH_WRITE:-}" || _cos_bypass_truthy "${COS_ALLOW_DIRECT_MAIN:-}"
      ;;
    branch_switch)
      _cos_bypass_truthy "${COS_ALLOW_BRANCH_SWITCH:-}"
      ;;
    reset_over_wip)
      _cos_bypass_truthy "${COS_ALLOW_RESET_OVER_WIP:-}"
      ;;
    commit_guard)
      _cos_bypass_truthy "${COS_BYPASS_COMMIT_GUARD:-}"
      ;;
    branch_ownership)
      _cos_bypass_truthy "${COS_ALLOW_BRANCH_OWNERSHIP_OVERRIDE:-}"
      ;;
    claim_gate)
      [ "${COS_ORCHESTRATOR_CLAIM_GATE_MODE:-}" = "warn" ] || _cos_bypass_truthy "${DISABLE_HOOK_ORCHESTRATOR_CLAIM_GATE:-}"
      ;;
    push_collision)
      _cos_bypass_truthy "${DISABLE_HOOK_PUSH_COLLISION_CHECK:-}"
      ;;
    direct_push)
      _cos_bypass_truthy "${COS_ALLOW_DIRECT_PUSH:-}"
      ;;
    direct_main)
      _cos_bypass_truthy "${COS_ALLOW_DIRECT_MAIN:-}"
      ;;
    research_compliance)
      _cos_bypass_truthy "${COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS:-}"
      ;;
    unproven_scope_both)
      _cos_bypass_truthy "${COS_ALLOW_UNPROVEN_SCOPE_BOTH:-}"
      ;;
    subagent_budget)
      _cos_bypass_truthy "${COS_ALLOW_SUBAGENT_BUDGET_BYPASS:-}"
      ;;
    *) return 1 ;;
  esac
}

cos_bypass_allows() {
  local key="$1"
  [ -n "$key" ] || return 1
  _cos_bypass_list_contains "$key" && return 0
  _cos_bypass_legacy_alias_allows "$key" && return 0
  return 1
}
