#!/usr/bin/env bash
# Shared settings-driver helpers for shell tooling.
# Bash 3.x compatible.

cos_detect_harness() {
  local project_root="${1:-.}"
  local explicit="${COGNITIVE_OS_HARNESS:-}"

  if [ -n "$explicit" ]; then
    printf '%s\n' "$explicit"
    return
  fi

  # Installation metadata is the durable source of truth after first install.
  # This matters when a project carries more than one driver marker during a
  # migration; Git hook auto-update runs without Codex/Claude env hints.
  local meta_file="$project_root/.cognitive-os/install-meta.json"
  if [ -f "$meta_file" ] && command -v jq >/dev/null 2>&1; then
    local meta_harness
    meta_harness="$(jq -r '.harness // empty' "$meta_file" 2>/dev/null || true)"
    case "$meta_harness" in
      claude|codex)
        printf '%s\n' "$meta_harness"
        return
        ;;
    esac
  fi

  if [ -f "$project_root/.codex/hooks.json" ] && [ ! -f "$project_root/.claude/settings.json" ]; then
    printf '%s\n' "codex"
    return
  fi

  if [ -f "$project_root/.claude/settings.json" ] && [ ! -f "$project_root/.codex/hooks.json" ]; then
    printf '%s\n' "claude"
    return
  fi

  if [ -n "${CODEX_PROJECT_DIR:-}" ] || [ -n "${CODEX_SESSION_ID:-}" ] || [ -n "${CODEX_HOME:-}" ]; then
    printf '%s\n' "codex"
    return
  fi

  printf '%s\n' "claude"
}

cos_settings_driver_relpath() {
  local harness="${1:-claude}"
  case "$harness" in
    codex) printf '%s\n' ".codex/hooks.json" ;;
    *) printf '%s\n' ".claude/settings.json" ;;
  esac
}

cos_settings_driver_label() {
  cos_settings_driver_relpath "$1"
}

cos_settings_driver_path() {
  local project_root="${1:-.}"
  local harness="${2:-$(cos_detect_harness "$project_root")}"
  printf '%s/%s\n' "$project_root" "$(cos_settings_driver_relpath "$harness")"
}
