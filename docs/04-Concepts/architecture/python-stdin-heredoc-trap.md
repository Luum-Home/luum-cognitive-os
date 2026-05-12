# Python stdin heredoc trap

Do not pipe JSON or other data into `python - <<'PY'`.

```bash
# WRONG: the heredoc is Python's stdin, so the pipe is discarded.
producer --json | python3 - <<'PY'  # cos: allow-python-stdin-heredoc-example
import json, sys
payload = json.load(sys.stdin)  # reads empty input
PY
```

`python -` reads the Python program from stdin. A heredoc also supplies stdin.
When both a pipe and heredoc are present, the heredoc wins and `sys.stdin` inside
the program is not the piped data. The usual failure is:

```text
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

## Safe patterns

Use `python -c` when the JSON should arrive on stdin:

```bash
producer --json | python3 -c '
import json, sys
payload = json.load(sys.stdin)
print(payload["status"])
'
```

Use a temporary file when the Python program is easier to read as a heredoc:

```bash
tmp=$(mktemp)
producer --json > "$tmp"
python3 - "$tmp" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
print(payload["status"])
PY
rm -f "$tmp"
```

Use process substitution when the shell supports it:

```bash
python3 -c 'import json, sys; print(json.load(sys.stdin)["status"])' \
  < <(producer --json)
```

## Enforcement

`scripts/cos-python-stdin-antipattern-audit` scans tracked files for the broken
pattern and is wired into `bash scripts/cos-ci-local.sh quick` and architecture
readiness. Any future pipe into a `python -` heredoc snippet is a CI failure
unless it is an explicitly marked educational example with
`cos: allow-python-stdin-heredoc-example`.
