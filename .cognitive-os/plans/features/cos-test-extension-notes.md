# cos-test extension reconnaissance (Batch 3, T3.1)

## Module layout
- Module: `luum-agent-os/cmd/cos-test` (own go.mod, go 1.22). Built with `go build .` from `cmd/cos-test/`.
- Packages: `internal/cli`, `internal/config`, `internal/runner`, `internal/ui`. New batch-3 packages: `internal/banner`, `internal/lanes`.
- Entry: `main.go` -> `cli.Execute()`.

## Cobra registration pattern
- Each subcommand file declares a package-scoped `var fooCmd = &cobra.Command{...}` and calls `rootCmd.AddCommand(fooCmd)` inside an `init()` function. Per-command flags are bound on the same `fooCmd.Flags()`.
- Persistent flags (`--ci`, `--verbose`, `--no-color`) live in `root.go` `init()`.
- `rootCmd` exported (lowercase) only inside the package; `cli.Execute()` is the external entry.
- Pattern to add new commands: new file under `internal/cli/` with `init()` registering on `rootCmd`.

## Runner package
- `runner.PytestRunner` (NewPytestRunner(cfg)) builds args via `BuildArgs(rc)` and runs via `Run(rc, eventsChan)` (streamed) or `RunSync(rc)` (blocking, stdout passthrough).
- `runner.RunConfig` fields: Categories, Filter, Verbose, ExtraArgs, ReportPath. ExtraArgs is the extension hook for new flags (`-n auto`, `-m "x"`, `--testmon`, etc.).
- Pytest invocation: `python -m pytest ...args`, cwd = config.ProjectRoot, env adds PYTHONDONTWRITEBYTECODE=1.
- JSON report is written to `tests/.report.json` and parsed by `ParseJSONReport`.

## Config package
- `config.DefaultConfig()` walks up to find a `tests/` dir; sets ProjectRoot, TestsDir, HooksDir, etc.
- Categories enum: unit/behavior/integration/system/e2e. Batch 3 lanes are a SUPERSET (audit, contract, hooks, chaos) — we do NOT extend this enum; lane info comes from `.cognitive-os/test-lanes.yaml` via `internal/lanes`.

## Test invocation conventions
- All pytest commands run via `python -m pytest`, never the `pytest` binary directly. Reuse this in batch 3.
- Args are passed as flat string slice. To build complex invocations (e.g. parallel + serial split for `parallel: marker` lanes), construct two `RunConfig`s with different `ExtraArgs` and call `RunSync` twice; aggregate exit codes.
- Wrapping `scripts/pytest-with-summary.sh` is reserved for a later batch (T4.x). Batch 3 calls pytest directly through the existing Runner.

## File structure conventions
- One subcommand per file in `internal/cli/`.
- Tests next to source: `*_test.go` in same package. No external test framework; stdlib `testing` only.
- `go fmt` and `go vet` clean. Existing code uses tabs (gofmt default), one statement per line.

## Lane registry (consumed in batch 3)
- `.cognitive-os/test-lanes.yaml` (8 lanes registered today: unit, audit, contract, integration, behavior, hooks, e2e, chaos). Schema:
  - `paths: [string,...]`
  - `parallel: true | false | marker` (string)
  - `marker_serial: <name>` (only when parallel == "marker")
  - `stateful_reason: <text>`
- We parse a minimal subset by hand-rolled scanner (no external YAML dep) to keep the module dependency-free; design §1 already endorses the bash-side avoidance, and Go-side we accept a tiny self-contained parser for the same reason.

## Inventory history (for ETA aggregator)
- Per-run dir: `.cognitive-os/reports/test-runs/<UTC-ts>-<args-slug>/`.
- `metadata.txt` contains `args=...` line; we match a lane name token in the slug or args to attribute a run to a lane.
- Wall-time NOT in metadata.txt or inventory.md today. Best-effort aggregator approximates duration as (max file mtime in dir - dir mtime). When unavailable or zero matches, banner prints "ETA: unknown (no history)".

## Hard-rule confirmations
- Do NOT modify `run.go`, `pytest-with-summary.sh`, `tests/conftest.py`, `pytest.ini`, `Makefile`.
- Reuse `runner.PytestRunner` via `ExtraArgs`; do NOT duplicate exec logic.
- All new code under `internal/cli/`, `internal/banner/`, `internal/lanes/`.
