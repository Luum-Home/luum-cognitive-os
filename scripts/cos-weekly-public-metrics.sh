#!/usr/bin/env bash
# SCOPE: os-only
# cos-weekly-public-metrics.sh — local replacement for weekly-public-metrics.yml.
#
# Per ADR-131. Updates the dogfood + aspirational metrics and (optionally) the
# README badges. Does not commit or push; review and commit manually.

set -uo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$HOME/Projects/luum/luum-agent-os")"
cd "$REPO_ROOT"

echo "[cos-weekly-public-metrics] $(date -u +%Y-%m-%dT%H:%M:%SZ) — start"

if [ -f scripts/dogfood_score.py ]; then
  python3 scripts/dogfood_score.py --json > public-metrics-dogfood.json
  echo "  ✓ dogfood_score → public-metrics-dogfood.json"
else
  echo "  ⊘ dogfood_score.py not present"
fi

if [ -f scripts/aspirational_audit.py ]; then
  python3 scripts/aspirational_audit.py --json > public-metrics-aspirational.json
  echo "  ✓ aspirational_audit → public-metrics-aspirational.json"
else
  echo "  ⊘ aspirational_audit.py not present"
fi

if [ -f scripts/update_readme_badges.py ]; then
  python3 scripts/update_readme_badges.py
  echo "  ✓ README badges updated"
else
  echo "  ⊘ update_readme_badges.py not present"
fi

echo "[cos-weekly-public-metrics] done. Review and commit manually if README/badges changed."
exit 0
