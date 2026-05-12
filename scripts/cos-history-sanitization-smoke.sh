#!/usr/bin/env bash
# ADR-218 post-execute smoke test.
#
# Asserts that NO sensitive token configured in
# `manifests/history-sanitization.yaml` (resolved through env vars) appears
# anywhere in the rewritten git history — including HEAD, the tombstone
# branch, and every other ref returned by `git for-each-ref`.
#
# Exits 0 if all configured tokens have 0 hits across `git log --all -p`.
# Exits 1 if any token has >0 hits (smoke FAIL — do NOT force-push).
# Exits 2 on environmental error (not in a git repo, manifest missing, etc.).
#
# When ZERO env vars are resolved, the script prints a warning and exits 0
# (skip-with-warning) so the runbook can be exercised in environments where
# the operator has not yet configured codenames.
#
# Usage:
#   COS_HISTORY_SANITIZE_OPERATOR_EMAIL=...  \
#   COS_HISTORY_SANITIZE_HOME_PREFIX=...     \
#   COS_HISTORY_SANITIZE_REPO_PATH=...       \
#   COS_HISTORY_SANITIZE_CONSUMER_CODENAME_A=...  \
#   ...                                       \
#   bash scripts/cos-history-sanitization-smoke.sh [--repo PATH] [--manifest PATH]
#
# Optional flags:
#   --repo PATH         path to the git repository (default: $PWD)
#   --manifest PATH     path to the sanitization manifest
#                       (default: <repo>/manifests/history-sanitization.yaml)
#   --refs-only         scan only the refs reported by `git for-each-ref`
#                       (default: scan `git log --all -p` AND every ref tip)
#   --quiet             suppress per-token rows; print only summary
#   --json              emit machine-readable JSON summary
#   --help              print this help and exit 0
#
set -euo pipefail

REPO="${PWD}"
MANIFEST=""
QUIET=0
JSON=0
REFS_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --manifest) MANIFEST="$2"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    --json) JSON=1; shift ;;
    --refs-only) REFS_ONLY=1; shift ;;
    --help|-h)
      sed -n '1,40p' "$0"
      exit 0 ;;
    *)
      echo "[smoke] unknown flag: $1" >&2
      exit 2 ;;
  esac
done

if [[ -z "${MANIFEST}" ]]; then
  MANIFEST="${REPO}/manifests/history-sanitization.yaml"
fi

if ! git -C "${REPO}" rev-parse --git-dir >/dev/null 2>&1; then
  echo "[smoke] not a git repository: ${REPO}" >&2
  exit 2
fi

if [[ ! -f "${MANIFEST}" ]]; then
  echo "[smoke] manifest not found: ${MANIFEST}" >&2
  exit 2
fi

# ── Discover env vars from manifest (no consumer codenames in this script) ──
# Extract `value_env: COS_HISTORY_SANITIZE_*` lines from rules: section.
ENV_VARS=()
while IFS= read -r env_var || [[ -n "$env_var" ]]; do
  ENV_VARS+=("$env_var")
done < <(
  awk '
    /^rules:/ { in_rules = 1; next }
    /^[a-zA-Z_]+:/ && !/^[[:space:]]/ { in_rules = 0 }
    in_rules && /value_env:/ {
      sub(/.*value_env:[[:space:]]*/, "")
      gsub(/[[:space:]"]/, "")
      print
    }
  ' "${MANIFEST}"
)

if [[ "${#ENV_VARS[@]}" -eq 0 ]]; then
  echo "[smoke] no value_env entries discovered in ${MANIFEST}" >&2
  exit 2
fi

# ── Resolve tokens from environment ─────────────────────────────────────────
declare -a TOKENS=()
declare -a TOKEN_NAMES=()
for var in "${ENV_VARS[@]}"; do
  value="${!var:-}"
  if [[ -n "${value}" ]]; then
    TOKENS+=("${value}")
    TOKEN_NAMES+=("${var}")
  fi
done

if [[ "${#TOKENS[@]}" -eq 0 ]]; then
  if [[ "${JSON}" -eq 1 ]]; then
    printf '{"status":"skipped","reason":"no env vars set","env_vars_checked":%s,"tokens_resolved":0}\n' "${#ENV_VARS[@]}"
  else
    echo "[smoke] WARN: no sanitization env vars are set; skipping token scan."
    echo "[smoke] WARN: discovered ${#ENV_VARS[@]} value_env entries in manifest:"
    for v in "${ENV_VARS[@]}"; do echo "  - ${v}"; done
    echo "[smoke] WARN: set them to the same values used by --execute and re-run."
    echo "[smoke] PASS (skip-with-warning)"
  fi
  exit 0
fi

# ── Build the haystack ──────────────────────────────────────────────────────
# We scan `git log --all -p` (covers every commit reachable from any ref
# including the tombstone branch). For belt-and-braces, we also walk every
# ref tip with `git for-each-ref` and grep its tree.
TMPDIR_SMOKE=$(mktemp -d)
trap 'rm -rf "${TMPDIR_SMOKE}"' EXIT

HAYSTACK="${TMPDIR_SMOKE}/history.txt"
if [[ "${REFS_ONLY}" -eq 0 ]]; then
  git -C "${REPO}" log --all -p --no-color > "${HAYSTACK}" 2>/dev/null || true
else
  : > "${HAYSTACK}"
fi

# Append per-ref tree contents so we cover refs the log walk may not chase
# (e.g. annotated tags pointing at non-commit objects, replace refs).
REFS_FILE="${TMPDIR_SMOKE}/refs.txt"
git -C "${REPO}" for-each-ref --format='%(refname)' > "${REFS_FILE}" 2>/dev/null || true
while IFS= read -r ref; do
  [[ -z "${ref}" ]] && continue
  git -C "${REPO}" grep -I --no-color -e "" "${ref}" 2>/dev/null \
    | head -c 5242880 >> "${HAYSTACK}" || true
done < "${REFS_FILE}"

if [[ ! -s "${HAYSTACK}" ]]; then
  echo "[smoke] empty haystack — repo may have no commits or no refs" >&2
  exit 2
fi

# ── Scan each token ─────────────────────────────────────────────────────────
declare -a HITS=()
FAIL=0
for i in "${!TOKENS[@]}"; do
  token="${TOKENS[$i]}"
  # Use grep -F (fixed string) to avoid regex surprises in operator paths.
  # `|| true` because grep returns 1 on no match, which is the GOOD case here.
  count=$(grep -Fc -- "${token}" "${HAYSTACK}" || true)
  count="${count:-0}"
  HITS+=("${count}")
  if [[ "${count}" -gt 0 ]]; then
    FAIL=1
  fi
done

# ── Verify report exists (best-effort, last report) ─────────────────────────
REPORT_DIR="${REPO}/.cognitive-os/reports/history-sanitization"
LATEST_REPORT=""
if [[ -d "${REPORT_DIR}" ]]; then
  LATEST_REPORT=$(ls -1t "${REPORT_DIR}"/*.json 2>/dev/null | head -n1 || true)
fi

# ── Verify tombstone branch exists ──────────────────────────────────────────
TOMBSTONE_REF=$(git -C "${REPO}" for-each-ref --format='%(refname:short)' \
  'refs/heads/history-sanitization-*' \
  'refs/heads/tombstone/pre-history-rewrite-*' 2>/dev/null | head -n1 || true)

# ── Verify SHA inventory preserved ──────────────────────────────────────────
SHA_INVENTORY=$(ls -1 "${REPO}"/docs/01-Build-Log/history/pre-sanitization-sha-inventory-*.txt 2>/dev/null | head -n1 || true)

# ── Emit results ────────────────────────────────────────────────────────────
if [[ "${JSON}" -eq 1 ]]; then
  printf '{\n'
  printf '  "status": "%s",\n' "$([[ ${FAIL} -eq 0 ]] && echo PASS || echo FAIL)"
  printf '  "repo": "%s",\n' "${REPO}"
  printf '  "manifest": "%s",\n' "${MANIFEST}"
  printf '  "tokens_resolved": %d,\n' "${#TOKENS[@]}"
  printf '  "env_vars_checked": %d,\n' "${#ENV_VARS[@]}"
  printf '  "latest_report": "%s",\n' "${LATEST_REPORT}"
  printf '  "tombstone_branch": "%s",\n' "${TOMBSTONE_REF}"
  printf '  "sha_inventory": "%s",\n' "${SHA_INVENTORY}"
  printf '  "results": [\n'
  for i in "${!TOKENS[@]}"; do
    sep=","
    [[ "${i}" -eq $(( ${#TOKENS[@]} - 1 )) ]] && sep=""
    printf '    {"env_var": "%s", "hits": %d, "verdict": "%s"}%s\n' \
      "${TOKEN_NAMES[$i]}" "${HITS[$i]}" \
      "$([[ ${HITS[$i]} -eq 0 ]] && echo PASS || echo FAIL)" "${sep}"
  done
  printf '  ]\n}\n'
else
  if [[ "${QUIET}" -eq 0 ]]; then
    printf '%-55s %8s   %s\n' "TOKEN (env var)" "HITS" "VERDICT"
    printf '%-55s %8s   %s\n' "-------------------------------------------------------" "--------" "-------"
    for i in "${!TOKENS[@]}"; do
      verdict="PASS"
      [[ "${HITS[$i]}" -gt 0 ]] && verdict="FAIL"
      printf '%-55s %8d   %s\n' "${TOKEN_NAMES[$i]}" "${HITS[$i]}" "${verdict}"
    done
    echo
  fi
  echo "[smoke] tombstone branch:    ${TOMBSTONE_REF:-<none>}"
  echo "[smoke] latest report:       ${LATEST_REPORT:-<none>}"
  echo "[smoke] sha inventory:       ${SHA_INVENTORY:-<none>}"
  echo "[smoke] tokens resolved:     ${#TOKENS[@]} of ${#ENV_VARS[@]} env vars"
  if [[ "${FAIL}" -eq 0 ]]; then
    echo "[smoke] PASS — 0 leaked tokens across HEAD + tombstone + all refs"
  else
    echo "[smoke] FAIL — at least one configured token still appears in history" >&2
    echo "[smoke] DO NOT force-push. Restore from backup mirror and investigate." >&2
  fi
fi

exit "${FAIL}"
