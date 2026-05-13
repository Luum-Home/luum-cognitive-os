#!/usr/bin/env bash
# SCOPE: os-only
# SessionStart hook: Stack-Aware Skill Recommendation
#
# Detects project stack (package.json, go.mod, pyproject.toml, Cargo.toml,
# Dockerfile, etc.) and writes skill recommendations to:
#   .cognitive-os/state/stack-recommendations.json
#
# See: docs/02-Decisions/adrs/ADR-286-stack-aware-skill-recommendation-session-start.md
#
# Runs asynchronously — I/O bound, does not block session start.
# Advisory only — exits 0 unconditionally.
# Killswitch: COS_DISABLE_STACK_RECOMMEND=1

set -uo pipefail

# Killswitch
if [ "${COS_DISABLE_STACK_RECOMMEND:-}" = "1" ]; then
  exit 0
fi

# ADR-028 §584: respect killswitch flag for non-critical hooks.
KILLSWITCH_LIB="$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
if [ -f "$KILLSWITCH_LIB" ]; then
  # shellcheck disable=SC1090
  source "$KILLSWITCH_LIB" 2>/dev/null || true
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

cd "$PROJECT_DIR" && python3 -c "
import sys, json, os, tempfile
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, '.')
try:
    from lib.stack_skill_recommender import StackSkillRecommender
except ImportError as e:
    print(f'[stack-recommend] import error: {e}', file=sys.stderr)
    sys.exit(0)

project_path = os.environ.get(
    'COGNITIVE_OS_PROJECT_DIR',
    os.environ.get('CODEX_PROJECT_DIR',
    os.environ.get('CLAUDE_PROJECT_DIR', '.'))
)

try:
    recommender = StackSkillRecommender()
    recs = recommender.recommend(project_path)
    output = {
        'generated_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'project_path': str(Path(project_path).resolve()),
        'recommendations': [
            {
                'skill_name': r.skill_name,
                'reason': r.reason,
                'source': r.source,
                'install_command': r.install_command,
                'priority': r.priority,
            }
            for r in recs
        ],
    }
    state_dir = Path(project_path) / '.cognitive-os' / 'state'
    state_dir.mkdir(parents=True, exist_ok=True)
    out_path = state_dir / 'stack-recommendations.json'
    tmp_path = out_path.with_suffix('.json.tmp')
    tmp_path.write_text(json.dumps(output, indent=2), encoding='utf-8')
    tmp_path.replace(out_path)
except Exception as exc:
    print(f'[stack-recommend] error: {exc}', file=sys.stderr)
    sys.exit(0)
" 2>&1 || true

exit 0
