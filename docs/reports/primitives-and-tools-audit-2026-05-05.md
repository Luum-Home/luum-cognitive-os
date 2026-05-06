# Primitive & Tool Adoption Audit — 2026-05-05

**Status**: research-only — no decisions, no integrations.
**Scope**: 41 repos/sources provided by the user; covers browser/scraping, agent orchestration, skills/primitives, memory/knowledge, and miscellaneous.
**Doctrine**: this audit applies the same discipline as `surface-5-tui-ui-candidates-2026-05-05.md`. License + reality + fit must be verified before any adoption. The Cognitive Prosthesis doctrine (real/measurable/reversible/honest/evidence-backed) governs all recommendations.

---

## Methodology

Metadata was collected via `gh repo view --json name,description,licenseInfo,stargazerCount,primaryLanguage,pushedAt,url` for each GitHub repo (41 calls). Repos returning data are treated as public and verifiable. Repos with `licenseInfo: null` are treated as unlicensed/unknown — conservative default is to study-only. Reality classification follows `scripts/aspirational_audit.py` conventions: REAL = stars + recent pushes + named maintainers + visible issue activity; DORMANT = stale last-push (>6 months); ASPIRATIONAL = claims-without-demonstrated-substance.

License hard gate: AGPL-3.0 and SSPL are substrate-blocked per `rules/license-policy.md`. MIT, Apache-2.0, BSD-3-Clause, MPL-2.0 are allowed. "Other" licenses require inspection before substrate use. CC BY-NC-4.0 (autoskills) blocks commercial substrate adoption.

Web searches and WebFetch reads supplemented gh metadata for repos where description alone was insufficient, focusing on architecture, registry mechanics, and fit with COS surfaces. The primitive registry question (user's explicit ask) was answered by inspecting all Skills/Primitives/Catalogs repos and the HKUDS/CLI-Anything description in detail.

---

## Skill / Primitive Registries — the "gestor de repositorios de primitivas" question

The user specifically asked: "hay supuestamente un gestor de repositorios de primitivas." After auditing the full list, three repos credibly function as primitive/skill registries or managers:

### The credible candidates

**1. HKUDS/CLI-Anything** (33,570 stars, Apache-2.0, Python, pushed 2026-05-05) — strongest registry claim.
CLI-Anything auto-generates `SKILL.md` files for any CLI tool and publishes them to a unified **CLI-Hub** catalog at `clianything.cc`. Agents can call `npx skills` to browse, select, and install skills autonomously. This is the closest thing on this list to a live, automated primitive registry: it has a meta-skill (discovery), a publication pipeline (SKILL.md → catalog), and a runtime that agents self-serve. Stars + daily pushes + production deployments confirm REAL status.

**2. midudev/autoskills** (5,089 stars, CC BY-NC-4.0, Ruby, pushed 2026-05-04) — project-scoped skill installer.
autoskills scans your project's tech stack and installs curated AI agent skills from a pre-verified registry. SHA-256 hash verification before write. License CC BY-NC-4.0 blocks commercial substrate use, but the _architecture_ (detect-stack → match-registry → verify-hash → install) is a pattern worth copying. Most comparable to what a future COS `install-recommended` CLI could look like.

**3. obra/superpowers** (179,318 stars, MIT, Shell, pushed 2026-05-05) — skill collection, not a registry manager.
Superpowers is a skills _framework_ and methodology, not a catalog or installer. It provides an organized library of composable skills (TDD, planning, review, worktree management) with a philosophy-first approach. It does not have registry/discovery mechanics. It is the leading Claude Code skills reference in the community. MIT license makes it fully adoptable.

**Verdict**: HKUDS/CLI-Anything is the most credible "gestor de repositorios de primitivas" on this list. It has working discovery mechanics, an active catalog, and permissive licensing. autoskills is the second candidate architecturally, but its license blocks substrate use. obra/superpowers is a canonical skills library that is not itself a manager.

There is a fourth candidate outside this list worth naming for context: the Anthropic official `skills` format (SKILL.md convention) that all three above reference — this is the de-facto standard for Claude Code skill packaging.

---

## Per-repo audit

### Browser / scraping / data layer

| Repo | License | Stars | Lang | Last push | Reality | Fit | Recommendation |
|---|---|---|---|---|---|---|---|
| lightpanda-io/browser | **AGPL-3.0** | 30,024 | Zig | 2026-05-05 | REAL | Poor (license block) | reject (substrate); reference only |
| volcengine/OpenViking | **AGPL-3.0** | 23,482 | Python | 2026-05-04 | REAL | Medium (architecture patterns) | reject (substrate); pattern-only |
| D4Vinci/Scrapling | BSD-3-Clause | 45,153 | Python | 2026-05-05 | REAL | Medium | adopt-pattern-only |
| daijro/camoufox | MPL-2.0 | 7,984 | C++ | 2026-04-29 | REAL | Low (anti-detect focus) | reference |
| projectdiscovery/katana | MIT | 16,655 | Go | 2026-05-05 | REAL | Medium | adopt-pattern-only |
| xcrawl-api/xcrawl-skills | **None** | 390 | None | 2026-03-20 | DORMANT | Low | reject |

**lightpanda-io/browser** is technically impressive (headless browser in Zig, AI-first design, 30k stars, daily commits) but AGPL-3.0 is a hard substrate block. The architecture is worth studying for any future COS surface that needs headless browsing. **Scrapling** (BSD-3-Clause, 45k stars) is REAL and production-grade — its adaptive element tracking and built-in MCP server could complement the `web-crawler` skill, but COS already has Firecrawl integration (`packages/`) so adoption requires justified gap analysis first. **Katana** (MIT, Go) is a serious crawling framework from ProjectDiscovery; relevant if COS ever needs structured spidering beyond what Firecrawl provides. **OpenViking** (AGPL) has genuinely interesting architecture — a `viking://` filesystem protocol with L0/L1/L2 tiered context delivery that maps cleanly to COS context-management concerns, but the AGPL block stands. Pattern-study the tiered delivery model.

---

### Agent orchestration / multi-agent / harness

| Repo | License | Stars | Lang | Last push | Reality | Fit | Recommendation |
|---|---|---|---|---|---|---|---|
| agentscope-ai/agentscope | Apache-2.0 | 24,618 | Python | 2026-04-30 | REAL | Low-Medium | reference |
| ComposioHQ/agent-orchestrator | MIT | 6,816 | TypeScript | 2026-05-05 | REAL | Medium | adopt-pattern-only |
| HKUDS/OpenHarness | MIT | 11,963 | Python | 2026-05-03 | REAL | **High** | adopt-as-substrate candidate |
| HKUDS/OpenSpace | MIT | 6,025 | Python | 2026-04-16 | REAL | Medium | reference |
| HKUDS/CLI-Anything | Apache-2.0 | 33,570 | Python | 2026-05-05 | REAL | **High** | adopt-as-substrate candidate |
| JackChen-me/open-multi-agent | MIT | 6,048 | TypeScript | 2026-05-05 | REAL | Medium | adopt-pattern-only |
| multica-ai/multica | **Other** | 24,816 | TypeScript | 2026-05-04 | REAL | Low | reference (license unclear) |
| floci-io/floci | MIT | 4,360 | Java | 2026-05-05 | REAL | None (AWS emulator) | reject |
| mindsdb/anton | MIT | 652 | Python | 2026-05-05 | DORMANT-leaning | Low | reject |
| garrytan/gbrain | MIT | 13,265 | TypeScript | 2026-05-05 | REAL | **High** | adopt-as-substrate candidate |
| NousResearch/hermes-agent-self-evolution | **None** | 2,793 | Python | 2026-03-29 | DORMANT | Medium (patterns) | pattern-only |
| gepa-ai/gepa | MIT | 4,216 | Jupyter Notebook | 2026-05-05 | REAL | **High** | adopt-pattern-only |
| Mirix-AI/MIRIX | Apache-2.0 | 3,532 | Python | 2026-04-28 | REAL | Low | reference |
| gnekt/My-Brain-Is-Full-Crew | Other | 3,000 | Shell | 2026-04-12 | ASPIRATIONAL | None | reject |

**floci-io/floci**: Description says "AWS Local Emulator" — mismatch with this audit category entirely. Reject.

**HKUDS cluster** (OpenHarness + OpenSpace + CLI-Anything): This is the most interesting family in the list. OpenHarness provides lightweight agent infrastructure (tool registry, skills system, memory, multi-agent coordination) with MIT license and 12k stars. Its skills system is explicitly compatible with the `anthropics/skills` format, meaning it would plug into COS's existing skill conventions. CLI-Anything (covered above) is the registry manager. OpenSpace adds self-evolution capabilities. The HKUDS team appears to be building a coherent agent OS layer; the three repos together cover harness + skill-registry + agent-adaptation.

**garrytan/gbrain**: 13k stars, MIT, TypeScript, Garry Tan's production system managing 17k pages, 4k people, 723 companies. The RESOLVER.md dispatcher (routing intents to specific workflows), 34 bundled skills, MCP server with 30+ tools, and hybrid search (vector + keyword + RRF) make this highly relevant to COS's `lib/dispatch.py` (ADR-049) and skill routing. It is an opinionated but real system.

**gepa-ai/gepa**: GEPA (Genetic-Pareto text evolution) achieves 90x cost reduction vs. Opus-class models on documented benchmarks. Its Reflective Text Evolution approach (execute → trace → diagnose → mutate) overlaps with COS's `self-improve` skill and the `metrics-calibrator` primitive. MIT license, 4k stars, production adoption at Shopify/Databricks. Pattern-study or light adoption candidate.

**open-multi-agent**: TypeScript, MIT, automatic task DAG from a single goal string, 3 runtime dependencies, MCP integration, live tracing with HTML dashboards. This overlaps significantly with COS's `task-dag` concept in RULES-COMPACT.md §11. Three dependencies makes integration feasible.

**NousResearch/hermes-agent-self-evolution**: No license file and last push was 2026-03-29 (dormant). The DSPy + GEPA integration for skill/prompt optimization is a valuable pattern — see GEPA above — but the repo itself is not adoptable.

---

### Skills / primitives / catalogs

| Repo | License | Stars | Lang | Last push | Reality | Fit | Recommendation |
|---|---|---|---|---|---|---|---|
| midudev/autoskills | **CC BY-NC-4.0** | 5,089 | Ruby | 2026-05-04 | REAL | Medium (architecture) | pattern-only |
| mattpocock/skills | MIT | 60,891 | Shell | 2026-04-30 | REAL | **High** | adopt-as-substrate candidate |
| forrestchang/andrej-karpathy-skills | **None** | 113,817 | None | 2026-04-20 | REAL | High (single CLAUDE.md) | reference |
| luongnv89/claude-howto | MIT | 31,242 | Python | 2026-05-02 | REAL | Medium | reference |
| shanraisshan/claude-code-best-practice | MIT | 51,165 | HTML | 2026-05-05 | REAL | Medium | reference |
| affaan-m/everything-claude-code | MIT | 173,907 | JavaScript | 2026-05-03 | REAL | **High** | adopt-pattern-only |
| obra/superpowers | MIT | 179,318 | Shell | 2026-05-05 | REAL | **High** | adopt-as-substrate candidate |
| gsd-build/get-shit-done | MIT | 60,218 | JavaScript | 2026-05-05 | REAL | **High** | adopt-pattern-only |
| Mibayy/token-savior | MIT | 797 | Python | 2026-05-04 | REAL | **High** | adopt-as-substrate candidate |
| lhr-present/tokenshrink | **None** | 3 | JavaScript | 2026-04-06 | ASPIRATIONAL | None | reject |

This is the most important section per the user's question.

**mattpocock/skills** (MIT, 60k stars, Shell): Matt Pocock's personal `.claude` directory published as the reference implementation for real-world Claude Code skills from production engineering. The 60k stars and sustained activity signal community adoption at scale. This is a best-practices corpus, not a registry, but it is the single most credible signals source for what patterns are actually working in production.

**affaan-m/everything-claude-code** (MIT, 173k stars): 48 agents, 182 skills, 68 commands, 34 rule sets, 20+ hooks, cross-harness support (Claude Code, Cursor, Codex, OpenCode). This is the largest open-source skills-and-rules collection. Critically: it calls out "research-first development" as a pattern and has an `AgentShield` layer with 102 static analysis rules — both resonate with COS doctrine. However at this scale, any adoption decision must be scope-limited; adopting whole-cloth would violate the subtraction doctrine.

**obra/superpowers** (MIT, 179k stars): The most mature methodology framework. Seven-phase workflow (Brainstorm → Spec → Plan → TDD → Subagent Dev → Review → Finalize) enforced via skills. Now in the official Anthropic marketplace. Its subagent-driven development model and TDD discipline match COS's `test-driven-development` and `verification-before-completion` primitives.

**gsd-build/get-shit-done** (MIT, 60k stars): Spec-driven development system with six commands forming a repeatable loop and explicit artifact persistence (`PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `CONTEXT.md`). This overlaps substantially with COS's own SDD workflow. The key difference: GSD's `STATE.md` and `CONTEXT.md` artifacts are flat files; COS uses Engram for the same purpose. GSD is worth studying as a cross-validation of COS's own SDD design.

**token-savior** (MIT, 797 stars, Python): Small star count but credible claims: structural code navigation (symbol-indexed access vs. full-file reads), Bayesian validity scoring, contradiction detection, progressive-disclosure contracts (3-layer), and −77% token reduction on 96 real tasks. This MCP server addresses the same problem as COS's `context-management` rule and `caveman`/`caveman-compress` primitives but via a different mechanism (structural navigation vs. compression). High fit for the `lib/` layer.

**forrestchang/andrej-karpathy-skills** (no license, 113k stars): A single CLAUDE.md derived from Karpathy's observations. Enormous community reach but no license declaration means adoption carries risk. Read it as a reference; do not copy verbatim.

---

### Memory / knowledge / context

| Repo | License | Stars | Lang | Last push | Reality | Fit | Recommendation |
|---|---|---|---|---|---|---|---|
| memvid/memvid | Apache-2.0 | 15,344 | Rust | 2026-03-16 | DORMANT | Medium | pattern-only |
| MemPalace/mempalace | MIT | 51,234 | Python | 2026-05-03 | REAL | High | adopt-pattern-only |
| safishamsi/graphify | MIT | 43,275 | Python | 2026-05-05 | REAL | **High** | adopt-as-substrate candidate |
| yifanfeng97/Hyper-Extract | Other | 829 | Python | 2026-04-30 | REAL | Low | reference |
| mindfold-ai/Trellis | **AGPL-3.0** | 7,167 | TypeScript | 2026-05-05 | REAL | Medium (AGPL block) | reject (substrate); pattern-only |
| Gentleman-Programming/engram | MIT | 3,221 | Go | 2026-05-05 | REAL | **Critical** | special — see below |
| egdev6/engram-monitor | None | 36 | TypeScript | 2026-04-25 | REAL | Medium | reference |

**Gentleman-Programming/engram** requires special attention. This is a Go binary with SQLite + FTS5, MCP server, HTTP API, CLI, and TUI — which is the same system COS already uses as its Engram layer. The `feat/integrate-engram-cloud` branch directly corresponds to ADR-141 (Engram Cloud as cross-instance replication transport). This is not a separate project to adopt — it IS the upstream for COS's Engram. The branch adds `engram cloud config/enroll`, autosync, and upgrade tooling. Monitoring this branch for merge-ready status is mandatory before any multi-instance COS deployment. MIT license, Go binary, minimal dependencies.

**egdev6/engram-monitor** (no license, 36 stars): A TypeScript dashboard for monitoring Engram events. No license = cannot adopt as substrate. But it represents a proof-of-concept for what COS's `Surface 2` (Engram monitoring panel) could look like. Tag as reference for ADR-172 Surface 2 design.

**MemPalace/mempalace** (MIT, 51k stars, Python): 96.6% retrieval recall (R@5) on LongMemEval. Local-first. No API calls required. Hierarchical memory organization (wings > rooms > drawers) with pluggable retrieval backends. This is architecturally complementary to COS Engram (which covers decision/session memory) — MemPalace targets verbatim conversation retrieval. The pattern (scoped search + retrieval recall benchmarks + no-cloud default) is worth adopting into any Engram retrieval improvements.

**graphify** (MIT, 43k stars, Python): Builds a queryable knowledge graph from code, SQL schemas, scripts, docs, papers, videos — with tree-sitter AST parsing (no API calls for code), multi-platform agent support, and an MCP server. Installs as a `/graphify` skill in Claude Code. COS does not currently have a code knowledge graph primitive. Graphify would strengthen the `primitive-usage-map` and `impact-analysis` skills by providing a static graph layer that does not depend on LLM read-on-demand.

**memvid** (Apache-2.0, Rust, 15k stars): Last push 2026-03-16 (DORMANT by 7 weeks). The single-file `.mv2` architecture (BM25 + HNSW + temporal index, no server) is architecturally novel. Apache-2.0 allows adoption. However, the dormancy and the fact that COS Engram already covers persistent memory makes this pattern-study only.

**Trellis** (AGPL-3.0): "The best agent harness." 7k stars, very active. But AGPL-3.0 is a substrate block. Study patterns, cannot adopt.

---

### Other

| Source | Type | Reality | Notes | Recommendation |
|---|---|---|---|---|
| gist rohitg00/2067... | GitHub Gist | REAL (content) | LLM Wiki v2: 3-layer knowledge architecture, decay/reinforcement, four consolidation tiers (working→episodic→semantic→procedural), event-driven hooks. No license. | reference |
| ccleaks.com | Website | REAL | Reverse-engineered Claude Code source analysis site. Newsroom-grade audit of CC's 512K-line TypeScript codebase. Covers hidden models, pricing tiers, permission bypass vectors, multi-agent swarm protocol. |  out-of-scope for adoption |

**ccleaks.com** is a legitimate investigative analysis site (registered domain, The Register coverage, HN thread), not a leak aggregator in the malicious sense. However, it is a content site, not an adoptable codebase. Its architectural breakdown of Claude Code internals (boot sequence, 43-tool execution engine, query loop, MCP integration) is high-quality reference material for understanding the substrate COS runs on, but nothing to integrate. Flag as out-of-scope for code adoption.

**gist rohitg00**: The LLM Wiki v2 content describes production memory architecture patterns (four consolidation tiers, confidence decay, event hooks for ingestion) that directly match COS Engram's design space. The four-tier model (working → episodic → semantic → procedural) is not currently explicit in COS's Engram taxonomy. Worth incorporating into Engram's documentation as a reference framework. No code, no license concern.

---

## Top picks for adoption (max 5)

### 1. graphify (safishamsi/graphify) — adopt-as-substrate
**Gap it fills**: COS has no static code knowledge graph. `primitive-usage-map` and `impact-analysis` skills operate on LLM-read files; graphify would provide a pre-built, AST-accurate dependency graph layer at near-zero token cost.
**Fit**: The `/graphify` Claude Code skill integrates directly with the COS skill format. The MCP server variant would expose the graph to all running agents. Tree-sitter parsing means local execution without API calls.
**Why not build from scratch**: 43k stars, 26 language support, benchmarked on real codebases, multi-harness tested. Building equivalent AST graph infrastructure would take months and is not core COS IP.
**Risk**: Python dependency; multi-language support means the dependency surface is larger than it appears. Run `graphify .` on the COS repo and verify output before committing.

### 2. Gentleman-Programming/engram (feat/integrate-engram-cloud) — track as upstream
**Gap it fills**: This IS COS Engram upstream. The cloud branch adds exactly what ADR-141 specifies (cross-instance replication). Not an "adoption" decision — it is a "watch and cherry-pick" decision.
**Action needed**: Monitor this branch weekly. When `engram cloud enroll` and autosync stabilise, cherry-pick or vendor the upgrade tooling. No architecture decision required — it is already architecturally aligned.

### 3. token-savior (Mibayy/token-savior) — adopt as MCP layer
**Gap it fills**: COS `context-management` rule currently relies on character-count thresholds. Token-savior's structural navigation (symbol → pointer, not whole-file reads) and Bayesian memory validity scoring would make the rule computable, not just heuristic.
**Fit**: MCP server architecture means it drops into any MCP-capable harness. The −77% token reduction claim has 96 real tasks behind it, which meets COS's evidence bar.
**Why not build from scratch**: The core structural navigation logic (tree-sitter + symbol indexing + progressive-disclosure contracts) is well-defined and testable but non-trivial to build correctly.

### 4. HKUDS/OpenHarness — adopt-as-substrate candidate for harness layer
**Gap it fills**: OpenHarness provides a 10-subsystem harness scaffold (tool registry + skills + memory + multi-agent + safety) that is explicitly compatible with the `anthropics/skills` SKILL.md format. COS builds its own harness primitives incrementally; OpenHarness provides a reference implementation with 12k stars of validation.
**Fit**: MIT license, Python (COS-native), skills system compatible with COS skill format, plugin system following Claude Code conventions. Low integration friction.
**Caveat**: HKUDS has three repos (OpenHarness + OpenSpace + CLI-Anything) that may have inter-dependencies. Audit them as a trio before isolated adoption.

### 5. MemPalace/mempalace — adopt-pattern into Engram retrieval
**Gap it fills**: COS Engram does not publish retrieval recall benchmarks. MemPalace's 96.6% R@5 on LongMemEval and its hybrid BM25 + semantic + scoped-search architecture represent a validated retrieval pattern that could improve Engram's FTS5-based search.
**Fit**: MIT, Python, no-cloud default, pluggable backends. Its hierarchical memory organization (wings > rooms > drawers) maps to COS's Engram topic-key hierarchy.
**Why pattern-over-substrate**: COS already has a running Engram. MemPalace is not a drop-in replacement; it is a source of retrieval improvement patterns and benchmark targets.

---

## Top picks for pattern study only (max 5)

1. **volcengine/OpenViking** (AGPL block) — Tiered context delivery (L0/L1/L2 on-demand) reduced token cost by 83-96% in their benchmark. The `viking://` filesystem protocol for context organization is a pattern COS's context-management rules could encode.

2. **gsd-build/get-shit-done** (MIT) — Cross-validation of COS's SDD pipeline. GSD's `STATE.md` + `CONTEXT.md` persistence model for multi-session workflows offers a flat-file fallback pattern when Engram is unavailable. The six-command loop (init → discuss → plan → execute → verify → ship) is a simplified, auditable version of the COS SDD workflow.

3. **gepa-ai/gepa** (MIT) — Reflective Text Evolution (execute → trace → reflect → mutate) is a principled prompt/skill optimization primitive. Study for potential integration into the `self-improve` skill. The Pareto-frontier selection strategy prevents single-objective overfitting. 90x cost reduction claim is production-verified.

4. **affaan-m/everything-claude-code** (MIT) — AgentShield's 102 static analysis rules for agent harnesses. This is a live benchmark for what COS's `security-audit` and `agent-security` primitives should cover. Cross-reference the rule list against COS's existing rules to identify gaps.

5. **gist rohitg00** — Four-tier memory consolidation model (working → episodic → semantic → procedural). Formalises COS Engram's implicit consolidation behavior. Recommend incorporating this framing into Engram's architectural documentation.

---

## Aspirational / risky / abandoned (do not adopt)

- **lhr-present/tokenshrink** — 3 stars, no license, last push April 2026. ASPIRATIONAL.
- **xcrawl-api/xcrawl-skills** — No license, no primary language, 390 stars, stale since March 2026. DORMANT + unlicensed.
- **floci-io/floci** — AWS local emulator in Java. Not relevant to this audit.
- **mindsdb/anton** — 652 stars, described as "AI coworker" with no clear differentiator. DORMANT-leaning.
- **gnekt/My-Brain-Is-Full-Crew** — Non-commercial license ("Other"), personal project (nutrition + mental wellness + knowledge), no transferable primitives. ASPIRATIONAL scope.
- **NousResearch/hermes-agent-self-evolution** — No license, dormant since March 2026. DORMANT + unlicensed.
- **mindfold-ai/Trellis** — AGPL-3.0 substrate block. Self-described "best agent harness" — bold claim for 7k stars. Cannot adopt.
- **lightpanda-io/browser** — AGPL-3.0 substrate block despite being genuinely impressive (Zig, 30k stars, AI-first).
- **yifanfeng97/Hyper-Extract** — "Other" license (non-standard), 829 stars. Study once license is clarified.
- **garrytan/gbrain** — MIT, 13k stars, legitimately interesting. Excluded from top-5 not because it's weak but because its PostgreSQL dependency and opinionated persona (Garry Tan's personal deployment) make it a pattern reference rather than a drop-in substrate for COS. The RESOLVER.md dispatcher pattern is the transferable part.
- **multica-ai/multica** — "Other" license. Cannot advise substrate use until the license file is read and confirmed not BSL/SSPL.

---

## Sources

- https://github.com/lightpanda-io/browser
- https://github.com/volcengine/OpenViking
- https://github.com/D4Vinci/Scrapling
- https://github.com/daijro/camoufox
- https://github.com/projectdiscovery/katana
- https://github.com/xcrawl-api/xcrawl-skills
- https://github.com/agentscope-ai/agentscope
- https://github.com/ComposioHQ/agent-orchestrator
- https://github.com/HKUDS/OpenHarness
- https://github.com/HKUDS/OpenSpace
- https://github.com/HKUDS/CLI-Anything
- https://clianything.cc/
- https://github.com/JackChen-me/open-multi-agent
- https://github.com/multica-ai/multica
- https://github.com/floci-io/floci
- https://github.com/mindsdb/anton
- https://github.com/garrytan/gbrain
- https://github.com/NousResearch/hermes-agent-self-evolution
- https://github.com/gepa-ai/gepa
- https://github.com/Mirix-AI/MIRIX
- https://github.com/gnekt/My-Brain-Is-Full-Crew
- https://github.com/midudev/autoskills
- https://github.com/mattpocock/skills
- https://github.com/forrestchang/andrej-karpathy-skills
- https://github.com/luongnv89/claude-howto
- https://github.com/shanraisshan/claude-code-best-practice
- https://github.com/affaan-m/everything-claude-code
- https://github.com/obra/superpowers
- https://github.com/gsd-build/get-shit-done
- https://github.com/Mibayy/token-savior
- https://github.com/lhr-present/tokenshrink
- https://github.com/memvid/memvid
- https://github.com/MemPalace/mempalace
- https://github.com/safishamsi/graphify
- https://github.com/yifanfeng97/Hyper-Extract
- https://github.com/mindfold-ai/Trellis
- https://github.com/Gentleman-Programming/engram
- https://github.com/Gentleman-Programming/engram/tree/feat/integrate-engram-cloud
- https://github.com/egdev6/engram-monitor
- https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2
- https://ccleaks.com/
- https://ccleaks.com/architecture
- https://dev.to/imaginex/a-claude-code-skills-stack-how-to-combine-superpowers-gstack-and-gsd-without-the-chaos-44b3
- https://medium.com/@tentenco/superpowers-gsd-and-gstack-what-each-claude-code-framework-actually-constrains-12a1560960ad
- https://awesomeclaudeskills.com/skill/obra/superpowers
- https://www.firecrawl.dev/blog/best-claude-code-skills
- https://news.ycombinator.com/item?id=47586778
- https://www.theregister.com/2026/03/31/anthropic_claude_code_source_code/
