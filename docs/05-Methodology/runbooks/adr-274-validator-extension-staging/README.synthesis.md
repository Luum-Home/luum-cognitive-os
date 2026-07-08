---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/adr-274-validator-extension-staging/README.md
provenance: "Records the staged (not-yet-applied) patch that extends hooks/adr-section-validator.sh with an Operational Guide requirement, plus the operator procedure to review, apply, test, and roll it back."
---

## What it is

A staging-directory README for a patch to `hooks/adr-section-validator.sh` that adds a new validation check, `require_operational_guide`, enforcing that qualifying ADRs document an "Operational Guide" section.

## Key mechanics

- **Trigger conditions for the new check**: fires only when an ADR has `tier: maintainer` in frontmatter, `status: accepted` or `implemented`, an `implementation_files:` block with ≥1 entry, is not a tombstone, is not superseded, and has no `<!-- adr-274-exempt: <reason> -->` marker.
- **What's required when triggered**: a `## Operational Guide` section header plus at least 3 of 5 documented sub-sections (`### What changes for the operator`, `### What this answers`, `### Daily operational pattern`, `### When sources disagree`, `### Reading guide for cold readers`; `### Anti-confusion` accepted as an alias).
- **Behavior**: WARN to stderr with exit 0 by default; escalates to exit 2 (blocking) under `COS_STRICT_ADR_VALIDATION=1`, matching the existing section-contract gate's enforcement pattern.
- **Deployment is a 6-step operator procedure**: review the unified diff (`adr-section-validator.patch`) → set `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` → `git apply` the patch → run the portability test (`tests/red_team/portability/test_cos-operational-guide-audit.py`) → spot-check against a known-bad ADR (expect a WARNING on stderr) and a compliant one, ADR-273 (expect silent exit 0).
- **Why staged, not deployed directly**: `hooks/*.sh` are protected by `protected-config-write-guard` per ADR-117 — agents cannot modify them directly. Same staging discipline as the sibling ADR-273 Slice C hooks directory. The companion audit script (`scripts/cos-operational-guide-audit.py`) is already shipped and operational; this patch is described as "the second half of the ADR-274 contract enforcement."
- **Rollback**: `git apply -R` on the same patch file.

## Relations & where used

Sibling staging pattern to `adr-273-slice-c-staging/` and `adr-275-session-start-hook-staging/` — all three gated by the same `protected-config-write-guard`. Extends the existing `hooks/adr-section-validator.sh` section-contract gate rather than replacing it.

## Status / caveats

Point-in-time staged state — the README states status "STAGED, not yet deployed" as of this writing; operators should verify current deployment by checking `hooks/adr-section-validator.sh` directly rather than assuming this doc reflects live behavior. No internal inconsistencies found.
