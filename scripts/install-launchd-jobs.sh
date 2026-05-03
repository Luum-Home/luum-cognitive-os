#!/usr/bin/env bash
# SCOPE: os-only
# install-launchd-jobs.sh — generate + load the three weekly launchd jobs.
#
# Per ADR-131. Replaces cos-config-audit.yml, primitive-gap-audit.yml, and
# weekly-public-metrics.yml with macOS launchd schedules.
#
# Schedules (local time on the Mac):
#   cos-config-audit       Mondays 09:00
#   weekly-public-metrics  Mondays 12:00
#   primitive-gap-audit    Mondays 12:30
#
# Logs land under ~/Library/Logs/cos/.
# Plists land under ~/Library/LaunchAgents/.
#
# Subcommands:
#   install     generate plists, copy to ~/Library/LaunchAgents/, launchctl load
#   uninstall   launchctl unload + remove the plists
#   status      list currently loaded jobs
#
# This script is idempotent: re-running install replaces existing plists.

set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/cos"
ACTION="${1:-install}"

JOBS=(
  "config-audit:cos-weekly-config-audit.sh:1:9:0"
  "public-metrics:cos-weekly-public-metrics.sh:1:12:0"
  "primitive-gap:cos-weekly-primitive-gap.sh:1:12:30"
)

generate_plist() {
  local name="$1"
  local script="$2"
  local weekday="$3"
  local hour="$4"
  local minute="$5"
  local label="com.luum.cos.${name}"
  local plist="$LAUNCH_AGENTS/${label}.plist"

  cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${REPO_ROOT}/scripts/${script}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>${weekday}</integer>
        <key>Hour</key>
        <integer>${hour}</integer>
        <key>Minute</key>
        <integer>${minute}</integer>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/${name}.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/${name}.err.log</string>
    <key>WorkingDirectory</key>
    <string>${REPO_ROOT}</string>
</dict>
</plist>
EOF
  echo "  → $plist"
}

cmd_install() {
  mkdir -p "$LAUNCH_AGENTS" "$LOG_DIR"

  echo "[install-launchd-jobs] generating plists into $LAUNCH_AGENTS"
  for spec in "${JOBS[@]}"; do
    IFS=':' read -r name script weekday hour minute <<< "$spec"
    generate_plist "$name" "$script" "$weekday" "$hour" "$minute"

    local label="com.luum.cos.${name}"
    local plist="$LAUNCH_AGENTS/${label}.plist"

    # Unload first if already loaded; bootstrap then handles fresh load.
    launchctl bootout "gui/$(id -u)" "$plist" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$plist"
    echo "  ✓ loaded $label"
  done

  echo
  echo "Installed 3 weekly jobs. Inspect logs at $LOG_DIR/"
  echo "Run \`bash $0 status\` to verify."
}

cmd_uninstall() {
  for spec in "${JOBS[@]}"; do
    IFS=':' read -r name _ _ _ _ <<< "$spec"
    local label="com.luum.cos.${name}"
    local plist="$LAUNCH_AGENTS/${label}.plist"
    launchctl bootout "gui/$(id -u)" "$plist" 2>/dev/null || true
    rm -f "$plist"
    echo "  ✓ removed $label"
  done
}

cmd_status() {
  for spec in "${JOBS[@]}"; do
    IFS=':' read -r name _ _ _ _ <<< "$spec"
    local label="com.luum.cos.${name}"
    if launchctl list | grep -q "$label"; then
      echo "  ✓ $label  (loaded)"
    else
      echo "  ⊘ $label  (not loaded)"
    fi
  done
}

case "$ACTION" in
  install)   cmd_install ;;
  uninstall) cmd_uninstall ;;
  status)    cmd_status ;;
  *)
    echo "Usage: $0 [install|uninstall|status]" >&2
    exit 2
    ;;
esac
