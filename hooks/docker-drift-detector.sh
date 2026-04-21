#!/usr/bin/env bash
# SCOPE: os-only
# docker-drift-detector.sh — SessionStart advisory
#
# Detects running cognitive-os-* containers whose image sha does NOT match
# the @sha256 digest pinned in docker-compose.cognitive-os.yml. This catches
# the stale-container scenario where someone updated the pin but didn't run
# `docker compose up -d --force-recreate`, leaving old containers with the
# old (possibly broken) image.
#
# Fast (<200ms typical), advisory only, exits 0 always. Writes to stderr so
# it shows up in session-start context. Logs structured record to
# .cognitive-os/metrics/docker-drift.jsonl.
#
# Graceful degradation:
#   - No compose file → silent exit 0
#   - No docker binary → silent exit 0
#   - No running containers → silent exit 0
#   - Docker daemon not responding → log warning to stderr, exit 0
#
# Companion: scripts/cos-config-audit.sh meta.docker_container_freshness
# runs the same check but emits a richer report.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.cognitive-os.yml"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
METRICS_FILE="$METRICS_DIR/docker-drift.jsonl"

# Silent exit if nothing to check
[ -f "$COMPOSE_FILE" ] || exit 0

# Find docker binary (may be outside PATH on fresh shells)
DOCKER=""
for candidate in \
  /opt/homebrew/bin/docker \
  /usr/local/bin/docker \
  /Applications/OrbStack.app/Contents/Resources/bin/docker
do
  if [ -x "$candidate" ]; then
    DOCKER="$candidate"
    break
  fi
done
[ -n "$DOCKER" ] || DOCKER="$(command -v docker 2>/dev/null || true)"
[ -n "$DOCKER" ] || exit 0

# Fast docker responsiveness check (< 1s); if daemon not up, silent exit
if ! timeout 1 "$DOCKER" info >/dev/null 2>&1; then
  exit 0
fi

# Extract @sha256 pinned images from compose: key = "repo:tag", value = sha
# Example line: "    image: foo/bar:3@sha256:abcdef..."
# awk emits <base>|<sha> one per line.
PIN_TSV=$(awk '
  /^[[:space:]]*image:[[:space:]]*[^[:space:]#]+@sha256:[0-9a-f]{64}/ {
    for (i = 1; i <= NF; i++) {
      if ($i ~ /@sha256:/) {
        split($i, parts, "@sha256:")
        print parts[1] "|" parts[2]
      }
    }
  }
' "$COMPOSE_FILE")

[ -n "$PIN_TSV" ] || exit 0

# List running cognitive-os-* containers: name<TAB>image_ref
RUNNING=$("$DOCKER" ps --filter 'name=cognitive-os-' --format '{{.Names}}	{{.Image}}' 2>/dev/null)
[ -n "$RUNNING" ] || exit 0

# For each running container, compare its actual image sha vs the pin for
# its image base (repo:tag portion).
drift_count=0
fresh_count=0
drift_names=""

while IFS=$'\t' read -r name image_ref; do
  [ -z "$name" ] && continue
  base="${image_ref%%@*}"                 # strip @sha256:... if present
  pinned=$(echo "$PIN_TSV" | awk -F'|' -v b="$base" '$1 == b {print $2; exit}')
  [ -z "$pinned" ] && continue            # unpinned → skip

  running_sha=$("$DOCKER" inspect --format '{{.Image}}' "$name" 2>/dev/null | sed 's/^sha256://')
  [ -z "$running_sha" ] && continue

  case "$running_sha" in
    "$pinned"*)
      fresh_count=$((fresh_count + 1))
      ;;
    *)
      drift_count=$((drift_count + 1))
      drift_names="${drift_names:+$drift_names, }$name"
      ;;
  esac
done <<< "$RUNNING"

# Log structured record (best-effort)
mkdir -p "$METRICS_DIR" 2>/dev/null || true
ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")
printf '{"ts":"%s","fresh":%d,"drift":%d,"drift_containers":"%s"}\n' \
  "$ts" "$fresh_count" "$drift_count" "$drift_names" \
  >> "$METRICS_FILE" 2>/dev/null || true

# Emit one-line summary to stderr (Claude sees it as SessionStart context)
if [ "$drift_count" -gt 0 ]; then
  echo "[docker-drift] WARNING: $drift_count cognitive-os container(s) running stale image: $drift_names" >&2
  echo "[docker-drift]   Fix: docker compose -f docker-compose.cognitive-os.yml pull && docker compose -f docker-compose.cognitive-os.yml up -d --force-recreate" >&2
elif [ "$fresh_count" -gt 0 ]; then
  echo "[docker-drift] $fresh_count cognitive-os container(s) fresh" >&2
fi

exit 0
