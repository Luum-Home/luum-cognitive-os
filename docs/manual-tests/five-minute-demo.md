# Five-Minute Product Demo

> Manual proof path for showing that Cognitive OS is easy to adopt, serious to trust, and portable across harness drivers.

## Goal

Show a new reviewer that Cognitive OS can become active in a throwaway project in minutes, without depending on a single vendor-specific project layout as the source of truth.

This demo proves four claims:

- the core installs into `.cognitive-os/`
- settings can be projected to a selected harness driver
- status tooling can inspect the active installation
- the durable product contracts have automated tests

## Time Budget

Target: 5 minutes on a developer machine with `bash`, `python3`, and `jq`.

If the demo exceeds 5 minutes because dependencies are missing, record the missing dependency as onboarding work instead of treating the delay as acceptable.

## Demo Script

The executable version of this demo is:

```bash
bash scripts/demo-portability-proof.sh
```

For a narrower first-run onboarding proof with explicit performance budgets:

```bash
bash scripts/demo-first-run-onboarding.sh
```

For a faster local run that skips provider/kernel Go tests:

```bash
bash scripts/demo-portability-proof.sh --skip-provider-tests
```

The manual equivalent is below.

Run from the Cognitive OS source repository:

```bash
COS_REPO="$(pwd)"
DEMO_PROJECT="$(mktemp -d)"

cd "$DEMO_PROJECT"
"$COS_REPO/install.sh" \
  --from "$COS_REPO" \
  --harness=codex \
  --force \
  --skip-manifest-check
```

Verify the installed core and Codex projection:

```bash
test -d "$DEMO_PROJECT/.cognitive-os"
test -f "$DEMO_PROJECT/.codex/hooks.json"
test -d "$DEMO_PROJECT/.cognitive-os/skills/cos"
```

Inspect the active state:

```bash
COGNITIVE_OS_PROJECT_DIR="$DEMO_PROJECT" \
  bash "$COS_REPO/scripts/cos-status.sh" --json
```

Show that the same source can project to the Claude driver without rewriting the system:

```bash
CLAUDE_DEMO_PROJECT="$(mktemp -d)"

cd "$CLAUDE_DEMO_PROJECT"
"$COS_REPO/install.sh" \
  --from "$COS_REPO" \
  --harness=claude \
  --force \
  --skip-manifest-check

test -f "$CLAUDE_DEMO_PROJECT/.claude/settings.json"
```

Return to the source repo and run the product-contract lane:

```bash
cd "$COS_REPO"
python3 -m pytest \
  tests/contracts/test_kernel_contract.py \
  tests/contracts/test_product_zones.py \
  tests/unit/test_execution_profile.py \
  tests/unit/test_compatibility_layer.py \
  tests/unit/test_outcome_metrics.py -q
```

Run the provider/kernel lane when proving ecosystem-churn resilience:

```bash
go test ./internal/provider/... ./internal/validator/... ./pkg/hook/... -count=1
```

## Acceptance Criteria

- Codex harness install exits `0`.
- `.cognitive-os/` exists in the demo project.
- `.codex/hooks.json` exists when `--harness=codex` is selected.
- Claude harness install exits `0`.
- `.claude/settings.json` exists when `--harness=claude` is selected.
- `cos-status.sh --json` exits `0`.
- Core fingerprints under `.cognitive-os/hooks/cos`, `.cognitive-os/skills/cos`, and `.cognitive-os/templates/cos` match between Codex and Claude installs.
- Codex settings use `CODEX_PROJECT_DIR`; Claude settings use `CLAUDE_PROJECT_DIR`.
- Product-contract tests pass.

## What This Does Not Claim

This demo does not claim that every extension, dashboard, squad workflow, or future control-plane feature is production-ready. Those remain optional or experimental unless they have their own proof path.

It also does not claim every harness has identical capabilities. The product contract is that core behavior is authored once, then projected through explicit compatibility drivers where the harness supports it.
