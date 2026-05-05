# Proof Drill Opt-In Run — 2026-05-05

## Goal

Run the provider smoke and Docker/headless proof drills that are explicitly
classified as opt-in in `manifests/proof-drill-registry.yaml`.

## Commands and results

| Command | Exit | Result |
|---|---:|---|
| `bash scripts/smoke-qwen-fallback.sh` | 0 | Passed all 4 checks: provider reachability, `qwen_provider.call()`, orchestrator helper, and cascade kill-switch. |
| `bash scripts/smoke-multi-provider-fallback.sh` | 0 | Passed for configured Qwen provider; OpenRouter, Gemini, Ollama, OpenAI, DeepSeek, and Claude SDK skipped as unconfigured. |
| `scripts/cos-headless-service-drill --json` | 0 | Docker worker self-test passed; local-command task completed; provider smoke intentionally skipped. |
| `COS_RUN_PROVIDER_SMOKE=1 scripts/cos-headless-service-drill --json --keep-workspace` | 0 | Local Docker task completed, but Codex provider subtask failed because host Codex defaulted to `gpt-5.5`, which this installed CLI rejected as requiring an upgrade. |
| `codex exec -m gpt-5.4 --json --sandbox read-only --skip-git-repo-check 'Reply exactly: COS_PROVIDER_SMOKE_OK'` | 0 | Direct host Codex provider smoke passed with explicit model override. |
| `COS_RUN_PROVIDER_SMOKE=1 COS_CODEX_EXEC_MODEL=gpt-5.4 scripts/cos-headless-service-drill --json --keep-workspace` | 0 | Full Docker/headless + host Codex provider proof passed. |

## Evidence

Final successful kept workspace:

`/tmp/cos-headless-service.Ul85fJ`

Final successful provider artifact:

`/tmp/cos-headless-service.Ul85fJ/.cognitive-os/service/artifacts/task-headless-codex-provider-drill/lease-4e02aee4c48d`

Final successful local task artifact:

`/tmp/cos-headless-service.Ul85fJ/.cognitive-os/service/artifacts/task-headless-service-drill/lease-4f37eb572009`

Local task result:

```text
service-ok
```

Provider task result summary:

```json
{
  "status": "completed",
  "returncode": 0,
  "provider_calls": 1,
  "command_shape": [
    "codex",
    "exec",
    "--json",
    "--sandbox",
    "read-only",
    "--skip-git-repo-check",
    "--model",
    "gpt-5.4",
    "<prompt>"
  ],
  "redactions": 0
}
```

Provider stdout contained the expected agent message:

```text
COS_PROVIDER_SMOKE_OK
```

## Fix applied during the proof

The first full provider drill exposed a host-version/model mismatch: the host
Codex CLI was authenticated, but its default model selection attempted `gpt-5.5`
and failed with an invalid-request error requiring a newer Codex version.

The service-control-plane host adapter now honors `COS_CODEX_EXEC_MODEL` for
opt-in Codex provider smokes. The headless drill help text documents this flag.

## Automated validation

```bash
python3 -m pytest tests/unit/test_service_control_plane_local_queue.py tests/contracts/test_proof_drill_registry.py -q
# 15 passed

python3 -m pytest tests/integration/test_headless_service_drill.py -q
# 1 skipped; Docker proof remains opt-in/manual unless its explicit integration gate is enabled
```

## What this proves

- Qwen live fallback is configured and working in this host environment.
- Multi-provider fallback handles configured providers and skips unconfigured
  providers cleanly.
- Docker/headless service worker can self-test, submit a local task, process it,
  drain the queue, and keep artifact bundles.
- Host Codex account-session probing works without exposing credential stores.
- Host Codex provider execution can be invoked through the SO control-plane
  adapter when explicitly opted in and pinned to a supported model.

## What this does not prove

- Claude CLI account-session support on this host; `claude` was not found on
  `PATH` during the proof.
- Codex or Claude account sessions inside Docker; both were unsupported by
  design because credential stores are not mounted.
- Remote ingress, Kubernetes, VM, or hosted worker paths.
- Provider support for unconfigured providers skipped by the multi-provider
  smoke.
