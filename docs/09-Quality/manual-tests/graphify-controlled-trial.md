# Graphify Controlled Trial Manual Test

## Purpose

Verify that Cognitive OS can use Graphify as an optional maintainer graph-indexing tool without scanning noisy local directories, mutating assistant instructions, installing hooks, or treating graph output as verification evidence.

## Preconditions

- Run from the Cognitive OS repository root.
- `.graphifyignore` exists.
- `uvx` or `graphify` is available on `PATH`.
- No Graphify git hook is installed for this test.
- No `graphify codex install` or equivalent assistant-instruction installer is run for this test.

## Procedure

1. Preview the command:

   ```bash
   scripts/cos-graphify-build lib --out /tmp/cos-graphify-manual --dry-run
   ```

2. Build a code-only graph for a bounded source slice:

   ```bash
   scripts/cos-graphify-build lib --out /tmp/cos-graphify-manual --skip-benchmark
   ```

3. Confirm the graph artifact exists:

   ```bash
   test -f /tmp/cos-graphify-manual/graphify-out/graph.json
   ```

4. Run one bounded query:

   ```bash
   graphify query "Which modules handle memory and routing?" \
     --graph /tmp/cos-graphify-manual/graphify-out/graph.json \
     --budget 1200
   ```

5. Confirm no Graphify hooks were installed:

   ```bash
   git config --get core.hooksPath || true
   grep -R "graphify-hook-start" .git/hooks 2>/dev/null || true
   ```

6. Generate a preload matrix for a bounded topic:

   ```bash
   scripts/cos-graphify-preload-matrix lib/harness_adapter/base.py --json --out /tmp/cos-graphify-manual/preload-matrix.json
   ```

7. Join the matrix with an explicit Claude Code session JSONL path:

   ```bash
   scripts/cos-graphify-run-telemetry \
     --session /path/to/claude-session.jsonl \
     --matrix-json /tmp/cos-graphify-manual/preload-matrix.json \
     --out /tmp/cos-graphify-manual/run-telemetry.md
   ```

   Use a real session path only when the operator intentionally selects that file. To intentionally scan for the latest Claude session instead, add `--latest-claude-session --project-filter <project-substring> --since-hours <hours>` and omit `--session`. Do not scan live session stores implicitly for this manual test.

## Expected Result

- The dry run prints a `graphify extract` command with `.graphifyignore` patterns applied.
- The build writes `/tmp/cos-graphify-manual/graphify-out/graph.json`.
- The bounded query returns graph context without requiring broad repository reads.
- No assistant instruction files are mutated by the procedure.
- No Graphify git hook markers are present after the procedure.
- The telemetry report labels metrics as `actual`, `estimated`, or `mixed` and does not claim causal token reduction from a single run.
- Latest-session discovery only occurs when `--latest-claude-session` is explicitly present; otherwise `--session` is required.

## Failure Handling

- If the dry-run command includes noisy roots such as `reference/`, `dashboard/`, `.venv/`, or `.git/` without an exclusion, fix `.graphifyignore` before running extraction.
- If Graphify is unavailable, install it as an operator tool with `uvx --from graphifyy graphify` or a temporary venv; do not vendor it into Cognitive OS.
- If a semantic backend is required unexpectedly during the code-only test, check whether docs/media excludes were removed or `--include-docs` was passed.
- If the telemetry report has zero actual tokens, verify that the selected session JSONL contains Claude `message.usage` fields.
