#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: documentation, governance
# Project 10-category docs convention check (ADR-054/055).
#
# Dual-mode:
#   CLI:  bash hooks/project-docs-convention.sh [--project-dir DIR] [--strict] [--json]
#   PreToolUse hook: reads stdin JSON; if tool_input.file_path hits
#                    `docs/` in a project without the 10 canonical dirs,
#                    emits a warning (never blocks unless --strict).
#
# Exit codes:
#   0 — convention satisfied OR soft-warn (default)
#   2 — convention violated AND (--strict OR COS_STRICT_DOCS_CONVENTION=1)
#
# Always safe on error: a missing docs/ dir is a WARNING, not a crash.
#
# Author: luum (ADR-054/055)
set -uo pipefail

CATEGORIES=(
    "01-contexto"
    "02-arquitectura"
    "03-dominio-riesgo"
    "04-seguridad"
    "05-features"
    "06-backoffice"
    "07-investigacion"
    "08-estandares"
    "09-plan-ejecucion"
    "10-resumenes"
)

PROJECT_DIR=""
STRICT=0
JSON_OUT=0
STDIN_MODE=0

# Parse args
while [ $# -gt 0 ]; do
    case "$1" in
        --project-dir) PROJECT_DIR="$2"; shift 2;;
        --strict)      STRICT=1; shift;;
        --json)        JSON_OUT=1; shift;;
        --stdin)       STDIN_MODE=1; shift;;
        -h|--help)
            cat <<EOF
Usage: $0 [--project-dir DIR] [--strict] [--json]
       (or via stdin from PreToolUse hook)

Checks <project>/docs/ for the 10 canonical ADR-054 categories.
Missing categories:
  - default: WARNING to stderr, exit 0
  - --strict or COS_STRICT_DOCS_CONVENTION=1: exit 2
EOF
            exit 0;;
        *) shift;;
    esac
done

# Env kill-switch → strict
if [ "${COS_STRICT_DOCS_CONVENTION:-0}" = "1" ]; then
    STRICT=1
fi

# PreToolUse hook path: stdin contains JSON payload from Claude Code.
# If tool writes to docs/, extract the project_dir and check convention.
HOOK_FILE_PATH=""
if [ ! -t 0 ] && [ -z "$PROJECT_DIR" ]; then
    INPUT=$(cat 2>/dev/null || true)
    if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
        HOOK_FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
        if [ -n "$HOOK_FILE_PATH" ] && echo "$HOOK_FILE_PATH" | grep -q "/docs/"; then
            # Derive project dir = path before /docs/
            PROJECT_DIR="${HOOK_FILE_PATH%%/docs/*}"
        else
            # Hook fired but not a docs/ write — silent pass.
            exit 0
        fi
    else
        exit 0
    fi
fi

# CLI fallback: default to CWD
if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR="$(pwd)"
fi

DOCS_DIR="$PROJECT_DIR/docs"
missing=()
present=()

if [ ! -d "$DOCS_DIR" ]; then
    msg="docs/ directory missing under $PROJECT_DIR — run /project-scaffold"
    if [ "$JSON_OUT" = "1" ]; then
        printf '{"project_dir":"%s","status":"missing_docs_dir","missing":[],"present":[]}\n' "$PROJECT_DIR"
    else
        echo "WARNING: $msg" >&2
    fi
    [ "$STRICT" = "1" ] && exit 2
    exit 0
fi

for cat in "${CATEGORIES[@]}"; do
    if [ -d "$DOCS_DIR/$cat" ]; then
        present+=("$cat")
    else
        missing+=("$cat")
    fi
done

if [ "$JSON_OUT" = "1" ]; then
    # Emit JSON
    printf '{"project_dir":"%s","status":"%s","present_count":%d,"missing_count":%d,"missing":[' \
        "$PROJECT_DIR" \
        "$([ ${#missing[@]} -eq 0 ] && echo ok || echo violation)" \
        "${#present[@]}" \
        "${#missing[@]}"
    for i in "${!missing[@]}"; do
        [ "$i" -gt 0 ] && printf ','
        printf '"%s"' "${missing[$i]}"
    done
    printf ']}\n'
fi

if [ ${#missing[@]} -eq 0 ]; then
    [ "$JSON_OUT" = "1" ] || echo "OK: 10/10 canonical docs categories present under $DOCS_DIR"
    exit 0
fi

if [ "$JSON_OUT" != "1" ]; then
    {
        echo "WARNING: ADR-054 docs convention — ${#missing[@]}/10 canonical categories missing under $DOCS_DIR"
        for m in "${missing[@]}"; do
            echo "  - docs/$m/"
        done
        echo "  Fix: uv run python3 scripts/project-scaffold.py --project-dir $PROJECT_DIR --project-name '<name>'"
    } >&2
fi

if [ "$STRICT" = "1" ]; then
    exit 2
fi
exit 0
