#!/usr/bin/env bash
# SCOPE: os-only
# Version management for Cognitive OS
# Usage:
#   bash scripts/version.sh            # show current version
#   bash scripts/version.sh bump patch  # 0.1.0 -> 0.1.1
#   bash scripts/version.sh bump minor  # 0.1.0 -> 0.2.0
#   bash scripts/version.sh bump major  # 0.1.0 -> 1.0.0
#   bash scripts/version.sh check       # verify VERSION matches across files
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "${PROJECT_ROOT}/hooks/_lib/portable.sh"
VERSION_FILE="$PROJECT_ROOT/VERSION"

# Files that contain the version string:
# 1. VERSION (source of truth)
# 2. cmd/cos/internal/cli/root.go (dynamic VERSION-file fallback)
# 3. cmd/cos-test/internal/cli/root.go (dynamic VERSION-file fallback)
# 4. docs/INDEX.md (version in header)

COS_ROOT_GO="$PROJECT_ROOT/cmd/cos/internal/cli/root.go"
COS_TEST_ROOT_GO="$PROJECT_ROOT/cmd/cos-test/internal/cli/root.go"
INDEX_MD="$PROJECT_ROOT/docs/INDEX.md"

get_version() {
  if [ ! -f "$VERSION_FILE" ]; then
    echo "Error: VERSION file not found at $VERSION_FILE" >&2
    exit 1
  fi
  tr -d '[:space:]' < "$VERSION_FILE"
}

validate_semver() {
  local ver="$1"
  if ! echo "$ver" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Error: '$ver' is not valid semver (expected X.Y.Z)" >&2
    exit 1
  fi
}

bump_version() {
  local current="$1"
  local part="$2"
  local major minor patch

  major=$(echo "$current" | cut -d. -f1)
  minor=$(echo "$current" | cut -d. -f2)
  patch=$(echo "$current" | cut -d. -f3)

  case "$part" in
    major)
      major=$((major + 1))
      minor=0
      patch=0
      ;;
    minor)
      minor=$((minor + 1))
      patch=0
      ;;
    patch)
      patch=$((patch + 1))
      ;;
    *)
      echo "Error: invalid bump target '$part'. Use: major, minor, or patch" >&2
      exit 1
      ;;
  esac

  echo "${major}.${minor}.${patch}"
}

update_all_locations() {
  local old_ver="$1"
  local new_ver="$2"

  # 1. VERSION file
  echo "$new_ver" > "$VERSION_FILE"
  echo "  Updated VERSION: $old_ver -> $new_ver"

  # 2. cos CLI root.go
  if [ -f "$COS_ROOT_GO" ]; then
    portable_sed_inplace "s/Version: \"${old_ver}\"/Version: \"${new_ver}\"/" "$COS_ROOT_GO"
    echo "  Updated cmd/cos/internal/cli/root.go"
  fi

  # 3. cos-test CLI root.go
  if [ -f "$COS_TEST_ROOT_GO" ]; then
    portable_sed_inplace "s/Version: \"${old_ver}\"/Version: \"${new_ver}\"/" "$COS_TEST_ROOT_GO"
    echo "  Updated cmd/cos-test/internal/cli/root.go"
  fi

  # 4. docs/INDEX.md
  if [ -f "$INDEX_MD" ]; then
    portable_sed_inplace "s/Cognitive OS v${old_ver}/Cognitive OS v${new_ver}/g" "$INDEX_MD"
    echo "  Updated docs/INDEX.md"
  fi
}

check_consistency() {
  local ver
  ver=$(get_version)
  local ok=true

  echo "Source of truth (VERSION): $ver"
  echo ""

  # Check cos CLI
  if [ -f "$COS_ROOT_GO" ]; then
    local cos_ver=""
    cos_ver=$(grep 'Version: "' "$COS_ROOT_GO" | head -1 | sed 's/.*"\(.*\)".*/\1/' || true)
    if [ -n "$cos_ver" ]; then
      if [ "$cos_ver" = "$ver" ]; then
        echo "  [OK] cmd/cos/internal/cli/root.go: $cos_ver"
      else
        echo "  [MISMATCH] cmd/cos/internal/cli/root.go: $cos_ver (expected $ver)"
        ok=false
      fi
    elif grep -q 'readVersionFile' "$COS_ROOT_GO"; then
      echo "  [OK] cmd/cos/internal/cli/root.go: dynamic VERSION-file fallback"
    else
      echo "  [MISMATCH] cmd/cos/internal/cli/root.go: no static version or VERSION fallback"
      ok=false
    fi
  else
    echo "  [SKIP] cmd/cos/internal/cli/root.go not found"
  fi

  # Check cos-test CLI
  if [ -f "$COS_TEST_ROOT_GO" ]; then
    local costest_ver=""
    costest_ver=$(grep 'Version: "' "$COS_TEST_ROOT_GO" | head -1 | sed 's/.*"\(.*\)".*/\1/' || true)
    if [ -n "$costest_ver" ]; then
      if [ "$costest_ver" = "$ver" ]; then
        echo "  [OK] cmd/cos-test/internal/cli/root.go: $costest_ver"
      else
        echo "  [MISMATCH] cmd/cos-test/internal/cli/root.go: $costest_ver (expected $ver)"
        ok=false
      fi
    elif grep -q 'VERSION' "$COS_TEST_ROOT_GO"; then
      echo "  [OK] cmd/cos-test/internal/cli/root.go: dynamic VERSION-file fallback"
    else
      echo "  [MISMATCH] cmd/cos-test/internal/cli/root.go: no static version or VERSION fallback"
      ok=false
    fi
  else
    echo "  [SKIP] cmd/cos-test/internal/cli/root.go not found"
  fi

  # Check docs/INDEX.md
  if [ -f "$INDEX_MD" ]; then
    if head -1 "$INDEX_MD" | grep -q "v${ver}"; then
      echo "  [OK] docs/INDEX.md heading contains version $ver"
    else
      echo "  [MISMATCH] docs/INDEX.md heading does not contain 'v${ver}'"
      ok=false
    fi
  else
    echo "  [SKIP] docs/INDEX.md not found"
  fi

  echo ""
  if [ "$ok" = true ]; then
    echo "All version locations are consistent."
  else
    echo "Version mismatch detected. Run: bash scripts/version.sh bump <part>"
    exit 1
  fi
}

# ── Main ──────────────────────────────────────────────────────────────

case "${1:-show}" in
  show|"")
    get_version
    ;;
  bump)
    part="${2:-}"
    if [ -z "$part" ]; then
      echo "Usage: bash scripts/version.sh bump <major|minor|patch>" >&2
      exit 1
    fi
    current=$(get_version)
    validate_semver "$current"
    new_ver=$(bump_version "$current" "$part")
    echo "Bumping version: $current -> $new_ver"
    update_all_locations "$current" "$new_ver"
    echo ""
    echo "Done. Don't forget to:"
    echo "  1. Add a new ## [$new_ver] section to CHANGELOG.md"
    echo "  2. Commit: git commit -am 'chore: bump version to $new_ver'"
    echo "  3. Tag: git tag v$new_ver"
    ;;
  check)
    check_consistency
    ;;
  *)
    echo "Usage: bash scripts/version.sh [show|bump <major|minor|patch>|check]" >&2
    exit 1
    ;;
esac
