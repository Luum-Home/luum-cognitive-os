---
type: concept-synthesis
source: docs/04-Concepts/architecture/harness-engineering.md
---

## What it is
Defines "harness engineering" for COS: designing the environment around an AI coding model (context, tools, memory, verification, runtime boundaries) so it works as a governed agent rather than an unconstrained chatbot — implemented as a portable operating layer projected into Claude Code, Codex, Cursor, and future runtimes via explicit drivers.

## Key mechanics
- Operating thesis (5 properties): governable, verifiable, portable, context-efficient, progressive — "a stronger harness is not necessarily a larger harness."
- Pillar matrix (8 pillars, each with implementation + status + risk + next pressure point): repository-as-system (`AGENTS.md`, `cognitive-os.yaml`, `rules/`, `skills/`, `hooks/`, `manifests/harness-profiles.yaml` — Strong); progressive context (`rules/RULES-COMPACT.md`, `.codex/project-index.md` — Strong); durable memory (Engram, session summaries, git context capture — Strong); verification (tests, DoD gates, trust reports — Strong); multi-agent orchestration (`cos-agent`, sprint primitives — Medium/Strong); tool surface (Medium); harness portability (`lib/harness_adapter` — Medium/Strong); self-improvement (Medium).
- Minimal harness profile: required hook spine = `hooks/session-init.sh`, `hooks/auto-verify.sh`, `hooks/session-learning.sh`; required command spine = `scripts/cos-doctor-harness.sh`, `scripts/measure_harness_profiles.py`, `scripts/cos_sprint.py`, `bin/cos-agent`, `bin/cos-skill`. Executable contract lives in `manifests/harness-profiles.yaml`.
- 3-tier memory contract: repository artifacts (primary, every harness can read files) → runtime metrics JSONL (`.cognitive-os/metrics/`) → MCP memory (Engram, valuable but must degrade gracefully without it).
- Multi-agent guidance: use subagents for independent/bounded work or when exploration would flood context; avoid when next action is blocked on the result, task needs constant shared state, or subagent would self-approve its own implementation.
- Verification doctrine: completion requires acceptance criteria, relevant tests run, failures reported not hidden, reproducible claims, trust report for significant work.
- 6 anti-patterns: harness maximalism, context stuffing, chat-only state, self-approval, driver masquerade, opaque specialization.

## Relations & where used
Synthesis layer linking to Cross-Harness Authoring, Cross-Runtime Portability, Memory Lifecycle, Harness Driver Parity, Skills and Rules Portability Gap; ADR-036, ADR-057, ADR-064. External references: Anthropic's "Effective harnesses for long-running agents" and "multi-agent research system" posts, Claude Agent SDK blog, Vercel's "we removed 80% of our agent's tools", and a community GitHub issue on context degradation (flagged as anecdotal, not an official guarantee).

## Status / caveats
Closed gaps section lists implemented tooling: `manifests/harness-profiles.yaml`, `cos init-check`/`cos doctor harness`, `cos measure harness-profiles`, `cos sprint run --dispatch`, and a contract test `tests/contracts/test_harness_engineering_docs.py` protecting this doc. Ongoing guardrails (not unimplemented scope): keep auditing always-on hook/rule count; prefer real non-Claude agent runs over stubbed integration paths.
