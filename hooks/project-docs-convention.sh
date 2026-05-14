#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: documentation, governance
# Project 10-category docs convention check (ADR-054/055).
#
# Dual-mode:
#   CLI:  bash hooks/project-docs-convention.sh [--project-dir DIR] [--strict] [--json]
#   PreToolUse hook: reads stdin JSON; if tool_input.file_path hits
#                    `docs/`, first warns on new Markdown docs to search/update
#                    existing docs before creating parallel docs, then checks
#                    the 10 canonical dirs convention.
#
# Exit codes:
#   0 — convention satisfied OR soft-warn (default)
#   2 — convention violated AND (--strict OR COS_STRICT_DOCS_CONVENTION=1),
#       or new docs creation under COS_STRICT_DOCS_REINVENTION=1
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

DOCS_REINVENTION_STRICT=0
if [ "${COS_STRICT_DOCS_REINVENTION:-0}" = "1" ]; then
    DOCS_REINVENTION_STRICT=1
fi

ADR_RESERVATION_STRICT=0
if [ "${COS_STRICT_ADR_RESERVATION:-0}" = "1" ]; then
    ADR_RESERVATION_STRICT=1
fi

# PreToolUse hook path: stdin contains JSON payload from Claude Code.
# If tool writes to docs/, extract the project_dir and check convention.
HOOK_FILE_PATH=""
HOOK_TOOL_NAME=""
if [ ! -t 0 ] && [ -z "$PROJECT_DIR" ]; then
    INPUT=$(cat 2>/dev/null || true)
    if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
        HOOK_FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
        HOOK_TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // .tool // empty' 2>/dev/null || true)
        if [ -n "$HOOK_FILE_PATH" ] && echo "$HOOK_FILE_PATH" | grep -q "/docs/"; then
            # Derive project dir = path before /docs/
            PROJECT_DIR="${HOOK_FILE_PATH%%/docs/*}"
        elif [ -n "$HOOK_FILE_PATH" ] && echo "$HOOK_FILE_PATH" | grep -q "^docs/"; then
            PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
            HOOK_FILE_PATH="$PROJECT_DIR/$HOOK_FILE_PATH"
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


# Pre-write docs reinvention guard. Soft by default: it nudges agents to update
# existing docs instead of creating parallel docs. Strict mode is opt-in because
# legitimate new docs are common during reconstruction.
_docs_reinvention_guard() {
    local target="$1"
    local tool_name="$2"

    [ -n "$target" ] || return 0
    echo "$target" | grep -qE '/docs/.+\.md$' || return 0

    # Edits to an existing doc are the desired path; only warn before new files.
    [ ! -e "$target" ] || return 0

    local base query
    base="$(basename "$target" .md)"
    query=$(printf '%s' "$base" | tr '_-' ' ' | tr -cs '[:alnum:] ' '\n' | awk 'length($0) >= 4 {print tolower($0)}' | sort -u | head -6 | tr '\n' ' ')

    local candidates=""
    if command -v python3 >/dev/null 2>&1; then
        candidates=$(PROJECT_DIR="$PROJECT_DIR" QUERY="$query" TARGET="$target" python3 - <<'PYDOC' 2>/dev/null || true
import os, re
from pathlib import Path

root = Path(os.environ.get("PROJECT_DIR", "."))
target = Path(os.environ.get("TARGET", ""))
terms = {t for t in re.findall(r"[a-z0-9]+", os.environ.get("QUERY", "").lower()) if len(t) >= 4}
if not terms:
    raise SystemExit(0)
rows = []
for path in (root / "docs").rglob("*.md"):
    try:
        if path.resolve() == target.resolve():
            continue
        text = path.read_text(errors="ignore")[:4000].lower()
    except OSError:
        continue
    haystack = f"{path.stem.lower()} {text}"
    score = sum(1 for term in terms if term in haystack)
    if score:
        rows.append((score, path.relative_to(root).as_posix()))
for _, rel in sorted(rows, key=lambda item: (-item[0], item[1]))[:5]:
    print(rel)
PYDOC
)
    fi

    {
        echo "DOC REINVENTION GUARD: creating a new Markdown doc at ${target#$PROJECT_DIR/}."
        echo "  Before writing, search/update existing documentation unless this doc has a distinct owner/purpose."
        echo "  Suggested checks:"
        printf '    - grep -Rni %q docs/ README.md\n' "${query:-$base}"
        echo "    - update the closest existing doc instead of creating a parallel one"
        if [ -n "$candidates" ]; then
            echo "  Similar existing docs to inspect:"
            printf '%s\n' "$candidates" | sed 's/^/    - /'
        fi
        [ -n "$tool_name" ] && echo "  Tool: $tool_name"
    } >&2

    [ "$DOCS_REINVENTION_STRICT" = "1" ] && return 2
    return 0
}

if [ -n "$HOOK_FILE_PATH" ]; then
    _docs_reinvention_guard "$HOOK_FILE_PATH" "$HOOK_TOOL_NAME" || exit $?
fi

# ADR reservation guard. Creating a new ADR number without a reservation is a
# coordination bug when multiple agent sessions are active. Soft by default so
# reconstruction work can proceed; strict mode blocks unreserved ADR creation.
_adr_reservation_guard() {
    local target="$1"
    local tool_name="$2"

    [ -n "$target" ] || return 0
    echo "$target" | grep -qE '/docs/02-Decisions/adrs/ADR-[0-9]{3}.*\.md$' || return 0
    [ ! -e "$target" ] || return 0

    local reserved="missing"
    if command -v python3 >/dev/null 2>&1; then
        reserved=$(PROJECT_DIR="$PROJECT_DIR" TARGET="$target" python3 - <<'PYADR' 2>/dev/null || true
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

project = Path(os.environ.get("PROJECT_DIR", "."))
target = Path(os.environ.get("TARGET", ""))
match = re.search(r"ADR-(\d{3})", target.name)
if not match:
    print("missing")
    raise SystemExit(0)
number = int(match.group(1))
state = project / ".cognitive-os" / "locks" / "adr-reservations.json"
try:
    data = json.loads(state.read_text(encoding="utf-8"))
except Exception:
    print("missing")
    raise SystemExit(0)
now = datetime.now(timezone.utc)
for item in data.get("reservations", []):
    if not isinstance(item, dict) or int(item.get("number", -1)) != number:
        continue
    try:
        expires = datetime.fromisoformat(str(item.get("expires_at", "")).replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
    except Exception:
        continue
    if expires > now:
        reserved_path = str(item.get("path", ""))
        if not reserved_path or reserved_path == target.relative_to(project).as_posix():
            print("active")
            raise SystemExit(0)
print("missing")
PYADR
)
    fi

    [ "$reserved" = "active" ] && return 0

    {
        echo "ADR RESERVATION GUARD: creating ${target#$PROJECT_DIR/} without an active ADR reservation."
        echo "  Reserve first to avoid concurrent-session ADR number collisions:"
        echo "    python3 scripts/adr_reserve.py --title '<decision title>' --session-id \"\${COGNITIVE_OS_SESSION_ID:-manual}\" --json"
        [ -n "$tool_name" ] && echo "  Tool: $tool_name"
    } >&2

    [ "$ADR_RESERVATION_STRICT" = "1" ] && return 2
    return 0
}

if [ -n "$HOOK_FILE_PATH" ]; then
    _adr_reservation_guard "$HOOK_FILE_PATH" "$HOOK_TOOL_NAME" || exit $?
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
        echo "  Fix: uv run python3 scripts/project_scaffold.py --project-dir $PROJECT_DIR --project-name '<name>'"
    } >&2
fi

if [ "$STRICT" = "1" ]; then
    exit 2
fi
exit 0
