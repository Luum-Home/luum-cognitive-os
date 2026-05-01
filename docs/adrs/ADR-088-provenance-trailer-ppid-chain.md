# ADR-088 — Provenance trailer attribution via PPID chain

## Status

Accepted.

**Date:** 2026-04-30

---

## Context

Commit `7492ce0` introduced `X-COS-Origin` / `X-COS-Session` / `X-COS-Harness`
trailers to every local commit via `.githooks/prepare-commit-msg` →
`scripts/commit_provenance.py`. The intent was to distinguish manual, agent,
hook, cron, and sub-agent commits in audit queries.

However, `commit_provenance.py` had a serious attribution bug: when the git hook
process is invoked by a sub-shell (or by `git commit` run under a stripped
environment), the three inference functions — `infer_kind()`, `infer_harness()`,
and `read_current_session()` — each fell back to their own defaults independently:

- `infer_kind()` → `"manual"` (no env vars)
- `infer_harness()` → `"unknown"` (no env vars)
- `read_current_session()` → glob `.current-session-*` by **mtime**, returning
  the most-recently-modified marker on disk — which can belong to **any** session,
  not the one that made the commit.

We verified this empirically. Running:

```bash
env -i bash .githooks/prepare-commit-msg /tmp/test-msg
```

produced the trailer:

```
X-COS-Origin: kind=manual session=1777570196-94294-3bcc1d20 harness=unknown
```

where `1777570196-94294-3bcc1d20` is a session ID from a **different** session
that happened to have the most recently written `.current-session-*` file on
disk. The three values came from three different sources, producing an
internally inconsistent and incorrect trailer.

---

## Decision

We implement three complementary fixes as a single commit:

### Option A — Rich JSON marker format + PPID-chain lookup

**New marker format:** `write_context_marker.py` (new script) writes
`.cognitive-os/sessions/.context-<pid>.json` with:

```json
{
  "session": "1777570196-94294-3bcc1d20",
  "kind": "orchestrator",
  "harness": "claude",
  "pid": 12345,
  "ppid": 1234,
  "started_at": "2026-04-30T17:30:00Z",
  "parent_chain": [12345, 1234, 567]
}
```

Valid `kind` values: `orchestrator`, `subagent`, `cron`, `hook`, `human`.
`parent_chain` is a PPID walk captured at write time (up to 10 levels).

**PPID-chain lookup in `commit_provenance.py`:** New function
`find_owning_context(repo)` walks the process tree from `os.getpid()` upward
via `ps -o ppid= -p <pid>`. For each PID in the chain it looks for
`.context-<pid>.json`. The first match is the owning session. All three fields
— session, kind, harness — are read from one context object, eliminating the
multi-source inconsistency.

Fallback priority when no chain match:

1. PPID chain → `.context-<pid>.json`
2. Environment variables (existing logic)
3. Most-recently-modified `.context-<pid>.json` (mtime, last resort)
4. Legacy `.current-session-<pid>` plain-text files (backwards compat)
5. `"manual"` / `"unknown"` defaults

**Backwards compatibility:** Old `.current-session-<pid>` files (plain text
containing only a session ID) are still read in step 4. They produce a minimal
context dict `{session, kind="unknown", harness="unknown", _legacy=True}`. No
migration is required; old files coexist with new JSON markers. The old format
is deprecated and will not be written for new sessions.

**Marker writer in `session-init.sh`:** On `SessionStart`, after writing the
legacy `.current-session-$$` file, `session-init.sh` now also calls:

```bash
python3 scripts/write_context_marker.py orchestrator
```

This ensures the orchestrator's JSON marker is on disk before any sub-agent is
spawned, making it discoverable via PPID-chain walk.

**Stale marker cleanup in `session-init.sh`:** At the end of the init block, a
Python snippet drops `.context-<pid>.json` files whose PID is dead or that are
older than 24 hours, preventing accumulation.

### Option B — Sub-agent markers at spawn

The preamble-injection approach is used for sub-agent markers. The agent
preamble (`templates/agent-preamble.md`) now instructs every sub-agent to run:

```bash
python3 scripts/write_context_marker.py subagent 2>/dev/null || true
```

as its very first Bash call. This writes `.context-<pid>.json` with
`kind=subagent` for the sub-agent's PID, so commits made by sub-agents are
attributed correctly.

**Coverage caveat:** This only covers sub-agents whose preamble includes the
updated template. Sub-agents invoked via paths that render a different preamble,
or that do not execute Bash at all, will not write their own marker. In those
cases the PPID-chain walk will find the orchestrator's marker, producing
`kind=orchestrator` — still accurate at session level, but not granular to
sub-agent. This is documented in the runbook as a known limitation.

### Option C — Runbook disclaimer

`docs/measurements/hook-timing-runbook.md` gains a "Commit provenance trailer —
known limitations" section documenting: depth-10 cap, fork-and-orphan edge case,
screen/tmux stripped-env case, and the one-time artifact on the commit that
installs the fix. Includes verification commands.

---

## Consequences

**Positive:**
- Accurate session/kind/harness attribution for all commits made inside a COS
  session, including sub-agents, without requiring env-var propagation across
  sub-shells.
- Three values (session, kind, harness) now always come from one context object,
  eliminating the multi-source inconsistency that produced the empirical bug.
- PPID-chain walk adds ~5ms per commit (10 `ps` invocations, each ~0.5ms on
  macOS). Negligible for an operation that runs once per `git commit`.
- Legacy repos without JSON markers continue to work via the plain-text fallback.

**Negative / risks:**
- `write_context_marker.py` is a new write path. Any bug there could leave
  malformed JSON files. Mitigation: atomic temp+rename write; `_load_json_marker`
  returns None on parse failure so the lookup falls through to env vars.
- Sub-agent coverage is incomplete. Preamble injection only reaches sub-agents
  whose preamble includes the updated template. Other spawn paths are not covered.
  This is strictly better than the current state (zero coverage) and is
  explicitly documented.
- Marker file accumulation if cleanup is skipped (e.g., if session-init.sh
  never runs). Follow-up: add cleanup to session-cleanup.sh as belt+suspenders.

**Follow-up items:**
- Mirror the stale-marker cleanup in `hooks/session-cleanup.sh` for robustness.
- Audit other sub-agent spawn paths (dispatch-gate, lib/dispatch.py, raw Agent
  calls from skills) and add `write_context_marker.py subagent` there if
  feasible.

---

## Alternatives rejected

- Keep the previous behavior unchanged — rejected because the audit or runtime failure would remain deterministic and would continue masking real regressions.

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/behavior/test_git_context_hook.py -q
```
