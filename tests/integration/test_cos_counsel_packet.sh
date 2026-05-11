#!/usr/bin/env bash
# Integration test for cos-counsel-packet (ADR-270 #3).
# Verifies a packet is produced and contains the cover README + ADR + sibling ADRs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

OUT="$TMPDIR/counsel-holaos.zip"

python3 scripts/cos-counsel-packet \
  --tool holaos \
  --adr ADR-270 \
  --output "$OUT" >/dev/null

if [ ! -f "$OUT" ]; then
  echo "FAIL: packet not produced" >&2
  exit 1
fi

LISTING="$(unzip -l "$OUT" 2>/dev/null)"

if ! printf '%s' "$LISTING" | grep -q "README.md"; then
  echo "FAIL: README.md missing from packet" >&2
  exit 1
fi

if ! printf '%s' "$LISTING" | grep -q "ADR/ADR-270"; then
  echo "FAIL: primary ADR missing from packet" >&2
  echo "$LISTING" >&2
  exit 1
fi

if ! printf '%s' "$LISTING" | grep -q "ExistingADRs/ADR-259"; then
  echo "FAIL: sibling ADR-259 missing from packet" >&2
  exit 1
fi

echo "PASS: cos-counsel-packet integration smoke"
