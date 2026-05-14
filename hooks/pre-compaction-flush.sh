#!/usr/bin/env bash
# SCOPE: both
# PreCompact hook: Reminds the agent to save durable memories to Engram
# before context compaction destroys working memory.
#
# Inspired by OpenClaw's pre-compaction flush pattern.
# Registered as PreCompact hook in settings.local.json.

# This hook runs BEFORE context compaction occurs.
# It outputs a system message that the agent will see and act on.

# ---------------------------------------------------------------------------
# Step 1: Run anchored summarizer to persist structured context
# ---------------------------------------------------------------------------
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-}}}"
SESSION_DIR="${COGNITIVE_OS_SESSION_DIR:-${CODEX_SESSION_DIR:-${CLAUDE_SESSION_DIR:-}}}"
if [ -z "$SESSION_DIR" ]; then
  if [ -n "$SESSION_ID" ]; then
    SESSION_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"
  else
    SESSION_DIR="$PROJECT_DIR/.cognitive-os/sessions/current"
  fi
fi

python3 -c "
import sys; sys.path.insert(0, '$PROJECT_DIR')
from lib.anchored_summarizer import AnchoredSummarizer
AnchoredSummarizer.auto_save(session_dir='$SESSION_DIR')
" 2>/dev/null || true

cat <<'FLUSH_MSG'
Session nearing compaction. Save any important decisions, discoveries, or bug fixes to Engram NOW.

Before compaction completes, you MUST:
1. Call mem_session_summary with a structured summary of this session
2. Call mem_save for any unsaved decisions, bug fixes, or discoveries
3. Note any in-progress tasks in the summary for the next session to resume

This is NOT optional. Without this, the next session starts blind.
FLUSH_MSG
