#!/usr/bin/env bash
# SCOPE: both
# Shared ADR-186 context-budget accountant for hooks that emit additionalContext.

context_budget_project_dir() {
  printf '%s' "${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
}

context_budget_session_id() {
  printf '%s' "${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}}"
}

context_budget_cos_root() {
  local hook_dir
  hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  cd "$hook_dir/.." && pwd
}

context_budget_filter_json() {
  local source="$1"
  local hook_json="$2"
  local layer="${3:-static}"
  local project_dir cos_root session_id
  project_dir="$(context_budget_project_dir)"
  cos_root="$(context_budget_cos_root)"
  session_id="$(context_budget_session_id)"
  python3 - "$project_dir" "$cos_root" "$source" "$session_id" "$layer" "$hook_json" <<'PY' 2>/dev/null || printf '%s' "$hook_json"
from __future__ import annotations
import sys
from pathlib import Path
project = Path(sys.argv[1]).resolve()
cos_root = Path(sys.argv[2]).resolve()
source = sys.argv[3]
session_id = sys.argv[4]
layer = sys.argv[5]
hook_json = sys.argv[6]
sys.path.insert(0, str(cos_root))
from lib.context_budget import filter_hook_output
sys.stdout.write(filter_hook_output(project, source=source, hook_json=hook_json, session_id=session_id, layer=layer))
PY
}

context_budget_record_text() {
  local source="$1"
  local text="$2"
  local layer="${3:-static}"
  local project_dir cos_root session_id
  project_dir="$(context_budget_project_dir)"
  cos_root="$(context_budget_cos_root)"
  session_id="$(context_budget_session_id)"
  python3 - "$project_dir" "$cos_root" "$source" "$session_id" "$layer" "$text" <<'PY' >/dev/null 2>&1 || true
from __future__ import annotations
import sys
from pathlib import Path
project = Path(sys.argv[1]).resolve()
cos_root = Path(sys.argv[2]).resolve()
source = sys.argv[3]
session_id = sys.argv[4]
layer = sys.argv[5]
text = sys.argv[6]
sys.path.insert(0, str(cos_root))
from lib.context_budget import record_usage
record_usage(project, source=source, layer=layer, text=text, session_id=session_id)
PY
}
