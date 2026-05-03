# ADR-122 — Preflight Gate Refinements

<!-- SCOPE: OS -->

**Status**: Accepted — 2026-05-02
**Date**: 2026-05-02
**Author**: Matias Nahuel Améndola (operator)
**Related**: ADR-116 (multi-session coordination primitives), ADR-109 (validation capsule worktree isolation), ADR-121 (foundation hardening program)

## Status

Accepted (2026-05-02). Refines the ADR-116 preflight gate (`scripts/cos_work_inventory.py --strict` invoked by `hooks/agent-prelaunch.sh`) to eliminate four classes of false positives that trained operators and agents to seek bypasses.

## Context

The ADR-116 preflight gate blocked Agent launches with a coarse policy: any dirty linked worktree produced a `BLOCK` regardless of context. Four false-positive classes were identified:

1. **Validation capsule paths** — ephemeral worktrees in `cos-validation-capsules/` and `TMPDIR`-rooted paths are transient and self-cleaning. Blocking on them is noise.
2. **Self-collision race detection** — when the same physical worktree appeared in both `collect_worktrees()` and `collect_worktrees_direct()` (e.g., via symlink), the dedup logic counted it twice on the same branch and raised a spurious `multi-worktree-same-branch` race risk.
3. **Same-severity for all branches** — a dirty worktree on a completely unrelated branch has a much lower collision risk than one on the current branch. Hardcoding `BLOCK` for all dirty linked worktrees over-signals.
4. **Read-only sub-agents** — `Explore`, `Plan`, `Code Reviewer`, and `Security Engineer` agents are structurally read-only. Blocking them on dirty linked worktrees prevents safe exploratory work.

## Decision

Four surgical refinements layered on top of the existing ADR-116 pipeline. A single kill-switch `COS_PREFLIGHT_STRICT=1` restores pre-refinement conservative behavior without reverting code.

### Refinement 1 — Ephemeral path filter

**Constant**: `EPHEMERAL_PATH_PATTERNS: tuple[str, ...]` in `scripts/cos_work_inventory.py`.

**Patterns** (v1, hardcoded; v2 may read from `cognitive-os.yaml`):
- `*/cos-validation-capsules/*`
- `*/luum-agent-os-validation-*`
- Any path that is a child of resolved `$TMPDIR`

Applied in both `collect_worktrees()` and `collect_worktrees_direct()` via `skip_ephemeral: bool = True` keyword argument. The kill-switch passes `skip_ephemeral=False`.

### Refinement 2 — Dedup race detection

In `collect_race_risks()`, the `branch_to_worktrees` dict is now keyed by `_canonical_path()` (via `os.path.realpath()`) before counting worktrees per branch. A path seen twice under different names (symlink vs. real path) is counted once.

**Helper**: `_canonical_path(path: str | Path) -> str`

### Refinement 3 — Branch-aware severity

**Helper**: `_classify_worktree_finding(worktree, current_branch, current_path, allow_read_only) -> "BLOCK" | "WARN"`

Rules (applied in order):
1. `allow_read_only=True` → `WARN`
2. Worktree branch matches current branch (including detached HEAD identity `detached@<sha12>`) → `BLOCK`
3. Worktree path is under `current_path` (sub-path) → `BLOCK`
4. Otherwise → `WARN`

Replaces the hardcoded `"BLOCK"` at `build_findings()` line ~928.

**Detached HEAD identity**: `f"detached@{head[:12]}"` — two detached worktrees at the same SHA are treated as the same logical state.

### Refinement 4 — Read-only sub-agent recognition

**CLI flag**: `--allow-read-only` added to `build_parser()`. Passed through `collect_inventory()` → `build_findings()` → `_classify_worktree_finding()`.

**Hook detection** (`hooks/agent-prelaunch.sh`): after the Agent tool check, parse `subagent_type` from stdin via `jq`. Whitelist: `Explore`, `Plan`, `Code Reviewer`, `Security Engineer`. Also grep `$DESCRIPTION` for `READ_ONLY: true`. Set `ALLOW_RO_ARG=--allow-read-only` when matched. Append to inventory invocation.

**Read-only whitelist** (exact strings):
- `Explore`
- `Plan`
- `Code Reviewer`
- `Security Engineer`

### Kill-switch

`COS_PREFLIGHT_STRICT=1` (environment variable):
- Logged to STDERR (stdout carries JSON payload)
- Forces `args.allow_read_only = False`
- Passes `skip_ephemeral=False` to both `collect_worktrees*` functions
- Sets `args._preflight_strict_override = True` (internal sentinel)

## Consequences

**Benefits**:
- Validation capsule WIP no longer triggers BLOCK
- Self-collision race risk no longer reported for single physical worktree
- Read-only Explore/Plan agents launch successfully when other-branch worktrees are dirty
- Legitimate BLOCK cases (same-branch dirty WIP) preserved

**Risks**:
- Over-permissive read-only marker abuse — mitigated by whitelist (not arbitrary strings)
- Validation capsule pattern drift — mitigated by `EPHEMERAL_PATH_PATTERNS` constant (single source of truth)
- Detached HEAD misclassification — covered by tests; detached with unknown current identity defaults to WARN (safe)

**Rollback**: set `COS_PREFLIGHT_STRICT=1` globally (env or `cognitive-os.yaml`). Full revert: `git revert` the ADR-122 commit.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Filter in `build_findings` instead of `collect_worktrees*` | Wastes IO (dirty-state collected for paths that would be discarded) |
| Per-refinement kill-switch flags | One switch is simpler to document and reason about |
| Tool-grant introspection for read-only detection | Requires mocking tool grants; whitelisted subagent_type is parseable |
| `EPHEMERAL_PATH_PATTERNS` from `cognitive-os.yaml` | Deferred to v2; hardcoded is testable and sufficient for v1 |

## Verification

```bash
# Criterion 1: --allow-read-only appears in --help
python3 scripts/cos_work_inventory.py --help | grep allow-read-only

# Criterion 2: refinement unit tests pass
pytest tests/audit/test_cos_work_inventory_refinements.py -v

# Criterion 3: hook behavior tests pass
pytest tests/behavior/test_agent_prelaunch_read_only.py -v

# Criterion 4: kill-switch produces same JSON shape
COS_PREFLIGHT_STRICT=1 python3 scripts/cos_work_inventory.py --all --strict --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'findings' in d and 'summary' in d"

# Criterion 5: bash -n passes
bash -n hooks/agent-prelaunch.sh

# Criterion 6: this ADR exists and references ADR-116
grep -q "ADR-116" docs/adrs/ADR-122-preflight-gate-refinements.md
```
