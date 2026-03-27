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

## Metrics

Truncation events are logged to `.cognitive-os/metrics/truncation-events.jsonl` with original size, truncated size, and the command that produced the output.
