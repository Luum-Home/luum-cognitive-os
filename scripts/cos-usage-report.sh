#!/usr/bin/env bash
# cos-usage-report.sh — Heatmap aggregator for COS runtime telemetry.
#
# Reads the four JSONL files written by lib/telemetry.py and produces a usage
# report: top skills, top hooks, zero-invocation skills, agent cost per model,
# rate-limit histogram, and (optionally) an efficiency metric comparing token
# savings from skills against token cost of hooks.
#
# Usage:
#   bash scripts/cos-usage-report.sh [--days N] [--json] [--efficiency] [--help]
#
# Flags:
#   --days N       Aggregate the last N days (default: 7)
#   --json         Emit machine-parseable JSON (implies no color)
#   --efficiency   Show net tokens saved vs spent (see calculation below)
#   --help         Show this help and exit
#
# Reads:
#   .cognitive-os/metrics/skill-usage.jsonl
#   .cognitive-os/metrics/hook-usage.jsonl
#   .cognitive-os/metrics/agent-launches.jsonl
#   .cognitive-os/metrics/rate-limit-events.jsonl

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"

DAYS=7
MODE="pretty"
SHOW_EFFICIENCY=0

usage() {
  cat <<EOF
cos usage — show runtime telemetry heatmaps

Usage:
  bash scripts/cos-usage-report.sh [flags]

Flags:
  --days N       Aggregate last N days (default: 7)
  --json         Machine-parseable JSON output
  --efficiency   Include net tokens-saved-vs-spent metric
  --help         Show this help and exit

Reports:
  - Top 10 most-invoked skills
  - Top 10 most-fired hooks
  - Skills exposed but never invoked (archive candidates)
  - Agent cost per model
  - Rate-limit event histogram

Exit code: 0 always.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --days)
      shift
      DAYS="${1:-7}"
      ;;
    --json)
      MODE="json"
      ;;
    --efficiency)
      SHOW_EFFICIENCY=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown flag: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required for cos-usage-report" >&2
  exit 1
fi

PROJECT_ROOT="$PROJECT_ROOT" \
DAYS="$DAYS" \
MODE="$MODE" \
SHOW_EFFICIENCY="$SHOW_EFFICIENCY" \
python3 <<'PYEOF'
import json, os, sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

root = Path(os.environ["PROJECT_ROOT"])
days = int(os.environ.get("DAYS", "7"))
mode = os.environ.get("MODE", "pretty")
show_eff = os.environ.get("SHOW_EFFICIENCY", "0") == "1"

sys.path.insert(0, str(root))
try:
    from lib.telemetry import (
        iter_records,
        SKILL_USAGE_FILE, HOOK_USAGE_FILE,
        AGENT_LAUNCHES_FILE, RATE_LIMIT_FILE,
    )
except Exception as exc:
    print(f"error: cannot import lib.telemetry ({exc})", file=sys.stderr)
    sys.exit(1)

cutoff = datetime.now(timezone.utc) - timedelta(days=days)


def _in_window(rec):
    ts = rec.get("timestamp")
    if not ts:
        return False
    try:
        # Accept both "...Z" and "+00:00" suffixes.
        norm = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(norm) >= cutoff
    except Exception:
        return False


# ── Load all four streams, filtered by window ────────────────────────────
skill_rec  = [r for r in iter_records(SKILL_USAGE_FILE)    if _in_window(r)]
hook_rec   = [r for r in iter_records(HOOK_USAGE_FILE)     if _in_window(r)]
agent_rec  = [r for r in iter_records(AGENT_LAUNCHES_FILE) if _in_window(r)]
rate_rec   = [r for r in iter_records(RATE_LIMIT_FILE)     if _in_window(r)]

# ── Top skills ────────────────────────────────────────────────────────────
skill_counter = Counter(r.get("name", "?") for r in skill_rec)
top_skills = skill_counter.most_common(10)

# ── Top hooks ─────────────────────────────────────────────────────────────
hook_counter = Counter(r.get("name", "?") for r in hook_rec)
top_hooks = hook_counter.most_common(10)

# ── Zero-invocation skills (candidates for archive) ───────────────────────
skills_dir = root / ".claude" / "skills"
exposed = set()
if skills_dir.is_dir():
    for entry in skills_dir.iterdir():
        if entry.is_dir() and not entry.name.startswith("."):
            exposed.add(entry.name)
invoked = set(skill_counter.keys())
ghost_skills = sorted(exposed - invoked)

# ── Agent cost per model ──────────────────────────────────────────────────
model_cost = defaultdict(lambda: {"launches": 0, "cost_usd": 0.0, "tokens": 0})
for r in agent_rec:
    m = r.get("model", "unknown")
    bucket = model_cost[m]
    bucket["launches"] += 1
    bucket["cost_usd"] += float(r.get("cost_estimated", 0) or 0)
    bucket["tokens"]  += int(r.get("tokens_in", 0) or 0) + int(r.get("tokens_out", 0) or 0)

# ── Rate-limit histogram ──────────────────────────────────────────────────
rate_hist = Counter(r.get("type", "?") for r in rate_rec)

# ── Efficiency metric ─────────────────────────────────────────────────────
# Heuristic (see sprint-5-observability.md for derivation):
#   - Each compose-prompt invocation saves ~1150 tokens (inline canon ~1200
#     vs template ref ~50). Other skills get a generic 200-token saving.
#   - Each hook firing costs ~50 tokens (heuristic: duration × token-rate).
PER_SKILL_SAVINGS = {"compose-prompt": 1150}
GENERIC_SKILL_SAVINGS = 200
PER_HOOK_COST = 50

tokens_saved = 0
for name, count in skill_counter.items():
    per = PER_SKILL_SAVINGS.get(name, GENERIC_SKILL_SAVINGS)
    tokens_saved += per * count

tokens_spent = 0
for name, count in hook_counter.items():
    tokens_spent += PER_HOOK_COST * count

net_tokens = tokens_saved - tokens_spent

out = {
    "window_days": days,
    "top_skills": [{"name": n, "count": c} for n, c in top_skills],
    "top_hooks":  [{"name": n, "count": c} for n, c in top_hooks],
    "ghost_skills_count": len(ghost_skills),
    "ghost_skills": ghost_skills,
    "agent_cost_per_model": {k: dict(v) for k, v in model_cost.items()},
    "rate_limit_histogram": dict(rate_hist),
    "efficiency": {
        "tokens_saved": tokens_saved,
        "tokens_spent": tokens_spent,
        "net_tokens":   net_tokens,
    },
    "totals": {
        "skill_invocations": sum(skill_counter.values()),
        "hook_firings":      sum(hook_counter.values()),
        "agent_launches":    len(agent_rec),
        "rate_limit_events": len(rate_rec),
    },
}

if mode == "json":
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    sys.exit(0)

# ── Pretty output ─────────────────────────────────────────────────────────
def hdr(title):
    print()
    print(title)
    print("─" * len(title))

print(f"COS Usage Report — last {days} day(s)")
print(f"  skills: {out['totals']['skill_invocations']} invocations"
      f"  |  hooks: {out['totals']['hook_firings']} firings"
      f"  |  agents: {out['totals']['agent_launches']}"
      f"  |  rate-limit: {out['totals']['rate_limit_events']}")

hdr("Top 10 skills")
if top_skills:
    for name, count in top_skills:
        print(f"  {count:>6}  {name}")
else:
    print("  (none)")

hdr("Top 10 hooks")
if top_hooks:
    for name, count in top_hooks:
        print(f"  {count:>6}  {name}")
else:
    print("  (none)")

hdr(f"Ghost skills ({len(ghost_skills)} / {len(exposed)} exposed, 0 invocations in window)")
if ghost_skills:
    for name in ghost_skills[:20]:
        print(f"  · {name}")
    if len(ghost_skills) > 20:
        print(f"  … ({len(ghost_skills) - 20} more)")
else:
    print("  (none)")

hdr("Agent cost per model")
if model_cost:
    print(f"  {'model':<16}{'launches':>10}{'tokens':>12}{'cost (USD)':>14}")
    for m, b in sorted(model_cost.items(), key=lambda kv: -kv[1]["cost_usd"]):
        print(f"  {m:<16}{b['launches']:>10}{b['tokens']:>12}{b['cost_usd']:>14.4f}")
else:
    print("  (no agent launches recorded)")

hdr("Rate-limit histogram")
if rate_hist:
    for t, c in rate_hist.most_common():
        print(f"  {c:>6}  {t}")
else:
    print("  (no rate-limit events)")

if show_eff:
    hdr("Efficiency (tokens)")
    print(f"  saved by skills : {tokens_saved:>10}")
    print(f"  spent by hooks  : {tokens_spent:>10}")
    verdict = "net gain" if net_tokens > 0 else ("net loss" if net_tokens < 0 else "break-even")
    print(f"  net             : {net_tokens:>10}  ({verdict})")

print()
PYEOF
exit 0
