# Runtime Environment Flags

This is the human-readable index for public Cognitive OS runtime environment
flags. The machine-readable source is `manifests/runtime-env-flags.yaml`.

Runtime flags are operator controls for skip, disable, bypass, allow, force,
run, dry-run, mock, and opt-in behavior. Public flags should be recorded in the
manifest with owner files, documentation, default behavior, allowed values, risk
level, and whether they bypass a safety primitive.

## Current families

| Family | Purpose |
|---|---|
| `hook-suppression` | Per-session hook suppression such as `DISABLE_HOOK_*`. |
| `llm-dispatch` | Provider routing and fallback controls. |
| `startup-safe-mode` | Startup circuit breaker and SessionStart suppression. |
| `test-opt-in` | Heavy, Docker, external-service, or cost-bearing test opt-ins. |
| `safety-bypass` | Explicit operator bypasses for safety primitives. |
| `optional-service` | Optional scanner, daemon, gateway, or integration enablement. |
| `watchdog-observability` | Watchdog and hot-path observability controls. |
| `secret-loading` | Controls whether local development secret files may be loaded. |

## Secret-loading flags

### `COS_SKIP_DOTENV`

`COS_SKIP_DOTENV=1` tells Qwen live-smoke paths to avoid repo-local `.env`
loading and rely only on already-exported environment variables.

Use it when an agent or automation needs to run a live smoke without indirectly
reading blocked local secret files:

```bash
COS_SKIP_DOTENV=1 ALIBABA_QWEN_API_KEY="$ALIBABA_QWEN_API_KEY" \
  bash scripts/smoke-qwen-fallback.sh
```

Default human workflow remains unchanged: without `COS_SKIP_DOTENV`, the Qwen
smoke may load project-local development credentials according to its existing
operator flow.

### `COS_ALLOW_CREDENTIAL_SAFE_ENV`

`COS_ALLOW_CREDENTIAL_SAFE_ENV=1` is an explicit approval flag for the
credential-safe script runner. Prefer the `--approve` CLI flag for one-off
runs; use the environment flag only when a wrapper cannot pass CLI arguments.

```bash
COS_ALLOW_CREDENTIAL_SAFE_ENV=1 \
  scripts/cos-credential-safe-run qwen-fallback-smoke --json
```

The runner is allowlist-only and redacts stdout/stderr before returning output
to the agent.

## Test opt-in flags

### `COS_CODEX_EXEC_MODEL`

`COS_CODEX_EXEC_MODEL` pins the model passed to `codex exec` for explicit
provider proof drills. Leave it unset for normal use. Set it only when the host
Codex CLI default model is unsupported by the installed CLI version.

```bash
COS_RUN_PROVIDER_SMOKE=1 COS_CODEX_EXEC_MODEL=gpt-5.4 \
  scripts/cos-headless-service-drill --json --keep-workspace
```

This flag does not authorize provider calls by itself. Provider execution still
requires `COS_RUN_PROVIDER_SMOKE=1`, a ready host Codex account-session probe,
and the service-control-plane approval path.

## Contract rules for new public flags

1. Add the flag to `manifests/runtime-env-flags.yaml`.
2. Link at least one owner file and one documentation file.
3. State the default and allowed values.
4. Mark the risk level.
5. Mark whether the flag bypasses a safety primitive.
6. Add or update tests for default behavior and non-default behavior.
7. Do not record secret values, tokens, or credential file contents in tests or
   documentation.
