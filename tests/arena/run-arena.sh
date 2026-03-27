#!/usr/bin/env bash
#
# Cognitive OS Competitive Arena Runner
# Usage: ./run-arena.sh [--competitor <id>] [--task <id>] [--dry-run] [--parallel] [--list]
#
set -euo pipefail

ARENA_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$ARENA_DIR/../../.." && pwd)"
CONFIG_FILE="$ARENA_DIR/arena-config.yaml"
RESULTS_DIR="$PROJECT_ROOT/.cognitive-os/metrics/arena"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RESULTS_FILE="$RESULTS_DIR/arena-results-$TIMESTAMP.jsonl"
REPORT_FILE="$RESULTS_DIR/arena-report-$TIMESTAMP.md"
WORKTREES_DIR="$PROJECT_ROOT/.arena-worktrees"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Defaults
FILTER_COMPETITOR=""
FILTER_TASK=""
DRY_RUN=false
PARALLEL=false
VERBOSE=false

usage() {
    echo "Cognitive OS Competitive Arena"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --competitor <id>   Run only for specified competitor"
    echo "  --task <id>         Run only specified task"
    echo "  --dry-run           Show what would be run without executing"
    echo "  --parallel          Run competitors in parallel (per task)"
    echo "  --list              List all competitors and tasks"
    echo "  --verbose           Show detailed output"
    echo "  -h, --help          Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --list"
    echo "  $0 --competitor cognitive-os --task create-go-service"
    echo "  $0 --task fix-known-bug --parallel"
    echo "  $0 --dry-run"
}

log() { echo -e "${BLUE}[ARENA]${NC} $1"; }
ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERR]${NC} $1"; }

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --competitor) FILTER_COMPETITOR="$2"; shift 2 ;;
        --task) FILTER_TASK="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --parallel) PARALLEL=true; shift ;;
        --list) LIST=true; shift ;;
        --verbose) VERBOSE=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) err "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# Check dependencies
check_deps() {
    for cmd in yq jq git; do
        if ! command -v "$cmd" &>/dev/null; then
            err "$cmd is required but not installed"
            exit 1
        fi
    done
}

# Parse config using yq
get_competitors() {
    yq -r '.arena.competitors[].id' "$CONFIG_FILE"
}

get_competitor_field() {
    local id="$1" field="$2"
    yq -r ".arena.competitors[] | select(.id == \"$id\") | .$field" "$CONFIG_FILE"
}

get_tasks() {
    yq -r '.arena.tasks[].id' "$CONFIG_FILE"
}

get_task_field() {
    local id="$1" field="$2"
    yq -r ".arena.tasks[] | select(.id == \"$id\") | .$field" "$CONFIG_FILE"
}

# List competitors and tasks
list_all() {
    echo ""
    echo -e "${CYAN}=== Competitors ===${NC}"
    echo ""
    printf "%-15s %-25s %-10s %-12s %s\n" "ID" "NAME" "TYPE" "INSTALLED" "REQUIRES"
    printf "%-15s %-25s %-10s %-12s %s\n" "---" "----" "----" "---------" "--------"

    while IFS= read -r id; do
        name=$(get_competitor_field "$id" "name")
        type=$(get_competitor_field "$id" "type")
        installed=$(get_competitor_field "$id" "installed")
        requires=$(get_competitor_field "$id" 'requires // [] | join(", ")')

        if [[ "$installed" == "true" ]]; then
            status="${GREEN}yes${NC}"
        else
            status="${RED}no${NC}"
        fi

        printf "%-15s %-25s %-10s " "$id" "$name" "$type"
        echo -e "${status}           ${requires}"
    done < <(get_competitors)

    echo ""
    echo -e "${CYAN}=== Tasks ===${NC}"
    echo ""
    printf "%-20s %-30s %-12s %-10s %s\n" "ID" "NAME" "CATEGORY" "DIFFICULTY" "TIMEOUT"
    printf "%-20s %-30s %-12s %-10s %s\n" "---" "----" "--------" "----------" "-------"

    while IFS= read -r id; do
        name=$(get_task_field "$id" "name")
        category=$(get_task_field "$id" "category")
        difficulty=$(get_task_field "$id" "difficulty")
        timeout=$(get_task_field "$id" "timeout")
        printf "%-20s %-30s %-12s %-10s %ss\n" "$id" "$name" "$category" "$difficulty" "$timeout"
    done < <(get_tasks)

    echo ""
}

# Create isolated worktree for a competitor run
create_worktree() {
    local competitor="$1" task="$2"
    local worktree_path="$WORKTREES_DIR/${competitor}-${task}-$TIMESTAMP"

    if [[ -d "$PROJECT_ROOT/.git" ]]; then
        local branch="arena/${competitor}-${task}-$TIMESTAMP"
        git -C "$PROJECT_ROOT" worktree add -b "$branch" "$worktree_path" HEAD 2>/dev/null || {
            # Fallback: copy if not a git repo
            mkdir -p "$worktree_path"
            rsync -a --exclude='.arena-worktrees' --exclude='node_modules' --exclude='.git' \
                "$PROJECT_ROOT/" "$worktree_path/"
        }
    else
        mkdir -p "$worktree_path"
        rsync -a --exclude='.arena-worktrees' --exclude='node_modules' \
            "$PROJECT_ROOT/" "$worktree_path/"
    fi

    echo "$worktree_path"
}

# Clean up worktree
cleanup_worktree() {
    local worktree_path="$1"

    if [[ -d "$PROJECT_ROOT/.git" ]]; then
        git -C "$PROJECT_ROOT" worktree remove --force "$worktree_path" 2>/dev/null || true
    fi
    rm -rf "$worktree_path" 2>/dev/null || true
}

# Run a single competitor on a single task
run_single() {
    local competitor="$1" task="$2"

    local comp_name=$(get_competitor_field "$competitor" "name")
    local comp_type=$(get_competitor_field "$competitor" "type")
    local comp_cmd=$(get_competitor_field "$competitor" "command")
    local comp_installed=$(get_competitor_field "$competitor" "installed")
    local task_name=$(get_task_field "$task" "name")
    local task_prompt=$(get_task_field "$task" "prompt")
    local task_timeout=$(get_task_field "$task" "timeout")

    log "Running: ${comp_name} on '${task_name}'"

    # Check if installed
    if [[ "$comp_installed" != "true" ]]; then
        warn "Skipping $comp_name — not installed"
        echo "{\"competitor\":\"$competitor\",\"task\":\"$task\",\"status\":\"skipped\",\"reason\":\"not_installed\",\"timestamp\":\"$TIMESTAMP\"}" >> "$RESULTS_FILE"
        return 0
    fi

    if $DRY_RUN; then
        log "[DRY RUN] Would run $comp_name on $task_name (timeout: ${task_timeout}s)"
        return 0
    fi

    # Create worktree
    local worktree
    worktree=$(create_worktree "$competitor" "$task")
    log "Worktree: $worktree"

    # Touch start marker
    touch "$worktree/.arena-start"

    local start_time=$(date +%s)
    local exit_code=0
    local output_file="$RESULTS_DIR/output-${competitor}-${task}-$TIMESTAMP.log"

    mkdir -p "$RESULTS_DIR"

    case "$comp_type" in
        native)
            # Cognitive OS: run via claude with full .cognitive-os config
            timeout "${task_timeout}s" claude --print --dangerously-skip-permissions \
                -p "$task_prompt" \
                --cwd "$worktree" \
                > "$output_file" 2>&1 || exit_code=$?
            ;;
        cli)
            case "$competitor" in
                aider)
                    timeout "${task_timeout}s" aider --yes --message "$task_prompt" \
                        --auto-commits \
                        > "$output_file" 2>&1 || exit_code=$?
                    ;;
                codex)
                    timeout "${task_timeout}s" codex --approval-mode full-auto \
                        "$task_prompt" \
                        > "$output_file" 2>&1 || exit_code=$?
                    ;;
                goose)
                    echo "$task_prompt" | timeout "${task_timeout}s" goose run \
                        > "$output_file" 2>&1 || exit_code=$?
                    ;;
                opencode)
                    timeout "${task_timeout}s" opencode --print \
                        -p "$task_prompt" \
                        > "$output_file" 2>&1 || exit_code=$?
                    ;;
                claude-code)
                    # Vanilla claude without cognitive-os
                    timeout "${task_timeout}s" claude --print --dangerously-skip-permissions \
                        -p "$task_prompt" \
                        --cwd "$worktree" \
                        --no-config \
                        > "$output_file" 2>&1 || exit_code=$?
                    ;;
                *)
                    warn "No runner defined for CLI competitor: $competitor"
                    exit_code=99
                    ;;
            esac
            ;;
        docker)
            warn "Docker competitors require manual setup. Skipping $comp_name."
            echo "{\"competitor\":\"$competitor\",\"task\":\"$task\",\"status\":\"skipped\",\"reason\":\"docker_not_automated\",\"timestamp\":\"$TIMESTAMP\"}" >> "$RESULTS_FILE"
            cleanup_worktree "$worktree"
            return 0
            ;;
        ide)
            warn "IDE competitors ($comp_name) cannot be automated. Manual benchmark required."
            echo "{\"competitor\":\"$competitor\",\"task\":\"$task\",\"status\":\"skipped\",\"reason\":\"ide_manual_only\",\"timestamp\":\"$TIMESTAMP\"}" >> "$RESULTS_FILE"
            cleanup_worktree "$worktree"
            return 0
            ;;
        clone)
            warn "Clone-type competitor $comp_name requires custom runner. Skipping."
            echo "{\"competitor\":\"$competitor\",\"task\":\"$task\",\"status\":\"skipped\",\"reason\":\"custom_runner_needed\",\"timestamp\":\"$TIMESTAMP\"}" >> "$RESULTS_FILE"
            cleanup_worktree "$worktree"
            return 0
            ;;
        *)
            warn "Unknown competitor type: $comp_type"
            exit_code=99
            ;;
    esac

    local end_time=$(date +%s)
    local elapsed=$((end_time - start_time))

    # Collect basic metrics
    local files_changed=0
    local files_created=0
    local tests_created=0

    if [[ -d "$worktree/.git" ]]; then
        files_changed=$(git -C "$worktree" diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')
        files_created=$(git -C "$worktree" ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')
        tests_created=$(git -C "$worktree" diff --name-only HEAD 2>/dev/null | grep -c '_test\.\|\.spec\.\|\.test\.' || echo 0)
    fi

    # Check if Go code compiles (if applicable)
    local compiles="n/a"
    if find "$worktree" -name "*.go" -newer "$worktree/.arena-start" -print -quit 2>/dev/null | grep -q .; then
        if (cd "$worktree" && go build ./... 2>/dev/null); then
            compiles="true"
        else
            compiles="false"
        fi
    fi

    # Determine status
    local status="completed"
    if [[ $exit_code -eq 124 ]]; then
        status="timeout"
    elif [[ $exit_code -ne 0 ]]; then
        status="error"
    fi

    # Output size as proxy for token usage
    local output_size=0
    if [[ -f "$output_file" ]]; then
        output_size=$(wc -c < "$output_file" | tr -d ' ')
    fi

    # Write result
    local result
    result=$(jq -n \
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
        }')

    echo "$result" >> "$RESULTS_FILE"

    if [[ "$status" == "completed" ]]; then
        ok "$comp_name on $task_name: ${elapsed}s, ${files_changed} files changed"
    elif [[ "$status" == "timeout" ]]; then
        warn "$comp_name on $task_name: TIMEOUT after ${task_timeout}s"
    else
        err "$comp_name on $task_name: ERROR (exit code $exit_code)"
    fi

    # Cleanup worktree
    cleanup_worktree "$worktree"
}

# Generate markdown report from results
generate_report() {
    log "Generating report: $REPORT_FILE"

    local template="$ARENA_DIR/arena-report-template.md"

    cat > "$REPORT_FILE" << 'REPORT_HEADER'
# Cognitive OS Competitive Arena Report

REPORT_HEADER

    echo "**Date**: $(date '+%Y-%m-%d %H:%M:%S')" >> "$REPORT_FILE"
    echo "**Config**: arena-config.yaml v1.0" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    echo "## Results Summary" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    if [[ -f "$RESULTS_FILE" ]]; then
        echo "| Competitor | Task | Status | Time (s) | Files | Tests | Compiles |" >> "$REPORT_FILE"
        echo "|-----------|------|--------|----------|-------|-------|----------|" >> "$REPORT_FILE"

        while IFS= read -r line; do
            local comp task status time files tests compiles
            comp=$(echo "$line" | jq -r '.competitor')
            task=$(echo "$line" | jq -r '.task')
            status=$(echo "$line" | jq -r '.status')
            time=$(echo "$line" | jq -r '.metrics.time_seconds // "—"')
            files=$(echo "$line" | jq -r '.metrics.files_changed // "—"')
            tests=$(echo "$line" | jq -r '.metrics.tests_created // "—"')
            compiles=$(echo "$line" | jq -r '.metrics.compiles // "—"')

            echo "| $comp | $task | $status | $time | $files | $tests | $compiles |" >> "$REPORT_FILE"
        done < "$RESULTS_FILE"

        echo "" >> "$REPORT_FILE"

        # Per-competitor summary
        echo "## Per-Competitor Summary" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"

        for comp in $(jq -r '.competitor' "$RESULTS_FILE" | sort -u); do
            local total completed skipped avg_time
            total=$(jq -r "select(.competitor == \"$comp\") | .status" "$RESULTS_FILE" | wc -l | tr -d ' ')
            completed=$(jq -r "select(.competitor == \"$comp\" and .status == \"completed\") | .status" "$RESULTS_FILE" | wc -l | tr -d ' ')
            skipped=$(jq -r "select(.competitor == \"$comp\" and .status == \"skipped\") | .status" "$RESULTS_FILE" | wc -l | tr -d ' ')
            avg_time=$(jq -r "select(.competitor == \"$comp\" and .status == \"completed\") | .metrics.time_seconds" "$RESULTS_FILE" | awk '{sum+=$1; n++} END {if(n>0) printf "%.0f", sum/n; else print "—"}')

            echo "### $comp" >> "$REPORT_FILE"
            echo "- Tasks: $total total, $completed completed, $skipped skipped" >> "$REPORT_FILE"
            echo "- Average time: ${avg_time}s" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
        done
    else
        echo "_No results found._" >> "$REPORT_FILE"
    fi

    echo "" >> "$REPORT_FILE"
    echo "## Scoring Methodology" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Weights: Quality (35%), Completeness (25%), Speed (20%), Cost (20%)" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Quality scores require LLM evaluation of the output against architecture patterns." >> "$REPORT_FILE"
    echo "Run \`/arena --evaluate\` to trigger LLM-based quality scoring." >> "$REPORT_FILE"

    ok "Report saved: $REPORT_FILE"
}

# Main execution
main() {
    if [[ "${LIST:-}" == "true" ]]; then
        check_deps
        list_all
        exit 0
    fi

    check_deps
    mkdir -p "$RESULTS_DIR"
    mkdir -p "$WORKTREES_DIR"

    log "Arena run: $TIMESTAMP"
    log "Results: $RESULTS_FILE"
    echo ""

    local competitors tasks

    if [[ -n "$FILTER_COMPETITOR" ]]; then
        competitors="$FILTER_COMPETITOR"
    else
        competitors=$(get_competitors)
    fi

    if [[ -n "$FILTER_TASK" ]]; then
        tasks="$FILTER_TASK"
    else
        tasks=$(get_tasks)
    fi

    # Run each task for each competitor
    while IFS= read -r task; do
        [[ -z "$task" ]] && continue

        local task_name=$(get_task_field "$task" "name")
        echo ""
        echo -e "${CYAN}━━━ Task: $task_name ━━━${NC}"
        echo ""

        if $PARALLEL; then
            local pids=()
            while IFS= read -r competitor; do
                [[ -z "$competitor" ]] && continue
                run_single "$competitor" "$task" &
                pids+=($!)
            done <<< "$competitors"

            for pid in "${pids[@]}"; do
                wait "$pid" || true
            done
        else
            while IFS= read -r competitor; do
                [[ -z "$competitor" ]] && continue
                run_single "$competitor" "$task"
            done <<< "$competitors"
        fi
    done <<< "$tasks"

    echo ""
    log "All runs complete."

    # Generate report
    generate_report

    echo ""
    ok "Arena finished. Results: $RESULTS_FILE"
    ok "Report: $REPORT_FILE"
}

main "$@"
