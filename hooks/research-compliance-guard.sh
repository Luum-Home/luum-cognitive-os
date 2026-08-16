#!/usr/bin/env bash
# SCOPE: both
# research-compliance-guard.sh — portable pre-commit guard for research/license boundaries.
#
# Blocks common research-to-runtime and proprietary/unlicensed research reuse
# mistakes in consumer projects without requiring COS maintainer-only companion
# manifests. This guard is intentionally conservative and self-contained so it
# can ship in the default/core install profile.
#
# Event: PreToolUse / Matcher: Bash / Trigger: command contains git commit
# Exit: 0 allow / 2 block
# Bypass: COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS=1
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

resolve_root() {
  if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ] && [ -d "$COGNITIVE_OS_PROJECT_DIR" ]; then
    cd "$COGNITIVE_OS_PROJECT_DIR" 2>/dev/null && pwd && return 0
  fi
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "$CLAUDE_PROJECT_DIR" ]; then
    cd "$CLAUDE_PROJECT_DIR" 2>/dev/null && pwd && return 0
  fi
  if [ -n "${CODEX_PROJECT_DIR:-}" ] && [ -d "$CODEX_PROJECT_DIR" ]; then
    cd "$CODEX_PROJECT_DIR" 2>/dev/null && pwd && return 0
  fi
  git -C "${PWD:-.}" rev-parse --show-toplevel 2>/dev/null && return 0
  case "$SCRIPT_DIR" in
    */.cognitive-os/hooks/cos) cd "$SCRIPT_DIR/../../.." 2>/dev/null && pwd && return 0 ;;
  esac
  cd "$SCRIPT_DIR/.." 2>/dev/null && pwd
}

ROOT_DIR="$(resolve_root)"
LOG_DIR="$ROOT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/research-compliance-guard.jsonl"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

_log() {
  mkdir -p "$LOG_DIR" 2>/dev/null || true
  printf '%s\n' "$1" >> "$LOG_FILE" 2>/dev/null || true
}

INPUT="$(cat 2>/dev/null || true)"
CMD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command", ""))
except Exception: pass' 2>/dev/null || true)"

if [ "${COS_RESEARCH_COMPLIANCE_FORCE:-0}" != "1" ] && [[ "$CMD" != *"git commit"* ]]; then
  exit 0
fi

if [ "${COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS=1\"}"
  exit 0
fi

STAGED="$(git -C "$ROOT_DIR" diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)"
[ -z "$STAGED" ] && exit 0

failures=()

MAC_HOME_SEG='/'"Users"
LINUX_HOME_SEG='/'"home"
HOME_PATH_RE="(^|[^A-Za-z0-9_.-])((${MAC_HOME_SEG}|${LINUX_HOME_SEG})/[A-Za-z0-9._-]+|${MAC_HOME_SEG}/[^.][^/[:space:]]+/Projects/)"
# Wider token, used ONLY to classify a hit that HOME_PATH_RE already produced —
# never to create one. HOME_PATH_RE stops at the first character illegal in an
# account name, so the user segment it captures is truncated exactly where the
# evidence needed to judge it begins. Detection semantics are unchanged: the
# classification below can only remove a finding, never add one.
HOME_TOKEN_RE="(${MAC_HOME_SEG}|${LINUX_HOME_SEG})/[^/[:space:]]+"
# Companion token for HOME_PATH_RE's SECOND branch. That branch opens its user
# segment with [^.], not with the account-name class, so it fires on segments
# beginning with a regex metacharacter — `[a-z0-9._-]+/Projects/` inside a
# quoted git grep, for one. HOME_TOKEN_RE stops at the first `/`, so those hits
# survive extraction but are then discarded by the account-name filter in
# _home_paths_all_exempt(), leaving the file with zero classifiable tokens and
# no way to earn an exemption. Same classification-only contract as
# HOME_TOKEN_RE: this can remove a finding, never create one.
HOME_PROJECTS_TOKEN_RE="${MAC_HOME_SEG}/[^.][^/[:space:]]+/Projects/"

# User segments that are not a personal home by construction.
#
# `runner` is the fixed home of a GitHub Actions runner: identical on every
# runner in the world, published in the runner image, allocated to a machine
# rather than to a person. The bar for adding an entry here is that question
# and only that question — *does this string identify a person on some
# machine?* If the answer is "it depends", it does not belong. A username that
# merely happens to be common (admin, dev, ubuntu) does NOT qualify: somewhere
# it is someone's actual account.
#
# Observed 2026-08-15: a report auditing home-path leakage blocked its own
# commit on four matches, all of them the CI runner path, which the report
# itself classified as CI before concluding zero leaks.
#
# `jovyan` clears the same bar for the same reason: it is the fixed home
# account of the jupyter/docker-stacks images, a coined word (from "jovian",
# of Jupiter) chosen by that project precisely so it would never collide with
# a person's account. It is allocated to an IMAGE, identical in every
# container built from it, and published in the image documentation. Nobody is
# named jovyan on any machine, so the question "does this string identify a
# person?" has a clean no, not an "it depends".
#
# Parity note, and a real behavioural difference worth knowing: the other
# three members express this same exemption as a `/`-ANCHORED PREFIX
# (ALLOWED_POSIX_PREFIXES in scripts/check-local-privacy.sh,
# DEFAULT_ALLOWED_ABSOLUTE_PATHS in scripts/provenance_scan.py,
# ALLOWED_POSIX_PREFIXES in scripts/check_absolute_paths.py), so for them the
# bare home directory of the account still blocks while a subdirectory of it
# passes. This guard has no prefix mechanism, only segments, so here both
# forms pass. The divergence goes in the direction the 2026-08-15 family
# report already recorded as the siblings' open defect (finding #1: prefix
# exemptions anchored to the slash), not toward leniency about persons.
CI_MACHINE_SEGMENTS=" runner jovyan "

# Placeholder segments, kept in parity with PLACEHOLDER_USERS in
# scripts/check-local-privacy.sh and PLACEHOLDER_USER_SEGMENTS in
# scripts/check_absolute_paths.py.
PLACEHOLDER_SEGMENTS=' <user> {user} $USER ${USER} USER ... '

# True when the segment is a pattern *matching* usernames rather than being
# one. Same discriminator as `describes_a_username` in
# scripts/check-local-privacy.sh (commit 3a6e737b): none of []()*+?\|^$ is
# legal in a POSIX or macOS account name, so a segment containing one is
# describing usernames by construction. Exact, not heuristic — it cannot mask
# an accidental commit of a real path, only a deliberately obfuscated one,
# which this guard never caught.
_describes_a_username() {
  case "$1" in
    *'['*|*']'*|*'('*|*')'*|*'*'*|*'+'*|*'?'*|*'\'*|*'|'*|*'^'*|*'$'*) return 0 ;;
  esac
  return 1
}

_is_exempt_home_segment() {
  local seg="$1"
  [ -n "$seg" ] || return 1
  case "$CI_MACHINE_SEGMENTS" in *" $seg "*) return 0 ;; esac
  case "$PLACEHOLDER_SEGMENTS" in *" $seg "*) return 0 ;; esac
  _describes_a_username "$seg"
}

# True when EVERY home-path token in the file is provably not a personal home.
# Fail-closed on purpose: a file with no extractable token is not exempt, so a
# hit shape this function cannot parse keeps blocking instead of slipping past.
_home_paths_all_exempt() {
  local file="$1" token seg found=0

  # Branch 1 of HOME_PATH_RE: home root + account segment.
  while IFS= read -r token; do
    [ -z "$token" ] && continue
    seg="${token#*/}"
    seg="${seg#*/}"
    # Only tokens whose segment opens with a character legal in an account
    # name can have produced a BRANCH-1 hit. A segment opening with a quote or
    # a backtick is the tail of a shell snippet that merely mentions the home
    # root — branch 1 never fired on it, so it must not be allowed to deny an
    # exemption either. Branch 2 is a different question and is asked below;
    # applying this filter to it was the defect.
    case "$seg" in
      [A-Za-z0-9._-]*) ;;
      *) continue ;;
    esac
    found=1
    _is_exempt_home_segment "$seg" || return 1
  done < <(grep -oE "$HOME_TOKEN_RE" "$file" 2>/dev/null)

  # Branch 2 of HOME_PATH_RE: macOS home root + segment + /Projects/. Measured
  # 2026-08-15: a document describing the leak pattern was refused on the line
  # `git grep -nI -E '<mac home>/[a-z0-9._-]+/Projects/' -- '*.md'`. Branch 1
  # was silent on it, branch 2 fired, and the loop above dropped the only token
  # in the file because its segment opens with `[`. found stayed 0, so the
  # function reported "not exempt" — not because the segment failed the
  # exemption test, but because it was never asked.
  while IFS= read -r token; do
    [ -z "$token" ] && continue
    seg="${token#*/}"
    seg="${seg#*/}"
    seg="${seg%%/*}"
    [ -n "$seg" ] || continue
    found=1
    _is_exempt_home_segment "$seg" || return 1
  done < <(grep -oE "$HOME_PROJECTS_TOKEN_RE" "$file" 2>/dev/null)

  # Still fail-closed: a hit shape neither loop can parse leaves found=0 and
  # keeps blocking instead of slipping past.
  [ "$found" -eq 1 ]
}

add_failure() {
  failures+=("$1")
}

is_scannable_text() {
  case "$1" in
    *.md|*.mdx|*.txt|*.rst|*.adoc|*.yaml|*.yml|*.json|*.toml|*.py|*.js|*.jsx|*.ts|*.tsx|*.go|*.rs|*.sh|README|README.*) return 0 ;;
    *) return 1 ;;
  esac
}

while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  abs="$ROOT_DIR/$rel"

  case "$rel" in
    .research/*|research/*|_research/*)
      add_failure "$rel: research clones/working copies must stay ignored and must not be committed"
      continue
      ;;
  esac

  [ -f "$abs" ] || continue
  is_scannable_text "$rel" || continue

  size="$(wc -c < "$abs" 2>/dev/null || echo 0)"
  [ "${size:-0}" -gt 1048576 ] && continue

  if grep -Eq "$HOME_PATH_RE" "$abs" 2>/dev/null && ! _home_paths_all_exempt "$abs"; then
    add_failure "$rel: contains a personal absolute home path; use repo-local or redacted paths"
  fi

  case "$rel" in
    lib/*|packages/*|scripts/*|src/*|app/*|cmd/*)
      if grep -Eq '(\.research/|_research/|\.cognitive-os/external-source-cache)' "$abs" 2>/dev/null; then
        add_failure "$rel: runtime code references research-only source/cache paths"
      fi
      ;;
  esac

  case "$rel" in
    docs/*|README*|*.md|*.mdx)
      if grep -Eiq '(proprietary|all rights reserved|unlicensed|no license|license absent|unknown license)' "$abs" 2>/dev/null; then
        if ! grep -Eiq '(conceptual research only|conceptual-only|clean-room|no code[^[:alnum:]]+assets[^[:alnum:]]+prompts|no reuse|do not copy|do not port|do not vendor)' "$abs" 2>/dev/null; then
          add_failure "$rel: proprietary/unlicensed research must state conceptual-only/no-reuse/clean-room boundary"
        fi
        if grep -Eiq '(reference implementation|base(d)? on|adopt|port|copy|vendor)' "$abs" 2>/dev/null; then
          if ! grep -Eiq '(do not adopt|do not port|do not copy|do not vendor|not a reference implementation|avoid .*reference implementation)' "$abs" 2>/dev/null; then
            add_failure "$rel: unsafe reuse wording near proprietary/unlicensed research"
          fi
        fi
      fi
      ;;
  esac
done <<< "$STAGED"

if [ "${#failures[@]}" -eq 0 ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"pass\",\"files_scanned\":$(printf '%s\n' "$STAGED" | sed '/^$/d' | wc -l | tr -d ' ')}"
  exit 0
fi

payload="$(printf '%s\n' "${failures[@]}" | python3 -c 'import json,sys; print(json.dumps([l.rstrip() for l in sys.stdin if l.strip()]))' 2>/dev/null || echo '[]')"
_log "{\"timestamp\":\"$TS\",\"action\":\"block\",\"findings\":$payload}"

echo "=== RESEARCH-COMPLIANCE-GUARD: BLOCKED ===" >&2
echo "Research, license, or clean-room boundary issues were found:" >&2
for item in "${failures[@]}"; do
  echo "  - $item" >&2
done
echo "Resolve by keeping research clones ignored, using repo-local paths, and documenting proprietary/unlicensed research as conceptual-only with no code/assets/prompts/schema reuse." >&2
exit 2
