# Credential-Safe Script Runner Manual Test

## Purpose

Prove that a maintainer can run an allowlisted live-smoke script that needs
local env-file credentials without exposing secret values to the agent transcript
or audit artifacts.

This is a narrow exception to the general rule that agents do not touch `.env`.
The wrapper reads only allowlisted keys, forces child scripts to skip their own
`.env` loading when applicable, captures stdout/stderr, redacts secret values,
checks command integrity, starts the child with a sanitized environment, bounds
model-visible output, and writes an audit record containing key names only.

This primitive cannot make a fully privileged local agent cryptographically
unable to read files; the repository still relies on the blocked-path rule for
direct `.env` access. Its security boundary is operational: agents run only the
allowlisted wrapper command, the wrapper parses only allowlisted env-file keys,
and secret material is never returned to the transcript or audit log.

## Qwen fallback smoke

Run from the repo root:

```bash
scripts/cos-credential-safe-run qwen-fallback-smoke --approve
```

Expected:

- `scripts/smoke-qwen-fallback.sh` runs with `COS_SKIP_DOTENV=1` forced;
- the script content hash matches the pinned manifest integrity value before it
  runs;
- only `ALIBABA_QWEN_API_KEY`, `ALIBABA_QWEN_BASE_URL`, and
  `ALIBABA_QWEN_WORKSPACE_ID` are loaded from `.env`;
- parent-process secrets that are not allowlisted are not passed to the child
  process;
- stdout/stderr shown to the agent are redacted;
- `.cognitive-os/metrics/credential-safe-runs.jsonl` records command metadata,
  command hash, loaded key names, return code, and redaction count, not secret
  values.

## JSON mode

```bash
scripts/cos-credential-safe-run qwen-fallback-smoke --approve --json
```

Expected JSON fields include:

- `script_id`
- `returncode`
- `loaded_keys`
- `redaction_count`
- `audit_path`
- redacted `stdout` and `stderr`

## Non-goals

- The runner is not a general shell.
- The runner does not allow arbitrary commands.
- The runner does not allow arbitrary env keys from `.env`.
- The runner does not allow arbitrary env files; `qwen-fallback-smoke` accepts
  only repo-root `.env`.
- The runner does not make provider calls safe for unattended automation; human
  approval is still required.
