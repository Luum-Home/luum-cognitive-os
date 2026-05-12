# Session Handoff — 2026-04-17

> End-of-session state for the next agent / human picking up the work.
> Parent branch: `main` at tag `v0.11.1`.

## What landed today

| Commit | Tag | Scope |
|---|---|---|
| [1540ef4](https://github.com/Luum-Home/luum-cognitive-os/commit/1540ef4) | v0.10.0 | `uv sync` in cos-update.sh with SHA cache |
| [6de320c](https://github.com/Luum-Home/luum-cognitive-os/commit/6de320c) | — | Lote 1: invert order — uv sync BEFORE self-install |
| [0db8c14](https://github.com/Luum-Home/luum-cognitive-os/commit/0db8c14) | v0.11.0 | Lote 2: MCP auto-register loop + `install.sh --install-deps` + drift fix |
| [4439db9](https://github.com/Luum-Home/luum-cognitive-os/commit/4439db9) | — | ADR-025 commit TBD → 0db8c14 |
| [80e3262](https://github.com/Luum-Home/luum-cognitive-os/commit/80e3262) | — | ADR-026 design review (R2 + R3) |
| [7bd601f](https://github.com/Luum-Home/luum-cognitive-os/commit/7bd601f) | — | ADR-026a auto-answers (D2.1–D2.4, D3.1–D3.3) |
| [896dde1](https://github.com/Luum-Home/luum-cognitive-os/commit/896dde1) | — | R3 close-out: docstrings + cos_mcp:217-219 fix |
| [d3aa371](https://github.com/Luum-Home/luum-cognitive-os/commit/d3aa371) | v0.11.1 | Lote 3 (R1): `lib/paths.py::project_root()` + 10 sites migrated |

Net test delta vs. v0.11.0: **+10 passing (5820 total)**, 42 pre-existing failures unchanged.

## Pending work, priority order

### 1. Lote 4 — R2 refactor (`lib/config_loader.py`)

**Status**: ready to start. All decisions pre-approved in ADR-026a.

**Scope**:
- Create `lib/config_loader.py` with three variants:
  - `read_top_level_int(key, default)` — hot-path readers (cold-start safe)
  - `load_structured()` — heavy gates that need the full YAML dict
  - `find_config_path()` — legacy-compat locator
- Migrate the 3 characterized sites (per `tests/unit/test_cos_yaml_readers.py`)
- **Fix site-3 env-var precedence** in the same PR (D2.2 YES)
- **Defer schema validation** to a later ADR (D2.4 YES)
- **Scope-limit**: do NOT absorb adjacent parsers here (D2.3 YES) — that is R2b

**Effort estimate**: ~9h (per ADR-026a). Add 2–3h if test rewrites hit private helpers.

**Acceptance criteria candidate**:
- `python3 -m pytest tests/unit/test_cos_yaml_readers.py` still green (all 43)
- New `tests/unit/test_config_loader.py` covers the 3 variants
- Exactly 3 call sites migrated (verified by grep diff)
- Site-3 env-var precedence fixed with a regression test
- ADR-026a updated: status CLOSED for R2

### 2. R2b — adjacent parsers (U4)

**Status**: open. Identified by the ADR-026a spot-check.

**Scope**:
- Write characterization tests for the 4 additional parsers: `lib/rate_limiter.py`, `lib/sdd_pipeline.py`, `lib/queue_advisor.py`, `lib/smart_infra.py`
- Decide per parser whether semantics match one of the 3 R2 variants or diverge
- Migrate matches; NOTE-comment the outliers

**Effort estimate**: ~4–5h.

### 3. U1 — `memory.py` routing (open decision)

**Status**: open. Needs product input, not resolvable from code alone.

**Question**: does `lib/memory.py` belong to the `safe_engram` (silent/wrapper) or `engram_client` (raising/CLI-facing) contract? Currently the docstring mentions `safe_engram` but the implementation is not routed.

**Unblocks**: closing the R3 audit item completely (currently marked CLOSED in ADR-026 but U1 technically remains).

### 4. U3 — bash-side YAML readers

**Status**: open, out of R2 scope.

**Context**: 42 shell scripts (`.sh`) read `cognitive-os.yaml` via `grep`/`awk`. Options:
- Migrate to invoke `python3 -m lib.config_loader …`
- Keep bash-side separate and document both as "two-language parity"

**No decision yet**. Track as separate ADR when Lote 4 lands.

## Manual followups (human-only)

1. **GitHub Releases UI** — no `gh` CLI on this machine. Publish formatted notes for v0.10.0 / v0.11.0 / v0.11.1 at:
   - https://github.com/Luum-Home/luum-cognitive-os/releases/new?tag=v0.10.0
   - https://github.com/Luum-Home/luum-cognitive-os/releases/new?tag=v0.11.0
   - https://github.com/Luum-Home/luum-cognitive-os/releases/new?tag=v0.11.1
   Tag annotation messages are already written; paste as-is.
2. **Delete 6 orphaned `claude/*` remote branches** — 403 from CLI, use the GitHub UI.
3. **Lote 2 smoke test** — instructions in `docs/09-Quality/manual-tests/lote-2-mcp-loop.md`:
   - Fresh clone + `bash install.sh --install-deps` → `claude mcp list` shows the manifest MCPs
   - Modify `manifests/dependencies.yaml`, run `bash scripts/cos-update.sh`, verify diff applied
   - Simulate missing `claude` CLI → WARN + exit 0 (non-fatal)
   - Second run unchanged → per-MCP skip (SHA is telemetry, not a gate)

## Pre-existing test debt (not introduced today)

Full unit suite: **42 failures** before and after today's changes. One example:
- `tests/unit/test_dod_gate_behavior.py::TestDodGateBlocking::test_blocks_when_no_criteria_in_production`
  — `dod-gate.sh` returns 0 when the spec expects 2 in `production` phase with missing DoD criteria.
  Unrelated to R1/R3/MCP work.

Run to see the full list:
```bash
python3 -m pytest tests/unit/ --tb=no -q | tail -60
```

No new red tests introduced by today's commits. Ownership of the 42 failures is outside this session's scope.

## Conventions established this session

- **SHA caches are telemetry, not gates** — per-item idempotence always runs (from the drift bug in `register-mcps.sh`).
- **Install paths split**: `install.sh` is opt-in (`--install-deps`), `cos-update.sh` is auto. Rationale in ADR-025.
- **ADR addenda** use `NNNa-…` naming (see ADR-026a) to extend a parent ADR without rewriting it.
- **Characterization-first refactor**: commit tests that freeze current behavior before refactoring (Lote 3 pattern, per 6ed3e63/d5f6f12/540998a).

## Known hazards for the next agent

- `lib/*.py` files may be symlinks to `packages/*/lib/` — always `ls -la` before editing. Today's new `lib/paths.py` is a real file.
- `.claude/settings.json` is generated by `scripts/apply-efficiency-profile.sh`. Multiple sub-agents today modified it by accident; restore with `git checkout .claude/settings.json` before commit.
- When two agents run in parallel, choose non-overlapping file surfaces. Today's Lote 3 and R3 close-out ran concurrently because their surfaces were disjoint (`lib/paths.py`+R1 sites vs `lib/safe_engram.py`+`cos_mcp.py`).
