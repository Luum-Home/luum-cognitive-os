#!/usr/bin/env bash
#
# Quick Arena: Cognitive OS vs Vanilla Claude Code
# Runs 2 tasks on the cognitive-os-demo project without external dependencies.
#
# Usage: ./quick-arena.sh [--dry-run] [--task <id>] [--verbose]
#
# No yq dependency — parses tasks inline.
#
set -euo pipefail

ARENA_DIR="$(cd "$(dirname "$0")" && pwd)"
COGNITIVE_OS_ROOT="$(cd "$ARENA_DIR/../.." && pwd)"
DEMO_PROJECT="/Users/matias.nahuel.amendola/Projects/luum/cognitive-os-demo"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RESULTS_DIR="$COGNITIVE_OS_ROOT/.cognitive-os/metrics/arena"
RESULTS_FILE="$RESULTS_DIR/quick-arena-$TIMESTAMP.jsonl"
REPORT_FILE="$RESULTS_DIR/quick-arena-report-$TIMESTAMP.md"
WORKTREES_DIR="$DEMO_PROJECT/.arena-worktrees"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Defaults
DRY_RUN=false
FILTER_TASK=""
VERBOSE=false

log()  { echo -e "${BLUE}[ARENA]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; }

usage() {
    echo "Quick Arena — Cognitive OS vs Vanilla Claude Code"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run       Show what would run without executing"
    echo "  --task <id>     Run only one task (create-go-service | fix-known-bug)"
    echo "  --verbose       Show full command output"
    echo "  -h, --help      Show this help"
    echo ""
    echo "Competitors: cognitive-os (with .cognitive-os config), claude-code (vanilla)"
    echo "Tasks: create-go-service, fix-known-bug"
    echo "Target: $DEMO_PROJECT"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)  DRY_RUN=true; shift ;;
        --task)     FILTER_TASK="$2"; shift 2 ;;
        --verbose)  VERBOSE=true; shift ;;
        -h|--help)  usage; exit 0 ;;
        *)          err "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# ── Preflight checks ──────────────────────────────────────────────────

preflight() {
    if ! command -v claude &>/dev/null; then
        err "claude CLI not found. Install Claude Code first."
        exit 1
    fi
    if ! command -v jq &>/dev/null; then
        err "jq not found. Install via: brew install jq"
        exit 1
    fi
    if [[ ! -d "$DEMO_PROJECT" ]]; then
        err "Demo project not found at $DEMO_PROJECT"
        exit 1
    fi
    if [[ ! -d "$DEMO_PROJECT/.git" ]]; then
        err "Demo project is not a git repo — cannot create worktrees"
        exit 1
    fi
}

# ── Task definitions (inline, no yq needed) ───────────────────────────
# Compatible with bash 3.x (no associative arrays)

task_name() {
    case "$1" in
        create-go-service) echo "Create Go Microservice" ;;
        fix-known-bug)     echo "Fix Known Bug" ;;
    esac
}

task_timeout() {
    case "$1" in
        create-go-service) echo 300 ;;
        fix-known-bug)     echo 120 ;;
    esac
}

task_prompt() {
    case "$1" in
        create-go-service)
            cat <<'PROMPT'
Create a new Go microservice called 'preferences' under micro-services/preferences/.
Requirements:
- Clean architecture: domain, application, infrastructure layers
- CRUD endpoints: GET/POST/PUT/DELETE /api/preferences/:userId
- PostgreSQL with GORM for persistence
- Entity: UserPreference (id UUID, userId string, key string, value string, createdAt, updatedAt)
- Unit tests for the use case layer
- Dockerfile with multi-stage build
PROMPT
            ;;
        fix-known-bug)
            cat <<'PROMPT'
The function CreateTransfer in the transfers-p2p service panics when amount is zero.
Find the bug, fix it with proper validation (return error for amount <= 0),
and add a unit test covering zero, negative, and valid amounts.
PROMPT
            ;;
    esac
}

# ── Worktree helpers ──────────────────────────────────────────────────

create_worktree() {
    local label="$1"
    local wt_path="$WORKTREES_DIR/${label}-$TIMESTAMP"
    local branch="arena/${label}-$TIMESTAMP"

    git -C "$DEMO_PROJECT" worktree add -b "$branch" "$wt_path" HEAD >/dev/null 2>&1
    echo "$wt_path"
}

cleanup_worktree() {
    local wt_path="$1"
    git -C "$DEMO_PROJECT" worktree remove --force "$wt_path" >/dev/null 2>&1 || true
    local branch_name=$(basename "$wt_path")
    git -C "$DEMO_PROJECT" branch -D "arena/$branch_name" >/dev/null 2>&1 || true
    rm -rf "$wt_path" 2>/dev/null || true
}

# ── Runner ────────────────────────────────────────────────────────────

run_competitor() {
    local competitor="$1" task="$2"
    local tname; tname=$(task_name "$task")
    local tprompt; tprompt=$(task_prompt "$task")
    local ttimeout; ttimeout=$(task_timeout "$task")

    log "Running: ${BOLD}${competitor}${NC} on '${tname}' (timeout: ${ttimeout}s)"

    if $DRY_RUN; then
        log "[DRY RUN] Would run $competitor on $tname"
        return 0
    fi

    # Create isolated worktree
    local worktree
    worktree=$(create_worktree "${competitor}-${task}")
    log "  Worktree: $worktree"

    touch "$worktree/.arena-start"

    local start_time exit_code=0
    start_time=$(date +%s)
    local output_file="$RESULTS_DIR/output-${competitor}-${task}-$TIMESTAMP.log"

    case "$competitor" in
        cognitive-os)
            # Copy .cognitive-os config into the worktree so skills/rules are active
            if [[ -d "$DEMO_PROJECT/.cognitive-os" ]]; then
                cp -R "$DEMO_PROJECT/.cognitive-os" "$worktree/.cognitive-os"
            fi
            (cd "$worktree" && timeout "${ttimeout}s" env -u CLAUDECODE claude --print --dangerously-skip-permissions \
                -p "$tprompt" \
                > "$output_file" 2>&1) || exit_code=$?
            ;;
        claude-code)
            # Vanilla: run in a bare worktree without .cognitive-os
            rm -rf "$worktree/.cognitive-os" 2>/dev/null || true
            (cd "$worktree" && timeout "${ttimeout}s" env -u CLAUDECODE claude --print --dangerously-skip-permissions \
                -p "$tprompt" \
                > "$output_file" 2>&1) || exit_code=$?
            ;;
    esac

    local end_time elapsed
    end_time=$(date +%s)
    elapsed=$((end_time - start_time))

    # Collect metrics
    local files_changed=0 files_created=0 tests_created=0
    if [[ -d "$worktree/.git" ]]; then
        files_changed=$(git -C "$worktree" diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')
        files_created=$(git -C "$worktree" ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')
        tests_created=$(git -C "$worktree" diff --name-only HEAD 2>/dev/null | grep -c '_test\.' || echo 0)
    fi

    # Check compilation
    local compiles="n/a"
    if find "$worktree" -name "*.go" -newer "$worktree/.arena-start" -print -quit 2>/dev/null | grep -q .; then
        if (cd "$worktree" && go build ./... 2>/dev/null); then
            compiles="true"
        else
            compiles="false"
        fi
    fi

    local status="completed"
    [[ $exit_code -eq 124 ]] && status="timeout"
    [[ $exit_code -ne 0 && $exit_code -ne 124 ]] && status="error"

    local output_size=0
    [[ -f "$output_file" ]] && output_size=$(wc -c < "$output_file" | tr -d ' ')

    # Write JSONL result
    jq -cn \
        --arg competitor "$competitor" \
        --arg task "$task" \
        --arg status "$status" \
        --arg timestamp "$TIMESTAMP" \
        --argjson time "$elapsed" \
        --argjson exit_code "$exit_code" \
        --argjson files_changed "$files_changed" \
        --argjson files_created "$files_created" \
        --argjson tests_created "$tests_created" \
        --arg compiles "$compiles" \
        --argjson output_bytes "$output_size" \
        '{
            competitor: $competitor,
            task: $task,
            status: $status,
            timestamp: $timestamp,
            metrics: {
                time_seconds: $time,
                exit_code: $exit_code,
                files_changed: $files_changed,
                files_created: $files_created,
                tests_created: $tests_created,
                compiles: $compiles,
                output_bytes: $output_bytes
            }
        }' >> "$RESULTS_FILE"

    # Print result
    if [[ "$status" == "completed" ]]; then
        ok "$competitor on $tname: ${elapsed}s, ${files_changed} changed, ${files_created} created, ${tests_created} tests"
    elif [[ "$status" == "timeout" ]]; then
        warn "$competitor on $tname: TIMEOUT after ${ttimeout}s"
    else
        err "$competitor on $tname: ERROR (exit $exit_code)"
    fi

    if $VERBOSE && [[ -f "$output_file" ]]; then
        echo "--- output (last 30 lines) ---"
        tail -30 "$output_file"
        echo "--- end ---"
    fi

    cleanup_worktree "$worktree"
}

# ── Report ────────────────────────────────────────────────────────────

generate_report() {
    {
        echo "# Quick Arena Report"
        echo ""
        echo "**Date**: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "**Competitors**: cognitive-os, claude-code (vanilla)"
        echo "**Target project**: cognitive-os-demo"
        echo ""
        echo "## Results"
        echo ""
        echo "| Competitor | Task | Status | Time (s) | Files Changed | Files Created | Tests | Compiles |"
        echo "|-----------|------|--------|----------|---------------|---------------|-------|----------|"

        while IFS= read -r line; do
            comp=$(echo "$line" | jq -r '.competitor')
            task=$(echo "$line" | jq -r '.task')
            st=$(echo "$line" | jq -r '.status')
            tm=$(echo "$line" | jq -r '.metrics.time_seconds')
            fc=$(echo "$line" | jq -r '.metrics.files_changed')
            fcr=$(echo "$line" | jq -r '.metrics.files_created')
            tc=$(echo "$line" | jq -r '.metrics.tests_created')
            cm=$(echo "$line" | jq -r '.metrics.compiles')
            echo "| $comp | $task | $st | $tm | $fc | $fcr | $tc | $cm |"
        done < "$RESULTS_FILE"

        echo ""
        echo "## Analysis"
        echo ""
        echo "Review the output logs in \`$RESULTS_DIR/\` for detailed comparison."
        echo ""
        echo "Scoring weights: Quality (35%), Completeness (25%), Speed (20%), Cost (20%)"
    } > "$REPORT_FILE"

    ok "Report: $REPORT_FILE"
}

# ── Main ──────────────────────────────────────────────────────────────

main() {
    preflight
    mkdir -p "$RESULTS_DIR" "$WORKTREES_DIR"

    echo ""
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}  Quick Arena: Cognitive OS vs Vanilla Claude Code  ${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    log "Timestamp: $TIMESTAMP"
    log "Target: $DEMO_PROJECT"
    log "Results: $RESULTS_DIR/"
    echo ""

    local tasks=("create-go-service" "fix-known-bug")

    if [[ -n "$FILTER_TASK" ]]; then
        tasks=("$FILTER_TASK")
    fi

    local competitors=("cognitive-os" "claude-code")

    for task in "${tasks[@]}"; do
        echo -e "${CYAN}━━━ Task: $(task_name "$task") ━━━${NC}"
        echo ""
        for comp in "${competitors[@]}"; do
            run_competitor "$comp" "$task"
            echo ""
        done
    done

    if ! $DRY_RUN; then
        generate_report
    fi

    echo ""
    ok "Quick arena finished."
    [[ -f "$RESULTS_FILE" ]] && ok "Results: $RESULTS_FILE" || true
    [[ -f "$REPORT_FILE" ]] && ok "Report: $REPORT_FILE" || true
}

main "$@"
