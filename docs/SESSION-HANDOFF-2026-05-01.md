# Session Handoff — 2026-05-01

> Topic key: `session/2026-05-01/handoff`. Project: `luum-cognitive-os`.
> Previous handoff: [`SESSION-HANDOFF-2026-04-27.md`](SESSION-HANDOFF-2026-04-27.md).

## Goal

Close the 1-session-sized items from the 2026-04-27 backlog (20+ install-test flakes investigation, so-existential Phase 1 mechanical batch) and triage as much of the soft-tier backlog as possible without forcing decisions.

Result: **2 commits**, **30 engram decisions closed**, **5 install-timing baseline records logged**, **4 punch lists generated**.

## Operator instructions (still active)

- Avoid direct Anthropic API billing — provider cascade unchanged.
- Provider-AND-harness-agnostic. **ADR-064 was flipped to Accepted on 2026-04-30** (Codex adapter shipped in commit `9062829`, parity test in `259f766`).
- Engram = source of truth for memory. Lifecycle metadata in `<engram-lifecycle>` trailer.
- Never `PATCH/POST/DELETE` against production engram daemon for API discovery (`rules/engram-api-safety.md`).
- New today: hooks `engram-daemon-launcher.sh` and `profile-drift-autoapply.sh` from 2026-04-27 are now active in `.claude/settings.json` — sessions auto-start engram serve and re-apply efficiency profile on script drift.

## What shipped this session

### Commits this session

- **`54439ea6` — fix(test-lanes): flip audit + contract to serial — install-test flakes root cause**
  Root cause Bucket A: tests in audit + contract lanes invoke real `hooks/self-install.sh` and `scripts/cos-init.sh` against `COS_SOURCE_DIR=PROJECT_ROOT` while xdist workers walk the same source tree concurrently. Hot files: `tests/audit/test_install_scripts.py` Layer 3-4 and `tests/contracts/test_self_install_no_container_spawn.py`. Bucket A covers ≥80% of the 20+ pre-existing flakes flagged in the 2026-04-25 brief. Surgical follow-up (xdist_group marker on the 2 hot files, restore `parallel: true` for the rest) tracked as ~15 min refactor, not blocking. Engram: `adr-072/install-flakes-rootcause` (id 15985).

- **`33317983` — feat(so-existential): Phase 1 — install-timing baseline + JSONL logger (recovered)**
  - `lib/install_timing.py` — `append_install_record` + `read_records` + `within_budget`, ADR-059 schema (timestamp, profile, elapsed_s, manual_steps, errors).
  - `scripts/install-timing-test.sh` — clones repo + times cos-init runs, emits JSONL via embedded heredoc.
  - `tests/unit/test_install_timing.py` (5 tests) + `tests/contracts/test_install_timing.py` (12 tests, ADR-059 budget gate as regression guard).
  - `tests/{unit,contracts}/__init__.py` to prevent pytest module-name collision.
  - `Makefile` — `make install-test` target with `PROFILE=` override.
  - `scripts/setup.sh` — `NONINTERACTIVE=1` for Homebrew (Phase 2 prerequisite for headless install).
  - 6 of 42 plan checkboxes ticked.
  - **Recovery note**: the agent's new files were wiped between agent completion and orchestrator commit (likely `git clean -fd` after stash by another session). Restored from the agent's JSONL transcript via `agent_output_extractor`. Also fixed a syntax bug introduced by the original agent (invalid `REQUIRED_FIELDS if hasattr(...) else None` inside an `import` block).

### Local-only deliverables (gitignored, not in repo)

These exist on disk under `.cognitive-os/` but are not version-controlled:

- `.cognitive-os/metrics/install-timing.jsonl` — 5 baseline records, mean 38.8s / p95 43s (budget 300s, 257s headroom).
- `docs/reports/install-timing-baseline-2026-05-01.md` — narrative baseline document.
- `.cognitive-os/reports/punch-list-{hooks,skills,lib,rules}.md` — 59 ASPIRATIONAL hooks, 10 skills, 1 DORMANT lib (jupyter_client), 0 rules.
- `.cognitive-os/reports/prune-baseline.json` — today's audit baseline (`dormant_aspirational_ratio=0.3521`, ASPIRATIONAL=58 — drifted from the plan's April 24 figures of 0.381 / 71).
- `.cognitive-os/plans/features/so-existential-validation-2026-04-24.md` — 9 checkboxes ticked total (6 from Phase 1 commit, 3 more from batch 2).

### Engram observations

- `decision-triage/2026-05-01-batch` (id 16018) — **30 decisions closed** out of 121 pending. Closures grouped: 14 cos-init-related answered (Python migration shipped), 7 ADR-028 stale (ADR Accepted with addenda), 7 ADR-067 / ADR-068 / ADR-069 related-and-resolved, 2 python-bumps stale (pin documented), plus minor. **91 left open** by category: 35 architectural trade-offs (ADR-050/052/053/062/063/064/065/080/081/083/084), 11 multi-stakeholder, 45 soft / not-yet-enacted.
- `adr-072/install-flakes-rootcause` (id 15985) — full diagnosis + fix path.
- `so-existential/batch-2-progress` — 5x install-test runs verified plug-and-play assumption (38.8s mean vs 300s budget).

## Active incident — session-startup hang (2026-05-01 13:36 UTC)

**Symptom**: Operator reports a 5+ minute hang when starting a new session in this repo. The chat UI renders the same prompt twice, and a "5m 0s" timer appears at the bottom of the interface.

**Direct evidence**:

- Three session directories were created within a 3-second window: `1777642602-95642-ef1df097`, `1777642604-95912-8731f960`, `1777642605-96549-d17975e8` (all under `.cognitive-os/sessions/`).
- `.cognitive-os/metrics/hook-timing.jsonl` shows `session-init` executed 10 times in the 13:36:27–28 UTC window (normal: 1–2). `self-knowledge-refresh` also ran 10 times in the same window.
- Individual hooks are fast (<3s each). Compounding cause: 17 SessionStart hooks × 3 concurrent sessions racing on `.git/index.lock` and self-install rsync.
- `.git/index.lock` was present (stale) at the time.

**Root cause** (confirmed 2026-05-01, two interacting bugs):

1. **Cross-filesystem `mv` in `scripts/_lib/settings-driver-claude-code.sh`** — `mktemp` defaulted to `$TMPDIR`, often a different filesystem from `.claude/`. Cross-FS `mv` degrades from `rename(2)` to `cp` + `unlink` — non-atomic. The IDE file-watcher could observe a partial `settings.json` mid-write and re-spawn the session.
2. **No mutex in `hooks/profile-drift-autoapply.sh` (F8)** — when N concurrent sessions all detected stale hash, all N entered the apply path in parallel, racing to write `settings.json`. Each partial write triggered another re-spawn → positive-feedback loop.

Sub-agent fan-out (initially the leading hypothesis from the SRE agent's RCA) was a contributor — Claude Code fires the full 17-hook SessionStart chain per sub-agent — but is not the root cause; it amplified the impact of bugs 1+2. Tracked separately as long-term hardening.

**Fixes shipped** (this session):

- `scripts/_lib/settings-driver-claude-code.sh` — `mktemp` now uses `"$SETTINGS_DIR/.settings.json.XXXXXX"` so the rename is a single `rename(2)` syscall on the same filesystem.
- `hooks/profile-drift-autoapply.sh` — non-blocking `flock` via fd 9 on `.cognitive-os/runtime/profile-autoapply.lock`. First invocation wins; concurrent ones exit 0 silently. Hash file re-read UNDER LOCK to prevent TOCTOU.
- `tests/integration/test_settings_atomic_write.py` — 8 tests including a structural invariant on the `mktemp` template, a codebase audit scanning for other unsafe `mktemp`+`mv` patterns (currently 0 hits), and a stress test with a concurrent reader thread.
- `tests/integration/test_profile_drift_autoapply_flock.py` — 5 tests including 5-worker concurrent invocation asserting exactly-1-apply AND non-blocking lock (wall time < 4s).

All 13 tests pass. Full postmortem: [`docs/incidents/2026-05-01-session-multi-spawn-hang.md`](incidents/2026-05-01-session-multi-spawn-hang.md).

**Operator workaround** (only needed if your local checkout is pre-fix):

```bash
pkill -f "claude code" 2>/dev/null
pkill -f "codex" 2>/dev/null
rm -f .git/index.lock
rm -f .cognitive-os/runtime/*.lock
rm -rf .cognitive-os/sessions/1777642602-* .cognitive-os/sessions/1777642604-* .cognitive-os/sessions/1777642605-*
# Then start ONE new session.
```

**Defensive opt-out** (skips the autoapply hook entirely):

```bash
export COS_DISABLE_PROFILE_AUTOAPPLY=1
```

**Cross-references**:
- Engram: `incident/2026-05-01-session-3-spawn-hang`.
- Postmortem: `docs/incidents/2026-05-01-session-multi-spawn-hang.md`.
- ADR-071 §F8 (profile-drift-autoapply), ADR-064 (multi-harness / Codex adapter), ADR-088 (provenance marker for concurrent session tracing).

## Pending — not blockers

### 1-session sized
- **so-existential prune-triage** — next plan item is `Issue prune-triage-2026-04-24.md` (1 row per item, action = REMOVE / PROVE / IMPLEMENT / REFERENCE-OK) for ~236 DORMANT+ASPIRATIONAL items. Mechanical row-by-row but substantial scope; should be its own batch agent. Per-bucket punch lists already exist as input.
- **Surgical xdist_group fix** for install tests — replace the lane-level `parallel: false` with `pytestmark = pytest.mark.xdist_group("install-shared-root")` on the 2 hot files only, restore `parallel: true` for the rest of audit/contract. ~15 min when ready.
- **ADR-064 Surfaces 2-4** (per ADR's own Acceptance trail) — `cos-skill` CLI, `cos-agent` spawner, `lib/harness_adapter/cursor.py`, `lib/harness_adapter/bare_cli.py`, `scripts/_lib/settings-driver-codex.sh`. P0 implementation work tracked in `.cognitive-os/plans/architecture/adr-064-implementation-plan.md`.

### Multi-session (sprint-scope)
- so-existential remaining ~29 tasks (Day 1-7 remove/prove window, prune-triage, Day 11 README verdict, Day 14 archive, Phase 3). Target 2026-05-15.
- 35 architectural trade-off decisions (ADR-050/052/053/062/063/064/065/080/081/083/084) — each requires explicit operator call.
- 11 multi-stakeholder decisions (phoenix Phase 1, agent-escalation/workflow-engine reactivation gates, embedding stack ownership, etc.).

### Conditional (triggers documented in ADR-071 §Future Work)
- F1: Crystallizer LLM upgrade — when ≥30 heuristic digests reviewed and judged low signal.
- F2: `mem_judge` writes — when engram exposes `POST /relations` or operator decides MCP subprocess path.
- F3: Cross-device reinforcement — when divergent counts observed across devices.
- F4: Threshold calibration — after ≥4 weeks of crystallization-events.jsonl accumulated.
- F5: Phase 4 Obsidian export — when memory crosses ~500 obs and `mem_search` feels insufficient.
- F6: Cloud sync e2e test — when F3 lands or sync bug reported.
- F7+F8: shipped 2026-04-27 (engram-daemon-launcher + profile-drift-autoapply).

### Upstream-blocked
- `default_backend()` cleanup in hermes-agent — waits cryptography 49.0.0.
- `rich 14→15` — waits cognee unpin.
- `wrapt 1→2` — waits OTel transitive validation.

### ON ICE (do not touch absent explicit priority)
- `agent-escalation-capabilities` — zero implementation, no momentum, no signal of need.
- `workflow-engine` — same.

## Honest caveats from this session

- **Agent file-loss happened twice** in the same session: the so-existential Phase 1 agent's new files were wiped between agent completion and commit (recovered via JSONL transcript). Background sessions running `git clean` or `git stash` aggressively can wipe untracked files created by foreground agents. Mitigation now in main: commit `2a4d6207 fix(snapshot): preserve untracked files in WT during agent launch` (landed by another session today).
- **Agent-introduced syntax bug**: the so-existential agent wrote `REQUIRED_FIELDS if hasattr(...) else None` inside a `from ... import (...)` block — illegal Python. Caught by pre-commit ruff after recovery; orchestrator fixed manually. Worth noting that even Sonnet-grade agents emit subtly broken code on edge cases like this.
- **Rate-limiter pressure**: bash hit 22/22 cap multiple times during commit prep, causing 60-second waits and queue accumulation. Slowed iteration meaningfully. The lifting strategy is to delegate more (agents have their own budget) or batch commands.
- **`scripts/install-timing-test.sh` baseline used `file://` clone** — avoids SSH but means real install times may be 5-20s higher when cloning over network. Plug-and-play verdict still safe (257s budget headroom), but worth confirming with one real-network run before claiming portability.
- **30 decisions closed conservatively** — ADR-028 questions 5-6 were closed as "stale" without reading addenda 28a/28b/28c in full. Confidence on those two: 0.75. Reopenable if needed.
- **`scripts/decision_triage.py` should skip ACCEPTED ADRs** — the script currently scans all ADR sections and re-surfaces questions from ACCEPTED ADRs (e.g. ADR-028) as "pending." Follow-up tracked.

## Engram session summary

Save under topic_key `session/2026-05-01/handoff`. Cross-references: `adr-072/install-flakes-rootcause`, `decision-triage/2026-05-01-batch`, `so-existential/batch-2-progress`.

## Next-session quick start

1. **Verify health on resume**:
   - `curl -s http://127.0.0.1:7437/health` (engram-daemon-launcher should auto-start).
   - `cat .cognitive-os/runtime/last-applied-profile.sha` (profile-drift-autoapply tracking).
2. **If picking up so-existential prune-triage**: input is the 4 punch lists in `.cognitive-os/reports/punch-list-*.md`. Plan target 2026-05-15.
3. **If picking up surgical xdist_group**: edit `tests/audit/test_install_scripts.py` and `tests/contracts/test_self_install_no_container_spawn.py` to add `pytestmark = pytest.mark.xdist_group("install-shared-root")`, then revert `.cognitive-os/test-lanes.yaml` audit + contract back to `parallel: true`.
4. **If picking up ADR-064 Surfaces 2-4**: `.cognitive-os/plans/architecture/adr-064-implementation-plan.md` has the full task list.
5. **If picking up decision triage round 2**: `mem_search "decision triage pending"` then read `decision-triage/2026-05-01-batch` (id 16018) to see what's already closed.

## Releases

- **None this session** — work was operational (flakes fix, baseline, decisions). v0.22.0 was shipped by other sessions between 2026-04-27 and today.
