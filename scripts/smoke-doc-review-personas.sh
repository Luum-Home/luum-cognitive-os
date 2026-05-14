#!/usr/bin/env bash
# SCOPE: os-only
# @on-demand: live e2e smoke test for /doc-review-personas; requires ALIBABA_QWEN_API_KEY; exits 77 (skip) if absent
# smoke-doc-review-personas.sh — live end-to-end check for /doc-review-personas.
#
# Creates a tmp corpus with intentional defects, runs the real skill with 2
# personas, and verifies the report surfaces at least one S1 or S2 finding.
#
# Requires ALIBABA_QWEN_API_KEY (via .env or env). Exits 77 (skip) if absent,
# so CI can conditionally run this.

set -uo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"

if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$PROJECT_DIR/.env"
  set +a
fi

if [ -z "${ALIBABA_QWEN_API_KEY:-}" ]; then
  echo "[skip] ALIBABA_QWEN_API_KEY not set — skipping live smoke (exit 77)"
  exit 77
fi

TMP_DIR="$(mktemp -d -t doc-review-personas-smoke-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/docs"

# Intentional defects seeded across 3 files:
#   1. README lacks installation instructions + has broken link
#   2. BUDGET has dates that don't close + no ROI
#   3. SPEC has a typo / missing tilde
cat > "$TMP_DIR/docs/00-MOCs/entrypoints/README.md" <<'EOF'
# Projecto Demo

Este es un proyecto demo.

Ver [arquitectura](docs/04-Concepts/architecture/overview.md) para mas detalles.
EOF

cat > "$TMP_DIR/docs/BUDGET.md" <<'EOF'
# Presupuesto

- Sprint 1: semanas 1-3
- Sprint 2: semanas 4-6
- Sprint 3: semanas 5-7

Costo total: se definira mas adelante.
EOF

cat > "$TMP_DIR/docs/SPEC.md" <<'EOF'
# Especificacion tecnica

La solucion utiliza una arquitectura de microservicios.
La tecnica aplicada es nueva y revolucionaria.
EOF

echo "[smoke] running /doc-review-personas with cfo + editor_qa against $TMP_DIR/docs"
OUTPUT_FILE="$TMP_DIR/report.md"

if ! uv run python3 scripts/doc_review_personas.py \
      --docs-dir "$TMP_DIR/docs" \
      --personas cfo,editor_qa \
      --output-file "$OUTPUT_FILE" \
      --model haiku ; then
  # Exit 1 means S1 found — that's a PASS for the smoke (we seeded defects)
  rc=$?
  if [ $rc -ne 1 ]; then
    echo "[smoke] FAIL: CLI exited with $rc (expected 0 or 1)"
    exit 1
  fi
fi

if [ ! -s "$OUTPUT_FILE" ]; then
  echo "[smoke] FAIL: report is empty"
  exit 2
fi

# Require at least one S1 or S2 finding — smoke docs are deliberately broken
if ! grep -qE '(Críticos \(S1|Medios \(S2)' "$OUTPUT_FILE" ; then
  echo "[smoke] FAIL: no S1/S2 section headers in report"
  exit 3
fi

if ! grep -qE '^\| ' "$OUTPUT_FILE" ; then
  echo "[smoke] FAIL: no finding rows in markdown tables"
  exit 4
fi

echo "[smoke] OK — report at $OUTPUT_FILE"
echo "[smoke] first 40 lines:"
head -40 "$OUTPUT_FILE"
exit 0
