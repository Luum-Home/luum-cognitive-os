#!/usr/bin/env bash
# SCOPE: both
# killswitch_check.sh — ADR-028 D5
#
# Source this file at the TOP of any hook to suppress non-critical hooks
# when the emergency kill-switch is active.
#
# Usage (in any hook):
#   source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
#   # ... rest of hook ...
#
# Critical whitelist — these hooks are NEVER suppressed:
#   credential-guard.sh
#   license-guard.sh
#   pre-compaction-flush.sh
#   session-cleanup.sh
#   self-install.sh
#   session-init.sh
#   destructive-git-blocker.sh   (R3 hardening: safety blockers cannot be killed)
#   destructive-rm-blocker.sh    (R3 hardening: safety blockers cannot be killed)
#   secret-detector.sh           (R3 hardening: credential leak prevention)
#
# HOOK_NAME must be set to the basename of the calling hook before sourcing,
# OR the library auto-detects it from BASH_SOURCE[1].
#
# Killswitch is considered ACTIVE if EITHER:
#   - The flag file .cognitive-os/runtime/hook-killswitch.flag exists, OR
#   - The environment variable SO_KILLSWITCH=1 is set (ADR-028 Q#5 env-var
#     fallback for full-disk scenarios where the flag file cannot be written)
#
# Behaviour:
#   - If killswitch is NOT active              → no-op (hook runs normally)
#   - If killswitch IS active and hook IS in whitelist  → no-op (hook runs)
#   - If killswitch IS active and hook is NOT in whitelist → exit 0 silently
#
# The flag file path respects $PROJECT_DIR (env) or auto-detects from cwd / script path.

# ── Locate flag file ─────────────────────────────────────────────────
_ks_project_dir="${PROJECT_DIR:-}"
if [ -z "$_ks_project_dir" ]; then
  # Walk up from cwd until we find cognitive-os.yaml or .claude/
  _ks_dir="$(pwd)"
  while [ "$_ks_dir" != "/" ]; do
    if [ -f "$_ks_dir/cognitive-os.yaml" ] || [ -d "$_ks_dir/.claude" ]; then
      _ks_project_dir="$_ks_dir"
      break
    fi
    _ks_dir="$(dirname "$_ks_dir")"
  done
fi
_ks_flag="${_ks_project_dir:-.}/.cognitive-os/runtime/hook-killswitch.flag"

# ── Check killswitch: flag file OR SO_KILLSWITCH=1 env var (ADR-028 Q#5) ─────
# The env-var fallback preserves emergency-stop capability when the disk is full
# and the flag file cannot be written.
_ks_active=0
if [ -f "$_ks_flag" ]; then
  _ks_active=1
elif [ "${SO_KILLSWITCH:-}" = "1" ]; then
  _ks_active=1
fi

if [ "$_ks_active" -eq 0 ]; then
  unset _ks_project_dir _ks_flag _ks_dir _ks_active
  return 0 2>/dev/null || true
fi

# ── Determine calling hook name ──────────────────────────────────────
_ks_hook_name="${HOOK_NAME:-}"
if [ -z "$_ks_hook_name" ] && [ -n "${BASH_SOURCE[1]:-}" ]; then
  _ks_hook_name="$(basename "${BASH_SOURCE[1]}")"
fi

# ── Critical whitelist ───────────────────────────────────────────────
_ks_critical_hooks=(
  "credential-guard.sh"
  "license-guard.sh"
  "pre-compaction-flush.sh"
  "session-cleanup.sh"
  "self-install.sh"
  "session-init.sh"
  "destructive-git-blocker.sh"
  "destructive-rm-blocker.sh"
  "secret-detector.sh"
)

_ks_is_critical=0
for _ks_h in "${_ks_critical_hooks[@]}"; do
  if [ "$_ks_hook_name" = "$_ks_h" ]; then
    _ks_is_critical=1
    break
  fi
done

# ── Cleanup locals and act ───────────────────────────────────────────
unset _ks_project_dir _ks_flag _ks_dir _ks_h _ks_critical_hooks _ks_hook_name _ks_active

if [ "$_ks_is_critical" -eq 0 ]; then
  unset _ks_is_critical
  # Non-critical hook + killswitch active → suppress silently
  exit 0
fi

unset _ks_is_critical
# Critical hook → fall through and let the hook run normally

# ── hooks/_lib/killswitch_check.sh — exempt from hook-matcher wiring ─
