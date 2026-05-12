# ADR-274 — adr-section-validator extension staging

**Status**: STAGED, not yet deployed to `hooks/adr-section-validator.sh`.

The change to `hooks/adr-section-validator.sh` is protected by
`protected-config-write-guard` (control-plane path). Agent-side direct edits
are intentionally blocked. The operator must apply this extension manually
after review, similar to ADR-273 Slice C hooks.

## What this extension adds

A new check `require_operational_guide` that fires when an ADR has:

- `tier: maintainer` in frontmatter
- `status: accepted` (or `implemented`)
- `implementation_files:` block with ≥1 entry
- Not a tombstone (filename or status)
- Not superseded
- No `<!-- adr-274-exempt: <reason> -->` marker

When triggered, the check requires:

1. A `## Operational Guide` section header
2. At least 3 of the 5 documented sub-sections:
   - `### What changes for the operator`
   - `### What this answers` (or "What the … answers")
   - `### Daily operational pattern`
   - `### When sources disagree` (or "When surface disagree")
   - `### Reading guide for cold readers`
   - (alias accepted: `### Anti-confusion`)

Behavior: WARN to stderr (exit 0) by default; exit 2 (block) under
`COS_STRICT_ADR_VALIDATION=1`, matching the existing section-contract gate.

## How to deploy

The operator should:

1. Review the unified diff in `adr-section-validator.patch` in this dir.
2. Set `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` for the deployment session.
3. Apply the patch:
   ```bash
   cd "$CLAUDE_PROJECT_DIR"
   git apply docs/05-Methodology/runbooks/adr-274-validator-extension-staging/adr-section-validator.patch
   ```
4. Run the portability test:
   ```bash
   python3 -m pytest tests/red_team/portability/test_cos-operational-guide-audit.py -q
   ```
5. Spot-check on a known-bad ADR (ADR-272 or similar in the backfill list):
   ```bash
   printf '{"tool_input":{"file_path":"docs/02-Decisions/adrs/ADR-272-...md"}}' \
     | bash hooks/adr-section-validator.sh
   ```
   Expect: a WARNING line on stderr mentioning "Operational Guide".
6. Spot-check on ADR-273 (compliant):
   ```bash
   printf '{"tool_input":{"file_path":"docs/02-Decisions/adrs/ADR-273-pending-truth-ledger-and-bilateral-verification.md"}}' \
     | bash hooks/adr-section-validator.sh
   ```
   Expect: silent exit 0 (no warning).

## Why staged here, not in hooks/

Per ADR-117 + protected-config-write-guard, agents cannot directly modify
`hooks/*.sh` files. This is the same staging discipline used by ADR-273
Slice C hooks (`docs/05-Methodology/runbooks/adr-273-slice-c-staging/`). The audit script
(`scripts/cos-operational-guide-audit.py`) is already shipped and operational;
the gate extension is the second half of the ADR-274 contract enforcement.

## Rollback

Revert the patch:
```bash
git apply -R docs/05-Methodology/runbooks/adr-274-validator-extension-staging/adr-section-validator.patch
```
