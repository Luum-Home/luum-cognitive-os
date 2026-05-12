# Phase 5.3 — Review Subcommand: Implementation Notes

## Subcommand Routing Design

`cmd/cos-dispatch/main.go` inspects `os.Args[1:]` before parsing any flags:

```
os.Args[1] == "review"  →  runReview(args[2:])
anything else           →  runDispatch(fs, flags)   # default stdin path
```

The branch is a single `if` statement with a string equality check.  No third-party router library (cobra, urfave/cli) was introduced — `flag.NewFlagSet` scoped per subcommand is sufficient for the current surface area.

## Backwards Compatibility Preserved

The contract from ADR-008 is satisfied in full:

1. `cos-dispatch` (no args) → dispatch
2. `cos-dispatch -flag` → dispatch (first arg starts with `-`, never reaches the `"review"` branch)
3. `cos-dispatch review` → subcommand

The existing E2E tests in `main_test.go` continue to pass unchanged.  Two new backward-compat tests (`TestReview_BackwardsCompat_StdinDispatchStillWorks`, `TestReview_FlagOnly_StdinDispatch`) execute the compiled binary with stdin payloads and assert valid JSON on stdout.

## Dispatch Logic Extraction

`dispatch.go` contains `runDispatch` (extracted from the original `main.go`) and `registerDispatchFlags`.  `main.go` is now a 30-line router.  The extraction is purely structural — no behavior changed.

## Review Subcommand Flags

| Flag | Effect |
|------|--------|
| `--list` | Default action; print table of pending artifacts |
| `--all` | Include already-reviewed artifacts in `--list` |
| `--enable NAME` | `enabled=1`, `feedback='enabled'` |
| `--disable NAME` | `enabled=0`, `feedback='disabled'` |
| `--delete NAME` | Remove `.go` file; DB row kept with `feedback='deleted'` |
| `--modify NAME` | Open in `$EDITOR` (fallback: `vi`); on editor exit 0 set `feedback='modified'` |
| `--db PATH` | Override DB path |
| `--output-dir PATH` | Override output directory for file ops |

## Editor Modify Flow

`--modify` opens `$EDITOR filePath` with stdin/stdout/stderr inherited from the process so interactive terminals work.  If the editor exits non-zero the feedback update is **skipped** (not an error): this allows the user to abort an edit without changing the artifact state.

## Generator Wire-Up in Dispatch Path

`dispatch.go` constructs an `SQLGenerator` alongside `SQLTracker` when `cfg.Patterns.AutoGenerate.Enabled` is true.  The generator is passed to the dispatcher via the new `dispatcher.WithGenerator` option.

`dispatcher.go` tracks a `dispatchCount` (atomic int64) and calls `maybeRunGenerator()` after every `Dispatch` call.  The trigger fires every N dispatches where N defaults to 100 (configurable via `cfg.Patterns.AnalysisInterval`).  The Analyze+Generate cycle runs in a goroutine so the response path is never blocked.

## source_pattern_id Resolution (Phase 5.2 Known Limitation)

Phase 5.2 left `source_pattern_id = NULL` in all `generated_artifacts` rows because `DetectedPattern` carries no persisted row ID.  Phase 5.3 does not change this (the scope guard prohibits touching `internal/pattern/*`).  The limitation is acknowledged; full resolution requires persisting `DetectedPattern` rows before calling `Generate` and passing the resulting IDs back.  This is tracked for Phase 5.5.

## Test Coverage (ADR-010 Compliance)

Eight binary-level tests in `review_test.go`:

| Test | ADR-010 Layer | What is verified |
|------|---------------|-----------------|
| `TestReview_ListEmpty` | Binary | exit 0, stdout contains "no artifacts" |
| `TestReview_ListWithArtifacts` | Binary | both names in stdout |
| `TestReview_EnableSuccess` | Binary | DB `enabled=1`, `feedback='enabled'` |
| `TestReview_DisableSuccess` | Binary | DB `enabled=0`, `feedback='disabled'` |
| `TestReview_DeleteRemovesFile` | Binary | file gone, DB row with `feedback='deleted'` |
| `TestReview_EnableNotFound` | Binary (negative) | exit 1, "not found" in output |
| `TestReview_BackwardsCompat_StdinDispatchStillWorks` | Binary (regression) | stdin dispatch → valid JSON |
| `TestReview_FlagOnly_StdinDispatch` | Binary (regression) | flag-only → dispatch path |

All tests use real SQLite temp files (`t.TempDir()`) and verify observable state, not return values alone.
