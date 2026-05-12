#!/usr/bin/env bash
# SCOPE: project
# credibility-audit.sh — Pre-launch scan for credibility/transparency risks
#
# Detects content that could damage reader trust at first contact:
# TODOs in production code, embarrassing commit messages, self-deprecating
# language, operator PII residue, aspirational promises, outdated date
# markers, agent-trailer leakage, placeholder text in user-facing docs.
#
# Output:
#   - Console summary by severity (BLOCK / WARN / INFO)
#   - Optional JSON via --json flag
#   - Exit codes:
#     0  clean (no BLOCK findings)
#     1  BLOCK findings present
#     2  scan failed
#
# Usage:
#   bash scripts/credibility-audit.sh
#   bash scripts/credibility-audit.sh --json
#   bash scripts/credibility-audit.sh --strict   # treat WARN as BLOCK
#
# Optional external tools that enhance results when installed:
#   - codespell  (typo detection)
#   - vale       (weasel-word + style detection)
#   - lychee     (broken-link detection in docs)
#
# See: scripts/install-credibility-tools.sh (optional installer)
set -euo pipefail

PROJECT_ROOT="${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}"
JSON_OUTPUT=""
STRICT=0

while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON_OUTPUT=1 ;;
    --strict) STRICT=1 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
  esac
  shift
done

# ────────────────────────────────────────────────────────────────────────────
# Result tracking — one row per finding
# ────────────────────────────────────────────────────────────────────────────
declare -a FINDINGS=()
BLOCK_COUNT=0
WARN_COUNT=0
INFO_COUNT=0

emit() {
  local severity="$1"
  local code="$2"
  local count="$3"
  local sample="$4"
  case "$severity" in
    BLOCK) BLOCK_COUNT=$((BLOCK_COUNT + 1)) ;;
    WARN)  WARN_COUNT=$((WARN_COUNT + 1)) ;;
    INFO)  INFO_COUNT=$((INFO_COUNT + 1)) ;;
  esac
  FINDINGS+=("${severity}|${code}|${count}|${sample}")
}

# Helper: count lines in input, ignore-empty
count_lines() {
  if [ -z "$1" ]; then echo 0; else echo "$1" | wc -l | tr -d ' '; fi
}

cd "${PROJECT_ROOT}"

# ────────────────────────────────────────────────────────────────────────────
# 1. TODO / FIXME / HACK / XXX in committed PRODUCTION code
# (excluding tests, docs, rules — those legitimately have TODOs)
# ────────────────────────────────────────────────────────────────────────────
# \bTODO\b avoids matching "todo" in random ids; XXX requires word boundary
# but NOT inside mktemp templates (XXXXXX). We accept TODO|FIXME|HACK with
# word boundaries; XXX requires standalone (not part of a larger token).
TODOS=$(git grep -nE '\b(TODO|FIXME|HACK)\b|(^|[^A-Za-z])XXX([^A-Za-z]|$)' -- \
        '*.go' '*.py' '*.sh' \
        ':(exclude)*test*' \
        ':(exclude)tests/*' \
        ':(exclude)docs/*' \
        ':(exclude)rules/*' \
        ':(exclude)skills/*' \
        2>/dev/null \
        | grep -vE 'mktemp.*XXXXXX|XXXXXX.*mktemp|tmpfile.*XXXXXX' \
        || true)
TODO_COUNT=$(count_lines "$TODOS")
if [ "$TODO_COUNT" -gt 0 ]; then
  SAMPLE=$(echo "$TODOS" | head -3 | tr '\n' ';' | sed 's/;$//')
  emit "WARN" "todo-in-production-code" "$TODO_COUNT" "$SAMPLE"
fi

# ────────────────────────────────────────────────────────────────────────────
# 2. Embarrassing commit messages
# ────────────────────────────────────────────────────────────────────────────
EMBARRASSING=$(git log --all --oneline 2>/dev/null \
               | grep -iE '\b(wip|hack|ugly|asdf|temp|doesnt work|not working|gross|sketchy|workaround)\b' \
               || true)
EMBARRASSING_COUNT=$(count_lines "$EMBARRASSING")
if [ "$EMBARRASSING_COUNT" -gt 0 ]; then
  SAMPLE=$(echo "$EMBARRASSING" | head -3 | tr '\n' ';' | sed 's/;$//')
  emit "WARN" "embarrassing-commit-messages" "$EMBARRASSING_COUNT" "$SAMPLE"
fi

# ────────────────────────────────────────────────────────────────────────────
# 3. Self-deprecating language in user-facing docs
# ────────────────────────────────────────────────────────────────────────────
# Self-deprecation = OUR product is bad. "broken" alone matches too many
# legitimate "we detect/prevent broken X" claims (which is the VALUE PROP).
# Tighten to phrases where the SUBJECT is the speaker/product.
SELF_DEPRECATE=$(grep -rinE "\b(it'?s a mess|this is a mess|this is a hack|it'?s a hack|it'?s terrible|it'?s gross|it'?s ugly|don'?t ask why|i hate this|this sucks|honestly broken)\b" \
                 README.md docs/08-References/business/ docs/08-References/root/competitive-landscape.md \
                 docs/value-proposition.md docs/00-MOCs/entrypoints/quickstart.md docs/00-MOCs/entrypoints/getting-started.md \
                 docs/00-MOCs/entrypoints/faq.md 2>/dev/null \
                 || true)
SELF_DEP_COUNT=$(count_lines "$SELF_DEPRECATE")
if [ "$SELF_DEP_COUNT" -gt 0 ]; then
  SAMPLE=$(echo "$SELF_DEPRECATE" | head -2 | tr '\n' ';' | sed 's/;$//')
  emit "BLOCK" "self-deprecating-in-user-docs" "$SELF_DEP_COUNT" "$SAMPLE"
fi

# ────────────────────────────────────────────────────────────────────────────
# 4. Operator personal info residue (HEAD only — history is ADR-218 territory)
# ────────────────────────────────────────────────────────────────────────────
PII_HEAD=$(git grep -ilE "matias\.nahuel|soporte\.esolutions" 2>/dev/null \
           | grep -vE "^docs/02-Decisions/adrs/ADR-(218|214)" \
           | grep -vE "session-self-bite-pattern" \
           || true)
PII_COUNT=$(count_lines "$PII_HEAD")
if [ "$PII_COUNT" -gt 0 ]; then
  SAMPLE=$(echo "$PII_HEAD" | head -3 | tr '\n' ';' | sed 's/;$//')
  emit "BLOCK" "operator-pii-in-tracked-files" "$PII_COUNT" "$SAMPLE"
fi

# ────────────────────────────────────────────────────────────────────────────
# 5. TBD / Coming Soon / Placeholder in user-facing docs
# ────────────────────────────────────────────────────────────────────────────
TBD=$(grep -rinE "\bTBD\b|\[Coming Soon\]|\[TBD\]|\[Placeholder\]|coming soon|< *to do *>" \
      README.md docs/00-MOCs/entrypoints/quickstart.md docs/00-MOCs/entrypoints/getting-started.md docs/00-MOCs/entrypoints/faq.md \
      docs/08-References/business/ 2>/dev/null || true)
TBD_COUNT=$(count_lines "$TBD")
if [ "$TBD_COUNT" -gt 0 ]; then
  SAMPLE=$(echo "$TBD" | head -2 | tr '\n' ';' | sed 's/;$//')
  emit "BLOCK" "placeholder-in-user-facing-docs" "$TBD_COUNT" "$SAMPLE"
fi

# ────────────────────────────────────────────────────────────────────────────
# 6. Outdated date markers (year < current - 2)
# ────────────────────────────────────────────────────────────────────────────
CURRENT_YEAR=$(date -u +%Y)
THRESHOLD_YEAR=$((CURRENT_YEAR - 2))
OUTDATED=$(grep -rinE "(as of |last updated.*|updated:.*)\b202[0-4]\b" \
           README.md docs/ 2>/dev/null \
           | awk -F: -v thr="$THRESHOLD_YEAR" '{
               match($0, /202[0-9]/);
               year = substr($0, RSTART, RLENGTH);
               if (year < thr) print
             }' \
           || true)
OUTDATED_COUNT=$(count_lines "$OUTDATED")
if [ "$OUTDATED_COUNT" -gt 0 ]; then
  SAMPLE=$(echo "$OUTDATED" | head -2 | tr '\n' ';' | sed 's/;$//')
  emit "WARN" "outdated-date-markers" "$OUTDATED_COUNT" "$SAMPLE"
fi

# ────────────────────────────────────────────────────────────────────────────
# 7. X-COS-Session / X-COS-Origin in commit BODIES (history)
# Internal session ids leak how dev was done; ADR-218 sanitization may scrub.
# ────────────────────────────────────────────────────────────────────────────
TRAILER_COUNT=$(git log --all --pretty=format:"%B" 2>/dev/null \
                | grep -cE "^X-COS-(Session|Origin|Harness):" || echo 0)
if [ "$TRAILER_COUNT" -gt 0 ]; then
  emit "INFO" "x-cos-trailers-in-commit-bodies" "$TRAILER_COUNT" "internal session ids visible to public"
fi

# ────────────────────────────────────────────────────────────────────────────
# 8. AI-provider-looking invented emails / co-author trailers
# Agents can hallucinate public provider identities. This is not a secret, but
# it damages authorship transparency and GitHub attribution.
# ────────────────────────────────────────────────────────────────────────────
if [ -x "scripts/ai-provider-identity-guard" ]; then
  AI_ID_JSON=$(scripts/ai-provider-identity-guard --project-dir "$PROJECT_ROOT" --tracked --json 2>/dev/null || true)
  AI_ID_COUNT=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("finding_count", 0))' <<< "$AI_ID_JSON" 2>/dev/null || echo 0)
  if [ "$AI_ID_COUNT" -gt 0 ]; then
    SAMPLE=$(python3 -c 'import json,sys; r=json.load(sys.stdin); print(";".join(f"{f["path"]}:{f["line"]}" for f in r.get("findings", [])[:3]))' <<< "$AI_ID_JSON" 2>/dev/null || echo "run scripts/ai-provider-identity-guard")
    emit "BLOCK" "ai-provider-invented-identity" "$AI_ID_COUNT" "$SAMPLE"
  fi
fi

# ────────────────────────────────────────────────────────────────────────────
# 9. Promises without backing ("will support", "coming soon")
# ────────────────────────────────────────────────────────────────────────────
PROMISES=$(grep -rinE "\b(will support|coming soon|to be added|future support|planned support)\b" \
           docs/08-References/business/ docs/08-References/root/competitive-landscape.md \
           docs/value-proposition.md README.md 2>/dev/null || true)
PROMISES_COUNT=$(count_lines "$PROMISES")
if [ "$PROMISES_COUNT" -gt 0 ]; then
  SAMPLE=$(echo "$PROMISES" | head -2 | tr '\n' ';' | sed 's/;$//')
  emit "WARN" "unbacked-promises-in-marketing-docs" "$PROMISES_COUNT" "$SAMPLE"
fi

# ────────────────────────────────────────────────────────────────────────────
# 10. Dead code refs (commented-out "old approach")
# ────────────────────────────────────────────────────────────────────────────
DEAD_CODE=$(git grep -nE '^\s*#\s*(old|deprecated|removed|legacy|dead code|TODO remove)' \
            -- '*.py' '*.sh' '*.go' \
            ':(exclude)*test*' \
            ':(exclude)tests/*' \
            2>/dev/null || true)
DEAD_COUNT=$(count_lines "$DEAD_CODE")
if [ "$DEAD_COUNT" -gt 0 ]; then
  SAMPLE=$(echo "$DEAD_CODE" | head -2 | tr '\n' ';' | sed 's/;$//')
  emit "WARN" "dead-code-comments" "$DEAD_COUNT" "$SAMPLE"
fi

# ────────────────────────────────────────────────────────────────────────────
# 11. Optional: codespell typo scan if installed
# ────────────────────────────────────────────────────────────────────────────
if command -v codespell >/dev/null 2>&1; then
  TYPOS=$(codespell --skip='.git,.venv,node_modules,.cognitive-os,reference,*.lock' \
                    --quiet-level=2 \
                    README.md docs/ 2>/dev/null | head -50 || true)
  TYPO_COUNT=$(count_lines "$TYPOS")
  if [ "$TYPO_COUNT" -gt 0 ]; then
    SAMPLE=$(echo "$TYPOS" | head -2 | tr '\n' ';' | sed 's/;$//')
    emit "INFO" "typos-codespell" "$TYPO_COUNT" "$SAMPLE"
  fi
fi

# ────────────────────────────────────────────────────────────────────────────
# 12. Optional: vale weasel-word scan if installed
# ────────────────────────────────────────────────────────────────────────────
if command -v vale >/dev/null 2>&1; then
  VALE_COUNT=$(vale --output line README.md docs/08-References/business/ 2>/dev/null \
               | wc -l | tr -d ' ' || echo 0)
  if [ "$VALE_COUNT" -gt 0 ]; then
    emit "INFO" "vale-style-warnings" "$VALE_COUNT" "run 'vale README.md docs/08-References/business/' for details"
  fi
fi

# ────────────────────────────────────────────────────────────────────────────
# 13. Optional: lychee broken-link scan if installed
# ────────────────────────────────────────────────────────────────────────────
if command -v lychee >/dev/null 2>&1; then
  BROKEN=$(lychee --no-progress --offline README.md docs/ 2>&1 \
           | grep -cE '✗|broken|404' || echo 0)
  if [ "$BROKEN" -gt 0 ]; then
    emit "WARN" "broken-internal-links" "$BROKEN" "run 'lychee README.md docs/' for details"
  fi
fi

# ────────────────────────────────────────────────────────────────────────────
# Output
# ────────────────────────────────────────────────────────────────────────────
TOTAL=$((BLOCK_COUNT + WARN_COUNT + INFO_COUNT))

if [ -n "$JSON_OUTPUT" ]; then
  printf '{\n  "schema_version": "credibility-audit-report/v1",\n'
  printf '  "summary": {\n'
  printf '    "block_count": %d,\n' "$BLOCK_COUNT"
  printf '    "warn_count": %d,\n' "$WARN_COUNT"
  printf '    "info_count": %d,\n' "$INFO_COUNT"
  printf '    "total": %d,\n' "$TOTAL"
  printf '    "strict_mode": %s\n' "$([ "$STRICT" -eq 1 ] && echo true || echo false)"
  printf '  },\n  "findings": [\n'
  first=1
  for finding in "${FINDINGS[@]}"; do
    [ "$first" -eq 1 ] && first=0 || printf ',\n'
    IFS='|' read -r sev code count sample <<< "$finding"
    sample=${sample//\\/\\\\}
    sample=${sample//\"/\\\"}
    printf '    {"severity":"%s","code":"%s","count":%s,"sample":"%s"}' \
           "$sev" "$code" "$count" "$sample"
  done
  printf '\n  ]\n}\n'
else
  echo ""
  echo "=== Credibility & Transparency Audit ==="
  echo ""
  if [ "$TOTAL" -eq 0 ]; then
    echo "  ✓ No findings."
  else
    [ "$BLOCK_COUNT" -gt 0 ] && echo "  🔴 BLOCK ($BLOCK_COUNT):"
    for finding in "${FINDINGS[@]}"; do
      IFS='|' read -r sev code count sample <<< "$finding"
      [ "$sev" = "BLOCK" ] && printf "     %s (%s): %s\n" "$code" "$count" "$sample"
    done
    [ "$WARN_COUNT" -gt 0 ] && echo "  🟡 WARN ($WARN_COUNT):"
    for finding in "${FINDINGS[@]}"; do
      IFS='|' read -r sev code count sample <<< "$finding"
      [ "$sev" = "WARN" ] && printf "     %s (%s): %s\n" "$code" "$count" "$sample"
    done
    [ "$INFO_COUNT" -gt 0 ] && echo "  🔵 INFO ($INFO_COUNT):"
    for finding in "${FINDINGS[@]}"; do
      IFS='|' read -r sev code count sample <<< "$finding"
      [ "$sev" = "INFO" ] && printf "     %s (%s): %s\n" "$code" "$count" "$sample"
    done
  fi
  echo ""
  echo "  Optional tools to install for richer scans:"
  command -v codespell >/dev/null 2>&1 && echo "     ✓ codespell"  || echo "     ☐ codespell  (brew install codespell)"
  command -v vale >/dev/null 2>&1      && echo "     ✓ vale"       || echo "     ☐ vale       (brew install vale)"
  command -v lychee >/dev/null 2>&1    && echo "     ✓ lychee"     || echo "     ☐ lychee     (brew install lychee)"
  echo ""
fi

# Exit code
if [ "$BLOCK_COUNT" -gt 0 ]; then
  exit 1
elif [ "$STRICT" -eq 1 ] && [ "$WARN_COUNT" -gt 0 ]; then
  exit 1
else
  exit 0
fi
