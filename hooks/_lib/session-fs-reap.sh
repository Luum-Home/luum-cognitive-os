#!/usr/bin/env bash
# SCOPE: os-only
# Archive-first filesystem reaper for .cognitive-os/sessions.
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
DRY_RUN=false
JSON=false
GRACE_SECONDS="${COS_SESSION_FS_REAP_GRACE_SECONDS:-86400}"
ARCHIVE_DAYS="${COS_SESSION_FS_REAP_ARCHIVE_DAYS:-90}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-dir)
      PROJECT_DIR="${2:-}"; [ -n "$PROJECT_DIR" ] || { echo "--project-dir requires value" >&2; exit 2; }; shift ;;
    --project-dir=*) PROJECT_DIR="${1#--project-dir=}" ;;
    --grace-seconds)
      GRACE_SECONDS="${2:-}"; [ -n "$GRACE_SECONDS" ] || { echo "--grace-seconds requires value" >&2; exit 2; }; shift ;;
    --grace-seconds=*) GRACE_SECONDS="${1#--grace-seconds=}" ;;
    --archive-retention-days)
      ARCHIVE_DAYS="${2:-}"; [ -n "$ARCHIVE_DAYS" ] || { echo "--archive-retention-days requires value" >&2; exit 2; }; shift ;;
    --archive-retention-days=*) ARCHIVE_DAYS="${1#--archive-retention-days=}" ;;
    --dry-run) DRY_RUN=true ;;
    --json) JSON=true ;;
    --help|-h)
      cat <<'EOF'
Usage: bash hooks/_lib/session-fs-reap.sh [--project-dir PATH] [--grace-seconds N] [--archive-retention-days N] [--dry-run] [--json]

Archive-first cleanup for .cognitive-os/sessions filesystem artifacts.
EOF
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

ARGS=("-m" "lib.session_lifecycle" "--project-dir" "$PROJECT_DIR" "--grace-seconds" "$GRACE_SECONDS" "--archive-retention-days" "$ARCHIVE_DAYS")
if [ "$DRY_RUN" = true ]; then ARGS+=("--dry-run"); fi
if [ "$JSON" = true ]; then ARGS+=("--json"); fi
PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 "${ARGS[@]}"
