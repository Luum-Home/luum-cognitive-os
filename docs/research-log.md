# Research Log

> Evaluation record for tools and frameworks considered for Cognitive OS integration.
> Author: luum | Updated: 2026-03-27

## Evaluation Summary

| Tool | Score | Ring | License | Decision | Key Insight |
|------|-------|------|---------|----------|-------------|
| Firecrawl | 6.2/10 | HOLD | AGPL-3.0 (BLOCKED) | Replaced by Crawl4AI | AGPL blocks SaaS usage; cloud-only model adds vendor lock-in |
| Crawl4AI | 29/30 | ADOPT | Apache-2.0 | Integrated | Best web crawler for LLM pipelines; local-first, async, markdown output |
| InsForge | 6.95/10 | HOLD | Apache-2.0 | Skip | Backend-as-service generator; wrong domain for agent OS |
| Parlant | 5.85/10 | HOLD | Apache-2.0 | Skip | Chatbot governance framework; not applicable to dev agents |
| Strix | 3/10 | HOLD | Apache-2.0 | Skip | DAST pentesting tool; wrong domain entirely |
| Semgrep | -- | TRIAL | LGPL-2.1 | Integrate for SAST | Static analysis for security scanning; used as dynamic-linked CLI |
| SuperClaude | 22K stars | Reference | MIT | 6 patterns adapted | Prompt engineering library; no runtime code, patterns only |
| ClaudeClaw (robonuggets) | 6/15 | HOLD | -- | Skip | Documentation-only repo; no runnable code |
| ClaudeClaw (aravhawk) | 12/15 | Reference | -- | 3 patterns adapted | Messaging gateway with excellent engineering patterns |
| Sprut Agent Kit | 1.6/3 | Reference | MIT | 4 patterns adapted | Content creator toolkit with novel agent persistence ideas |
| Xetro.ai | -- | Competitor | Proprietary | Comparison only | Consultancy rebranded as product; no real OSS offering |
| QuinotoSpec | -- | Reference | -- | 3 patterns implemented | Sprint planning and governance patterns for agent systems |
| Hermes Agent (Nous Research) | 26/30 | ADOPT | MIT | 4 patterns + submodule | Self-reinforcing learning loop, 9431 LOC, 465 tests. memory_scanner.py, memory_retriever.py, feedback_detector.py |
| Pi Coding Agent | 25/30 | ADOPT | MIT | 4 patterns + submodule | Powers OpenClaw (160K+ stars), 7 packages, 161 tests. file_mutation_queue.py, compaction cut-points |

## Detailed Evaluations

### Firecrawl

**What it is**: Cloud-based web scraping service that converts pages to LLM-ready markdown.

**What we evaluated**: Web crawling capabilities, JavaScript rendering, structured extraction.

**Decision**: BLOCKED by AGPL-3.0 license. Even self-hosted, AGPL requires open-sourcing any network-facing service that uses it. This is incompatible with commercial SaaS deployment.

**What we took**: Nothing. Replaced entirely by Crawl4AI.

**What we skipped**: The entire tool. No partial adoption is safe under AGPL.

**Key learning**: Always check license before evaluating features. AGPL is a hard blocker for any SaaS product.

### Crawl4AI

**What it is**: Open-source async web crawler optimized for LLM data extraction.

**Score breakdown**: Functionality 10/10, License 10/10 (Apache-2.0), Integration 9/10.

**Decision**: ADOPT. Integrated as `lib/web_crawler.py` and `/web-crawler` skill.

**What we took**: Core crawling engine, markdown conversion, async batch processing.

**What we skipped**: Browser automation features (we use our own via Claude in Chrome MCP).

**Why it won**: Apache-2.0 license, local-first architecture, native markdown output for LLM consumption, async support for parallel crawling, no cloud dependency.

### InsForge

**What it is**: AI-powered backend-as-a-service that generates API endpoints from natural language.

**Decision**: HOLD. While technically interesting, it solves a different problem (backend generation) than what Cognitive OS addresses (agent orchestration and self-improvement).

**What we took**: Nothing directly. The concept of schema-driven code generation informed our SDD pipeline design.

**What we skipped**: The entire runtime. Wrong domain.

### Parlant

**What it is**: Governance framework for conversational AI agents (chatbots).

**Decision**: HOLD. Focused on chatbot compliance (response filtering, tone management) rather than developer agent orchestration.

**What we took**: Nothing directly. The concept of behavioral contracts influenced our constitutional gates design.

**What we skipped**: Chat-specific governance features (inappropriate for coding agents).

### Strix

**What it is**: Dynamic Application Security Testing (DAST) tool for penetration testing.

**Decision**: HOLD. DAST operates at runtime against deployed services; our security needs are better served by SAST (static analysis) during development.

**What we took**: Nothing. Wrong security layer entirely.

**What we skipped**: All runtime penetration testing features.

### Semgrep

**What it is**: Static Application Security Testing (SAST) tool with pattern-based code scanning.

**Decision**: TRIAL. Integrated as `hooks/semgrep-scan.sh` hook and `/semgrep-scan` skill.

**What we took**: CLI-based scanning integrated into the SDD post-apply pipeline. Findings are classified using the adversarial review tier system (BLOCKER/CONCERN/SUGGESTION).

**What we skipped**: Semgrep App (cloud dashboard), custom rule authoring (using community rules for now).

**License note**: LGPL-2.1 is acceptable because we use Semgrep as a dynamically-linked external CLI tool, not as an embedded library.

### SuperClaude

**What it is**: Community prompt engineering library with 22K+ GitHub stars. Collection of `.claude/` configuration patterns.

**Decision**: Reference only. No runtime code to integrate; it is a prompt library.

**What we took** (6 patterns):
1. Confidence check -- pre-implementation readiness assessment (became `/confidence-check` skill)
2. Deep research -- multi-hop reasoning with configurable depth (became `/deep-research` skill)
3. Self-review -- 4-question post-implementation checklist (became `/self-review` skill)
4. Implementation completeness -- no-TODO enforcement rule
5. PDCA mistake template -- structured error documentation format
6. Error signature matching -- Jaccard similarity for error deduplication (became `lib/error_matching.py`)

**What we skipped**: Persona definitions (we use agent definitions instead), style preferences (subjective), file-type rules (we have our own architecture rules).

### ClaudeClaw (robonuggets)

**What it is**: Repository with documentation about Claude agent patterns.

**Decision**: HOLD. Contains ideas but no executable code. Documentation quality is insufficient for direct adoption.

**What we took**: Nothing. Ideas only, no implementation to reference.

**What we skipped**: All content. Docs-only repositories do not meet our adoption threshold.

### ClaudeClaw (aravhawk)

**What it is**: JavaScript messaging gateway with excellent software engineering patterns.

**Score**: 12/15 on engineering quality assessment.

**Decision**: Reference. Three patterns adapted to our Python/bash stack.

**What we took** (3 patterns):
1. SecretRef -- configuration-level secret resolution pattern (became `lib/secret_ref.py`)
2. Tool group:ref syntax -- structured tool permission references (influenced agent identity protocol)
3. Structured error classifier -- error categorization pattern (became `lib/error_classifier.py`)

**What we skipped**: JavaScript runtime, messaging-specific features, WebSocket handling.

### Sprut Agent Kit

**What it is**: Content creator toolkit for AI agents with novel persistence patterns.

**Score**: 1.6/3 (decent ideas, limited implementation maturity).

**Decision**: Reference. Four patterns adapted.

**What we took** (4 patterns):
1. Memory decay -- time-based relevance scoring for persistent memory (became `lib/memory_decay.py`)
2. Anti-sycophancy -- rule prohibiting agent flattery (influenced trust score mandatory self-doubt)
3. Skill routing table -- mapping tasks to optimal skills (influenced `rules/model-routing.md`)
4. Persistent agent pattern -- data directory for agent state across sessions (became `/create-persistent-agent` skill)

**What we skipped**: Content creation workflows, social media integrations, audience analysis features.

### Xetro.ai

**What it is**: AI engineering consultancy that rebranded as a product company.

**Decision**: Comparison only. No open-source offering to evaluate. Useful for competitive positioning but not for technical adoption.

**What we took**: Nothing. Proprietary, no code available.

**What we skipped**: Everything. Consultancy model, not a product we can integrate.

### QuinotoSpec

**What it is**: Sprint planning and governance specification framework for agent systems.

**Decision**: Reference. Three patterns implemented.

**What we took** (3 patterns):
1. Contract drift detection -- detecting when implementation diverges from spec (became `tests/behavior/test_contract_drift.py`)
2. Proposal conflict detection -- identifying contradictions between concurrent proposals (became `tests/behavior/test_proposal_conflicts.py`)
3. Sprint contracts -- verification lines that must pass before implementation begins (influenced readiness-check skill)

**What we skipped**: Sprint velocity tracking (we use agent KPIs instead), team standup automation (wrong domain).

### Sazonia Archive (TAC Course)

**What it is**: "Tactical Agentic Coding" course materials by IndyDevDan.

**Decision**: Reference. Five infrastructure patterns implemented.

**What we took** (5 patterns):
1. ClaudeExecutor -- programmatic CLI invocation for Claude (became `lib/claude_executor.py`)
2. Batch runner -- parallel agent execution with result aggregation (became `lib/batch_runner.py`)
3. Resume from state -- session state persistence and recovery (became `lib/session_state.py`, `lib/sdd_resume.py`)
4. Notifications -- multi-channel notification system (became `lib/notifications.py`)
5. Issue-to-PR pipeline -- automated issue analysis to pull request creation (became `lib/issue_pipeline.py`)

**What we skipped**: Video-specific content, Cursor IDE integration, VS Code extension patterns.

### Anthropic Engineering (Harness Design Article)

**What it is**: Official Anthropic blog post on building evaluation harnesses for AI agents.

**Decision**: Reference. Three architectural patterns adopted.

**What we took** (3 patterns):
1. Generator-evaluator loop -- the core `sdd-apply` / `sdd-verify` retry cycle with max 3 retries
2. Sprint contracts -- verification criteria that must be defined before implementation begins
3. Skeptical evaluator -- adversarial review mandate (every review must find at least one issue)

**What we skipped**: Evaluation dataset construction (we use live metrics instead), benchmark-specific harness patterns.

---

## 2026-04-08: Hermes/Pi Deep Investigation

**Agents launched**: 11 agents, 2 investigation rounds.
**Models**: Opus (analysis), Sonnet (implementation).
**Duration**: Full maturation sprint.
**See**: `.cognitive-os/plans/research/hermes-pi-investigation.md` for full notes.

### Summary Table

| Tool | Score | Ring | License | Decision | Key Finding |
|------|-------|------|---------|----------|-------------|
| Hermes Agent (Nous Research) | 26/30 | ADOPT | MIT | 4 patterns adopted + submodule | Self-reinforcing learning loop is genuine, not cosmetic. 9431 LOC, 465 tests. Honcho memory = separate design from Engram (not a reinvention). |
| Pi Coding Agent | 25/30 | ADOPT | MIT | 4 patterns adopted + submodule | Powers OpenClaw (160K+ stars). File mutation queue solves a real parallel-agent problem COS had not addressed. 7-package monorepo, 161 tests. |

### Key Finding: COS Was 30% Real, 70% Aspirational

Pre-investigation audit revealed COS had 3 unjustified reinventions (Engram vs Honcho, Squads vs Composio, SDD vs Spec Kit) and 5 adopted-but-inactive tools. Maturation sprint executed to close the gap:

1. **Memory scanning** — Hermes had it as a core tool, COS had zero equivalent. Added `lib/memory_scanner.py`.
2. **File mutation safety** — Pi solved this at scale (OpenClaw production), COS had only advisory locks. Added `lib/file_mutation_queue.py`.
3. **Hybrid retrieval** — Hermes's holographic plugin showed vector-only Engram search was insufficient. Added `lib/memory_retriever.py`.
4. **Feedback detection** — Hermes's review agent concept, simplified to `lib/feedback_detector.py`.
5. **Compaction cut-points** — Pi's pattern reinforced correct placement of `pre-compaction-flush.sh` checkpoints.

### Reinvention Audit Results

| COS Component | Comparable External | Assessment | Decision |
|---------------|--------------------|---------| ---------|
| Engram (SQLite, topic keys) | Honcho (hierarchical, app/user/session) | Different designs, different use cases | NOT a reinvention — keep both |
| Squads (agent teams) | Composio (fleet management, worktrees) | Different scope — Squads is governance, Composio is execution | NOT a reinvention — different problem |
| SDD pipeline (7 phases) | Spec Kit (3 phases: req/design/tasks) | SDD is deeper (explore/verify/archive) but Spec Kit has broader adoption | NOT a reinvention — different depth |

All 3 were judged as justified independent development. No consolidation required.

### Hermes Evaluation

**Repository**: NousResearch/hermes-agent
**License**: MIT (confirmed — safe for all adoption modes)

**Score breakdown**:
- Functionality: 9/10 (learning loop is genuine and working)
- License: 10/10 (MIT)
- Maintenance: 7/10 (active but solo maintainer risk)
- Integration: 5/10 (Python monolith, requires architecture adaptation)
- Community: 5/10 (growing, research-focused)

**What we took** (4 patterns):
1. Memory scanning — `lib/memory_scanner.py`
2. Hybrid retrieval — `lib/memory_retriever.py`
3. Injection fencing concept — influenced content-policy hook
4. Feedback detection — `lib/feedback_detector.py`

**What we skipped**: Honcho backend (have Engram), FastAPI server, 9431-line monolith structure.

### Pi Evaluation

**Repository**: Pi-agent/pi
**License**: MIT (confirmed — safe for all adoption modes)

**Score breakdown**:
- Functionality: 9/10 (proven at OpenClaw scale, 160K+ stars)
- License: 10/10 (MIT)
- Maintenance: 8/10 (active team, multiple contributors)
- Integration: 5/10 (TypeScript, requires porting)
- Community: 8/10 (large via OpenClaw)

**What we took** (4 patterns):
1. File mutation queue — `lib/file_mutation_queue.py`
2. Compaction cut-points — influenced `hooks/pre-compaction-flush.sh`
3. Structural-test detection — now enforced through `tests/unit/test_cos_test_quality_audit_scope.py`
4. Settings override — influenced `cognitive-os.yaml` phase-aware config

**What we skipped**: TypeScript runtime, Pi's memory system, double-while loop architecture.

---

## Evaluation Methodology

Tools are scored using `lib/research_scoring.py` with weighted criteria:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Functionality | 30% | Does it solve the problem well? |
| License | 25% | Is the license compatible? (AGPL/SSPL = automatic 0) |
| Maintenance | 15% | Active development, responsive maintainers? |
| Integration | 15% | How easily does it fit into our stack? |
| Community | 15% | Adoption, documentation quality, ecosystem? |

Ring classifications follow the Technology Radar model:
- **ADOPT**: Use in production. Proven value.
- **TRIAL**: Worth pursuing. Use in non-critical paths first.
- **HOLD**: Wait and see. Interesting but not ready or not needed.
- **AVOID**: Do not use. License, quality, or domain mismatch.

---

## 2026-04-30: Tier-0 learning-loop closure

**ADR:** [ADR-074](adrs/ADR-074-tier-0-learning-loop-closure.md)  
**Effort:** ~1 hour  

A 4-agent audit earlier today (Engram: `cos-learning-loop-wiring-audit`) found that
5/7 learning-loop components were LIVE, 1 was DETACHED (`skill-feedback-tracker.sh`
never registered), and 1 was PARTIAL (`feedback_detector` — signals captured but
not consumed downstream). Three Tier-0 gaps were closed in this session:

**Files touched:**
- `scripts/apply-efficiency-profile.sh` — added `skill-feedback-tracker.sh` to
  the `standard` profile's PostToolUse[Agent] hook list
- `.claude/settings.json` — regenerated; hook now present in PostToolUse[Agent] block
- `lib/feedback_consumer.py` — new module (97 LOC) exposing `read_recent_feedback`,
  `group_by_classification`, `surface_actionable`, `summarise_for_skill_improvement`
- `skills/analyze-improvements/SKILL.md` — Step 0 updated to call
  `feedback_consumer.summarise_for_skill_improvement()` before analysis
- `skills/self-improve/SKILL.md` — Integration Points table updated to reference
  `feedback_consumer`
- `docs/adrs/ADR-074-tier-0-learning-loop-closure.md` — decision record

**Tests added:**
- `tests/unit/test_feedback_consumer.py` — 22 unit tests covering all public
  functions of `feedback_consumer`; all pass

**Key finding:** The `CORE_RULES=("RULES-COMPACT.md")` patch from a prior
investigation has no effect in this (self-hosting) repo because `IS_SELF_HOSTING=true`
bypasses the CORE_RULES list entirely. The patch is deferred to client-project
deployment paths only (documented in ADR-074 § Action 3).

---

## 2026-04-30: Stage 2 selective expansion (Tier 1 #4 from ADR-074)

**ADR**: [ADR-075](adrs/ADR-075-stage2-selective-expansion.md)

### Measured token impact

Expansion of `RULES-COMPACT.md` via `hooks/inject-phase-context.sh`:

| Mode | `wc -c` (chars) | Tokens (÷4 est.) | vs full |
|------|----------------|------------------|---------|
| Input — RULES-COMPACT alone | 8,561 | ~2,140 | — |
| `tier_filter=None` (full, no filter) | 428,886 | ~107,221 | baseline |
| `tier_filter={0}` (Tier-0 only) | 63,067 | ~15,766 | **–85%** |
| `tier_filter={0,1}` (default) | 408,832 | ~102,208 | –5% |

**Key insight**: The ~90K token savings claim from the task spec is achievable only
with `tier_filter={0}`. The conservative default `[0, 1]` (which includes the 95
Tier-1 rules) yields only ~5% savings over full expansion. Operators who need the
full 85% reduction must explicitly set `expansion.tier_filter: [0]` in
`cognitive-os.yaml` and monitor escalation rates.

### Files changed

- `rules/*.md` — 112 files: 9 Tier-0, 95 Tier-1, 8 Tier-2 frontmatter added
- `lib/ref_key_loader.py` — `expand()` gains `tier_filter` param; `_read_tier()` added
- `hooks/inject-phase-context.sh` — reads `expansion.tier_filter` from YAML
- `cognitive-os.yaml` — `expansion.tier_filter: [0, 1]` feature flag
- `tests/unit/test_ref_key_loader.py` — 10 new tier-filtering tests (23 total, all pass)
- `docs/adrs/ADR-075-stage2-selective-expansion.md` — decision record

## 2026-04-30: Tier 2 Hermes alignment (ADRs + skill frontmatter)

- **ADR-076** (`docs/adrs/ADR-076-skill-frontmatter-alignment.md`): Accepted.
  Aligns all COS SKILL.md files with the Hermes spec (tools/skills_tool.py lines 28-46,
  MIT). Three optional fields added: `version: "1.0.0"`, `platforms: ["claude-code"]`,
  `prerequisites: []`. Executed by `scripts/align_skill_frontmatter.py` — **142 skills updated**.
- **ADR-077** (`docs/adrs/ADR-077-peer-card-local-model.md`): Accepted.
  Local peer-card model as a Honcho replacement using Engram as backing store. Schema:
  name, role, preferences, communication_patterns, domain_expertise, recent_topics.
  Phase 1 decision: **no-embeddings v1 / FTS5-only** through Engram `mem_search`.
  Update cadence is event-driven for high-confidence durable signals with
  session-end consolidation for repeated medium-confidence signals. `/peer-card`
  UX exposes `read`, `edit`, `forget`, and `explain`; free-text edit proposes a
  minimal JSON patch before write. `sentence-transformers` is rejected for v1;
  `sqlite-vec` remains the preferred Phase 2 candidate only after a concrete
  retrieval gap is demonstrated. Implementation is ready. Engram topic:
  `cos/tier2-hermes-alignment`.

## 2026-04-30: Mid-task memory tool (Tier 1 #5)

**ADR**: [ADR-078](adrs/ADR-078-mid-task-memory-tool.md)

Closed the Hermes "mid-task memory scan as a tool" gap identified in ADR-074's
Tier-1 backlog. The Hermes design has agents invoke memory scanning mid-task as a
callable tool — this ADR ports that primitive.

### Ported

| File | LOC | Source |
|------|-----|--------|
| `lib/memory_manager.py` | ~420 | Hermes `agent/memory_manager.py:83-374` (verbatim) + thin local `MemoryProvider` ABC (~50 LOC) + `EngramMemoryProvider` concrete impl (~90 LOC) |
| `skills/memory-scan/SKILL.md` | ~100 | New — exposes `lib.memory_scanner` as agent-callable skill |
| `hooks/memory-prefetch.sh` | ~50 | New — async UserPromptSubmit hook |
| `tests/unit/test_memory_manager.py` | ~230 | 30 unit tests covering MemoryManager + context fencing |
| `tests/unit/test_engram_memory_provider.py` | ~170 | 23 unit tests covering EngramMemoryProvider + scanner smoke |

### Key decisions

- Honcho / Hindsight / Mem0 providers rejected (out of scope, SaaS dependencies).
- `EngramMemoryProvider` gracefully degrades when Engram binary is absent (CI-safe).
- Hook registered under `UserPromptSubmit` (async) — not `PreToolUse[Agent]` — to
  avoid adding latency to every tool sub-call.
- Mid-task invocation is **opt-in**: no automated injection per turn (follow-up item).

### Files changed

- `lib/memory_manager.py` (new)
- `skills/memory-scan/SKILL.md` (new)
- `hooks/memory-prefetch.sh` (new)
- `scripts/apply-efficiency-profile.sh` (hook registered)
- `tests/unit/test_memory_manager.py` (new, 30 tests)
- `tests/unit/test_engram_memory_provider.py` (new, 23 tests)
- `docs/adrs/ADR-078-mid-task-memory-tool.md` (new)

## 2026-04-30: CORE_RULES applies to self-hosting (ADR-079)

**Finding**: `hooks/self-install.sh` contained a hard-coded override
`IS_SELF_HOSTING=true → EFFICIENCY_PROFILE=full → SYNC_ALL_RULES=true` that
bypassed the CORE_RULES reduction from commit `991b24a`. Every COS development
SessionStart loaded 16 extra rule files that are already covered by Stage-2
expansion via `RULES-COMPACT.md`.

**Measured token savings**: 83,118 chars ÷ 4 ≈ **~20,779 tokens per SessionStart**
saved by removing the override. The 16 files are: ROADMAP.md,
acceptance-criteria.md, adaptive-bypass.md, agent-quality.md, bash-naming.md,
closed-loop-prompts.md, credential-management.md, definition-of-done.md,
error-learning.md, lane-taxonomy.md, model-routing.md, phase-aware-agents.md,
python-naming.md, result-management.md, token-economy.md, trust-score.md.

**Decision**: Remove the IS_SELF_HOSTING force; add `COS_SYNC_ALL_RULES=1`
opt-in env var for developers who need full symlink set. Fixed
`test_self_hosting_always_full` → `test_self_hosting_detects_but_no_longer_forces_full`.

**Files changed**: `hooks/self-install.sh`, `tests/unit/test_efficiency_stress.py`,
`docs/adrs/ADR-079-corerules-applies-to-self-hosting.md` (new)

## 2026-04-30: SessionStart deep audit (self-host vs client)

Full measurement doc: [`docs/measurements/sessionstart-baseline.md`](measurements/sessionstart-baseline.md)

Component-by-component audit of what gets loaded at SessionStart for this self-hosted repo
versus a fresh client install. Both modes use `efficiency.profile: default` after ADR-079.

### Key findings

- **Total SessionStart context (self-host, post-ADR-079)**: ~37,917 bytes / ~9,480 tokens
- **Total SessionStart context (client default)**: ~39,917 bytes / ~9,980 tokens
- **Largest components**: `~/.claude/CLAUDE.md` (11,125 B / ~2,781 T) and `CATALOG-COMPACT.md` (14,280 B / ~3,570 T)
- **CATALOG-COMPACT is always injected** via claudeMd (`.claude/skills/CATALOG-COMPACT.md` symlink), not lazy-loaded
- Commits today that affect SessionStart: only `991b24a` (client –16,775 T) and ADR-079 staged (self-host –20,779 T)
- Commits `c8a5259`, `e93e3b7`, `f360fe4` affect Stage-2 PreToolUse[Agent] expansion only, not SessionStart

### Top unexplored levers

1. **CATALOG-COMPACT lazy-load** (–3,570 T, medium risk)
2. **Global CLAUDE.md user trim** (–1,500–2,000 T, user-controlled)
3. **ROADMAP.md demotion from Tier-0** (–1,810 T, low risk)
4. **SessionStart hook stdout consolidation** (–300 T, low risk)
5. **MCP engram instructions defer** (–400 T, medium risk, upstream dependency)

## 2026-04-30: Hook timing instrumentation

### Context

User reported silent 2-7 minute hangs between turns with zero harness feedback. Existing `hook-health.jsonl` (via `hooks/_lib/safe-jsonl.sh`) logs `{timestamp, hook, exit_code, duration_ms}` for ~147 of 165 hooks, but lacks the harness event type — making it impossible to know whether a slow hook was in Stop, PreToolUse, or PostToolUse.

### What landed

- `scripts/hook-timing-wrapper.sh` — trampoline that wraps every hook command and appends `{timestamp, event, hook, duration_ms, exit_code, pid}` to `.cognitive-os/metrics/hook-timing.jsonl`. Best-effort: logging failures never break the hook chain. Kill-switch: `COS_HOOK_TIMING_DISABLE=1`.
- `scripts/apply-efficiency-profile.sh` — modified `hook_entry`/`hook_entry_async`/`hook_group` to route all 82 hook commands through the wrapper with the harness event name threaded through as the first wrapper arg.
- `.claude/settings.json` — regenerated; every command is now `bash "$CLAUDE_PROJECT_DIR/scripts/hook-timing-wrapper.sh" <EventName> "$CLAUDE_PROJECT_DIR/hooks/<hook>.sh"`.
- `scripts/hook_timing_report.py` — aggregation tool with p50/p95/p99 per hook, top-N slowest invocations, failure counts, `--live` tail mode, `--event`/`--since` filters, `--json` output.
- `docs/measurements/hook-timing-runbook.md` — operator runbook with diagnosis workflow.

### First measurements (immediately after landing)

From 536 invocations across 33 hooks (data accumulated during this session):

| Hook | p95 |
|---|---|
| content-policy | 4.3s |
| inject-phase-context | 3.8s |
| destructive-rm-blocker | 1.6s |
| confidentiality-enforcer | 1.1s |
| rate-limiter | 1.1s |

These five are the highest-priority candidates for async reclassification or optimization.

### Wrapper overhead

Measured ~93ms per wrapper invocation on macOS (2x python3 subprocess launches for millisecond timing: ~27ms each + bash overhead). With 82 hooks registered, worst-case blocking overhead from wrapping is ~7.6s but hooks only fire for specific events. The 93ms is negligible against 2-7 minute hangs.

### How to monitor live

```bash
python3 scripts/hook_timing_report.py --live
```

## 2026-04-30: Learning loop final 30% (Phase 1 ship + Phases 2/3 design)

**Session goal**: close the remaining 30% of the COS learning loop across three gaps.

**Gap #1 — Auto-action on skill failures (SHIPPED)**

- Verified `skill-feedback.jsonl` schema: `{timestamp, skill, success: bool}` (boolean, not string).
- Created `lib/skill_failure_repair.py`: three public functions (`find_failing_skills`, `propose_repair_action`, `emit_repair_signal`). Handles window filtering, stale-skill detection (deprecate heuristic), and error-uniformity heuristic (regenerate vs investigate).
- Created `hooks/skill-failure-monitor.sh`: Stop-event hook with 5-minute cooldown guard. Calls the Python module; emits signals to `skill-repair-queue.jsonl`. Does NOT auto-regenerate.
- Registered in `scripts/apply-efficiency-profile.sh` (Stop group, sync).
- Created `skills/repair-skill/SKILL.md`: gated consumer skill that reads queue and delegates to `/add-skill`, `/skill-creator`, or marks deprecation.
- 19 unit tests, all passing (`tests/unit/test_skill_failure_repair.py`).
- ADR-090 (Accepted): documents the detect→signal→gated-action design, the runaway-loop rationale, and threshold choices.

**Gap #2 — Skill synthesis from success patterns (ADR DESIGN ONLY)**

- ADR-095 (Proposed): documents three candidate definitions of "success pattern" (Options A/B/C), detection windows, recurrence thresholds, output formats (draft SKILL.md vs auto-create experimental tier).
- Key finding: `session-learnings.jsonl` does NOT capture per-task tool sequences; Option A (repeated successful skill invocations) is the only option implementable with current data. Options B/C require new instrumentation.
- Five open questions documented; must be answered before implementation sprint.
- NO code written for this gap.

**Gap #3 — Review-agent pattern (ADR DESIGN ONLY)**

- Researched Hermes `_spawn_background_review` in `.claude/plugins/hermes-agent/run_agent.py` (lines 2749–2828). Documented what is portable (prompt templates, iteration cap, pattern) vs what is not (AIAgent fork, threading.Thread, shared `_memory_store`).
- ADR-096 (Proposed): documents four design dimensions (when/what/output/cost gate), five open questions, and cost analysis (Haiku ≈ $0.075/day at 50 agents; Sonnet exceeds governance threshold).
- Key finding: review agent and skill synthesis (ADR-095) should be co-designed — reviewer is the natural detector for success patterns.
- NO code written for this gap.

**ADR numbers used**: 090, 095, 096 (089 was already taken by multi-session git coordination; 091-094 were taken by a concurrent ADR rename migration).

## 2026-05-01: Phase 3 review-agent pattern shipped (final 30% of learning loop)

**Session goal**: implement ADR-096 (review-agent pattern) — the last unimplemented gap in the learning loop.

### What shipped

- **`lib/review_agent.py`** (source: `packages/agent-lifecycle/lib/review_agent.py`): 6 public functions — `should_review` (stochastic + budget gate), `select_reviewer_model` (cross-review matrix), `build_review_prompt` (Hermes template adapted to COS TRUST_REPORT conventions), `parse_review_response` (structured extraction with graceful-failure mode), `persist_finding` (JSONL + Engram best-effort), `daily_budget_state` (load/rollover budget tracker). Module constants: `DEFAULT_SAMPLE_RATE=0.2`, `DEFAULT_MAX_PER_DAY=50`, `REVIEWER_MODEL_MATRIX`.
- **`hooks/review-spawner.sh`** (source: `packages/agent-lifecycle/hooks/review-spawner.sh`): PostToolUse[Agent] hook. Reads config from cognitive-os.yaml, applies stochastic + budget gate, selects reviewer model via cross-review matrix, builds prompt, dispatches via `lib/dispatch.py`, parses response, persists finding. v1 sync (documented latency).
- **`skills/review-output/SKILL.md`** (source: `packages/agent-lifecycle/skills/review-output/`): Operator skill for manual review trigger. Supports `--task-id <id>` and `--recent N`. Bypasses sample-rate, respects daily budget.
- **`cognitive-os.yaml review:` block**: `sample_rate`, `max_per_day`, `default_model`, `always_review_kinds`.
- **`tests/unit/test_review_agent.py`**: 40 unit tests covering all public functions and edge cases.
- **`tests/integration/test_review_agent_flow.py`**: 7 integration tests covering end-to-end flow with mock dispatcher.
- **ADR-096**: promoted from Proposed → Accepted. Design space collapsed to 8 locked decisions. Implementation section added.

### Key decisions

- v1 sync (not async). Documents latency cost explicitly in hook header. v2 async is a follow-up.
- Cross-review matrix enforced: haiku→sonnet, sonnet→opus, opus→sonnet.
- No automatic skill modification from findings. Findings surface to `/analyze-improvements`.
- Hermes prompt templates adapted (not copied verbatim): tool references replaced, TRUST_REPORT format aligned, rubber-stamp prevention instruction added.

### Cost envelope

At 20% sample rate + haiku reviewer: ~$0.02–$0.05/day. At 50 reviews/day cap + haiku: ~$0.075/day max. Within governance bounds (ADR-096 §Decision 4–5).
