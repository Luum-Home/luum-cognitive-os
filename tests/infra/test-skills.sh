#!/usr/bin/env bash
# Layer 1: Skill Infrastructure Tests
# Verifies SKILL.md exists, has valid frontmatter, and catalog consistency.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"
SKILLS_DIR="$AOS/skills"
CATALOG="$SKILLS_DIR/CATALOG.md"

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
warn() { WARN=$((WARN + 1)); echo "  WARN: $1"; }

echo "=== SKILL INFRASTRUCTURE TESTS ==="
echo ""

# ---- Test 1: Each skill dir has SKILL.md ----
echo "--- SKILL.md existence ---"
for dir in "$SKILLS_DIR"/*/; do
  [ ! -d "$dir" ] && continue
  name=$(basename "$dir")

  # Skip special dirs
  [[ "$name" == "auto-generated" ]] && continue

  if [ -f "${dir}SKILL.md" ]; then
    pass "$name has SKILL.md"
  else
    fail "$name MISSING SKILL.md"
  fi
done

# ---- Test 2: SKILL.md has YAML frontmatter with name and description ----
echo ""
echo "--- SKILL.md frontmatter validation ---"
for dir in "$SKILLS_DIR"/*/; do
  [ ! -d "$dir" ] && continue
  name=$(basename "$dir")
  skill_md="${dir}SKILL.md"
  [ ! -f "$skill_md" ] && continue

  # Check for YAML frontmatter (starts with ---)
  FIRST_LINE=$(head -1 "$skill_md" 2>/dev/null)
  if [[ "$FIRST_LINE" != "---" ]]; then
    fail "$name/SKILL.md missing YAML frontmatter (no --- header)"
    continue
  fi

  # Extract frontmatter (between first and second ---)
  FRONTMATTER=$(sed -n '2,/^---$/p' "$skill_md" | head -n -1 2>/dev/null || sed -n '2,/^---$/p' "$skill_md" 2>/dev/null)

  # Check for name field
  if echo "$FRONTMATTER" | grep -qE '^\s*name:'; then
    pass "$name/SKILL.md has 'name' field"
  else
    fail "$name/SKILL.md missing 'name' field in frontmatter"
  fi

  # Check for description field
  if echo "$FRONTMATTER" | grep -qE '^\s*description:'; then
    pass "$name/SKILL.md has 'description' field"
  else
    fail "$name/SKILL.md missing 'description' field in frontmatter"
  fi
done

# ---- Test 3: CATALOG.md lists all skills on disk ----
echo ""
echo "--- Catalog vs disk consistency ---"
if [ ! -f "$CATALOG" ]; then
  fail "CATALOG.md not found at $CATALOG"
else
  for dir in "$SKILLS_DIR"/*/; do
    [ ! -d "$dir" ] && continue
    name=$(basename "$dir")
    [[ "$name" == "auto-generated" ]] && continue
    [ ! -f "${dir}SKILL.md" ] && continue

    if grep -qF "$name" "$CATALOG" 2>/dev/null; then
      pass "$name found in CATALOG.md"
    else
      warn "$name on disk but MISSING from CATALOG.md"
    fi
  done

  # Check reverse: catalog entries that don't exist on disk
  # Extract skill names from catalog table rows
  CATALOG_SKILLS=$(grep -E '^\| ' "$CATALOG" | grep -v '^\| Skill' | grep -v '^\|---' | awk -F'|' '{print $2}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$' || true)
  while IFS= read -r skill_name; do
    [ -z "$skill_name" ] && continue
    # Convert display name to dir name (lowercase, spaces to hyphens)
    dir_name=$(echo "$skill_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    # Also check exact match
    if [ -d "$SKILLS_DIR/$dir_name" ] || [ -d "$SKILLS_DIR/$skill_name" ]; then
      : # already checked above
    else
      # Try fuzzy: check if any dir name appears in the catalog entry
      FOUND=false
      for d in "$SKILLS_DIR"/*/; do
        bn=$(basename "$d")
        if echo "$skill_name" | grep -qiF "$bn"; then
          FOUND=true
          break
        fi
      done
      if ! $FOUND; then
        warn "CATALOG.md references '$skill_name' but no matching skill dir found"
      fi
    fi
  done <<< "$CATALOG_SKILLS"
fi

# ---- Summary ----
echo ""
echo "=== SKILLS SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  WARN: $WARN"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0
