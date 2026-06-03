#!/usr/bin/env bash
# SCOPE: both
# PreToolUse hook on Agent — injects phase context from cognitive-os.yaml into agent prompts.
# Universal hook: reads project type and phase from config, does NOT hardcode any
# project-specific architecture standards or constitutional gates.
#
# Transport: emits hookSpecificOutput.additionalContext on stdout (Claude Code native).
# Falls back to stderr when invoked outside Claude Code (no valid stdin JSON).

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_lib/portable.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# ── Strategy B: TTL cache (60s) ──────────────────────────────────────────────
# inject-phase-context was hitting p95 ~3674ms (budget: 2000ms) because it ran
# multiple synchronous Python subprocesses (engram search + ref_key expansion)
# on every PreToolUse fire. Cache the full context output for 60 seconds, but
# key it on content fingerprints rather than coarse mtimes so tests and rapid
# profile edits avoid stale phase/preamble output.
# A cache hit exits in <10ms, well within the 2000ms budget.
_PHASE_CACHE_DIR="${PROJECT_DIR}/.cognitive-os/cache/inject-phase-context"
_PHASE_CACHE_TTL=60  # seconds

_file_fingerprint() {
  local path="${1:-}"
  if [[ -n "$path" && -f "$path" ]]; then
    shasum -a 256 "$path" 2>/dev/null | cut -d' ' -f1 \
      || md5 "$path" 2>/dev/null | awk '{print $NF}' \
      || portable_stat_mtime "$path" 2>/dev/null \
      || echo "0"
  else
    echo "0"
  fi
}

_cache_key_for_context() {
  local yaml_fp preamble_fp gotchas_fp session_id tool_name prompt_fp cache_basis
  yaml_fp=$(_file_fingerprint "${COGNITIVE_OS_YAML:-/dev/null}")
  preamble_fp=$(_file_fingerprint "${PROJECT_DIR}/templates/agent-preamble.md")
  gotchas_fp=$(_file_fingerprint "${PROJECT_DIR}/templates/project-gotchas.md")
  session_id="${COGNITIVE_OS_SESSION_ID:-default}"
  tool_name="${1:-any}"
  prompt_fp="${2:-0}"
  cache_basis="${yaml_fp}:${preamble_fp}:${gotchas_fp}:${session_id}:${tool_name}:${prompt_fp}"
  printf '%s' "$cache_basis" \
    | shasum -a 256 2>/dev/null | cut -d' ' -f1 \
    || printf '%s' "$cache_basis" | md5 2>/dev/null \
    || echo "nocache"
}

_cache_hit() {
  # Returns 0 (hit) and prints cached content if still within TTL, else 1 (miss).
  local key="$1"
  local cache_file="$_PHASE_CACHE_DIR/${key}.ctx"
  local ts_file="$_PHASE_CACHE_DIR/${key}.ts"
  [[ -f "$cache_file" && -f "$ts_file" ]] || return 1
  local stored_ts now elapsed
  stored_ts=$(cat "$ts_file" 2>/dev/null || echo 0)
  now=$(date +%s 2>/dev/null || echo 0)
  elapsed=$(( now - stored_ts ))
  [[ "$elapsed" -le "$_PHASE_CACHE_TTL" ]] || return 1
  cat "$cache_file"
  return 0
}

_cache_store() {
  local key="$1"
  local content="$2"
  mkdir -p "$_PHASE_CACHE_DIR" 2>/dev/null || return 0
  printf '%s' "$content" > "$_PHASE_CACHE_DIR/${key}.ctx" 2>/dev/null || true
  date +%s > "$_PHASE_CACHE_DIR/${key}.ts" 2>/dev/null || true
}

COGNITIVE_OS_DIR="$PROJECT_DIR/.cognitive-os"
COGNITIVE_OS_YAML="$COGNITIVE_OS_DIR/cognitive-os.yaml"
if [[ ! -f "$COGNITIVE_OS_YAML" && -f "$PROJECT_DIR/cognitive-os.yaml" ]]; then
  COGNITIVE_OS_YAML="$PROJECT_DIR/cognitive-os.yaml"
fi

# additionalContext hard limit per Claude Code spec
MAX_CONTEXT_CHARS=10000

# Read input from stdin
INPUT=$(cat)

# Detect "real" Claude Code invocation: stdin is a JSON object with tool_name.
# When invoked manually (testing without Claude Code), tool_name will be empty
# and we'll emit to stderr for diagnostic visibility.
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || echo "")
AGENT_PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // empty' 2>/dev/null || echo "")
AGENT_PROMPT_FP=$(printf '%s' "$AGENT_PROMPT" | shasum -a 256 2>/dev/null | cut -d' ' -f1 || echo "0")
HAS_VALID_INPUT=0
if [[ -n "$TOOL_NAME" ]]; then
  HAS_VALID_INPUT=1
fi

# Only process Agent tool calls
if [[ -n "$TOOL_NAME" ]] && [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then
  exit 0
fi

# ── Cache check (Strategy B) ─────────────────────────────────────────────────
# If a valid cached context exists, emit it and exit immediately (<10ms path).
_CACHE_KEY=$(_cache_key_for_context "$TOOL_NAME" "$AGENT_PROMPT_FP")
if [[ "$HAS_VALID_INPUT" -eq 1 ]]; then
  _CACHED_OUTPUT=$(_cache_hit "$_CACHE_KEY" 2>/dev/null || true)
  if [[ -n "$_CACHED_OUTPUT" ]]; then
    printf '%s' "$_CACHED_OUTPUT"
    exit 0
  fi
fi

# --- Phase Context ---
PHASE="reconstruction"
if [[ -f "$COGNITIVE_OS_YAML" ]]; then
  PHASE=$(grep -E '^\s+phase:' "$COGNITIVE_OS_YAML" | head -1 | sed 's/.*phase:\s*//' | sed 's/\s*#.*//' | tr -d '[:space:]' || echo "reconstruction")
fi

# Build phase-specific rules (universal, not framework-specific)
case "$PHASE" in
  reconstruction)
    RULES="- Rewrite over patching; replace broken patterns.
- Follow project architecture standards strictly.
- Complete the fix in-session instead of documenting it as \"future work\".
- Break backwards compatibility if needed.
- Architecture violations are BLOCKERS, not warnings.
- If something doesn't compile after rewriting, FIX IT in this session."
    ;;
  stabilization)
    RULES="- Follow project architecture standards strictly.
- Rewrite non-compliant code instead of patching around it.
- Maintain backwards compatibility where possible.
- Architecture violations should be fixed or tracked as tasks."
    ;;
  production)
    RULES="- Preserve existing functionality.
- Use feature flags for all changes.
- Document risky changes as proposals, not implementations.
- Maintain backwards compatibility.
- Architecture violations are warnings — log them without blocking."
    ;;
  maintenance)
    RULES="- Bug fixes and security patches ONLY.
- Minimal changes, maximum stability.
- Document improvements as future work.
- Keep structure stable; limit work to the bug/security fix."
    ;;
  *)
    RULES="- Unknown phase ($PHASE). Default to conservative behavior."
    ;;
esac

# --- Project Type ---
PROJECT_TYPE="webapp"
PROJECT_NAME="my-project"
if [[ -f "$COGNITIVE_OS_YAML" ]]; then
  PROJECT_TYPE=$(grep -E '^\s+type:' "$COGNITIVE_OS_YAML" | head -1 | sed 's/.*type:\s*//' | sed 's/\s*#.*//' | tr -d '[:space:]' || echo "webapp")
  PROJECT_NAME=$(grep -E '^\s+name:' "$COGNITIVE_OS_YAML" | head -1 | sed 's/.*name:\s*//' | sed 's/\s*#.*//' | tr -d '[:space:]' || echo "my-project")
fi

# --- Squad Assignment (if applicable) ---
SQUAD_INFO=""
SQUADS_DIR="$COGNITIVE_OS_DIR/squads"
if [[ -d "$SQUADS_DIR" ]]; then
  ACTIVE_SQUAD=$(grep -E '^\s+active_squad:' "$COGNITIVE_OS_YAML" 2>/dev/null | head -1 | sed 's/.*active_squad:\s*//' | sed 's/\s*#.*//' | tr -d '[:space:]' || echo "")
  if [[ -n "$ACTIVE_SQUAD" && -f "$SQUADS_DIR/$ACTIVE_SQUAD.md" ]]; then
    SQUAD_INFO="ACTIVE SQUAD: $ACTIVE_SQUAD"
  fi
fi

# --- Load project-specific context from .claude/ if it exists ---
# Architecture standards and constitutional gates are project-specific
# and should be defined in {project}/.claude/rules/ not here.
PROJECT_CONTEXT=""
PROJECT_RULES_DIR="$PROJECT_DIR/.claude/rules"
if [[ -d "$PROJECT_RULES_DIR" ]]; then
  # Check for architecture rules
  if [[ -f "$PROJECT_RULES_DIR/architecture.md" ]]; then
    PROJECT_CONTEXT="${PROJECT_CONTEXT}\nSee .claude/rules/architecture.md for project architecture standards."
  fi
  # Check for constitutional gates
  if [[ -f "$PROJECT_RULES_DIR/constitutional-gates.md" ]]; then
    PROJECT_CONTEXT="${PROJECT_CONTEXT}\nSee .claude/rules/constitutional-gates.md for project constitutional gates."
  fi
fi

# --- Keyword-based gotcha injection ---
GOTCHAS=""

if [[ -n "$AGENT_PROMPT" ]]; then
  # lib/ symlink trap
  if echo "$AGENT_PROMPT" | grep -qiE 'lib/|packages/.*lib|duplicate.*lib|dedup'; then
    GOTCHAS="${GOTCHAS}
NOTE: SOME lib/*.py (~22%, 68 of 314) are SYMLINKS to packages/*/lib/*.py. Most are real files. Verify per file with: ls -la lib/<file>.py. If <file>.py exists in BOTH lib/ AND packages/*/lib/, run scripts/cos-lib-symlink-invariant-audit.py to detect silent drift (3 confirmed drifts as of 2026-05-11 — see ADR-267 §Layer 1 Hook #7). Check symlink direction before replacing files in packages/*/lib/."
  fi

  # settings.json trap
  if echo "$AGENT_PROMPT" | grep -qiE 'settings\.json|wire.*hook|add.*hook.*settings'; then
    GOTCHAS="${GOTCHAS}
NOTE: .claude/settings.json is GENERATED by scripts/apply-efficiency-profile.sh. Update the script, then run: bash scripts/apply-efficiency-profile.sh standard"
  fi

  # Hook creation trap
  if echo "$AGENT_PROMPT" | grep -qiE 'new hook|create hook|hooks/.*\.sh'; then
    GOTCHAS="${GOTCHAS}
NOTE: New hooks are registered in scripts/apply-efficiency-profile.sh under the appropriate profile (lean/standard/full) so they can fire."
  fi

  # Workflow trap
  if echo "$AGENT_PROMPT" | grep -qiE 'workflow|pipeline.*yaml|\.cognitive-os/workflows'; then
    GOTCHAS="${GOTCHAS}
NOTE: Workflow YAMLs in .cognitive-os/workflows/ follow the schema in docs/08-References/root/adw-patterns.md. Steps have type: agent|script|gate."
  fi

  # Plans directory trap
  if echo "$AGENT_PROMPT" | grep -qiE 'plans/|plan.*directory'; then
    GOTCHAS="${GOTCHAS}
WARNING: plans/ at root has structure but no content. Active plans are in .cognitive-os/plans/. Both exist intentionally."
  fi
fi

# --- Engram discovery injection (best-effort, 3s timeout) ---
ENGRAM_WARNINGS=""
if [[ -n "$AGENT_PROMPT" ]] && command -v python3 >/dev/null 2>&1; then
  # Extract key nouns from the prompt for Engram search
  SEARCH_TERMS=$(echo "$AGENT_PROMPT" | grep -oE '\b(lib|hook|settings|workflow|pipeline|packages|symlink|duplicate|profile|efficiency)\b' 2>/dev/null | sort -u | head -3 | tr '\n' ' ' || true)
  if [[ -n "$SEARCH_TERMS" ]]; then
    ENGRAM_WARNINGS=$(timeout 3 python3 -c "
import sys, json, subprocess
try:
    # Search engram for discovery-type memories matching keywords
    for term in '${SEARCH_TERMS}'.split():
        result = subprocess.run(
            ['python3', '-c', '''
import sys
sys.path.insert(0, \"$PROJECT_DIR\")
try:
    from lib.engram_client import search_observations
    results = search_observations(term.strip(), limit=2)
    for r in results:
        t = r.get(\"type\", \"\")
        if t in (\"discovery\", \"bugfix\", \"feedback\"):
            title = r.get(\"title\", \"\")[:80]
            print(f\"ENGRAM [{t}]: {title}\")
except Exception:
    pass
'''.replace('term.strip()', repr(term.strip()))],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            print(result.stdout.strip())
except Exception:
    pass
" 2>/dev/null || true)
  fi
fi

# --- Guard: skip preamble injection if already present in prompt ---
# This prevents double-injection if multiple hooks fire or if the orchestrator
# manually included the preamble in the task description.
ALREADY_HAS_PREAMBLE=0
if echo "$AGENT_PROMPT" | grep -q "TRUST_REPORT: SCORE="; then
  ALREADY_HAS_PREAMBLE=1
fi

# --- Compose context buffer (single string) ---
# Build everything into CONTEXT_BUF, then emit via the chosen transport.
CONTEXT_BUF=""

# Inject agent-preamble.md (the core quality contract)
PREAMBLE_FILE="$PROJECT_DIR/templates/agent-preamble.md"
if [[ "$ALREADY_HAS_PREAMBLE" -eq 0 ]] && [[ -f "$PREAMBLE_FILE" ]]; then
  PREAMBLE_CONTENT=$(cat "$PREAMBLE_FILE")
  # Interpolate {{phase}} placeholder
  PREAMBLE_CONTENT="${PREAMBLE_CONTENT//\{\{phase\}\}/$PHASE}"
  CONTEXT_BUF+="--- AGENT PREAMBLE (REQUIRED — read before starting) ---
${PREAMBLE_CONTENT}
--- END AGENT PREAMBLE ---

"
fi

CONTEXT_BUF+="
PROJECT: ${PROJECT_NAME} (${PROJECT_TYPE})
PHASE: ${PHASE}

PHASE RULES:
${RULES}

CONSTITUTIONAL GATES:
- Project-specific gates are loaded from the active harness rules when present.
- If no project gates are present, enforce the universal safety baseline: protect secrets, preserve data integrity, verify claims, and avoid irreversible actions without explicit approval."

if [[ -n "$GOTCHAS" ]]; then
  CONTEXT_BUF+="

KNOWN TRAPS (auto-detected from your task keywords):
${GOTCHAS}"
fi

if [[ -n "$ENGRAM_WARNINGS" ]]; then
  CONTEXT_BUF+="

RELEVANT DISCOVERIES (from project memory):
${ENGRAM_WARNINGS}"
fi

if [[ -n "$PROJECT_CONTEXT" ]]; then
  # PROJECT_CONTEXT may contain literal \n sequences — interpret them
  CONTEXT_BUF+="

PROJECT CONTEXT:$(printf '%b' "$PROJECT_CONTEXT")"
fi

if [[ -n "$SQUAD_INFO" ]]; then
  CONTEXT_BUF+="

${SQUAD_INFO}"
fi

# Inject gotchas file if working on COS internals — but only ONCE per session.
# Subsequent agents get a 1-line pointer instead of the full 3KB file.
GOTCHAS_FILE="$PROJECT_DIR/templates/project-gotchas.md"
if [[ -n "$AGENT_PROMPT" ]] && [[ -f "$GOTCHAS_FILE" ]]; then
  if echo "$AGENT_PROMPT" | grep -qiE 'lib/|hooks/|packages/|\.cognitive-os/|settings\.json|cognitive-os\.yaml'; then
    # Per-session dedup marker
    _SID="${COGNITIVE_OS_SESSION_ID:-default}"
    _GOTCHAS_MARKER="$PROJECT_DIR/.cognitive-os/sessions/$_SID/.gotchas-injected"
    if [[ -f "$_GOTCHAS_MARKER" ]]; then
      # Already seen this session — just remind it exists
      CONTEXT_BUF+="

Gotchas reference: templates/project-gotchas.md (already loaded this session)"
    else
      GOTCHAS_CONTENT=$(cat "$GOTCHAS_FILE")
      CONTEXT_BUF+="

--- PROJECT GOTCHAS (read before modifying COS internals) ---
${GOTCHAS_CONTENT}"
      mkdir -p "$(dirname "$_GOTCHAS_MARKER")" 2>/dev/null && touch "$_GOTCHAS_MARKER" 2>/dev/null || true
    fi
  fi
fi

CONTEXT_BUF+="
"

# --- Expand [`ref-key`] markers inline (ADR-027 Phase 2 / ADR-075 Stage 2) ---
# Any [`rule-name`] reference in the preamble or phase rules is replaced
# with the full content of rules/<rule-name>.md (max_depth=1, no recursion).
# Tier filtering: read expansion.tier_filter from cognitive-os.yaml.
# Default when key is absent: [0, 1] (Tier-0 + Tier-1; Tier-2 on-demand only).
_EXPANSION_TIER_FILTER=""
if [[ -f "$COGNITIVE_OS_YAML" ]] && command -v python3 >/dev/null 2>&1; then
  _EXPANSION_TIER_FILTER=$(python3 -c "
import sys
try:
    import yaml
    with open('${COGNITIVE_OS_YAML}') as f:
        cfg = yaml.safe_load(f) or {}
    tf = (cfg.get('expansion') or {}).get('tier_filter')
    if tf is None:
        print('0,1')
    else:
        print(','.join(str(t) for t in tf))
except Exception:
    print('0,1')
" 2>/dev/null || echo "0,1")
fi
# Normalise: empty → default
if [[ -z "$_EXPANSION_TIER_FILTER" ]]; then
  _EXPANSION_TIER_FILTER="0,1"
fi

if command -v python3 >/dev/null 2>&1; then
  _EXPANDED=$(printf '%s' "$CONTEXT_BUF" | python3 -c "
import sys
sys.path.insert(0, '${PROJECT_DIR}')
buf = sys.stdin.read()
try:
    from lib.ref_key_loader import expand
    raw_filter = '${_EXPANSION_TIER_FILTER}'.strip()
    # Parse comma-separated ints into a set; empty or 'all' means no filter.
    tier_filter = None
    if raw_filter and raw_filter != 'all':
        tier_filter = {int(t.strip()) for t in raw_filter.split(',') if t.strip().isdigit()}
    sys.stdout.write(expand(buf, max_depth=1, tier_filter=tier_filter))
except Exception:
    sys.stdout.write(buf)
" 2>/dev/null)
  # Only update CONTEXT_BUF if expansion succeeded (non-empty result)
  if [[ -n "$_EXPANDED" ]]; then
    CONTEXT_BUF="$_EXPANDED"
  fi
  unset _EXPANDED
fi
unset _EXPANSION_TIER_FILTER

# --- Truncate to 10K char limit ---
# additionalContext has a hard cap of 10,000 chars per Claude Code spec.
# Use Python for safe multi-byte truncation; fall back to bash arithmetic.
CONTEXT_LEN=${#CONTEXT_BUF}
if [[ "$CONTEXT_LEN" -gt "$MAX_CONTEXT_CHARS" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    # Use printf (no trailing newline) instead of <<< (adds trailing newline)
    # so the truncation math stays exact.
    CONTEXT_BUF=$(printf '%s' "$CONTEXT_BUF" | python3 -c "
import sys
buf = sys.stdin.read()
limit = ${MAX_CONTEXT_CHARS}
if len(buf) > limit:
    # Reserve room for truncation marker (no trailing newline)
    marker = '\n[truncated at 10K chars]'
    sys.stdout.write(buf[: limit - len(marker)] + marker)
else:
    sys.stdout.write(buf)
")
  else
    CONTEXT_BUF="${CONTEXT_BUF:0:9975}
[truncated at 10K chars]"
  fi
fi

# --- Emit via the selected transport ---
if [[ "$HAS_VALID_INPUT" -eq 1 ]]; then
  # Claude Code: emit hookSpecificOutput JSON on stdout
  if command -v python3 >/dev/null 2>&1; then
    # Use printf (no trailing newline) to preserve exact char count
    _JSON_OUTPUT=$(printf '%s' "$CONTEXT_BUF" | python3 -c "
import json, sys
ctx = sys.stdin.read()
out = {
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'additionalContext': ctx,
        'permissionDecision': 'allow',
    }
}
sys.stdout.write(json.dumps(out))
")
    # Store the serialized JSON in the TTL cache so subsequent calls skip all
    # the expensive Python subprocess work.
    _cache_store "$_CACHE_KEY" "$_JSON_OUTPUT" 2>/dev/null || true
    printf '%s' "$_JSON_OUTPUT"
  else
    # No python3 fallback — use jq
    _JSON_OUTPUT=$(jq -n \
      --arg ctx "$CONTEXT_BUF" \
      '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $ctx, permissionDecision: "allow"}}')
    _cache_store "$_CACHE_KEY" "$_JSON_OUTPUT" 2>/dev/null || true
    printf '%s' "$_JSON_OUTPUT"
  fi
else
  # No valid Claude Code input — degrade to stderr for manual/test invocations
  echo "$CONTEXT_BUF" >&2
fi

exit 0
