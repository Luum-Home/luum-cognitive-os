#!/usr/bin/env bash
# SCOPE: both
# Advisory installer checker for ADR-215 scanner dependencies.
set -euo pipefail
mode="${1:---check}"
missing=0
for tool in gitleaks trufflehog; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "$tool: installed"
  else
    echo "$tool: missing"
    missing=1
  fi
done
case "$mode" in
  --check) exit "$missing" ;;
  --dry-run) echo "Install with your package manager: gitleaks trufflehog"; exit 0 ;;
  *) echo "Usage: $0 [--check|--dry-run]" >&2; exit 2 ;;
esac
