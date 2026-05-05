# Runtime Environment Flags

This is the human-readable index for public Cognitive OS runtime environment
flags. The machine-readable source is `manifests/runtime-env-flags.yaml`.

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


### `COS_CLAUDE_EXEC_MODEL` and `COS_CLAUDE_BIN`

`COS_CLAUDE_EXEC_MODEL` pins the model passed to `claude -p` for explicit
Claude provider proof drills. `COS_CLAUDE_BIN` can point to a trusted Claude
Code executable when Claude is installed outside the process `PATH`.

```bash
COS_CLAUDE_EXEC_MODEL=sonnet scripts/cos-worker-run-once \
  --project-dir /tmp/cos-claude-provider.<id> \
  --worker-id host-claude-proof \
  --allow-provider-call \
  --json
```

These flags do not authorize provider calls by themselves. Provider execution
still requires a submitted provider task, `--allow-provider-call`, and a ready
`claude auth status` account-session probe.
