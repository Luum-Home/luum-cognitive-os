---
type: concept-synthesis
source: docs/04-Concepts/architecture/memory-lifecycle.md
provenance: "Cognitive OS must not rely on one chat window or one vendor harness as the place where project memory lives."
---

## What it is
How Cognitive OS saves, protects, retrieves, and verifies cross-session memory for Codex, Claude Code, and future harness drivers. Contract: capture intent while active, protect content before persistence, flush before compaction, record outcomes at shutdown, recover pending work at next start, verify the loop with an executable doctor.

## Key mechanics
- Two automation layers: hook automation (shell hooks run at harness lifecycle events, write local evidence under `.cognitive-os/`) and agent-tool automation (Engram MCP tools called by the agent — `mem_session_summary`, `mem_save` — when available; shell hooks cannot call MCP tools directly, hence `hooks/pre-compaction-flush.sh` explicitly instructs the agent).
- Verification: `bash scripts/cos-doctor-tools.sh` (full host doctor) and `bash scripts/cos-doctor-memory-lifecycle.sh --harness codex` (memory-only proof: Engram launcher, pending-task recovery, prompt capture, session-learning metrics, git context, resumable changelog, session-end crystallization, pre-compaction reminder).
- Save surfaces: `hooks/user-prompt-capture.sh` -> `prompt-captures.jsonl`; `hooks/pre-compaction-flush.sh` -> anchored summary + `mem_session_summary`/`mem_save` reminder; `hooks/session-learning.sh` -> `session-learnings.jsonl`; `hooks/git-context-capture.sh` -> `.cognitive-os/sessions/{id}/git-context.json`; `hooks/session-changelog.sh` -> `.cognitive-os/changelogs/{id}.md`; `hooks/engram-crystallize-on-session-end.sh` -> `crystallization-events.jsonl` + Engram digest.
- Recovery surfaces: `hooks/engram-daemon-launcher.sh`, `hooks/session-init.sh` + `session_init_helper.py` + `lib/project_profile_bootstrap.py` (first 3 sessions), `hooks/session-resume.sh`, `lib/memory_retriever.py`, `lib/engram_client.py`.
- Protection surfaces: `lib/safe_engram.py` (blocks suspicious content before writes), `lib/memory_scanner.py` (prompt-injection/credential/unsafe-memory classification), `lib/anchored_summarizer.py` (compact pre-compaction summaries).
- Env precedence: Project = `COGNITIVE_OS_PROJECT_DIR -> CODEX_PROJECT_DIR -> CLAUDE_PROJECT_DIR -> cwd`; Session = `COGNITIVE_OS_SESSION_ID -> CODEX_SESSION_ID -> CLAUDE_SESSION_ID`.
- Codex projects SessionStart/UserPromptSubmit/Stop only. Claude Code additionally gets `PreCompact` (`pre-compaction-flush.sh`) and `PostToolUse` (`engram-reinforce-on-access.sh`) — an explicit driver capability difference, not hidden lock-in.
- Project Profile Bootstrap: first 3 valid sessions write `.cognitive-os/project-profile/draft.{json,md}` from deterministic signals only (go.mod, pyproject.toml, package.json, Docker files, session metadata, prompt-capture categories); no full-repo scan, no Engram/MCP calls from shell; promotion is explicit via `python3 scripts/cos_profile_bootstrap.py promote --approved-by <reviewer>` writing `.cognitive-os/project-profile/profile.json` (does not write Engram).

## Relations & where used
`tests/contracts/test_memory_lifecycle_portability.py`, `tests/behavior/test_cos_doctor_tools.py`, `tests/behavior/test_engram_reinforce_hook.py`, `tests/contracts/test_session_start_tooling_contract.py`, `tests/unit/test_project_profile_bootstrap.py`, `tests/behavior/test_profile_bootstrap_cli.py`, ADR-071 (Engram Lifecycle Evolution), related docs: bootstrap-portability.md, harness-driver-parity.md.

## Status / caveats
Codex should only receive Claude-equivalent hook projections when equivalent event semantics are proven, not by default parity assumption.
