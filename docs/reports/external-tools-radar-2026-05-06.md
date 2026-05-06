---
report_type: external-tools-radar
date: 2026-05-06
source_clusters: 20
total_repos_audited: 235
total_pass_to_deep: 95
top_priority_count: 22
parent_inventory: docs/reports/external-tools-inventory-2026-05-06.md
budget_used_tool_calls: ~22
---

# External Tools Radar — 2026-05-06

Consolidation of 20 shallow cluster scouts into a single Phase-2 prioritization document. All cluster verdicts trusted as source-of-truth — this radar reorders by cross-cluster theme and surfaces extractable primitives over framework-fit.

## 1. Executive Summary

Five priorities to launch first into Phase 2 (deep audit). Each is the highest-signal primitive in its domain after de-duplicating across clusters:

- **obra/superpowers** (agent-swe, MIT, 179k★) — direct peer to COS skills system + methodology. Highest learn-rate target; shell-first means low porting cost. Compare skill schema, trigger conditions, methodology against COS rules/skills/RULES-COMPACT.
- **HKUDS/LightRAG + OSU-NLP-Group/HippoRAG** (memory-graph-rag, both MIT) — small extractable retrieval algorithms (dual-level retrieval, Personalized PageRank multi-hop) that drop into Engram without framework adoption.
- **stanfordnlp/dspy** (agent-experimental-A, MIT, 34k★) — Signatures/Modules/Optimizers map directly onto skill composition + agent quality gates (RULES §2, §8). Foundational for hermes-agent-self-evolution Phase-2 (which depends on DSPy).
- **coder/agentapi** (agent-wrappers, MIT, Go) — HTTP normalization across heterogeneous agent CLIs (Claude Code/Goose/Aider/Gemini/Amp/Codex). Direct fit for ADR-033 harness-agnostic event capture and `lib/harness_adapter/`.
- **snyk/agent-scan + praetorian-inc/augustus** (security-supply, both Apache-2.0) — clean delta vs Aguara: agent/MCP/skill-targeted scanning + 190-probe offensive corpus. Both Phase-2 to land before flow #1 promotion (per ADR-139..142).

## 2. Top-Tier Phase 2 Candidates (ranked by theme)

22 highest-priority pass-to-deep across clusters. Grouped by theme; license / stars / one-line WHY (extractable primitive).

### 2.1 Skills, Methodology, and Cross-Harness Standards
1. **obra/superpowers** — https://github.com/obra/superpowers — MIT — 179,656★ — Skill schema + agentic-engineering methodology peer to COS; compare against rules/skills/RULES-COMPACT.
2. **agentsmd/agents.md** — https://github.com/agentsmd/agents.md — MIT — 21,008★ — AGENTS.md cross-harness spec primitive COS lacks; emitter for `cognitive-os-init`.
3. **affaan-m/everything-claude-code** — https://github.com/affaan-m/everything-claude-code — MIT — 174,106★ — Skills/instincts/memory model + cross-harness abstraction; compare to skill registry + ADR-033.
4. **dmgrok/agent_skills_directory** — https://github.com/dmgrok/agent_skills_directory — MIT — 15★ — Skill quality-validation + security-scan scoring heuristics for `skill-router` ranking (low stars, novel primitive).

### 2.2 Memory, Graph, and Retrieval Algorithms
5. **HKUDS/LightRAG** — https://github.com/HKUDS/LightRAG — MIT — 34,788★ — Dual-level (entity+topic) retrieval algorithm; portable into Engram retrieval layer.
6. **OSU-NLP-Group/HippoRAG** — https://github.com/OSU-NLP-Group/HippoRAG — MIT — 3,483★ — Personalized PageRank multi-hop recall over entity graph; small algorithm port.
7. **getzep/graphiti** — https://github.com/getzep/graphiti — Apache-2.0 — 25,732★ — Bi-temporal edge schema (event-time vs ingest-time) — known gap in Engram model.
8. **MemPalace/mempalace** — https://github.com/MemPalace/mempalace — MIT — 51,256★ — Benchmark-led memory system; harvest scoring/eviction patterns to compare with Engram.
9. **Mibayy/token-savior** — https://github.com/Mibayy/token-savior — MIT — 799★ — MCP server claiming -77% tokens via structural code-nav + memory hybrid; sidecar candidate.

### 2.3 LLM Dispatch / Routing / Agent Plumbing
10. **simonw/llm** — https://github.com/simonw/llm — Apache-2.0 — 11,789★ — Plugin/provider architecture; map to `lib/dispatch.py` (ADR-049).
11. **musistudio/claude-code-router** — https://github.com/musistudio/claude-code-router — MIT — 33,483★ — Provider routing transforms + auth handling; same harness as ours.
12. **coder/agentapi** — https://github.com/coder/agentapi — MIT — 1,373★ — HTTP normalization across 6+ agent CLIs; uniform event schema for ADR-033.
13. **BeehiveInnovations/pal-mcp-server** — https://github.com/BeehiveInnovations/pal-mcp-server — Apache-2.0 — 11,513★ — Multi-model MCP bridge; cross-provider routing patterns.

### 2.4 Self-Evolution / Research-Grade Agents
14. **stanfordnlp/dspy** — https://github.com/stanfordnlp/dspy — MIT — 34,216★ — Signatures/Modules/Optimizers; foundational for prompt/skill composition + hermes-self-evolution.
15. **gepa-ai/gepa** — https://github.com/gepa-ai/gepa — MIT — 4,225★ — Reflective text-evolution primitive for prompts/code; pairs with dspy.
16. **NousResearch/hermes-agent** — https://github.com/NousResearch/hermes-agent — MIT — 134,556★ — Flagship adaptive agent; high mindshare, on-theme.
17. **coleam00/Archon** — https://github.com/coleam00/Archon — MIT — 20,862★ — Harness builder focused on deterministic/repeatable AI coding.

### 2.5 SWE-bench / Coding Agents
18. **SWE-agent/SWE-agent** — https://github.com/SWE-agent/SWE-agent — MIT — 19,142★ — ACI design (bash tool surface, file viewer, edit semantics) reference.
19. **Aider-AI/aider** — https://github.com/Aider-AI/aider — Apache-2.0 — 44,382★ — Edit-block diff format + repo-map context-selection heuristic.

### 2.6 Security / Supply-Chain
20. **snyk/agent-scan** — https://github.com/snyk/agent-scan — Apache-2.0 — 2,347★ — Agent/MCP/skill-specific security scanner; clean delta vs Aguara.
21. **praetorian-inc/augustus** — https://github.com/praetorian-inc/augustus — Apache-2.0 — 203★ — 190-probe offensive corpus, single Go binary; complements Aguara defense.

### 2.7 Browser / Web Surface
22. **unclecode/crawl4ai** — https://github.com/unclecode/crawl4ai — Apache-2.0 — 65,073★ — LLM-native crawler (markdown + structured extraction) for agent web-research/RAG ingestion.

(Tier-2 candidates, depth-on-demand: continuedev/continue, ComposioHQ/agent-orchestrator, JackChen-me/open-multi-agent, agentscope-ai/agentscope, microsoft/agent-framework, Pratiyush/llm-wiki, Epistates/turbovault, NVIDIA/garak, comet-ml/opik, e2b-dev/infra, testcontainers-python, tree-sitter + tree-sitter-analyzer, Textualize/textual, ratatui/ratatui, charmbracelet bubbletea/bubbles/lipgloss/huh/glamour/gum/vhs, lazygit, k9s, gh-dash, OpenHands, openclaw, gptme, oktsec, Hyper-Extract, agentevals, skillsbench, repomix, markdownlint-github, sinewaveai/agent-security-scanner-mcp, wrale/mcp-server-tree-sitter.)

## 3. Cluster Matrix

| Cluster | Total | Pass | Monitor | Reject | Top 3 Picks |
|---|---:|---:|---:|---:|---|
| agent-codegen | 12 | 4 | 6 | 2 | aider, everything-claude-code, continue |
| agent-experimental-A | 8 | 3 | 3 | 2 | dspy, simonw/llm, gptme |
| agent-orchestration | 11 | 4 | 6 | 1 | composio/agent-orch, open-multi-agent, agentscope |
| agent-research-selfevolve | 15 | 6 | 0 | 5 (incl 2 unres) | hermes-agent, gepa, archon |
| agent-swe | 6 | 4 (+1 alias) | 0 | 0 | superpowers, SWE-agent, agentless |
| agent-wrappers | 15 | 2 | 1 | 12 | agentapi, oktsec, mco |
| browser-automation | 5 | 3 (+1 pat) | 0 | 1 | crawl4ai, scrapling, katana |
| cli-claw-derivatives | 18 | 2 | 10 | 6 | OpenHands, openclaw |
| dev-tools-cli | 17 | 4 | 5 | 8 | tree-sitter, tree-sitter-analyzer, repomix |
| dev-tools-tui | 25 | 18 | 0 | 7 | lazygit, k9s, gh-dash |
| mcp-extensions | 10 | 4 | 0 | 6 | pal-mcp-server, snyk/agent-scan, agent-security-scanner-mcp |
| memory-graph-rag | 12 | 4 | 5 | 3 (incl 1 unres) | LightRAG, HippoRAG, graphiti |
| memory-obsidian | 8 | 5 | 0 | 3 | llm-wiki, turbovault, obsidian-wiki |
| memory-vector | 11 | 2 | 5 | 4 | mempalace, token-savior |
| observability-eval | 20 | 13 (9 phase2) | 0 | 7 | opik, garak, deepeval |
| security-supply | 10 | 4 (+1 pat) | 0 | 5 (incl skips) | snyk/agent-scan, augustus, e2b/infra |
| skills-prompts | 9 | 2 | 2 | 5 | agents.md, agent_skills_directory |
| tui-charm-go | 9 | 8 | 0 | 1 | bubbletea, bubbles, lipgloss |
| tui-py-other | 9 | 1 | 1 | 7 | textual |
| tui-rust | 5 | 2 (+1 inv) | 0 | 2 | ratatui, crossterm |
| **TOTALS** | **235** | **~95** | **~43** | **~97** | — |

## 4. License Findings (watch list)

Recurring non-permissive licenses encountered — block-listed under `[license-policy]`. Track these patterns when triaging future repos:

- **AGPL-3.0** (BLOCK): open-interpreter, qodo-ai/pr-agent, mindfold-ai/Trellis, heypinchy/pinchy, codeking-ai/cligate, repowise-dev/repowise, volcengine/OpenViking, basicmachines-co/basic-memory, thedotmack/claude-mem, lightpanda-io/browser, coder/coder.
- **GPL-3.0 / GPL-2.0** (BLOCK on adopt): warengonzaga/tinyclaw, koalaman/shellcheck-precommit, jonas/tig, ranger/ranger, saulpw/visidata.
- **Elastic-2.0 / BSL / SSPL** (BLOCK, source-available with field/hosted restrictions): Arize-ai/phoenix, superset-sh/superset, brianpetro/obsidian-smart-connections (custom Smart Plugins License — field-restricted), code-yeongyu/oh-my-openagent (Sustainable Use License).
- **FSL-1.1-MIT** (BLOCK during 2-yr functional period): Pythagora-io/gpt-pilot, charmbracelet/crush.
- **CC-BY-NC-4.0 / Llama Community / Custom Dual-Use Commercial** (BLOCK on adopt): midudev/autoskills (CC-BY-NC), meta-llama/PurpleLlama (Llama Community → patterns-only), jgravelle/jcodemunch-mcp + kuberstar/qartez-mcp (paid commercial tier).
- **Mixed MIT + proprietary EE** (BLOCK on adopt): langfuse/langfuse.
- **No LICENSE file** (default all-rights-reserved → BLOCK): cursor/cursor, kirodotdev/Kiro, lgcyaxi/oh-my-claude, nashsu/autocli-skill, bitbonsai/mcpvault, egdev6/engram-monitor, lhr-present/tokenshrink, forrestchang/andrej-karpathy-skills, xcrawl-api/xcrawl-skills, multica-ai/multica (Modified Apache-2.0 with hosting+logo retention).
- **Modified Apache-2.0 with hosted-service / commercial restriction** (BSL-equivalent, BLOCK): multica-ai/multica.
- **NOASSERTION → resolved** (verify in Phase 2): MiniMax-AI/MiniMax-M2 (LICENSE = MIT), affaan-m/everything-claude-code (MIT confirmed via cluster), agent0ai/agent-zero (MIT confirmed), OpenHands/OpenHands (MIT for non-`enterprise/`), augmentcode/augment-swebench-agent (MIT after appendix), pal-mcp-server (Apache-2.0 confirmed), NeMo-Guardrails (Apache-2.0 confirmed), notcurses (Apache-2.0 confirmed), AutoMaker-Org/automaker (MIT — but unmaintained), agents.md (MIT), goose (Apache-2.0). The recurring pattern: third-party notices or "no longer maintained" preambles confuse the GitHub classifier — always inspect LICENSE file.

**One unresolved license surface to confirm before any code adoption**: NousResearch/hermes-agent-self-evolution (LICENSE absent in cluster scout) — patterns OK, code adoption blocked until confirmed.

## 5. Cross-Cluster Duplicates / Mis-clustering

Repos surfaced in 2+ clusters or routed to the wrong cluster:

- **snyk/agent-scan** appears in both mcp-extensions and security-supply clusters with consistent PASS verdict — single Phase-2 deep audit covers both.
- **e2b-dev/mcp-server** in mcp-extensions but functionally adjacent to security-supply (E2B sandbox); already integrated as e2b-integration skill, archived upstream → reject.
- **trailofbits/skills** in skills-prompts cluster but already integrated under `[trailofbits-skills]` rule → reject (already-integrated, not a new candidate).
- **floci-io/floci** clustered as agent-wrappers but is an AWS-emulator (LocalStack analog) — re-cluster to infra/dev-tools.
- **onecli/onecli** clustered as agent-wrappers but is a secrets vault — re-cluster to security/secrets.
- **oktsec/oktsec** clustered as agent-wrappers but is a security primitive (signed agent-to-agent message bus) — kept and promoted in agent-wrappers due to clear value, but re-classify under security-supply.
- **gptscript-ai/gptscript** in dev-tools-cli but is an agent runtime DSL — should be agent-orchestration/agent-codegen; rejected as off-cluster.
- **seaweedfs/seaweedfs** in dev-tools-cli but is distributed object storage — reject off-theme.
- **superset-sh/superset** in dev-tools-cli but is Claude Code orchestration editor — should be agent-orchestration; rejected on Elastic-2.0 anyway.
- **untether** in dev-tools-cli but is Telegram-bridge agent transport — off-theme.
- **jayminwest/overstory** in memory-graph-rag but is multi-agent orchestration runtime — re-cluster.
- **garrytan/gbrain** in memory-obsidian but is a generic personal agent stack — re-cluster to agent-orchestration/wrappers.
- **gnekt/My-Brain-Is-Full-Crew** in memory-obsidian but is personal-life-management CrewAI — off-theme reject.
- **darrenburns/posting** in tui-py-other; not a primitive but a Textual reference app — reject as standalone candidate, harvest patterns within Textual deep audit.
- **gdamore/tcell** in tui-py-other but belongs in tui-charm-go cluster (it underpins Bubble Tea ecosystem).
- **block/goose ↔ aaif-goose/goose** redirect — counted once.
- **OpenClaw/OpenClaw ↔ openclaw/openclaw** GitHub case-collapse — counted once.

**Anomaly flags for operator sanity check** (verdicts that look statistically off):
- **agent-wrappers-templates**: 12/15 reject — high but credible (cluster is genuinely thin wrappers; verdict aligns with hypothesis).
- **dev-tools-tui**: 18/25 pass — high but justified by SURFACE-5 liberal-pass policy (ADR-173/187) for license-clean active TUI primitives. Operator should confirm Phase-2 capacity before launching all 18.
- **agent-swe**: 4/5 pass (alias-corrected), 0 reject — small cluster of well-curated SWE-bench references; reasonable.
- **safishamsi/graphify**: 43,430★ for a single-developer "skill turning folders into KG" repo — likely star-inflation. Already flagged in cluster scout for verification before deeper engagement.
- **agentapi vs CliRelay**: same shape (HTTP-normalized agent CLI) but agentapi is an orchestration primitive while CliRelay is provider-arbitrage (rejected ToS-grey). Verdict diff is correct, not anomalous.

## 6. Phase 2 Effort Estimate

Top-tier list = 22 candidates. Each Phase-2 deep audit (`reverse-engineer` or `repo-forensics` with primitive harvest) at Opus rates:

- Per-repo budget assumption: ~30K-60K tokens read + ~10-20K tokens summary = ~40-80K tokens per audit.
- Opus cost: ~$0.18/10K → $0.72-$1.44 per repo.
- 22-repo Phase-2 cost band: **~$16-32 in Opus token spend, ~10-20 hours wall-clock at 2-3 audits/day**.
- Tier-2 (~25 more candidates): ~$18-36 + ~12-25 hours additional if pursued.
- Recommendation: launch top-tier in 4 thematic batches (skills, memory, dispatch, security) over a sprint; defer tier-2 until top-tier yields refine the prompt template.

Decomposition guard: if any single deep audit exceeds $1.50, sub-decompose per `[token-economy]`. Use `/cost-predict` to ground per-cluster batch estimates.

## 7. Cross-References

Source cluster reports (all dated 2026-05-06):
- `docs/research/repo-scout/cluster-agent-codegen-2026-05-06.md`
- `docs/research/repo-scout/cluster-agent-experimental-A-llm-tooling-2026-05-06.md`
- `docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md`
- `docs/research/repo-scout/cluster-agent-research-selfevolve-2026-05-06.md`
- `docs/research/repo-scout/cluster-agent-swe-2026-05-06.md`
- `docs/research/repo-scout/cluster-agent-wrappers-templates-2026-05-06.md`
- `docs/research/repo-scout/cluster-browser-automation-2026-05-06.md`
- `docs/research/repo-scout/cluster-cli-claw-derivatives-2026-05-06.md`
- `docs/research/repo-scout/cluster-dev-tools-cli-2026-05-06.md`
- `docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md`
- `docs/research/repo-scout/cluster-mcp-extensions-2026-05-06.md`
- `docs/research/repo-scout/cluster-memory-graph-rag-2026-05-06.md`
- `docs/research/repo-scout/cluster-memory-obsidian-2026-05-06.md`
- `docs/research/repo-scout/cluster-memory-vector-2026-05-06.md`
- `docs/research/repo-scout/cluster-observability-eval-2026-05-06.md`
- `docs/research/repo-scout/cluster-security-supply-2026-05-06.md`
- `docs/research/repo-scout/cluster-skills-prompts-2026-05-06.md`
- `docs/research/repo-scout/cluster-tui-charm-go-2026-05-06.md`
- `docs/research/repo-scout/cluster-tui-py-other-2026-05-06.md`
- `docs/research/repo-scout/cluster-tui-rust-2026-05-06.md`

Parent inventory: `docs/reports/external-tools-inventory-2026-05-06.md`.

## 8. Open Questions (operator)

1. **Phase-2 batch ordering**: launch all 22 top-tier as parallel deep audits, or sequence in 4 thematic batches (skills → memory → dispatch → security) to refine the audit prompt between batches?
2. **TUI cluster scope**: 18 dev-tools-tui pass-to-deep + 8 charm-go + 1 textual + 1 ratatui = 28 TUI deep audits. Do we cap at top 5 (lazygit, k9s, gh-dash, bubbletea, textual) and shelve the rest as monitor?
3. **License re-verification before code adoption**: confirm LICENSE on NousResearch/hermes-agent-self-evolution (currently null) and on safishamsi/graphify (star-inflation flag) — block deep audit until resolved?
4. **Mis-clustered re-routing**: should floci, onecli, oktsec, jayminwest/overstory, garrytan/gbrain, tcell be re-routed to their correct clusters and re-scouted, or left as-is with current verdicts?
5. **Already-integrated cluster entries** (caveman, lychee, repomix, deepeval, ragas, promptfoo, parry, e2b, NeMo, semgrep): should Phase-2 produce a "delta-only" upgrade brief per skill, or skip and rely on monitor mode until upstream releases?

---

End of radar.
