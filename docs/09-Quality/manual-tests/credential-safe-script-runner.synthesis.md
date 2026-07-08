---
type: quality-synthesis
source: docs/09-Quality/manual-tests/credential-safe-script-runner.md
provenance: "Manual test proving a maintainer can run an allowlisted live-smoke script needing .env credentials without exposing secret values to the agent transcript or audit artifacts."
---

## What it is
A manual test for the credential-safe script runner (`scripts/cos-credential-safe-run`), a narrow, deliberately scoped exception to the general "agents never touch `.env`" rule. It lets an allowlisted script consume specific `.env` keys while keeping secret values out of the model-visible transcript and audit log.

## Key mechanics
- Security model is **operational, not cryptographic**: the wrapper parses only allowlisted env-file keys, forces child scripts to skip their own `.env` loading (`COS_SKIP_DOTENV=1`), verifies command integrity against a pinned content-hash manifest, starts the child with a sanitized environment, redacts secret values from captured stdout/stderr, bounds model-visible output, and writes an audit record with key *names* only (never values).
- Example: `scripts/cos-credential-safe-run qwen-fallback-smoke --approve` runs `scripts/smoke-qwen-fallback.sh`, loading only `ALIBABA_QWEN_API_KEY`, `ALIBABA_QWEN_BASE_URL`, `ALIBABA_QWEN_WORKSPACE_ID`; non-allowlisted parent-process secrets are never passed through.
- JSON mode (`--json`) surfaces `script_id`, `returncode`, `loaded_keys`, `redaction_count`, `audit_path`, and redacted `stdout`/`stderr`.
- Audit trail: `.cognitive-os/metrics/credential-safe-runs.jsonl` records command metadata, command hash, loaded key names, return code, redaction count — never secret values.

## Relations & where used
Referenced by rules/rate-limiting-adjacent security posture (credential-management, blocked-path rule for `.env`). It is explicitly a bounded exception to that broader rule, not a replacement — a fully privileged local agent could still theoretically read files directly, so the boundary is "agents only run the allowlisted wrapper command," not filesystem-level enforcement.

## Status / caveats
Explicitly enumerates non-goals: not a general shell, no arbitrary commands, no arbitrary env keys, no arbitrary env files (only repo-root `.env` for `qwen-fallback-smoke`), and does not make provider calls safe for unattended automation — human `--approve` is still required. No dated run log; procedural spec only.
