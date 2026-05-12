# Dependency Adoption Evidence — Rust Script Exposure Audit Slice — 2026-05-12

## Scope

Adopt a minimal Rust workspace for the first migration candidate: a read-only ADR-283 script exposure diagnostic named `cos-script-exposure-audit-rs`.

Dependency manifests staged in this slice:

- `Cargo.toml`
- `Cargo.lock`
- `crates/cos-script-exposure-audit-rs/Cargo.toml`

## Imported Dependencies

Runtime dependencies:

- `anyhow` — error context for CLI/library failures.
- `clap` with `derive` — CLI argument parsing compatible with the Python command shape.
- `json` — JSON parse/render without bringing in `serde_json`/`ryu`.
- `yaml-rust2` — YAML dispositions manifest parsing.

Development dependency:

- `assert_cmd` — integration-style CLI assertions for Rust parity tests.

## License Posture

Local `cargo metadata` check over the staged workspace reported 45 packages and no licenses matching the blocked strings `AGPL`, `SSPL`, `BSL`, `ELv2`, or `BUSL`.

Command:

```bash
cargo metadata --format-version=1 > /tmp/cos_cargo_metadata_full.json
python3 - <<'PY'
import json
m=json.load(open('/tmp/cos_cargo_metadata_full.json'))
blocked=[]
for p in m['packages']:
    lic=(p.get('license') or '').upper()
    if any(x in lic for x in ['AGPL','SSPL','BSL','ELV2','BUSL']):
        blocked.append((p['name'], p.get('license')))
print('packages', len(m['packages']))
print('blocked_licenses', blocked)
PY
```

Observed result:

```text
packages 45
blocked_licenses []
```

Implementation note: the first draft used `serde_json`, which introduced `ryu` with `Apache-2.0 OR BSL-1.0`. To keep the dependency set clear of the repository's literal `BSL` blocklist, the slice was rewritten to use the `json` crate instead.

## Closure Contract

| ADR-208 field | Evidence |
|---|---|
| Imported source and license posture | Rust crates listed above; local metadata license check passed. |
| COS target primitive | ADR-283 script exposure diagnostic. |
| Producer | `crates/cos-script-exposure-audit-rs/src/lib.rs` and `src/main.rs`. |
| Consumer | Rust parity tests plus optional operator invocation via `cargo run -p cos-script-exposure-audit-rs -- ...`. |
| Scheduler or trigger | Manual/CI candidate only; Python CLI remains production default. |
| Evaluator/reward signal | Fixture parity against existing Python report shape and existing Python unit/behavior test preservation. |
| Lifecycle owner | Rust migration Wave 1 diagnostic slice. |
| Contract tests | `cargo test -p cos-script-exposure-audit-rs`; Python fixture parity command; existing Python script exposure tests. |
| Demotion path | Remove the Rust crate and keep `scripts/cos-script-exposure-audit` as the authoritative implementation if parity or maintenance cost regresses. |

## Validation Evidence

Executed locally:

```bash
cargo test -p cos-script-exposure-audit-rs
cargo clippy -p cos-script-exposure-audit-rs -- -D warnings
python3 -m pytest tests/unit/test_script_exposure_audit.py tests/behavior/test_script_exposure_audit_cli.py -q
```

Observed results:

- Rust tests: 3 passed.
- Rust clippy: passed with `-D warnings`.
- Existing Python tests: 13 passed.
- Python/Rust fixture parity: passed with and without dispositions.

## Adoption Decision

Adopt as a **parity candidate**, not as the production/default command. This keeps the Rust migration incremental and reversible while proving the first deterministic diagnostic scanner boundary.
