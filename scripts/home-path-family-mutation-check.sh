#!/usr/bin/env bash
# SCOPE: os-only
# home-path-family-mutation-check.sh — per-token mutation check for the
# "no operator home path in committed text" enforcer family.
#
# Why this exists, next to scripts/family_conformance_probe.py
# ------------------------------------------------------------
# The probe answers "does this candidate discriminate at all", using one
# must-trigger fixture and one must-not-trigger fixture. It is a per-FILE
# verdict, and a per-file verdict cannot see the failure that matters most
# here: a member that stops blocking a real leak because the same file also
# contains a CI path. Widening a detection regex until the false positive
# disappears passes the probe and produces exactly that.
#
# So this asks a narrower question, four times per member:
#
#   ci        a machine-allocated path alone            -> must PASS
#   describes a path pattern that MATCHES home paths    -> must PASS
#   personal  an operator home path alone               -> must BLOCK
#   mixed     all three in one file                     -> must BLOCK,
#             and for members that report matched text, the report must name
#             the personal token and NOT the exempt ones.
#
# `mixed` is the mutation the others cannot catch. `ci`, `describes` and
# `personal` on their own are the controls that keep `mixed` interpretable:
# without them a member that blocks everything also passes `mixed`.
#
# Why `describes` is a separate case from `ci`, and not a redundant one: the
# family's members match home paths through TWO shapes — `home root + account
# segment`, and `home root + segment + /Projects/`. A machine-allocated path
# like the CI one instantiates only the first. The 2026-08-15 defect in
# hooks/research-compliance-guard.sh lived entirely in the second, so a check
# built from `ci` and `personal` alone reports the repaired member as healthy
# for a reason unrelated to the repair. `describes` is written in the second
# shape on purpose.
#
# Granularity note, stated rather than hidden: hooks/research-compliance-guard.sh
# reports one finding per FILE, not per match, so for that member the `mixed`
# assertion degrades to "blocks the mixed file". Its per-token behaviour is
# still exercised — _home_paths_all_exempt() requires EVERY token in the file
# to be exempt — but the evidence is the verdict, not a quoted token.
#
# Read-only against this repository: every guard runs against a throwaway git
# repository under $TMPDIR. Deterministic. No session state.
#
# Exit: 0 all members behave / 1 at least one violation / 2 error
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Home roots are assembled at run time, never written as a literal: a file that
# holds the assembled prefix trips the very guards under test, this one
# included. Same concession, same reason as tests/fixtures/family-probe.
MAC_HOME="/""Users"
LINUX_HOME="/""home"

# The token classes. PROBE_USER is a synthetic account that exists on no
# machine; it stands in for the operator's real home segment.
PROBE_USER="mnprobe"
CI_TOKEN="${LINUX_HOME}/runner/work/luum-agent-os/build/out.log"
# Second shape: home root + segment + /Projects/. Every character that makes
# this a description rather than an instance ( [ ] + ) is illegal in a POSIX
# account name.
DESCRIBES_TOKEN="${MAC_HOME}/[a-z0-9._-]+/Projects/"
PERSONAL_TOKEN="${MAC_HOME}/${PROBE_USER}/Projects/luum/luum-agent-os/build/out.log"

MEMBERS=(
  "hooks/research-compliance-guard.sh"
  "scripts/check-local-privacy.sh"
  "scripts/check_absolute_paths.py"
  "scripts/provenance_scan.py"
)

FIXTURE_REL="docs/06-Daily/reports/mutation-fixture.md"
violations=0

make_sandbox() {
  local body="$1" sandbox
  sandbox="$(mktemp -d "${TMPDIR:-/tmp}/home-path-mutation.XXXXXX")" || return 1
  mkdir -p "$sandbox/$(dirname "$FIXTURE_REL")"
  printf '%s\n' "$body" > "$sandbox/$FIXTURE_REL"
  (
    cd "$sandbox" || exit 1
    git init -q .
    git config user.email probe@example.invalid
    git config user.name probe
    git add "$FIXTURE_REL"
  ) >/dev/null 2>&1
  printf '%s' "$sandbox"
}

# Runs one member inside one sandbox. Echoes "<verdict>\t<output>".
run_member() {
  local member="$1" sandbox="$2" out rc interp
  case "$member" in
    *.py) interp="python3" ;;
    *) interp="bash" ;;
  esac
  out="$(cd "$sandbox" && COGNITIVE_OS_PROJECT_DIR="$sandbox" \
      COS_RESEARCH_COMPLIANCE_FORCE=1 \
      "$interp" "$REPO_DIR/$member" </dev/null 2>&1)"
  rc=$?
  if [ "$rc" -eq 0 ]; then
    printf 'PASS\t%s' "$out"
  else
    printf 'BLOCK\t%s' "$out"
  fi
}

check() {
  local member="$1" label="$2" body="$3" want="$4" sandbox result verdict output
  sandbox="$(make_sandbox "$body")" || { echo "ERROR: sandbox failed" >&2; exit 2; }
  result="$(run_member "$member" "$sandbox")"
  verdict="${result%%$'\t'*}"
  output="${result#*$'\t'}"
  rm -rf "$sandbox"

  if [ "$verdict" = "$want" ]; then
    printf '    %-8s expected %-5s got %-5s  OK\n' "$label" "$want" "$verdict"
  else
    printf '    %-8s expected %-5s got %-5s  VIOLATION\n' "$label" "$want" "$verdict"
    violations=$((violations + 1))
  fi

  # For the mixed case, show which token the member actually named. Redacted
  # only for the synthetic account, which is safe to print in full.
  if [ "$label" = "mixed" ] && [ -n "$output" ]; then
    printf '%s\n' "$output" | sed 's/^/               | /'
  fi
}

echo "=== per-token mutation check: home-path-leak family ==="
echo "    ci        = ${LINUX_HOME}/runner/...                 (machine-allocated)"
echo "    describes = ${DESCRIBES_TOKEN}          (pattern, not instance)"
echo "    personal  = ${MAC_HOME}/${PROBE_USER}/Projects/...   (synthetic operator home)"
echo

CI_ONLY="# CI only

The job wrote its log to ${CI_TOKEN} before uploading."

DESCRIBES_ONLY="# Describes only

Hunt for leaked home paths in markdown with:

    git grep -nI -E '${DESCRIBES_TOKEN}' -- '*.md'"

PERSONAL_ONLY="# Personal only

The build wrote its output to ${PERSONAL_TOKEN}"

MIXED="# Mixed

The job wrote its log to ${CI_TOKEN} before uploading.
Audit command: git grep -nI -E '${DESCRIBES_TOKEN}' -- '*.md'
The build wrote its output to ${PERSONAL_TOKEN}"

for member in "${MEMBERS[@]}"; do
  echo "  $member"
  check "$member" "ci"        "$CI_ONLY"        "PASS"
  check "$member" "describes" "$DESCRIBES_ONLY" "PASS"
  check "$member" "personal"  "$PERSONAL_ONLY"  "BLOCK"
  check "$member" "mixed"     "$MIXED"          "BLOCK"
  echo
done

if [ "$violations" -eq 0 ]; then
  echo "OK: ${#MEMBERS[@]} members, 4 mutations each, no violations."
  exit 0
fi
echo "FAIL: $violations violation(s)." >&2
exit 1
