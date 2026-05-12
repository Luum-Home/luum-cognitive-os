#!/usr/bin/env bash
# SCOPE: os-only
# cos-ci-local.sh — local replacement for the suspended GitHub Actions CI.
#
# Per ADR-131. Consolidates what ci.yml / cross-platform.yml / go-quality.yml /
# test-quality.yml / test-lanes.yml used to run, into a single tiered runner.
#
# Usage:
#   bash scripts/cos-ci-local.sh [tier]
#
# Tiers:
#   quick (default) — pre-push gate. Target wall-clock under ~30 seconds.
#                     shellcheck (new only), gofmt, yaml validate, test-quality,
#                     secret-detector, .gitignore sanity.
#   full            — replaces ci.yml + go-quality.yml + cross-platform.yml.
#                     Target under ~5 minutes. Adds python core tests, go tests,
#                     go vet, docs integrity, cross-platform discipline tests.
#   deep            — replaces test-lanes.yml + linux smoke. Manual only.
#                     Target under ~15 minutes.
#
# Exit codes:
#   0 — all checks for the tier passed
#   1 — one or more checks failed (errors are surfaced inline)
#   2 — usage error (unknown tier, missing tools)
#
# Environment:
#   COS_CI_LOCAL_QUIET=1   suppress per-step section banners (CI-style logs only)
#   COS_CI_LOCAL_BAIL=0    do not stop on first failure; run every check, exit
#                          non-zero at the end (default: stop on first failure)
#   COS_CI_LOCAL_NO_DOCKER=1
#                          skip docker-dependent steps even in deep tier
#
# This script never modifies the working tree, never touches git, and never
# requires network access. All checks operate on the current checked-out files.

set -uo pipefail

readonly TIER="${1:-quick}"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$("$SCRIPT_DIR/cos-root" project)"
readonly BAIL="${COS_CI_LOCAL_BAIL:-1}"
readonly QUIET="${COS_CI_LOCAL_QUIET:-0}"
readonly NO_DOCKER="${COS_CI_LOCAL_NO_DOCKER:-0}"

cd "$REPO_ROOT" || exit 2

FAILED_STEPS=()
PASSED_STEPS=()
SKIPPED_STEPS=()

_section() {
  if [ "$QUIET" = "1" ]; then return 0; fi
  echo
  echo "── $1 ──────────────────────────────────────────"
}

_step() {
  # _step <label> <command...>
  local label="$1"; shift
  if [ "$QUIET" = "1" ]; then
    echo "  RUN: $label"
  else
    echo "  ▶ $label"
  fi
  if "$@"; then
    PASSED_STEPS+=("$label")
    [ "$QUIET" = "1" ] || echo "  ✓ $label"
    return 0
  else
    FAILED_STEPS+=("$label")
    echo "  ✗ FAIL: $label" >&2
    if [ "$BAIL" = "1" ]; then
      _summary
      exit 1
    fi
    return 1
  fi
}

_skip() {
  local label="$1"; local reason="$2"
  SKIPPED_STEPS+=("$label ($reason)")
  [ "$QUIET" = "1" ] || echo "  ⊘ skip: $label — $reason"
}

_summary() {
  echo
  echo "── cos-ci-local summary ──────────────────────────────"
  echo "  passed:  ${#PASSED_STEPS[@]}"
  echo "  failed:  ${#FAILED_STEPS[@]}"
  echo "  skipped: ${#SKIPPED_STEPS[@]}"
  if [ ${#FAILED_STEPS[@]} -gt 0 ]; then
    echo
    echo "  Failed steps:"
    for s in "${FAILED_STEPS[@]}"; do
      echo "    - $s"
    done
  fi
}

# ── Individual check functions ─────────────────────────────────────────────────

check_shellcheck() {
  command -v shellcheck >/dev/null 2>&1 || {
    _skip "shellcheck" "shellcheck not installed (brew install shellcheck)"
    return 0
  }
  if [ -f "$REPO_ROOT/scripts/lint-shell.sh" ]; then
    if [ -s "$REPO_ROOT/scripts/shellcheck-baseline.txt" ] && \
       grep -qv '^#' "$REPO_ROOT/scripts/shellcheck-baseline.txt" 2>/dev/null; then
      bash "$REPO_ROOT/scripts/lint-shell.sh" --new-only
    else
      bash "$REPO_ROOT/scripts/lint-shell.sh" --baseline
      echo "  (baseline mode — pre-existing violations accepted)"
      return 0
    fi
  else
    _skip "shellcheck" "scripts/lint-shell.sh not found"
    return 0
  fi
}

check_gofmt() {
  command -v gofmt >/dev/null 2>&1 || {
    _skip "gofmt" "go toolchain not installed"
    return 0
  }
  local out
  out=$(gofmt -l . 2>/dev/null | grep -v "^vendor/" || true)
  if [ -n "$out" ]; then
    echo "  Unformatted Go files (run: gofmt -w .):"
    echo "$out" | sed 's/^/    /'
    return 1
  fi
  return 0
}

check_go_vet() {
  command -v go >/dev/null 2>&1 || {
    _skip "go vet" "go toolchain not installed"
    return 0
  }
  go vet ./... 2>&1
}

check_go_core_tests() {
  command -v go >/dev/null 2>&1 || {
    _skip "go core tests" "go toolchain not installed"
    return 0
  }
  go test \
    ./internal/provider/... \
    ./internal/validator/... \
    ./pkg/hook/... \
    -count=1 -timeout 5m
}

check_yaml_syntax() {
  command -v python3 >/dev/null 2>&1 || {
    _skip "yaml syntax" "python3 not installed"
    return 0
  }
  python3 - <<'PY'
import sys, yaml, glob
errors = 0
exclude = ('.disabled',)  # don't validate suspended workflow files
for f in glob.glob('**/*.yaml', recursive=True) + glob.glob('**/*.yml', recursive=True):
    if any(f.endswith(e) for e in exclude):
        continue
    try:
        with open(f, encoding='utf-8') as fh:
            yaml.safe_load(fh)
    except Exception as e:
        print(f'  FAIL: {f}: {e}')
        errors += 1
sys.exit(1 if errors else 0)
PY
}

check_python_core_tests() {
  command -v python3 >/dev/null 2>&1 || {
    _skip "python core tests" "python3 not installed"
    return 0
  }
  python3 -m pytest \
    tests/contracts/test_kernel_contract.py \
    tests/contracts/test_product_zones.py \
    tests/contracts/test_killswitch.py \
    tests/unit/test_execution_profile.py \
    tests/unit/test_compatibility_layer.py \
    tests/unit/test_outcome_metrics.py \
    tests/unit/test_model_router.py \
    tests/unit/test_config_loader.py \
    tests/unit/test_cross_platform_discipline.py \
    tests/behavior/test_self_install.py \
    -q --tb=short 2>&1
}

check_cross_platform_discipline() {
  command -v python3 >/dev/null 2>&1 || {
    _skip "cross-platform discipline" "python3 not installed"
    return 0
  }
  python3 -m pytest \
    tests/unit/test_cross_platform_discipline.py \
    tests/unit/test_session_leak_detection.py \
    -q --tb=short 2>&1
}

check_test_quality() {
  command -v python3 >/dev/null 2>&1 || {
    _skip "test quality" "python3 not installed"
    return 0
  }
  if [ -f "$REPO_ROOT/scripts/check_test_quality.py" ]; then
    python3 "$REPO_ROOT/scripts/check_test_quality.py" --ci
  else
    _skip "test quality" "scripts/check_test_quality.py not found"
    return 0
  fi
}

check_secret_detector() {
  if [ -x "$REPO_ROOT/hooks/secret-detector.sh" ]; then
    CLAUDE_PROJECT_DIR="$REPO_ROOT" \
    COGNITIVE_OS_PROJECT_DIR="$REPO_ROOT" \
      bash "$REPO_ROOT/hooks/secret-detector.sh" 2>&1
  else
    _skip "secret detector" "hooks/secret-detector.sh not found"
    return 0
  fi
}

check_silent_failure_audit() {
  command -v python3 >/dev/null 2>&1 || {
    _skip "silent failure audit" "python3 not installed"
    return 0
  }
  if [ -x "$REPO_ROOT/scripts/cos-silent-failure-audit" ]; then
    "$REPO_ROOT/scripts/cos-silent-failure-audit" --fail-on-findings
  else
    _skip "silent failure audit" "scripts/cos-silent-failure-audit not found"
    return 0
  fi
}

check_python_stdin_antipattern_audit() {
  command -v python3 >/dev/null 2>&1 || {
    _skip "python stdin antipattern audit" "python3 not installed"
    return 0
  }
  if [ -x "$REPO_ROOT/scripts/cos-python-stdin-antipattern-audit" ]; then
    "$REPO_ROOT/scripts/cos-python-stdin-antipattern-audit" --fail-on-findings
  else
    _skip "python stdin antipattern audit" "scripts/cos-python-stdin-antipattern-audit not found"
    return 0
  fi
}

check_lab_first_gate() {
  command -v python3 >/dev/null 2>&1 || {
    _skip "lab-first promotion gate" "python3 not installed"
    return 0
  }
  if [ -x "$REPO_ROOT/scripts/cos-lab-first-gate" ]; then
    "$REPO_ROOT/scripts/cos-lab-first-gate" --json >/dev/null
  else
    _skip "lab-first promotion gate" "scripts/cos-lab-first-gate not found"
    return 0
  fi
}

check_self_improvement_discipline_gate() {
  command -v python3 >/dev/null 2>&1 || {
    _skip "self-improvement discipline gate" "python3 not installed"
    return 0
  }
  if [ -x "$REPO_ROOT/scripts/cos-self-improvement-discipline-gate" ]; then
    "$REPO_ROOT/scripts/cos-self-improvement-discipline-gate" --profile core --json >/dev/null
  else
    _skip "self-improvement discipline gate" "scripts/cos-self-improvement-discipline-gate not found"
    return 0
  fi
}


check_closure_discipline_audit() {
  command -v python3 >/dev/null 2>&1 || {
    _skip "closure discipline audit" "python3 not installed"
    return 0
  }
  if [ -x "$REPO_ROOT/scripts/cos-closure-discipline-audit" ]; then
    "$REPO_ROOT/scripts/cos-closure-discipline-audit" --fail-on-findings --json >/dev/null
  else
    _skip "closure discipline audit" "scripts/cos-closure-discipline-audit not found"
    return 0
  fi
}

check_adr_tier_claim_audit() {
  command -v python3 >/dev/null 2>&1 || {
    _skip "ADR tier claim audit" "python3 not installed"
    return 0
  }
  if [ -x "$REPO_ROOT/scripts/cos-tier-claim-audit" ]; then
    "$REPO_ROOT/scripts/cos-tier-claim-audit" --json >/dev/null
  else
    _skip "ADR tier claim audit" "scripts/cos-tier-claim-audit not found"
    return 0
  fi
}

check_core_adoption_profile() {
  if [ -x "$REPO_ROOT/scripts/cos-adoption-profile" ]; then
    "$REPO_ROOT/scripts/cos-adoption-profile" --profile core >/dev/null
  else
    _skip "core adoption profile" "scripts/cos-adoption-profile not found"
    return 0
  fi
}

check_active_primitive_index() {
  if [ -x "$REPO_ROOT/scripts/cos-active-primitive-index" ]; then
    "$REPO_ROOT/scripts/cos-active-primitive-index" --json >/dev/null
  else
    _skip "active primitive index" "scripts/cos-active-primitive-index not found"
    return 0
  fi
}

check_core_preamble_budget() {
  if [ -x "$REPO_ROOT/scripts/cos-preamble-budget" ]; then
    "$REPO_ROOT/scripts/cos-preamble-budget" --profile core >/dev/null
  else
    _skip "core preamble budget" "scripts/cos-preamble-budget not found"
    return 0
  fi
}

check_gitignore_sanity() {
  local missing=0
  for pattern in ".env" ".env.local" "*.pem" "*.key"; do
    if ! grep -q "$pattern" "$REPO_ROOT/.gitignore" 2>/dev/null; then
      echo "  WARN: $pattern not in .gitignore"
      missing=1
    fi
  done
  return "$missing"
}

check_docs_integrity() {
  command -v python3 >/dev/null 2>&1 || {
    _skip "docs integrity" "python3 not installed"
    return 0
  }
  python3 - <<'PY'
import re, sys
from pathlib import Path

docs = [Path('README.md'), Path('CONTRIBUTING.md'), Path('docs/00-MOCs/entrypoints/README.md')]
errors = 0

def normalize(target):
    target = target.strip().strip('<>')
    target = target.split('#', 1)[0]
    target = target.split('?', 1)[0]
    return target

for doc in docs:
    if not doc.exists():
        continue
    text = doc.read_text(encoding='utf-8')
    for raw_target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', text):
        target = normalize(raw_target)
        if not target or target.startswith(('http://', 'https://', 'mailto:', '#')):
            continue
        resolved = (doc.parent / target).resolve()
        if not resolved.exists():
            print(f'  FAIL: {doc} -> missing {target}')
            errors += 1

sys.exit(1 if errors else 0)
PY
}

check_test_lanes() {
  if [ -x "$REPO_ROOT/cmd/cos-test/cos-test" ] || \
     command -v cos-test >/dev/null 2>&1; then
    local cos_test_bin
    if [ -x "$REPO_ROOT/cmd/cos-test/cos-test" ]; then
      cos_test_bin="$REPO_ROOT/cmd/cos-test/cos-test"
    else
      cos_test_bin="cos-test"
    fi
    "$cos_test_bin" broad --no-docker
  else
    _skip "test lanes" "cos-test binary not built (cd cmd/cos-test && go build)"
    return 0
  fi
}

check_linux_smoke_docker() {
  if [ "$NO_DOCKER" = "1" ]; then
    _skip "linux smoke" "COS_CI_LOCAL_NO_DOCKER=1"
    return 0
  fi
  command -v docker >/dev/null 2>&1 || {
    _skip "linux smoke" "docker not installed"
    return 0
  }
  if [ ! -f "$REPO_ROOT/Dockerfile.ci-linux" ]; then
    _skip "linux smoke" "Dockerfile.ci-linux not found"
    return 0
  fi
  docker build -f "$REPO_ROOT/Dockerfile.ci-linux" -t luum-agent-os-ci-linux:local . >/dev/null
  docker run --rm luum-agent-os-ci-linux:local
}

# ── Tier dispatch ──────────────────────────────────────────────────────────────

run_quick() {
  _section "quick tier (pre-push gate)"
  _step "shellcheck (new violations only)"   check_shellcheck
  _step "gofmt -l ."                          check_gofmt
  _step "yaml syntax (all .yml/.yaml)"        check_yaml_syntax
  _step "test quality (structural detector)"  check_test_quality
  _step "secret detector"                     check_secret_detector
  _step "silent failure audit"                check_silent_failure_audit
  _step "python stdin antipattern audit"      check_python_stdin_antipattern_audit
  _step "core adoption profile"               check_core_adoption_profile
  _step "active primitive index"              check_active_primitive_index
  _step "core preamble budget"                check_core_preamble_budget
  _step "lab-first promotion gate"            check_lab_first_gate
  _step "self-improvement discipline gate"    check_self_improvement_discipline_gate
  _step "ADR tier claim audit"                check_adr_tier_claim_audit
  _step "closure discipline audit"            check_closure_discipline_audit
  _step ".gitignore sanity"                   check_gitignore_sanity
}

run_full() {
  run_quick
  _section "full tier (PR-equivalent)"
  _step "go vet"                              check_go_vet
  _step "go core tests"                       check_go_core_tests
  _step "python core tests"                   check_python_core_tests
  _step "cross-platform discipline tests"     check_cross_platform_discipline
  _step "docs integrity (markdown links)"     check_docs_integrity
}

run_deep() {
  run_full
  _section "deep tier (manual; replaces test-lanes + linux smoke)"
  _step "test lanes (cos-test broad)"         check_test_lanes
  _step "linux smoke (docker)"                check_linux_smoke_docker
}

# ── Main ───────────────────────────────────────────────────────────────────────

case "$TIER" in
  quick) run_quick ;;
  full)  run_full ;;
  deep)  run_deep ;;
  -h|--help|help)
    sed -n '/^# Usage:/,/^# This script/p' "$0" | sed 's/^# //; s/^#$//'
    exit 0
    ;;
  *)
    echo "Unknown tier: $TIER" >&2
    echo "Usage: $0 [quick|full|deep]" >&2
    exit 2
    ;;
esac

_summary
[ ${#FAILED_STEPS[@]} -eq 0 ] || exit 1
exit 0
