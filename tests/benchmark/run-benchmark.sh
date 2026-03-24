#!/usr/bin/env bash
# Cognitive OS Benchmark Runner
# Compares Cognitive OS vs BMAD METHOD v6 on standardized coding tasks
#
# Usage:
#   bash .cognitive-os/tests/benchmark/run-benchmark.sh [options]
#
# Options:
#   --system cognitive-os|bmad    System to benchmark (default: cognitive-os)
#   --task <task-id>          Run only a specific task (default: all)
#   --model <model>           Override model (default: from config)
#   --max-turns <n>           Override max turns (default: from config)
#   --dry-run                 Show what would run without executing
#   --no-cleanup              Keep worktrees after run
#   --help                    Show this help

set -euo pipefail

# --- Constants ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CONFIG_FILE="$SCRIPT_DIR/benchmark-config.yaml"
RESULTS_DIR="$PROJECT_ROOT/.cognitive-os/metrics"
RESULTS_FILE="$RESULTS_DIR/benchmark-results.jsonl"
WORKTREE_BASE="$PROJECT_ROOT/.cognitive-os/tests/benchmark/worktrees"
REPORT_TEMPLATE="$SCRIPT_DIR/benchmark-report-template.md"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
RUN_ID=$(date +"%Y%m%d-%H%M%S")

# --- Defaults ---
SYSTEM="cognitive-os"
TASK_FILTER=""
MODEL=""
MAX_TURNS=""
DRY_RUN=false
NO_CLEANUP=false

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# --- Functions ---

usage() {
    head -15 "$0" | tail -13 | sed 's/^# \?//'
    exit 0
}

log() { echo -e "${BLUE}[benchmark]${NC} $*"; }
log_ok() { echo -e "${GREEN}[benchmark]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[benchmark]${NC} $*"; }
log_err() { echo -e "${RED}[benchmark]${NC} $*"; }

check_dependencies() {
    local missing=()
    for cmd in claude git jq yq; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_err "Missing dependencies: ${missing[*]}"
        log_err "Install with: brew install ${missing[*]}"
        exit 1
    fi
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --system) SYSTEM="$2"; shift 2 ;;
            --task) TASK_FILTER="$2"; shift 2 ;;
            --model) MODEL="$2"; shift 2 ;;
            --max-turns) MAX_TURNS="$2"; shift 2 ;;
            --dry-run) DRY_RUN=true; shift ;;
            --no-cleanup) NO_CLEANUP=true; shift ;;
            --help|-h) usage ;;
            *) log_err "Unknown option: $1"; usage ;;
        esac
    done
}

read_config() {
    if [[ -z "$MODEL" ]]; then
        MODEL=$(yq '.settings.model' "$CONFIG_FILE")
    fi
    if [[ -z "$MAX_TURNS" ]]; then
        MAX_TURNS=$(yq '.settings.max_turns' "$CONFIG_FILE")
    fi
    TIMEOUT=$(yq '.settings.timeout_seconds' "$CONFIG_FILE")
}

get_benchmark_ids() {
    if [[ -n "$TASK_FILTER" ]]; then
        echo "$TASK_FILTER"
    else
        yq '.benchmarks[].id' "$CONFIG_FILE"
    fi
}

get_benchmark_field() {
    local id="$1" field="$2"
    yq ".benchmarks[] | select(.id == \"$id\") | .$field" "$CONFIG_FILE"
}

get_metric_count() {
    local id="$1"
    yq ".benchmarks[] | select(.id == \"$id\") | .metrics | length" "$CONFIG_FILE"
}

get_metric_field() {
    local id="$1" index="$2" field="$3"
    yq ".benchmarks[] | select(.id == \"$id\") | .metrics[$index].$field" "$CONFIG_FILE"
}

create_worktree() {
    local task_id="$1"
    local worktree_path="$WORKTREE_BASE/$RUN_ID-$task_id"

    mkdir -p "$WORKTREE_BASE"

    # If in a git repo, use git worktree; otherwise just copy
    if git -C "$PROJECT_ROOT" rev-parse --is-inside-work-tree &>/dev/null; then
        local branch="benchmark/$RUN_ID-$task_id"
        git -C "$PROJECT_ROOT" worktree add -b "$branch" "$worktree_path" HEAD 2>/dev/null || {
            # Fallback: copy directory
            log_warn "Git worktree failed, falling back to directory copy"
            mkdir -p "$worktree_path"
            rsync -a --exclude='.git' --exclude='node_modules' --exclude='.cognitive-os/tests/benchmark/worktrees' \
                "$PROJECT_ROOT/" "$worktree_path/"
        }
    else
        mkdir -p "$worktree_path"
        rsync -a --exclude='node_modules' --exclude='.cognitive-os/tests/benchmark/worktrees' \
            "$PROJECT_ROOT/" "$worktree_path/"
    fi

    echo "$worktree_path"
}

cleanup_worktree() {
    local worktree_path="$1" task_id="$2"

    if [[ "$NO_CLEANUP" == "true" ]]; then
        log "Keeping worktree: $worktree_path"
        return
    fi

    if git -C "$PROJECT_ROOT" rev-parse --is-inside-work-tree &>/dev/null; then
        git -C "$PROJECT_ROOT" worktree remove --force "$worktree_path" 2>/dev/null || true
        git -C "$PROJECT_ROOT" branch -D "benchmark/$RUN_ID-$task_id" 2>/dev/null || true
    else
        rm -rf "$worktree_path"
    fi
}

run_setup() {
    local worktree_path="$1" task_id="$2"
    local setup
    setup=$(get_benchmark_field "$task_id" "setup")

    if [[ "$setup" != "null" && -n "$setup" ]]; then
        log "Running setup for $task_id: $setup"
        (cd "$worktree_path" && eval "$setup") || {
            log_warn "Setup command failed (may be expected for some benchmarks)"
        }
    fi
}

build_prompt() {
    local task_id="$1" system="$2"
    local prompt
    prompt=$(get_benchmark_field "$task_id" "prompt")

    if [[ "$system" == "bmad" ]]; then
        # Wrap with BMAD context
        echo "You are using the BMAD Method v6. Follow BMAD conventions and patterns. Task: $prompt"
    else
        # Cognitive OS uses its own rules from .cognitive-os/
        echo "$prompt"
    fi
}

run_claude_headless() {
    local worktree_path="$1" prompt="$2" task_id="$3"
    local output_file="$WORKTREE_BASE/$RUN_ID-$task_id-output.json"

    log "Running Claude headless for task: $task_id"
    log "  Model: $MODEL"
    log "  Max turns: $MAX_TURNS"
    log "  Timeout: ${TIMEOUT}s"

    local start_time
    start_time=$(date +%s)

    # Run Claude Code headless
    if timeout "$TIMEOUT" claude -p "$prompt" \
        --output-format json \
        --max-turns "$MAX_TURNS" \
        --model "$MODEL" \
        2>/dev/null > "$output_file"; then
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))

        log_ok "Task $task_id completed in ${duration}s"
        echo "$output_file|$duration"
    else
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))

        log_err "Task $task_id failed or timed out after ${duration}s"
        echo "$output_file|$duration"
    fi
}

extract_tokens() {
    local output_file="$1"
    if [[ -f "$output_file" ]]; then
        # Try to extract token usage from Claude JSON output
        local input_tokens output_tokens
        input_tokens=$(jq -r '.usage.input_tokens // .stats.input_tokens // 0' "$output_file" 2>/dev/null || echo "0")
        output_tokens=$(jq -r '.usage.output_tokens // .stats.output_tokens // 0' "$output_file" 2>/dev/null || echo "0")
        echo "$((input_tokens + output_tokens))"
    else
        echo "0"
    fi
}

count_files() {
    local worktree_path="$1" pattern="$2"
    find "$worktree_path" -name "$pattern" -newer "$CONFIG_FILE" 2>/dev/null | wc -l | tr -d ' '
}

check_compilation() {
    local worktree_path="$1" task_id="$2"
    local metric_count
    metric_count=$(get_metric_count "$task_id")

    for ((i = 0; i < metric_count; i++)); do
        local mtype mcheck
        mtype=$(get_metric_field "$task_id" "$i" "type")
        mcheck=$(get_metric_field "$task_id" "$i" "check")

        if [[ "$mtype" == "boolean" && "$mcheck" != "null" && -n "$mcheck" ]]; then
            log "Running compilation check: $mcheck"
            if (cd "$worktree_path" && eval "$mcheck") &>/dev/null; then
                echo "true"
                return
            else
                echo "false"
                return
            fi
        fi
    done
    echo "skipped"
}

run_llm_eval() {
    local worktree_path="$1" task_id="$2"
    local metric_count
    metric_count=$(get_metric_count "$task_id")
    local scores=""

    for ((i = 0; i < metric_count; i++)); do
        local mtype mname mprompt
        mtype=$(get_metric_field "$task_id" "$i" "type")
        mname=$(get_metric_field "$task_id" "$i" "name")
        mprompt=$(get_metric_field "$task_id" "$i" "prompt")

        if [[ "$mtype" == "llm_eval" ]]; then
            log "Running LLM evaluation for metric: $mname"

            # Get git diff of changes for context
            local diff_context
            diff_context=$(cd "$worktree_path" && git diff HEAD 2>/dev/null | head -500 || echo "No git diff available")

            local eval_prompt="Evaluate the following code changes. $mprompt

Changes:
$diff_context"

            local score
            score=$(claude -p "$eval_prompt" --output-format text --max-turns 1 --model "$MODEL" 2>/dev/null | grep -oE '[0-9]+' | head -1 || echo "0")

            if [[ -z "$score" ]]; then
                score=0
            fi

            scores="$scores|$mname:$score"
            log_ok "  $mname: $score/10"
        fi
    done

    echo "$scores"
}

count_new_files() {
    local worktree_path="$1"
    # Count files modified or created (via git status)
    (cd "$worktree_path" && git status --porcelain 2>/dev/null | wc -l | tr -d ' ') || echo "0"
}

count_test_files() {
    local worktree_path="$1"
    # Count new test files
    (cd "$worktree_path" && git status --porcelain 2>/dev/null | grep -cE '_test\.go|\.spec\.ts|\.test\.ts|Test\.java' || echo "0")
}

save_result() {
    local task_id="$1" system="$2" duration="$3" tokens="$4" files="$5" tests="$6" compiles="$7" llm_scores="$8"

    mkdir -p "$RESULTS_DIR"

    local result
    result=$(jq -n \
        --arg run_id "$RUN_ID" \
        --arg timestamp "$TIMESTAMP" \
        --arg system "$system" \
        --arg model "$MODEL" \
        --arg task_id "$task_id" \
        --arg task_name "$(get_benchmark_field "$task_id" "name")" \
        --argjson duration "$duration" \
        --argjson tokens "$tokens" \
        --argjson files_created "$files" \
        --argjson tests_created "$tests" \
        --arg compilation "$compiles" \
        --arg llm_scores "$llm_scores" \
        '{
            run_id: $run_id,
            timestamp: $timestamp,
            system: $system,
            model: $model,
            task_id: $task_id,
            task_name: $task_name,
            duration_seconds: $duration,
            tokens_used: $tokens,
            files_created: $files_created,
            tests_created: $tests_created,
            compilation_success: ($compilation == "true"),
            llm_scores: $llm_scores
        }')

    echo "$result" >> "$RESULTS_FILE"
    log_ok "Result saved to $RESULTS_FILE"
}

generate_report() {
    local system="$1"
    local report_file="$RESULTS_DIR/benchmark-report-$RUN_ID.md"

    log "Generating benchmark report..."

    local date_str
    date_str=$(date +"%Y-%m-%d %H:%M")

    cat > "$report_file" << EOF
## Benchmark Report -- $date_str
### System: $system
### Model: $MODEL
### Run ID: $RUN_ID

| Task | Time | Tokens | Files | Tests | Compiles | LLM Scores |
|------|------|--------|-------|-------|----------|------------|
EOF

    # Read results for this run
    local total_time=0
    local total_tokens=0

    while IFS= read -r line; do
        local rid
        rid=$(echo "$line" | jq -r '.run_id')
        if [[ "$rid" != "$RUN_ID" ]]; then
            continue
        fi

        local task_id duration tokens files tests compiles llm_scores
        task_id=$(echo "$line" | jq -r '.task_id')
        duration=$(echo "$line" | jq -r '.duration_seconds')
        tokens=$(echo "$line" | jq -r '.tokens_used')
        files=$(echo "$line" | jq -r '.files_created')
        tests=$(echo "$line" | jq -r '.tests_created')
        compiles=$(echo "$line" | jq -r '.compilation_success')
        llm_scores=$(echo "$line" | jq -r '.llm_scores')

        local compile_icon="--"
        if [[ "$compiles" == "true" ]]; then compile_icon="pass"; fi
        if [[ "$compiles" == "false" ]]; then compile_icon="FAIL"; fi

        echo "| $task_id | ${duration}s | $tokens | $files | $tests | $compile_icon | $llm_scores |" >> "$report_file"

        total_time=$((total_time + duration))
        total_tokens=$((total_tokens + tokens))
    done < "$RESULTS_FILE"

    cat >> "$report_file" << EOF

### Total Time: ${total_time}s
### Total Tokens: $total_tokens
EOF

    log_ok "Report saved to $report_file"
    echo "$report_file"
}

# --- Main ---

main() {
    parse_args "$@"
    check_dependencies
    read_config

    log "========================================="
    log "Cognitive OS Benchmark Runner"
    log "========================================="
    log "System:     $SYSTEM"
    log "Model:      $MODEL"
    log "Max turns:  $MAX_TURNS"
    log "Run ID:     $RUN_ID"
    log "========================================="

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN - showing tasks without executing"
    fi

    local task_ids
    task_ids=$(get_benchmark_ids)

    local task_count=0
    while IFS= read -r task_id; do
        task_count=$((task_count + 1))
        local task_name
        task_name=$(get_benchmark_field "$task_id" "name")

        echo ""
        log "${CYAN}[$task_count] Task: $task_name ($task_id)${NC}"
        log "-------------------------------------------"

        if [[ "$DRY_RUN" == "true" ]]; then
            local prompt
            prompt=$(build_prompt "$task_id" "$SYSTEM")
            log "  Prompt: $prompt"
            continue
        fi

        # 1. Create isolated worktree
        log "Creating isolated worktree..."
        local worktree_path
        worktree_path=$(create_worktree "$task_id")
        log "  Worktree: $worktree_path"

        # 2. Run setup if defined
        run_setup "$worktree_path" "$task_id"

        # 3. Build prompt
        local prompt
        prompt=$(build_prompt "$task_id" "$SYSTEM")

        # 4. Run Claude headless
        local result
        result=$(run_claude_headless "$worktree_path" "$prompt" "$task_id")
        local output_file duration
        output_file=$(echo "$result" | cut -d'|' -f1)
        duration=$(echo "$result" | cut -d'|' -f2)

        # 5. Extract metrics
        local tokens files tests compiles llm_scores
        tokens=$(extract_tokens "$output_file")
        files=$(count_new_files "$worktree_path")
        tests=$(count_test_files "$worktree_path")
        compiles=$(check_compilation "$worktree_path" "$task_id")
        llm_scores=$(run_llm_eval "$worktree_path" "$task_id")

        # 6. Save results
        save_result "$task_id" "$SYSTEM" "$duration" "$tokens" "$files" "$tests" "$compiles" "$llm_scores"

        # 7. Cleanup
        cleanup_worktree "$worktree_path" "$task_id"

        # Cleanup output file
        rm -f "$output_file"

    done <<< "$task_ids"

    if [[ "$DRY_RUN" != "true" ]]; then
        # Generate report
        echo ""
        log "========================================="
        local report_path
        report_path=$(generate_report "$SYSTEM")
        log "========================================="
        log_ok "Benchmark complete! Results:"
        log "  JSONL: $RESULTS_FILE"
        log "  Report: $report_path"
        log ""
        log "To compare with BMAD, run:"
        log "  bash $SCRIPT_DIR/run-benchmark.sh --system bmad"
    fi
}

main "$@"
