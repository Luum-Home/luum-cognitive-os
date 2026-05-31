# Publication Safety Receipt v0

## Purpose

`publication-safety-receipt/v0` is the portable Cognitive OS receipt for a consumer repository's public-release safety gates.

Cognitive OS owns the runner, status normalization, and receipt shape. The consumer repository owns the actual commands, allowlists, scanner policy, and publication decision evidence.

## Config

Default location:

```text
manifests/publication-safety.yaml
```

Schema:

```yaml
schema_version: publication-safety-config/v0
enabled: true
mode: strict
default_timeout_seconds: 300
commands:
  - id: pre_publication_gate
    run: scripts/pre-publication-gate
    required: true
  - id: public_readiness
    command: ["python3", "scripts/public-readiness-audit.py", "--json"]
    required: true
```

`run` strings are parsed with `shlex.split`; Cognitive OS does not use `shell=True` for configured gates. Prefer `command: [...]` when arguments contain spaces.

## Receipt fields

Required top-level fields:

- `schema_version`: always `publication-safety-receipt/v0`.
- `generated_at`: UTC timestamp.
- `project_dir`: absolute project path evaluated.
- `config`: config path used.
- `status`: `pass`, `warn`, `fail`, or `skipped`.
- `summary`: counts and IDs for required failures and warnings.
- `steps`: one entry per configured command.
- `claim.public_release_ready`: true only when all required gates pass and no warning is promoted by strict CLI usage.
- `raw_output_policy`: documents that stdout/stderr are represented by hashes by default.

Each step records:

- `id`;
- `status`;
- `required`;
- `exit_code`;
- `timed_out`;
- `duration_ms`;
- `cwd`;
- `argv`;
- stdout/stderr byte counts and SHA-256 hashes;
- optional parsed payload status/schema when command stdout contains JSON.

Raw stdout/stderr are not persisted unless the operator uses `--write-step-logs` for local diagnostics.

## Status rules

- Required command exits non-zero: step `fail`.
- Optional command exits non-zero: step `warn`.
- Command exits zero and emits JSON status/result/decision of `pass`, `ok`, `success`, or `skipped`: step `pass`.
- Command exits zero and emits JSON `warn`: step `warn`.
- Command exits zero and emits JSON `fail`, `block`, `blocked`, or `error`: required step `fail`, optional step `warn`.
- No commands with `enabled: false`: receipt `skipped`.

Aggregate status is `fail` if any required step fails, else `warn` if any step warns, else `pass`; no steps yields `skipped`.

## Security boundary

The primitive must not hardcode project-specific paths, repo names, env variable names, trademark rules, or language allowlists. Those remain in consumer-owned gates. Cognitive OS may only invoke declared commands and normalize evidence.

## Verification

```bash
python3 -m pytest tests/unit/test_publication_safety.py tests/behavior/test_publication_safety_cli.py tests/contracts/test_publication_safety_contract.py -q
bash -n hooks/publication-safety.sh
scripts/cos publication safety --allow-missing-config --json
```
