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
      claude|codex|agents-md|opencode|vscode-copilot|cursor|qwen-code|kimi-code|gemini-cli|warp|amp-code|jetbrains-junie|qoder|factory-droid|cline|continue-dev|kilo-code|zed-ai|augment-code|goose|aider|shell-ci)
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
    claude) printf '%s\n' ".claude/settings.json" ;;
    codex) printf '%s\n' ".codex/hooks.json" ;;
    agents-md) printf '%s\n' "AGENTS.md" ;;
    opencode) printf '%s\n' "opencode.json" ;;
    vscode-copilot) printf '%s\n' ".github/copilot-instructions.md" ;;
    cursor) printf '%s\n' ".cursor/rules/cognitive-os.mdc" ;;
    qwen-code) printf '%s\n' ".qwen/settings.json" ;;
    kimi-code) printf '%s\n' "AGENTS.md" ;;
    gemini-cli) printf '%s\n' ".gemini/settings.json" ;;
    warp) printf '%s\n' "AGENTS.md" ;;
    amp-code) printf '%s\n' "AGENTS.md" ;;
    jetbrains-junie) printf '%s\n' ".junie/AGENTS.md" ;;
    qoder) printf '%s\n' "AGENTS.md" ;;
    factory-droid) printf '%s\n' "AGENTS.md" ;;
    cline) printf '%s\n' ".clinerules/cognitive-os.md" ;;
    continue-dev) printf '%s\n' ".continue/rules/cognitive-os.md" ;;
    kilo-code) printf '%s\n' ".kilocode/rules/cognitive-os.md" ;;
    zed-ai) printf '%s\n' ".rules" ;;
    augment-code) printf '%s\n' ".augment/rules/cognitive-os.md" ;;
    goose) printf '%s\n' ".goosehints" ;;
    aider) printf '%s\n' "CONVENTIONS.md" ;;
    shell-ci) printf '%s\n' ".cognitive-os/shell-ci-projection.json" ;;
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
