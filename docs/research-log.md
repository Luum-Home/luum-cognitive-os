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
3. Structural tests — added `tests/structural/` directory
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
