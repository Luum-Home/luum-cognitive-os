---
type: concept-synthesis
source: docs/04-Concepts/root/component-sources.md
status: "Last updated 2026-03-30"
provenance: "Track all external sources of skills, rules, hooks, tools, research, and infrastructure components referenced or integrated into luum-agent-os, with license status, for supply-chain and adoption-boundary discipline."
---

## What it is

Inventory of every external source (skills, security tools, testing tools, infra services, agent frameworks/OSes, sandbox infra, code-review tools, skill-ecosystem tools) integrated or evaluated for COS, with license and adoption status per source. Plugin submodules under `.claude/plugins/` (currently `hermes-agent`, `pi-mono`, `caveman`) must be discovered from `.gitmodules`, not hardcoded.

## Key mechanics

**Skills (external)**: Trail of Bits Security Skills (CC-BY-SA-4.0, 62 audit skills, OPTIONAL submodule at `.claude/plugins/trailofbits-skills/`); Antigravity Awesome Skills (MIT, 1,331+ skills, EVALUATED — see below).

**Security tools** (all OPTIONAL/PLANNED, license Apache-2.0/MIT/OSS): Aguara (189 rules/14 categories), mcp-aguara, Semgrep (+`p/ai-best-practices` 58 AI rules), Parry Guard (DeBERTa ML injection detection, Rust), Garak (179 probes), Promptfoo (PLANNED), MCP-Scan (PLANNED), NeMo Guardrails (Docker).

**Testing tools**: Tero/Mantis (garagon, Apache-2.0, WATCH), DeepEval/RAGAS/testcontainers-python (Apache-2.0, listed in NOTICE).

**Infra services (Docker)**: Langfuse (MIT core, ACTIVE), LiteLLM (MIT, ACTIVE), ClickHouse (Apache-2.0, ACTIVE dependency), SeaweedFS (Apache-2.0, ACTIVE dependency), Opik (Apache-2.0, OPTIONAL profile `observability`), Cognee (Apache-2.0, OPTIONAL profile `memory`), Crawl4AI (Apache-2.0, NOTICE).

**Agent frameworks adopted-as-patterns**:
- **Agent Zero** (16,494 stars, custom/NOASSERTION license — patterns only, not code): plugin marketplace → `cos` package manager; plugin/skill creation → `skill-creator`+`cos init`; plugin security scanning → Aguara+content-policy+secret-detector+Parry; self-update → post-merge hook+self-install.sh; agent teams → Claude Code Agent Teams.
- **Hermes Agent** (NousResearch, MIT, submodule since 2026-04-08, 9,431 LOC, 465 tests): memory scanning (`tools/memory_tool.py`→`lib/memory_scanner.py`, ADOPTED), hybrid retrieval (→`lib/memory_retriever.py`, ADOPTED), feedback detection (→`lib/feedback_detector.py`, ADOPTED), injection fencing (→influenced `hooks/content-policy.sh`, pattern). NOT adopted: Honcho (COS has Engram, confirmed non-reinvention), FastAPI server, monolith structure.
- **Pi Coding Agent** (MIT, submodule since 2026-04-08, 7-package monorepo, 161 tests, powers OpenClaw 160K+ stars): file mutation queue (→`lib/file_mutation_queue.py`, ADOPTED), compaction cut-points (→influenced `hooks/pre-compaction-flush.sh`), structural tests (→`tests/structural/`), settings override (→phase-aware `cognitive-os.yaml`). NOT adopted: TypeScript runtime, Pi memory system, double-while loop.
- **Caveman** (JuliusBrussee, MIT, submodule since 2026-05-02): WATCH only, no runtime code adopted.

**Agent Platforms**: Archon OS (13,844 stars, ACL v1.2 custom NOT OSI-approved — code adoption blocked; WATCH, patterns only: web crawling, MCP-for-RAG, agent work orders w/ git worktrees, document versioning). Full comparison table vs COS covers orchestration depth, quality gates (COS 55+ hooks vs Archon none), memory backend (Engram SQLite vs Supabase+PGVector), security (COS 10+ layers vs Archon minimal).

**Sandbox infra**: E2B (Apache-2.0, Firecracker microVMs, ~150ms boot, EVALUATE), E2B Infrastructure (EVALUATE, needs KVM hardware), E2B MCP Server (15 tools, lightest integration path).

**AI code review**: Gentleman Guardian Angel/GGA (MIT, 875 stars, pure Bash, 7 providers, 397 ShellSpec tests, EVALUATE — patterns worth adopting: ShellSpec hook testing, SHA-256 file-level caching, PR review mode, structured STATUS:PASSED/FAILED parsing, git-hook coexistence markers). Note: `tomyaparicio/gentleman-guardian-angel` fork is dead; canonical upstream org repo is the 875-star one.

**Skill ecosystem**: autoskills (CC-BY-NC-4.0, blocks code adoption, WATCH pattern-only), `skills` npm CLI (MIT, EVALUATE — legit integration target), skills.sh (EVALUATE, skill source).

**Web platform access**: opencli-rs / opencli-rs-skill (Apache-2.0, Rust, 55+ platforms via Chrome CDP session reuse, WATCH — too new, 6 days old at evaluation, no LICENSE file, curl-pipe-sh install, arbitrary JS execution in browser mode).

**Research/design influences adopted**: Tactical Agentic Coding/IndyDevDan (closed-loop prompts, Agent Experts Act/Learn/Reuse); BMAD Method v6 (9 patterns: adversarial review, step files, agent sidecars, readiness gate, dual-search, agent customization, prompt composition); OpenClaw (4-tier fault tolerance); WISC Framework/Cole Medin (context thresholds, cognitive load); arxiv 2507.11538 (>150 instructions degrade performance → capability levels); arxiv 2602.11988/ETH Zurich (context files reduce task success → adaptive bypass).

**Antigravity Awesome Skills evaluation** (28,344 stars, MIT, 1,331+ skills): quality VARIABLE (community-contributed), status WATCH-selective. Recommendation: cherry-pick 5-10 skills into `packages/antigravity-skills/`, do NOT bulk-install (would overwhelm 5-active-skill progressive loading limit).

## Relations & where used

`docs/04-Concepts/root/ecosystem-comparison.md`, `docs/03-PoCs/research/repo-scout/deep/*` (deep-dive addenda per evaluated tool), `docs/08-References/root/competitive-analysis.md`, `rules/agent-identity.md` (OneCLI Phase 2 target), `lib/task_dag.py` (Archon pattern target).

## Status / caveats

Multiple entries are explicitly license-gated: ACL v1.2 (Archon) blocks direct code adoption; CC-BY-NC-4.0 (autoskills) blocks commercial code use; Agent Zero's NOASSERTION license requires verification before any code adoption. COS's stated policy throughout: adopt architectural patterns via clean-room reimplementation, not copied code, when licenses are restrictive.
