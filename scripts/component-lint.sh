#!/usr/bin/env bash
# Component Linter — Detects copy-paste errors, stale fields, and inconsistencies
# Usage: bash scripts/component-lint.sh [--fix]
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIX_MODE="${1:-}"
ISSUES=0
WARNINGS=0

# Colors
RED='\033[0;31m'
YEL='\033[0;33m'
GRN='\033[0;32m'
NC='\033[0m'

issue() { ((ISSUES++)); echo -e "${RED}ERROR${NC}: $1"; }
warn()  { ((WARNINGS++)); echo -e "${YEL}WARN${NC}: $1"; }
ok()    { echo -e "${GRN}OK${NC}: $1"; }

echo "═══════════════════════════════════════"
echo "  Component Linter — Cognitive OS"
echo "═══════════════════════════════════════"
echo ""

# ─────────────────────────────────────
# CHECK 1: Duplicated frontmatter fields across skills
# ─────────────────────────────────────
echo "## Check 1: Duplicated frontmatter values"

# Collect all author fields (bash 3.x compatible)
author_tmp=$(mktemp)
for skill_dir in "$PROJECT_ROOT"/skills/*/; do
    skill_file="$skill_dir/SKILL.md"
    [ -f "$skill_file" ] || continue
    author=$(grep -m1 '^author:' "$skill_file" 2>/dev/null | sed 's/author: *//' | tr -d '"' | tr -d "'")
    [ -z "$author" ] && continue
    echo "$author" >> "$author_tmp"
done

# Find authors that appear >5 times
sort "$author_tmp" | uniq -c | sort -rn | while read count author; do
    if [ "$count" -gt 5 ]; then
        warn "Author '$author' appears in $count skills — possible copy-paste without adaptation"
        grep -rl "author: $author" "$PROJECT_ROOT"/skills/*/SKILL.md 2>/dev/null | while read f; do
            echo "    $(echo "$f" | sed "s|$PROJECT_ROOT/||")"
        done
    fi
done
rm -f "$author_tmp"

# ─────────────────────────────────────
# CHECK 2: Skills with identical descriptions
# ─────────────────────────────────────
echo ""
echo "## Check 2: Duplicate descriptions"

desc_tmp=$(mktemp)
for skill_dir in "$PROJECT_ROOT"/skills/*/; do
    skill_file="$skill_dir/SKILL.md"
    [ -f "$skill_file" ] || continue
    name=$(basename "$skill_dir")
    desc=$(grep -m1 '^description:' "$skill_file" 2>/dev/null | sed 's/description: *//' | tr -d '"' | tr -d "'")
    [ -z "$desc" ] && continue
    echo "$name|$desc" >> "$desc_tmp"
done

# Find duplicate descriptions
sort -t'|' -k2 "$desc_tmp" | awk -F'|' '
    prev_desc == $2 && prev_desc != "" { print "DUPLICATE: " prev_name " AND " $1 " -> " $2 }
    { prev_name = $1; prev_desc = $2 }
' | while read line; do
    issue "$line"
done
rm -f "$desc_tmp"

# ─────────────────────────────────────
# CHECK 3: Skills referencing wrong invocation command
# ─────────────────────────────────────
echo ""
echo "## Check 3: Mismatched skill name vs invocation"

for skill_dir in "$PROJECT_ROOT"/skills/*/; do
    skill_file="$skill_dir/SKILL.md"
    [ -f "$skill_file" ] || continue
    dir_name=$(basename "$skill_dir")

    # Check if 'name:' in frontmatter matches directory name
    declared_name=$(grep -m1 '^name:' "$skill_file" 2>/dev/null | sed 's/name: *//' | tr -d '"' | tr -d "'")
    if [ -n "$declared_name" ] && [ "$declared_name" != "$dir_name" ]; then
        warn "Skill dir '$dir_name' but frontmatter says name: '$declared_name'"
    fi
done

# ─────────────────────────────────────
# CHECK 4: Hooks without CONCERNS tag
# ─────────────────────────────────────
echo ""
echo "## Check 4: Hooks missing CONCERNS tag"

missing_concerns=0
for hook in "$PROJECT_ROOT"/hooks/*.sh; do
    [ -f "$hook" ] || continue
    hook_name=$(basename "$hook")
    if ! grep -q '# CONCERNS:' "$hook" 2>/dev/null; then
        warn "Hook '$hook_name' missing # CONCERNS: tag"
        ((missing_concerns++))
    fi
done
[ "$missing_concerns" -eq 0 ] && ok "All hooks have CONCERNS tags"

# ─────────────────────────────────────
# CHECK 5: Unregistered hooks (exist but not in settings.json)
# ─────────────────────────────────────
echo ""
echo "## Check 5: Unregistered hooks"

settings="$PROJECT_ROOT/.claude/settings.json"
if [ -f "$settings" ]; then
    unregistered=0
    for hook in "$PROJECT_ROOT"/hooks/*.sh; do
        [ -f "$hook" ] || continue
        hook_name=$(basename "$hook")
        # Skip _lib helpers and _archived
        [[ "$hook_name" == _* ]] && continue
        if ! grep -q "$hook_name" "$settings" 2>/dev/null; then
            warn "Hook '$hook_name' exists but NOT registered in settings.json"
            ((unregistered++))
        fi
    done
    [ "$unregistered" -eq 0 ] && ok "All hooks registered"
else
    warn "No .claude/settings.json found"
fi

# ─────────────────────────────────────
# CHECK 6: Skills not in CATALOG.md
# ─────────────────────────────────────
echo ""
echo "## Check 6: Skills not in CATALOG.md"

catalog="$PROJECT_ROOT/skills/CATALOG.md"
if [ -f "$catalog" ]; then
    uncataloged=0
    for skill_dir in "$PROJECT_ROOT"/skills/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")
        [ "$skill_name" = "auto-generated" ] && continue
        [ "$skill_name" = "_shared" ] && continue
        if ! grep -q "$skill_name" "$catalog" 2>/dev/null; then
            warn "Skill '$skill_name' not found in CATALOG.md"
            ((uncataloged++))
        fi
    done
    [ "$uncataloged" -eq 0 ] && ok "All skills in catalog"
else
    warn "No skills/CATALOG.md found"
fi

# ─────────────────────────────────────
# CHECK 7: Rules not in RULES-COMPACT.md
# ─────────────────────────────────────
echo ""
echo "## Check 7: Rules not in RULES-COMPACT.md"

compact="$PROJECT_ROOT/rules/RULES-COMPACT.md"
if [ -f "$compact" ]; then
    uncompacted=0
    for rule in "$PROJECT_ROOT"/rules/*.md; do
        [ -f "$rule" ] || continue
        rule_name=$(basename "$rule" .md)
        [ "$rule_name" = "RULES-COMPACT" ] && continue
        if ! grep -qi "$rule_name" "$compact" 2>/dev/null; then
            warn "Rule '$rule_name' not referenced in RULES-COMPACT.md"
            ((uncompacted++))
        fi
    done
    [ "$uncompacted" -eq 0 ] && ok "All rules in compact index"
else
    warn "No rules/RULES-COMPACT.md found"
fi

# ─────────────────────────────────────
# CHECK 8: Oversized components
# ─────────────────────────────────────
echo ""
echo "## Check 8: Oversized components"

for rule in "$PROJECT_ROOT"/rules/*.md; do
    [ -f "$rule" ] || continue
    lines=$(wc -l < "$rule" | tr -d ' ')
    if [ "$lines" -gt 200 ]; then
        warn "Rule '$(basename "$rule")' is $lines lines (max recommended: 60)"
    fi
done

for hook in "$PROJECT_ROOT"/hooks/*.sh; do
    [ -f "$hook" ] || continue
    hook_name=$(basename "$hook")
    [[ "$hook_name" == _* ]] && continue
    lines=$(wc -l < "$hook" | tr -d ' ')
    if [ "$lines" -gt 300 ]; then
        warn "Hook '$hook_name' is $lines lines (max recommended: 200)"
    fi
done

# ─────────────────────────────────────
# CHECK 9: Stale doc numbers
# ─────────────────────────────────────
echo ""
echo "## Check 9: Component counts"

actual_rules=$(find "$PROJECT_ROOT/rules" -name "*.md" -not -name "RULES-COMPACT.md" | wc -l | tr -d ' ')
actual_hooks=$(find "$PROJECT_ROOT/hooks" -name "*.sh" -not -path "*/\\_*" | wc -l | tr -d ' ')
actual_skills=$(find "$PROJECT_ROOT/skills" -mindepth 1 -maxdepth 1 -type d -not -name "auto-generated" -not -name "_shared" | wc -l | tr -d ' ')
actual_libs=$(find "$PROJECT_ROOT/lib" -name "*.py" -not -name "__init__.py" 2>/dev/null | wc -l | tr -d ' ')
actual_tests=$(find "$PROJECT_ROOT/tests" -name "*.py" -not -name "conftest.py" -not -name "__init__.py" 2>/dev/null | wc -l | tr -d ' ')

echo "  Rules:  $actual_rules"
echo "  Hooks:  $actual_hooks"
echo "  Skills: $actual_skills"
echo "  Libs:   $actual_libs"
echo "  Tests:  $actual_tests"

# ─────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────
echo ""
echo "═══════════════════════════════════════"
echo "  ERRORS: $ISSUES  |  WARNINGS: $WARNINGS"
echo "═══════════════════════════════════════"

[ "$ISSUES" -gt 0 ] && exit 1
exit 0
