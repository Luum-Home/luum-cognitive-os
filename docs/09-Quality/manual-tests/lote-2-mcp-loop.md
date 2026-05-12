# Manual Test Checklist: Lote 2 — MCP Auto-Install Loop

Tests the end-to-end MCP registration introduced in PR lote-2.
Verifies `install.sh --install-deps`, `scripts/register-mcps.sh`, and
`scripts/cos-update.sh` all close the loop declared in `manifests/dependencies.yaml`.

Run these steps in order. Each step has expected output and pass/fail criteria.

---

## Step 1 — Fresh install registers MCPs

**Purpose**: Verify `install.sh --install-deps` calls `register-mcps.sh` and
MCPs declared in the manifest appear in `claude mcp list`.

**Pre-conditions**: `claude` CLI is on PATH (`which claude` returns a path).

**Commands**:
```bash
# 1a. Back up your real settings BEFORE running (restore if needed)
cp ~/.claude/settings.json ~/.claude/settings.json.bak 2>/dev/null || true

# 1b. Remove existing MCPs so the test starts clean
#     WARNING: this deletes your registered MCPs — restore from backup after.
rm -f ~/.claude/settings.json

# 1c. Run the installer from the repo root with --install-deps
bash install.sh --from . --force --install-deps

# 1d. Check that the manifest's MCPs are now registered
claude mcp list
```

**Expected output**:
- `install.sh` output includes `"Installing dependencies (--install-deps)..."` and
  `"MCP registration: OK"` (or a WARN if `claude` CLI is absent, which is acceptable).
- `claude mcp list` shows at least `engram` (listed under `default` profile in the manifest).

**Pass criteria**:
- [ ] `claude mcp list` output contains `engram`
- [ ] No `ERROR:` lines in install.sh stderr

**Fail criteria**:
- `claude mcp list` shows no entries
- `install.sh` exits with code 1

---

## Step 2 — cos-update picks up a new MCP entry

**Purpose**: Verify that adding a new MCP entry to `manifests/dependencies.yaml`
and running `cos-update.sh` registers the new MCP.

**Pre-conditions**: Step 1 completed. `claude` CLI is on PATH.

**Commands**:
```bash
# 2a. Add a test MCP entry to the manifest (do NOT commit this)
cat >> manifests/dependencies.yaml <<'EOF'

  - name: test-mcp-manual
    criticality: optional
    transport: stdio
    command: echo
    args: ["test-mcp-stub"]
    register_to: ~/.claude/settings.json
EOF

# 2b. Also add it to the 'default' profile's mcp_servers_recommended
#     (edit manifests/dependencies.yaml and add 'test-mcp-manual' to the list)
#     Then run:
bash scripts/cos-update.sh --no-verify

# 2c. Verify
claude mcp list
```

**Expected output**:
- `cos-update.sh` stderr includes `"registering 'test-mcp-manual' via claude mcp add"` or
  `"registering 'test-mcp-manual' via settings.json"`.
- `claude mcp list` shows `test-mcp-manual`.

**Pass criteria**:
- [ ] `claude mcp list` contains `test-mcp-manual`
- [ ] `cos-update.sh` exits 0

**Cleanup**:
```bash
git checkout manifests/dependencies.yaml
claude mcp remove test-mcp-manual 2>/dev/null || true
```

---

## Step 3 — Second run is a no-op (SHA cache)

**Purpose**: Verify the SHA cache prevents redundant re-registration.

**Pre-conditions**: Step 1 or Step 2 completed. The manifest is in its committed state.

**Commands**:
```bash
# 3a. Run cos-update.sh twice in a row
bash scripts/cos-update.sh --no-verify 2>&1 | grep -E "mcps|MCP|Already"
bash scripts/cos-update.sh --no-verify 2>&1 | grep -E "mcps|MCP|Already"
```

**Expected output** (second run):
```
manifest unchanged (sha XXXXXXXX); mcps registration skipped
```
or
```
Already up to date. No changes applied.
```

**Pass criteria**:
- [ ] Second run stderr/stdout contains `"unchanged"` or `"skipped"` for MCPs
- [ ] `claude mcp add` is NOT called on the second run (no new entries in
      `~/.claude/settings.json` compared to after first run)

---

## Step 4 — Graceful degradation when claude CLI is absent

**Purpose**: Verify the script warns and exits 0 (does not abort) when `claude`
is not on PATH.

**Pre-conditions**: Any state. `jq` may or may not be installed.

**Commands**:
```bash
# 4a. Delete SHA cache so the script does NOT short-circuit
rm -f .cognitive-os/state/mcps.sha

# 4b. Run with a stripped PATH (no claude)
PATH=/usr/bin:/bin bash scripts/register-mcps.sh --profile default 2>&1
echo "Exit code: $?"
```

**Expected output**:
- One or more lines containing `"registering '...' via settings.json (no claude CLI)"`
  OR `"WARN:"` about missing claude, depending on whether `~/.claude/` exists.
- Exit code: `0`

**Pass criteria**:
- [ ] Script exits with code `0`
- [ ] No unhandled errors (no Python tracebacks without a `WARN:` prefix)
- [ ] Either `~/.claude/settings.json` is created/updated with `mcpServers`,
      OR a WARN is emitted explaining why registration was skipped
