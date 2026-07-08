---
type: quality-synthesis
source: docs/09-Quality/manual-tests/five-minute-demo.md
provenance: "Manual proof path showing Cognitive OS is easy to adopt, serious to trust, and portable across harness drivers, targeted at a 5-minute reviewer demo."
---

## What it is
A manual proof path ("five-minute product demo") aimed at showing a new reviewer that Cognitive OS installs into a throwaway project quickly, projects settings to a chosen harness driver, exposes status tooling, and has automated tests backing the durable-product contracts — without depending on any single vendor-specific project layout as the source of truth.

## Key mechanics
- **Target**: 5 minutes on a machine with `bash`, `python3`, `jq`; if exceeded due to missing deps, that's recorded as onboarding work, not accepted as normal.
- **Scripted versions**: `bash scripts/demo-portability-proof.sh` (full demo), `bash scripts/demo-first-run-onboarding.sh` (narrower, budgeted onboarding proof), `--skip-provider-tests` flag for a faster local run skipping provider/kernel Go tests.
- **Manual equivalent**: install into a temp dir via `install.sh --from <repo> --harness=codex --force --skip-manifest-check`; verify `.cognitive-os/`, `.codex/hooks.json`, `.cognitive-os/skills/cos` exist; inspect with `COGNITIVE_OS_PROJECT_DIR=<dir> bash scripts/cos-status.sh --json`; repeat install with `--harness=claude` into a second temp dir, verify `.claude/settings.json` exists — proving the same source projects to multiple harnesses without rewriting the system.
- **Product-contract lane**: `python3 -m pytest tests/contracts/test_kernel_contract.py tests/contracts/test_product_zones.py tests/unit/test_execution_profile.py tests/unit/test_compatibility_layer.py tests/unit/test_outcome_metrics.py -q`.
- **Provider/kernel lane** (ecosystem-churn resilience): `go test ./internal/provider/... ./internal/validator/... ./pkg/hook/... -count=1`.
- **Acceptance criteria**: both harness installs exit 0 with their respective marker files (`CODEX_PROJECT_DIR` / `CLAUDE_PROJECT_DIR`); `cos-status.sh --json` exits 0; core fingerprints under `.cognitive-os/{hooks,skills,templates}/cos` match between Codex and Claude installs; product-contract tests pass.

## Relations & where used
Shares its product-contract test set (`test_kernel_contract.py`, execution-profile/compatibility-layer/outcome-metrics tests) with `durable-product-verification.md`. Broader/less time-boxed sibling of `first-run-onboarding.md`.

## Status / caveats
Explicitly scopes non-claims: does not claim every extension/dashboard/squad workflow/control-plane feature is production-ready (those need their own proof path), and does not claim every harness has identical capabilities — "core behavior is authored once, then projected through explicit compatibility drivers where the harness supports it." No dated execution log embedded.
