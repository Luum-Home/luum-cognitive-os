<!-- SCOPE: both -->
# Result Management — Large Output Prevention

## Problem

Bash commands that produce large output (docker logs, test results, file listings, dependency trees) flood the context window, wasting tokens and pushing out important context.

## Automatic Protection

The `result-truncator.sh` PostToolUse hook automatically truncates Bash outputs exceeding `max_chars` (default: 5000). It preserves the first 2000 and last 1000 characters, which typically contain headers/initial context and summaries/errors respectively.

Outputs containing critical patterns (FAIL, ERROR, panic, PASS, coverage:) are preserved when the pattern would be lost by truncation.

## Agent Best Practices

### Prefer targeted commands over broad ones

| Instead of | Use |
|------------|-----|
| `cat large-file.log` | `grep "ERROR\|WARN" large-file.log` |
| `docker logs container` | `docker logs container --tail 50` |
| `find . -name "*.go"` | `find ./internal -name "*_test.go"` |
| `cat package.json` | `jq '.dependencies' package.json` |
| `ls -R` | `ls specific/directory/` |
| `yarn test` (full output) | `yarn test 2>&1 \| tail -30` |

### Use output limiters

- `head -n 50` / `tail -n 50` for log files
- `--tail N` for docker logs
- `jq` filters for JSON output
- `grep -c` for counts instead of full matches
- `wc -l` to check size before reading

### For test output

- Use `--summary` or `--reporter=dot` when checking if tests pass
- Pipe verbose output through `tail` to get just the summary
- Use `grep -A5 "FAIL\|ERROR"` to extract only failures

### For build output

- Redirect verbose output: `command 2>&1 | tail -20`
- Use `--quiet` or `--silent` flags when available
- Check exit code first: `command && echo "OK" || echo "FAILED"`

## Configuration

In `cognitive-os.yaml` under `resources.tokens.result_truncation`:

```yaml
result_truncation:
  enabled: true        # Toggle truncation on/off
  max_chars: 5000      # Truncate above this threshold
  head_chars: 2000     # Characters to keep from start
  tail_chars: 1000     # Characters to keep from end
  never_truncate_patterns:
    - "FAIL"           # Test failures
    - "ERROR"          # Error messages
    - "panic"          # Go panics
    - "PASS"           # Test passes (summary lines)
    - "coverage:"      # Coverage reports
```

## Large File Reading

Files exceeding ~40KB (~10K tokens) will trigger the Read tool's token limit error. The `large-file-advisor.sh` PreToolUse hook detects these reads before they happen and outputs an advisory.

### Automatic Protection

The `large-file-advisor.sh` hook fires on every Read tool use:
- Checks the target file size before the Read executes
- If file > 40KB: outputs an advisory with file size, line count, and section hints
- If offset/limit already provided: silently skips (user is handling pagination)
- Advisory only (exit 0) — never blocks reads
- Logs to `.cognitive-os/metrics/large-file-reads.jsonl`

### SmartReader Library

`lib/smart_reader.py` provides programmatic auto-pagination for agents and skills:

```python
from lib.smart_reader import SmartReader

reader = SmartReader()

# Auto-paginate: returns head+tail with truncation notice if too large
result = reader.read_file("path/to/large_file.py")

# Read a specific section by pattern (class name, function name, header)
result = reader.read_file("path/to/file.py", target_section="class MyHandler")

# Get file metadata before reading
summary = reader.file_summary("path/to/file.py")

# Iterate in chunks for streaming processing
for chunk in reader.read_chunked("path/to/file.py"):
    process(chunk)
```

### Large Files Index

At session start, a large files index can be generated:

```python
reader = SmartReader()
reader.save_large_files_index()  # Writes .cognitive-os/large-files-index.json
```

The index lists all project files exceeding 40KB with their size, line count, and estimated token count. Agents can consult this before attempting to read large files.

### Agent Best Practices for Large Files

| Instead of | Use |
|------------|-----|
| `Read(file_path="large.py")` | `Read(file_path="large.py", offset=1, limit=200)` |
| Reading entire file to find a function | `Grep` for the function, then `Read` with offset/limit |
| Reading a 1000-line config | `Read` with limit targeting the relevant section |

### Read Tool Strategy

1. **Check size first**: Use `file_summary()` or check the large-files-index
2. **Use offset+limit**: For known line ranges, pass offset and limit to Read
3. **Use target_section**: For finding specific classes/functions/headers
4. **Use Grep first**: Find the line number, then Read with offset around it
5. **Chunked reading**: For processing entire large files, use `read_chunked()`

## Metrics

Truncation events are logged to `.cognitive-os/metrics/truncation-events.jsonl` with original size, truncated size, and the command that produced the output.

Large file read advisories are logged to `.cognitive-os/metrics/large-file-reads.jsonl` with file path, size, and estimated tokens.
