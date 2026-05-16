# External-tools radar — Monitor Follow-up (2026-05-06)

Mode: light-deep (Phase 2 follow-up to 2026-05-06 cluster reports)

Total repos audited: **43**  

Verdict breakdown:
- ADOPT: 0
- TRIAL: 4
- MONITOR_CONFIRMED: 37
- REJECT: 2

## Summary table

| Repo | Shallow | Revised | Feature vs COS | Recommendation |
|------|---------|---------|----------------|----------------|
| Textualize/rich | monitor | **MONITOR_CONFIRMED** | Pure rendering library — orthogonal to COS orchestration; could improve any future Python TUI we ship. | small (drop-in pip dep) if/when we build a Python TUI |
| BerriAI/litellm | monitor | **MONITOR_CONFIRMED** | Broader provider matrix and observability hooks than lib/dispatch.py, but ADR-049's Qwen-primary topology is intentional. | medium-large (would replace dispatch.py and re-wire ADR-049) |
| FoundationAgents/MetaGPT | monitor | **MONITOR_CONFIRMED** | Role/SOP coordination overlaps squad-manager skill; but MetaGPT requires Python framework lock-in. | large (architectural mismatch) |
| agentgateway/agentgateway | monitor | **MONITOR_CONFIRMED** | Externalized gateway service; lib/dispatch.py is in-process and sufficient for current scale. | large (would require ops infra) |
| awslabs/agent-squad | monitor | **MONITOR_CONFIRMED** | Intent-classifier router overlaps skill_router.best_match; AWS-flavored not Anthropic-native. | medium (would compete with existing skill_router) |
| crewAIInc/crewAI | monitor | **MONITOR_CONFIRMED** | Crew abstraction overlaps squad-manager + agent-teams orchestrator; CrewAI is framework-first vs harness-first. | large (architectural mismatch) |
| maximhq/bifrost | monitor | **MONITOR_CONFIRMED** | Sub-100us overhead at 5k RPS — interesting if we externalize dispatch but unnecessary at COS scale. | large |
| TheR1D/shell_gpt | monitor | **MONITOR_CONFIRMED** | Single-shot CLI tool; COS already provides richer agent orchestration via skills. | n/a — no integration target |
| sigoden/aichat | monitor | **MONITOR_CONFIRMED** | Standalone end-user CLI; no skill/hook/rule interop with COS. | n/a (end-user tool) |
| MiniMax-AI/MiniMax-M2 | monitor | **MONITOR_CONFIRMED** | Model weights only — feeds into lib/dispatch.py routing if benchmarks justify. | n/a (consume via inference provider) |
| CodeGraphContext/CodeGraphContext | monitor | **MONITOR_CONFIRMED** | Code-graph KG overlaps Engram + cognee-integration skill; narrower scope. | medium (would duplicate Engram) |
| devwhodevs/engraph | monitor | **MONITOR_CONFIRMED** | Direct Engram-territory overlap with much smaller community. | n/a (Engram already covers) |
| microsoft/graphrag | monitor | **MONITOR_CONFIRMED** | Community-summarization is a unique RAG pattern; cognee-integration skill could borrow ideas. | medium (pattern extraction into cognee-integration) |
| safishamsi/graphify | monitor | **REJECT** | Cannot evaluate — star inflation flag unresolved. | n/a (signal integrity issue) |
| topoteretes/cognee | monitor | **MONITOR_CONFIRMED** | Already wired into COS via cognee-integration skill — monitoring is correct posture. | small (already integrated; track upstream) |
| QwenLM/qwen-code | monitor | **MONITOR_CONFIRMED** | Already core dependency — qwen is the default LLM in dispatch.py. | n/a (already adopted) |
| RooCodeInc/Roo-Code | monitor | **MONITOR_CONFIRMED** | Mode/role definitions interesting reference but COS orchestration is more sophisticated; no extractable skill primitive. | n/a (competitor) |
| anomalyco/opencode | monitor | **MONITOR_CONFIRMED** | Direct competitor harness; star count unreliable. No extractable skill primitive at surface. | n/a (competitor) |
| cline/cline | monitor | **MONITOR_CONFIRMED** | Reference for IDE-side agent UX; no architectural primitive aligned with COS harness model. | n/a (competitor) |
| openai/codex | monitor | **MONITOR_CONFIRMED** | Competitor harness; ADR-033 cross-harness-authoring already abstracts adapter concerns. | n/a (competitor harness — write adapter only if user demands) |
| shanraisshan/claude-code-best-practice | monitor | **MONITOR_CONFIRMED** | Documentation; could mine for prompt-engineering patterns but COS rules already comprehensive. | small (extract prompt patterns if any are novel) |
| DavidAnson/markdownlint-cli2 | monitor | **TRIAL** | Docs quality tool; could be wired into CI for ADR/RULES files. Not a skill, but a CI primitive. | small (add to .github/workflows) |
| JuliusBrussee/caveman | monitor | **MONITOR_CONFIRMED** | Already lives in COS as the caveman skill. | n/a (adopted) |
| junegunn/fzf | monitor | **MONITOR_CONFIRMED** | Shell utility; could power interactive prompts in COS scripts but not a skill primitive. | small (developer convenience) |
| lycheeverse/lychee | monitor | **MONITOR_CONFIRMED** | Already adopted; deep audit only on need. | n/a (adopted) |
| lycheeverse/lychee-action | monitor | **TRIAL** | Companion CI primitive; adopt-on-need if we wire link checking to PRs. | small (one workflow file) |
| Mirix-AI/MIRIX | monitor | **MONITOR_CONFIRMED** | Engram-overlap; memory-type taxonomy could inform Engram observation types. | small (taxonomy extraction) |
| egdev6/engram-monitor | monitor | **REJECT** | Engram-monitor dashboard idea is appealing, but no license = legal block. | n/a (license blocker) |
| letta-ai/letta | monitor | **MONITOR_CONFIRMED** | Self-improvement loop is novel; could inform self-improvement-protocol skill. Apache-2.0 allows pattern adoption. | medium (extract sleep-time pattern into self-improve skill) |
| memvid/memvid | monitor | **MONITOR_CONFIRMED** | Novelty (video-as-DB) is interesting but Engram is already production-ready; portability angle could inform Engram export. | small (export idea only) |
| rohitg00/agentmemory | monitor | **TRIAL** | Benchmark suite for memory systems could validate Engram quality regressions. | small (run benchmarks against Engram) |
| InternLM/WildClawBench | monitor | **MONITOR_CONFIRMED** | Benchmark targeting OpenClaw — low transferability to COS. | n/a (foreign harness) |
| dollspace-gay/OpenClaudia | monitor | **MONITOR_CONFIRMED** | Rust harness reference; not unique vs ironclaw/zeroclaw. | n/a |
| nashsu/AutoCLI | monitor | **MONITOR_CONFIRMED** | Specialized scraper; could be invoked as MCP tool but not extract patterns. | small (MCP wrapper if needed) |
| nearai/ironclaw | monitor | **TRIAL** | Closest architectural peer to COS in Rust. Privacy/security primitives could inform aguara-integration + content-policy. | medium (deep-dive on privacy primitives) — escalate-to-deep |
| nullclaw/nullclaw | monitor | **MONITOR_CONFIRMED** | Zig implementation language is barrier; no extractable primitive at surface. | n/a (language barrier) |
| qhkm/zeptoclaw | monitor | **MONITOR_CONFIRMED** | Claw-cluster Rust variant; not unique vs ironclaw/zeroclaw. | n/a |
| qwibitai/nanoclaw | monitor | **MONITOR_CONFIRMED** | Claw-cluster derivative; no distinct primitive. | n/a |
| sipeed/picoclaw | monitor | **MONITOR_CONFIRMED** | Edge/embedded runtime is orthogonal to COS desktop harness. | n/a (different deployment target) |
| smykla-skalski/klaudiush | monitor | **MONITOR_CONFIRMED** | Hook validator overlaps COS hook self-install model; small surface, possible pattern reference. | small (compare hook patterns) |
| zeroclaw-labs/zeroclaw | monitor | **MONITOR_CONFIRMED** | Claw-cluster Rust; not unique vs ironclaw. | n/a |
| luongnv89/claude-howto | monitor | **MONITOR_CONFIRMED** | Documentation/templates; could mine prompt patterns but COS rules already comprehensive. | small (mine templates if novel) |
| mattpocock/skills | monitor | **MONITOR_CONFIRMED** | Skills collection; could compare against COS skill registry. | small (review skills for borrow-worthy patterns) |

## Promotions (monitor → ADOPT/TRIAL)

- **DavidAnson/markdownlint-cli2** → `TRIAL` — Docs quality tool; could be wired into CI for ADR/RULES files. Not a skill, but a CI primitive. (effort: small (add to .github/workflows))
- **lycheeverse/lychee-action** → `TRIAL` — Companion CI primitive; adopt-on-need if we wire link checking to PRs. (effort: small (one workflow file))
- **rohitg00/agentmemory** → `TRIAL` — Benchmark suite for memory systems could validate Engram quality regressions. (effort: small (run benchmarks against Engram))
- **nearai/ironclaw** → `TRIAL` — Closest architectural peer to COS in Rust. Privacy/security primitives could inform aguara-integration + content-policy. (effort: medium (deep-dive on privacy primitives) — escalate-to-deep)

## Rejections (license/archived/integrity)

- **safishamsi/graphify** — license=`MIT`, archived=False, cadence=active (<30d)
- **egdev6/engram-monitor** — license=`NOASSERTION`, archived=False, cadence=active (<30d)

## Monitor confirmed (no change)

- Textualize/rich (cadence: active (<30d), license: MIT)
- BerriAI/litellm (cadence: active (<30d), license: NOASSERTION)
- FoundationAgents/MetaGPT (cadence: stale (90d-12mo), license: MIT)
- agentgateway/agentgateway (cadence: active (<30d), license: Apache-2.0)
- awslabs/agent-squad (cadence: active (<30d), license: Apache-2.0)
- crewAIInc/crewAI (cadence: active (<30d), license: MIT)
- maximhq/bifrost (cadence: active (<30d), license: Apache-2.0)
- TheR1D/shell_gpt (cadence: active (<30d), license: MIT)
- sigoden/aichat (cadence: warm (<90d), license: Apache-2.0)
- MiniMax-AI/MiniMax-M2 (cadence: stale (90d-12mo), license: NOASSERTION)
- CodeGraphContext/CodeGraphContext (cadence: active (<30d), license: MIT)
- devwhodevs/engraph (cadence: active (<30d), license: MIT)
- microsoft/graphrag (cadence: active (<30d), license: MIT)
- topoteretes/cognee (cadence: active (<30d), license: Apache-2.0)
- QwenLM/qwen-code (cadence: active (<30d), license: Apache-2.0)
- RooCodeInc/Roo-Code (cadence: active (<30d), license: Apache-2.0)
- anomalyco/opencode (cadence: active (<30d), license: MIT)
- cline/cline (cadence: active (<30d), license: Apache-2.0)
- openai/codex (cadence: active (<30d), license: Apache-2.0)
- shanraisshan/claude-code-best-practice (cadence: active (<30d), license: MIT)
- JuliusBrussee/caveman (cadence: active (<30d), license: MIT)
- junegunn/fzf (cadence: active (<30d), license: MIT)
- lycheeverse/lychee (cadence: active (<30d), license: Apache-2.0)
- Mirix-AI/MIRIX (cadence: active (<30d), license: Apache-2.0)
- letta-ai/letta (cadence: active (<30d), license: Apache-2.0)
- memvid/memvid (cadence: warm (<90d), license: Apache-2.0)
- InternLM/WildClawBench (cadence: active (<30d), license: MIT)
- dollspace-gay/OpenClaudia (cadence: active (<30d), license: MIT)
- nashsu/AutoCLI (cadence: active (<30d), license: Apache-2.0)
- nullclaw/nullclaw (cadence: active (<30d), license: MIT)
- qhkm/zeptoclaw (cadence: active (<30d), license: Apache-2.0)
- qwibitai/nanoclaw (cadence: active (<30d), license: MIT)
- sipeed/picoclaw (cadence: active (<30d), license: MIT)
- smykla-skalski/klaudiush (cadence: active (<30d), license: MIT)
- zeroclaw-labs/zeroclaw (cadence: active (<30d), license: Apache-2.0)
- luongnv89/claude-howto (cadence: active (<30d), license: MIT)
- mattpocock/skills (cadence: active (<30d), license: MIT)

## Per-repo artifacts

All 43 per-repo files in `docs/03-PoCs/research/repo-scout/monitor-followup/<owner>__<repo>-2026-05-06.md`.
