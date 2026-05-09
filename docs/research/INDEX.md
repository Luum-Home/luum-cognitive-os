# Research Index

> Browsable index of every research artifact in the repo, public and (by reference) private. Generated 2026-05-07. Re-run `find docs/research docs/reports docs/architecture docs/business -name '*.md'` to verify.

**Total**: ~538 markdown research/audit/forensics artifacts across 6 directories. Coverage: 151+ external tools evaluated, 15 frontier orchestration systems in prior-art, 11 orchestration gaps, 138 operational reports, 4 reusable audits with multiple editions.

---

## Quick navigation

| Section | What's there |
|---|---|
| [§1 Top-level research](#1-top-level-research) | Tool/topic-level research (9 files) |
| [§2 Orchestration line](#2-orchestration-line-2026-05-06-07) | 79-source prior-art + 11 gap reports + synthesis + checklist |
| [§3 Repo-scout](#3-repo-scout-129-files) | External tools landscape (clusters + deep dives + monitor follow-up) |
| [§4 Operational reports](#4-operational-reports-138-files) | Audits, forensics, postmortems, gap reports |
| [§5 Architecture research](#5-architecture-research-10-files) | Backend evaluations, benchmarks, control-plane research |
| [§6 Business research](#6-business-research-4-files) | Reality audits, competitive re-assessments |
| [§7 Strategy private](#7-strategy-private-gitignored-11-files) | `.cognitive-os/strategy/research/` — gitignored |
| [§8 Other audits](#8-other-audits-and-measurements) | `docs/measurements/`, `docs/manual-tests/`, etc. |

---

## 1. Top-level research

`docs/research/*.md` — individual tool/topic evaluations.

| File | Topic | Date |
|---|---|---|
| [archon-evaluation.md](archon-evaluation.md) | Archon agent OS | — |
| [claude-code-router-evaluation-2026-04-21.md](claude-code-router-evaluation-2026-04-21.md) | Claude Code Router | 2026-04-21 |
| [engram-mcp-sharing-feasibility-2026-04-20.md](engram-mcp-sharing-feasibility-2026-04-20.md) | Engram MCP sharing | 2026-04-20 |
| [llm-wiki-v2-engram-evolution-2026-04-27.md](llm-wiki-v2-engram-evolution-2026-04-27.md) | Engram → wiki v2 | 2026-04-27 |
| [minimal-context-principle.md](minimal-context-principle.md) | Context optimization | — |
| **[multi-agent-orchestration-prior-art-2026-05-06.md](multi-agent-orchestration-prior-art-2026-05-06.md)** | ★ 79-source prior-art (15 systems) | 2026-05-06 |
| [obsidian-doc-graph-ai-agent-memory-2026-05-05.md](obsidian-doc-graph-ai-agent-memory-2026-05-05.md) | Obsidian doc-graph for memory | 2026-05-05 |
| **[orchestration-coverage-gap-analysis-2026-05-06.md](orchestration-coverage-gap-analysis-2026-05-06.md)** | ★ Gap analysis with C1–C4 contract | 2026-05-06 |
| [wisc-framework-analysis.md](wisc-framework-analysis.md) | WISC framework | — |

---

## 2. Orchestration line (2026-05-06/07)

`docs/research/orchestration-gaps/*.md` — 13 files. Outcome: 14 ADRs (220–236, ADR-229 tombstone) drafted + Slice-A-implemented.

| File | Topic |
|---|---|
| **[SYNTHESIS-2026-05-06.md](orchestration-gaps/SYNTHESIS-2026-05-06.md)** | ★ Ranked synthesis (4-tier plan, ADR slate) |
| **[IMPLEMENTATION-CHECKLIST-2026-05-07.md](orchestration-gaps/IMPLEMENTATION-CHECKLIST-2026-05-07.md)** | ★ Honest 🟡 status per ADR + remaining slices |
| [agent-to-agent-handoff.md](orchestration-gaps/agent-to-agent-handoff.md) | A2A handoff protocols (closes MAST 2025 41–87% cycle failure mode) |
| [approval-policies-as-code.md](orchestration-gaps/approval-policies-as-code.md) | Policy-as-code (Codex `approval-policy.yaml` pattern) |
| [background-agent-patterns.md](orchestration-gaps/background-agent-patterns.md) | Detached/cloud agents (tmux + worktree local-first) |
| [cost-aware-routing.md](orchestration-gaps/cost-aware-routing.md) | Sync pre-call budget gate (closes $47K-incident class) |
| [cross-session-agent-teams.md](orchestration-gaps/cross-session-agent-teams.md) | File-IPC + fcntl (Claude Code Agent Teams pattern) |
| [event-driven-orchestrator-state.md](orchestration-gaps/event-driven-orchestrator-state.md) | Event sourcing (load-bearing for replay/retry/cost) |
| [failure-recovery-retry-semantics.md](orchestration-gaps/failure-recovery-retry-semantics.md) | Retry classifier + idempotency keys |
| [mcp-as-orchestration-bus.md](orchestration-gaps/mcp-as-orchestration-bus.md) | MCP server surface |
| [replay-timeline-architectures.md](orchestration-gaps/replay-timeline-architectures.md) | Shadow-git substrate (Devin-parity, no hypervisor) |
| [sandbox-primitives-integration.md](orchestration-gaps/sandbox-primitives-integration.md) | Bubblewrap/Seatbelt/E2B/Daytona/Modal/ConTree |
| [tool-discovery-dynamic-registration.md](orchestration-gaps/tool-discovery-dynamic-registration.md) | Deferred loading + ToolSearch (Anthropic-native) |

**Companion**: [`manifests/orchestration-research-evaluation.yaml`](../../manifests/orchestration-research-evaluation.yaml) — canonical C1–C4 contract.
**Validator**: [`scripts/validate_substrate_consumers.py`](../../scripts/validate_substrate_consumers.py) — 14/14 PASS on 2026-05-07.

---

## 3. Repo-scout (129 files)

`docs/research/repo-scout/` — external tools landscape. Three sub-levels:

### 3.1 Clusters (20 files — thematic groupings)

| Cluster | Theme |
|---|---|
| [cluster-agent-codegen-2026-05-06.md](repo-scout/cluster-agent-codegen-2026-05-06.md) | Code-generation agents |
| [cluster-agent-experimental-A-llm-tooling-2026-05-06.md](repo-scout/cluster-agent-experimental-A-llm-tooling-2026-05-06.md) | LLM tooling experiments |
| [cluster-agent-orchestration-2026-05-06.md](repo-scout/cluster-agent-orchestration-2026-05-06.md) | Agent orchestration |
| [cluster-agent-research-selfevolve-2026-05-06.md](repo-scout/cluster-agent-research-selfevolve-2026-05-06.md) | Self-evolving agent research |
| [cluster-agent-swe-2026-05-06.md](repo-scout/cluster-agent-swe-2026-05-06.md) | SWE agents |
| [cluster-agent-wrappers-templates-2026-05-06.md](repo-scout/cluster-agent-wrappers-templates-2026-05-06.md) | Agent wrappers/templates |
| [cluster-browser-automation-2026-05-06.md](repo-scout/cluster-browser-automation-2026-05-06.md) | Browser automation |
| [cluster-cli-claw-derivatives-2026-05-06.md](repo-scout/cluster-cli-claw-derivatives-2026-05-06.md) | "Claw" CLI derivatives |
| [cluster-dev-tools-cli-2026-05-06.md](repo-scout/cluster-dev-tools-cli-2026-05-06.md) | Dev CLI tools |
| [cluster-dev-tools-tui-2026-05-06.md](repo-scout/cluster-dev-tools-tui-2026-05-06.md) | Dev TUI tools |
| [cluster-mcp-extensions-2026-05-06.md](repo-scout/cluster-mcp-extensions-2026-05-06.md) | MCP extensions |
| [cluster-memory-graph-rag-2026-05-06.md](repo-scout/cluster-memory-graph-rag-2026-05-06.md) | Graph RAG |
| [cluster-memory-obsidian-2026-05-06.md](repo-scout/cluster-memory-obsidian-2026-05-06.md) | Obsidian-based memory |
| [cluster-memory-vector-2026-05-06.md](repo-scout/cluster-memory-vector-2026-05-06.md) | Vector memory |
| [cluster-observability-eval-2026-05-06.md](repo-scout/cluster-observability-eval-2026-05-06.md) | Observability + eval |
| [cluster-security-supply-2026-05-06.md](repo-scout/cluster-security-supply-2026-05-06.md) | Security + supply chain |
| [cluster-skills-prompts-2026-05-06.md](repo-scout/cluster-skills-prompts-2026-05-06.md) | Skills + prompts |
| [cluster-tui-charm-go-2026-05-06.md](repo-scout/cluster-tui-charm-go-2026-05-06.md) | Charm/Go TUI |
| [cluster-tui-py-other-2026-05-06.md](repo-scout/cluster-tui-py-other-2026-05-06.md) | Python/other TUI |
| [cluster-tui-rust-2026-05-06.md](repo-scout/cluster-tui-rust-2026-05-06.md) | Rust TUI (ratatui ecosystem) |

### 3.2 Deep dives (64 files)

`docs/research/repo-scout/deep/` — per-tool deep analysis (mostly 2026-05-06, with targeted addenda as requested).

**Coding agents / orchestrators (15)**:
[Aider-AI__aider](repo-scout/deep/Aider-AI__aider-2026-05-06.md) ·
[ComposioHQ__agent-orchestrator](repo-scout/deep/ComposioHQ__agent-orchestrator-2026-05-06.md) ·
[JackChen-me__open-multi-agent](repo-scout/deep/JackChen-me__open-multi-agent-2026-05-06.md) ·
[NousResearch__hermes-agent](repo-scout/deep/NousResearch__hermes-agent-2026-05-06.md) ·
[OpenHands__OpenHands](repo-scout/deep/OpenHands__OpenHands-2026-05-06.md) ·
[SWE-agent__SWE-agent](repo-scout/deep/SWE-agent__SWE-agent-2026-05-06.md) ·
[agentscope-ai__agentscope](repo-scout/deep/agentscope-ai__agentscope-2026-05-06.md) ·
[coder__agentapi](repo-scout/deep/coder__agentapi-2026-05-06.md) ·
[coleam00__Archon](repo-scout/deep/coleam00__Archon-2026-05-06.md) ·
[continuedev__continue](repo-scout/deep/continuedev__continue-2026-05-06.md) ·
[microsoft__agent-framework](repo-scout/deep/microsoft__agent-framework-2026-05-06.md) ·
[musistudio__claude-code-router](repo-scout/deep/musistudio__claude-code-router-2026-05-06.md) ·
[openclaw__openclaw](repo-scout/deep/openclaw__openclaw-2026-05-06.md) ·
[praetorian-inc__augustus](repo-scout/deep/praetorian-inc__augustus-2026-05-06.md) ·
[VRSEN__OpenSwarm](repo-scout/deep/VRSEN__OpenSwarm-2026-05-09.md)

**Memory & RAG (6)**:
[DEEP-PolyU__Awesome-GraphMemory](repo-scout/deep/DEEP-PolyU__Awesome-GraphMemory-2026-05-06.md) ·
[HKUDS__LightRAG](repo-scout/deep/HKUDS__LightRAG-2026-05-06.md) ·
[MemPalace__mempalace](repo-scout/deep/MemPalace__mempalace-2026-05-06.md) ·
[OSU-NLP-Group__HippoRAG](repo-scout/deep/OSU-NLP-Group__HippoRAG-2026-05-06.md) ·
[getzep__graphiti](repo-scout/deep/getzep__graphiti-2026-05-06.md) ·
[yifanfeng97__Hyper-Extract](repo-scout/deep/yifanfeng97__Hyper-Extract-2026-05-06.md)

**TUI / Charm ecosystem (12)**:
[Textualize__textual](repo-scout/deep/Textualize__textual-2026-05-06.md) ·
[charmbracelet__bubbles](repo-scout/deep/charmbracelet__bubbles-2026-05-06.md) ·
[charmbracelet__bubbletea](repo-scout/deep/charmbracelet__bubbletea-2026-05-06.md) ·
[charmbracelet__glamour](repo-scout/deep/charmbracelet__glamour-2026-05-06.md) ·
[charmbracelet__gum](repo-scout/deep/charmbracelet__gum-2026-05-06.md) ·
[charmbracelet__huh](repo-scout/deep/charmbracelet__huh-2026-05-06.md) ·
[charmbracelet__lipgloss](repo-scout/deep/charmbracelet__lipgloss-2026-05-06.md) ·
[charmbracelet__soft-serve](repo-scout/deep/charmbracelet__soft-serve-2026-05-06.md) ·
[charmbracelet__vhs](repo-scout/deep/charmbracelet__vhs-2026-05-06.md) ·
[crossterm-rs__crossterm](repo-scout/deep/crossterm-rs__crossterm-2026-05-06.md) ·
[ratatui__ratatui](repo-scout/deep/ratatui__ratatui-2026-05-06.md) ·
[zellij-org__zellij](repo-scout/deep/zellij-org__zellij-2026-05-06.md)

**CLI tools (12)**:
[ClementTsang__bottom](repo-scout/deep/ClementTsang__bottom-2026-05-06.md) ·
[antonmedv__fx](repo-scout/deep/antonmedv__fx-2026-05-06.md) ·
[aristocratos__btop](repo-scout/deep/aristocratos__btop-2026-05-06.md) ·
[derailed__k9s](repo-scout/deep/derailed__k9s-2026-05-06.md) ·
[dlvhdr__gh-dash](repo-scout/deep/dlvhdr__gh-dash-2026-05-06.md) ·
[gitui-org__gitui](repo-scout/deep/gitui-org__gitui-2026-05-06.md) ·
[jarun__nnn](repo-scout/deep/jarun__nnn-2026-05-06.md) ·
[jesseduffield__lazydocker](repo-scout/deep/jesseduffield__lazydocker-2026-05-06.md) ·
[jesseduffield__lazygit](repo-scout/deep/jesseduffield__lazygit-2026-05-06.md) ·
[sxyazi__yazi](repo-scout/deep/sxyazi__yazi-2026-05-06.md) ·
[wagoodman__dive](repo-scout/deep/wagoodman__dive-2026-05-06.md) ·
[yorukot__superfile](repo-scout/deep/yorukot__superfile-2026-05-06.md)

**DevOps / observability (6)**:
[allinurl__goaccess](repo-scout/deep/allinurl__goaccess-2026-05-06.md) ·
[hatoo__oha](repo-scout/deep/hatoo__oha-2026-05-06.md) ·
[sachaos__viddy](repo-scout/deep/sachaos__viddy-2026-05-06.md) ·
[tstack__lnav](repo-scout/deep/tstack__lnav-2026-05-06.md) ·
[wtfutil__wtf](repo-scout/deep/wtfutil__wtf-2026-05-06.md)

**Sandboxes / security (4)**:
[e2b-dev__infra](repo-scout/deep/e2b-dev__infra-2026-05-06.md) ·
[semgrep__semgrep](repo-scout/deep/semgrep__semgrep-2026-05-06.md) ·
[snyk__agent-scan](repo-scout/deep/snyk__agent-scan-2026-05-06.md) ·
[testcontainers__testcontainers-python](repo-scout/deep/testcontainers__testcontainers-python-2026-05-06.md)

**Research / DSPy (3)**:
[gepa-ai__gepa](repo-scout/deep/gepa-ai__gepa-2026-05-06.md) ·
[simonw__llm](repo-scout/deep/simonw__llm-2026-05-06.md) ·
[stanfordnlp__dspy](repo-scout/deep/stanfordnlp__dspy-2026-05-06.md)

**Misc community / tools (10)**:
[BeehiveInnovations__pal-mcp-server](repo-scout/deep/BeehiveInnovations__pal-mcp-server-2026-05-06.md) ·
[Mibayy__token-savior](repo-scout/deep/Mibayy__token-savior-2026-05-06.md) ·
[affaan-m__everything-claude-code](repo-scout/deep/affaan-m__everything-claude-code-2026-05-06.md) ·
[agentsmd__agents.md](repo-scout/deep/agentsmd__agents.md-2026-05-06.md) ·
[dmgrok__agent_skills_directory](repo-scout/deep/dmgrok__agent_skills_directory-2026-05-06.md) ·
[obra__superpowers](repo-scout/deep/obra__superpowers-2026-05-06.md) ·
[unclecode__crawl4ai](repo-scout/deep/unclecode__crawl4ai-2026-05-06.md)

### 3.3 Monitor follow-up (43 files)

`docs/research/repo-scout/monitor-followup/` — tools to keep watching (all dated 2026-05-06).

**LLM gateways**:
[BerriAI__litellm](repo-scout/monitor-followup/BerriAI__litellm-2026-05-06.md) ·
[agentgateway__agentgateway](repo-scout/monitor-followup/agentgateway__agentgateway-2026-05-06.md) ·
[maximhq__bifrost](repo-scout/monitor-followup/maximhq__bifrost-2026-05-06.md)

**Coding agents**:
[anomalyco__opencode](repo-scout/monitor-followup/anomalyco__opencode-2026-05-06.md) ·
[cline__cline](repo-scout/monitor-followup/cline__cline-2026-05-06.md) ·
[RooCodeInc__Roo-Code](repo-scout/monitor-followup/RooCodeInc__Roo-Code-2026-05-06.md) ·
[openai__codex](repo-scout/monitor-followup/openai__codex-2026-05-06.md) ·
[QwenLM__qwen-code](repo-scout/monitor-followup/QwenLM__qwen-code-2026-05-06.md) ·
[MiniMax-AI__MiniMax-M2](repo-scout/monitor-followup/MiniMax-AI__MiniMax-M2-2026-05-06.md)

**Multi-agent frameworks**:
[FoundationAgents__MetaGPT](repo-scout/monitor-followup/FoundationAgents__MetaGPT-2026-05-06.md) ·
[awslabs__agent-squad](repo-scout/monitor-followup/awslabs__agent-squad-2026-05-06.md) ·
[crewAIInc__crewAI](repo-scout/monitor-followup/crewAIInc__crewAI-2026-05-06.md)

**Memory**:
[letta-ai__letta](repo-scout/monitor-followup/letta-ai__letta-2026-05-06.md) ·
[Mirix-AI__MIRIX](repo-scout/monitor-followup/Mirix-AI__MIRIX-2026-05-06.md) ·
[rohitg00__agentmemory](repo-scout/monitor-followup/rohitg00__agentmemory-2026-05-06.md) ·
[topoteretes__cognee](repo-scout/monitor-followup/topoteretes__cognee-2026-05-06.md) ·
[safishamsi__graphify](repo-scout/monitor-followup/safishamsi__graphify-2026-05-06.md) ·
[devwhodevs__engraph](repo-scout/monitor-followup/devwhodevs__engraph-2026-05-06.md) ·
[egdev6__engram-monitor](repo-scout/monitor-followup/egdev6__engram-monitor-2026-05-06.md)

**Graph RAG**:
[microsoft__graphrag](repo-scout/monitor-followup/microsoft__graphrag-2026-05-06.md) ·
[CodeGraphContext__CodeGraphContext](repo-scout/monitor-followup/CodeGraphContext__CodeGraphContext-2026-05-06.md) ·
[memvid__memvid](repo-scout/monitor-followup/memvid__memvid-2026-05-06.md)

**TUI / CLI**:
[Textualize__rich](repo-scout/monitor-followup/Textualize__rich-2026-05-06.md) ·
[TheR1D__shell_gpt](repo-scout/monitor-followup/TheR1D__shell_gpt-2026-05-06.md) ·
[junegunn__fzf](repo-scout/monitor-followup/junegunn__fzf-2026-05-06.md) ·
[nashsu__AutoCLI](repo-scout/monitor-followup/nashsu__AutoCLI-2026-05-06.md) ·
[sigoden__aichat](repo-scout/monitor-followup/sigoden__aichat-2026-05-06.md)

**Skills**:
[mattpocock__skills](repo-scout/monitor-followup/mattpocock__skills-2026-05-06.md) ·
[luongnv89__claude-howto](repo-scout/monitor-followup/luongnv89__claude-howto-2026-05-06.md) ·
[shanraisshan__claude-code-best-practice](repo-scout/monitor-followup/shanraisshan__claude-code-best-practice-2026-05-06.md) ·
[smykla-skalski__klaudiush](repo-scout/monitor-followup/smykla-skalski__klaudiush-2026-05-06.md)

**"Claw" derivatives** (Claude Code clones/forks):
[dollspace-gay__OpenClaudia](repo-scout/monitor-followup/dollspace-gay__OpenClaudia-2026-05-06.md) ·
[nearai__ironclaw](repo-scout/monitor-followup/nearai__ironclaw-2026-05-06.md) ·
[nullclaw__nullclaw](repo-scout/monitor-followup/nullclaw__nullclaw-2026-05-06.md) ·
[qhkm__zeptoclaw](repo-scout/monitor-followup/qhkm__zeptoclaw-2026-05-06.md) ·
[qwibitai__nanoclaw](repo-scout/monitor-followup/qwibitai__nanoclaw-2026-05-06.md) ·
[sipeed__picoclaw](repo-scout/monitor-followup/sipeed__picoclaw-2026-05-06.md) ·
[zeroclaw-labs__zeroclaw](repo-scout/monitor-followup/zeroclaw-labs__zeroclaw-2026-05-06.md) ·
[InternLM__WildClawBench](repo-scout/monitor-followup/InternLM__WildClawBench-2026-05-06.md)

**Linting / docs**:
[DavidAnson__markdownlint-cli2](repo-scout/monitor-followup/DavidAnson__markdownlint-cli2-2026-05-06.md) ·
[lycheeverse__lychee](repo-scout/monitor-followup/lycheeverse__lychee-2026-05-06.md) ·
[lycheeverse__lychee-action](repo-scout/monitor-followup/lycheeverse__lychee-action-2026-05-06.md) ·
[JuliusBrussee__caveman](repo-scout/monitor-followup/JuliusBrussee__caveman-2026-05-06.md)

---

## 4. Operational reports (138 files)

`docs/reports/*.md` — too many to list individually. Categorized by purpose:

### 4.1 Repeated audits (multi-edition, valuable for trend)

- **Aspirational claims audit** (5 editions): [2026-04-20](../reports/aspirational-audit-2026-04-20.md) · [2026-05-02](../reports/aspirational-audit-2026-05-02.md) · [2026-05-03](../reports/aspirational-audit-2026-05-03.md) · [2026-05-05](../reports/aspirational-audit-2026-05-05.md) · [2026-05-06](../reports/aspirational-audit-2026-05-06.md)
- **External tools radar** (5): [inventory](../reports/external-tools-inventory-2026-05-06.md) · [comparative-matrix](../reports/external-tools-comparative-matrix-2026-05-06.md) · [radar](../reports/external-tools-radar-2026-05-06.md) · [radar-deep](../reports/external-tools-radar-deep-2026-05-06.md) · [radar-deep-tier2](../reports/external-tools-radar-deep-tier2-2026-05-06.md) · [monitor-followup](../reports/external-tools-radar-monitor-followup-2026-05-06.md)
- **Targeted 2026-05-09 TaskingAI addition**: [TaskingAI deep evaluation](repo-scout/deep/TaskingAI__TaskingAI-2026-05-09.md) · [TaskingAI radar addendum](../reports/external-tools-radar-taskingai-addendum-2026-05-09.md)
- **Targeted 2026-05-09 additions**: [EvoSkill deep evaluation](repo-scout/deep/sentient-agi__EvoSkill-2026-05-09.md) · [EvoSkill radar addendum](../reports/external-tools-radar-evoskill-addendum-2026-05-09.md) · [Langflow deep evaluation](repo-scout/deep/langflow-ai__langflow-2026-05-09.md) · [Langflow radar addendum](../reports/external-tools-radar-langflow-addendum-2026-05-09.md)
- **Primitive readiness ledgers** (5 families, all `-latest.md`): [hooks](../reports/primitive-readiness-ledger-hooks-latest.md) · [rules](../reports/primitive-readiness-ledger-rules-latest.md) · [scripts](../reports/primitive-readiness-ledger-scripts-latest.md) · [skills](../reports/primitive-readiness-ledger-skills-latest.md) · [templates](../reports/primitive-readiness-ledger-templates-latest.md)
- **Primitive gap matrix**: [latest](../reports/primitive-gap-latest.md) · [matrix-2026-04](../reports/primitive-gap-matrix-2026-04.md) · [regressions](../reports/primitive-gap-regressions.md)
- **Primitive lifecycle**: [lifecycle-backlog-scripts](../reports/primitive-readiness-lifecycle-backlog-scripts-latest.md) · [readiness-review-2026-05-04](../reports/primitive-readiness-review-2026-05-04.md) · [primitive-row-audit-latest](../reports/primitive-row-audit-latest.md) · [surface-coverage-session-2026-05-06](../reports/primitive-surface-coverage-session-2026-05-06.md) · [surface-reduction-latest](../reports/primitive-surface-reduction-latest.md) · [usage-map-latest](../reports/primitive-usage-map-latest.md)

### 4.2 Self-bite / state retention forensics

- [session-self-bite-pattern-2026-05-06.md](../reports/session-self-bite-pattern-2026-05-06.md) — original bug
- [state-retention-controller-postmortem-2026-05-06.md](../reports/state-retention-controller-postmortem-2026-05-06.md)
- [stash-hidden-wip-postmortem-2026-05-06.md](../reports/stash-hidden-wip-postmortem-2026-05-06.md)
- [validation-worktree-mutation-postmortem-2026-05-02.md](../reports/validation-worktree-mutation-postmortem-2026-05-02.md)
- [tool-discovery-preuse-self-bite-2026-05-06.md](../reports/tool-discovery-preuse-self-bite-2026-05-06.md)
- [stash-{intake-2026-05-06, resolution-2026-05-01, review-license-switch-2026-05-06}](../reports/) — 3
- [git-state-cleanup-20260506T220040Z.md](../reports/git-state-cleanup-20260506T220040Z.md)
- [worktree-intake-session50-2026-05-06.md](../reports/worktree-intake-session50-2026-05-06.md)
- [bug2-reset-cascade-forensics-2026-04-20.md](../reports/bug2-reset-cascade-forensics-2026-04-20.md)
- [d01-git-reset-forensics-2026-04-20.md](../reports/d01-git-reset-forensics-2026-04-20.md)
- [auto-rollback-router-trigger-forensics-2026-05-06.md](../reports/auto-rollback-router-trigger-forensics-2026-05-06.md)

### 4.3 ADR implementation tracking

- [adr-067-phase-2-2026-04-24.md](../reports/adr-067-phase-2-2026-04-24.md)
- [adr-137-plus-implementation-review-2026-05-04.md](../reports/adr-137-plus-implementation-review-2026-05-04.md)
- [adr-200-plus-closure-inventory-2026-05-06.md](../reports/adr-200-plus-closure-inventory-2026-05-06.md)
- [adr-implementation-reconciliation-2026-05-05.md](../reports/adr-implementation-reconciliation-2026-05-05.md)

### 4.4 AI agent harness landscape

- [ai-agent-harness-landscape-2026-05-04.md](../reports/ai-agent-harness-landscape-2026-05-04.md)
- [multi-provider-agent-delegation-research-2026-05-05.md](../reports/multi-provider-agent-delegation-research-2026-05-05.md)
- [kiro-lifecycle-hook-investigation-2026-05-05.md](../reports/kiro-lifecycle-hook-investigation-2026-05-05.md)
- [harness-docs-currentness-audit-2026-05-05.md](../reports/harness-docs-currentness-audit-2026-05-05.md)

### 4.5 Security / supply chain

- [secret-audit-release-readiness-2026-05-06.md](../reports/secret-audit-release-readiness-2026-05-06.md)
- [secret-protection-effectiveness-2026-05-06.md](../reports/secret-protection-effectiveness-2026-05-06.md)
- [dependencies-license-audit-2026-05-06.md](../reports/dependencies-license-audit-2026-05-06.md)
- [cross-stack-license-audit-tools-2026-05-06.md](../reports/cross-stack-license-audit-tools-2026-05-06.md)
- [confidentiality-enforcer-gitignored-downgrade-2026-05-06.md](../reports/confidentiality-enforcer-gitignored-downgrade-2026-05-06.md)

### 4.6 Skill / router

- [skill-router-false-positive-cluster-2026-05-06.md](../reports/skill-router-false-positive-cluster-2026-05-06.md)
- [skill-router-primitive-routing-postmortem-2026-05-05.md](../reports/skill-router-primitive-routing-postmortem-2026-05-05.md)
- [skill-side-dormant-2026-05-02.md](../reports/skill-side-dormant-2026-05-02.md)
- [self-improvement-auto-repair-primitive-loop-audit-2026-05-05.md](../reports/self-improvement-auto-repair-primitive-loop-audit-2026-05-05.md)
- [self-improvement-maintainer-agent-gap-2026-05-06.md](../reports/self-improvement-maintainer-agent-gap-2026-05-06.md)

### 4.7 Capability / portability gaps

- [private-content-portability-gap-2026-05-06.md](../reports/private-content-portability-gap-2026-05-06.md)
- [subagent-capability-contract-gap-2026-05-06.md](../reports/subagent-capability-contract-gap-2026-05-06.md)
- [lifecycle-promotion-gap-2026-05-05.md](../reports/lifecycle-promotion-gap-2026-05-05.md)
- [lifecycle-demotion-task-completed-2026-05-03.md](../reports/lifecycle-demotion-task-completed-2026-05-03.md)
- [demotion-loop-audit-bite-verification-2026-05-03.md](../reports/demotion-loop-audit-bite-verification-2026-05-03.md)
- [second-demotion-candidate-resolution-2026-05-03.md](../reports/second-demotion-candidate-resolution-2026-05-03.md)
- [dormant-b1-batch-2026-05-02.md](../reports/dormant-b1-batch-2026-05-02.md)

### 4.8 Test / CI / quality

- [test-suite-repair-ledger-2026-04-24.md](../reports/test-suite-repair-ledger-2026-04-24.md)
- [full-suite-validation-2026-04-23.md](../reports/full-suite-validation-2026-04-23.md)
- [test-quality-audit-2026-04-20.md](../reports/test-quality-audit-2026-04-20.md)
- [agentic-mastery-validation-2026-05-02.md](../reports/agentic-mastery-validation-2026-05-02.md)
- [boring-reliability-audit-2026-05-03.md](../reports/boring-reliability-audit-2026-05-03.md)
- [dx-assessment-2026-05-02.md](../reports/dx-assessment-2026-05-02.md)
- Python deps: [bumps-2026-04-24](../reports/python-major-bumps-2026-04-24.md) · [deps-review-2026-05-04](../reports/python-major-deps-review-2026-05-04.md) · [followup-2026-05-04](../reports/python-major-followup-2026-05-04.md) · [lane-resolution-2026-05-04](../reports/python-major-lane-resolution-2026-05-04.md)

### 4.9 Sessions / handoffs / claims

- [session-close-2026-04-20.md](../reports/session-close-2026-04-20.md), [session-close-lethal-receipts-2026-05-06.md](../reports/session-close-lethal-receipts-2026-05-06.md)
- [session-state-forensics-2026-05-05.md](../reports/session-state-forensics-2026-05-05.md)
- [task-and-plan-reconciliation-2026-05-05.md](../reports/task-and-plan-reconciliation-2026-05-05.md)
- [claim-boundary-resolution-2026-05-04.md](../reports/claim-boundary-resolution-2026-05-04.md), [claim-proof-latest.md](../reports/claim-proof-latest.md)
- [proof-drill-opt-in-run-2026-05-05.md](../reports/proof-drill-opt-in-run-2026-05-05.md)
- [redteam-consumer-rehearsal-2026-05-02.md](../reports/redteam-consumer-rehearsal-2026-05-02.md)
- [swarm-stress-2026-05-02.md](../reports/swarm-stress-2026-05-02.md)
- [implement-tier1-2026-05-02.md](../reports/implement-tier1-2026-05-02.md)
- [robustness-hardening-session-2026-05-06.md](../reports/robustness-hardening-session-2026-05-06.md)
- [primitive-surface-coverage-session-2026-05-06.md](../reports/primitive-surface-coverage-session-2026-05-06.md)

### 4.10 Other

- [alternatives-comparison-2026-04.md](../reports/alternatives-comparison-2026-04.md)
- [metrics-census.md](../reports/metrics-census.md)
- [hook-{audit-2026-04, registration-classification-2026-05-04}](../reports/) — 2
- [docker-image-review-2026-05-04.md](../reports/docker-image-review-2026-05-04.md)
- [merge-readiness-master-plan-2026-04-23.md](../reports/merge-readiness-master-plan-2026-04-23.md)
- [cos-init-migration-2026-04-24.md](../reports/cos-init-migration-2026-04-24.md)
- [cos-self-observability-deep-review-2026-05-05.md](../reports/cos-self-observability-deep-review-2026-05-05.md), [cos-side-deep-rebuttal-2026-05-05.md](../reports/cos-side-deep-rebuttal-2026-05-05.md)
- [cli-anything-deep-audit-2026-05-05.md](../reports/cli-anything-deep-audit-2026-05-05.md), [cli-anything-opus-deep-audit-2026-05-05.md](../reports/cli-anything-opus-deep-audit-2026-05-05.md)
- [bidirectional-agent-channel-investigation-2026-05-05.md](../reports/bidirectional-agent-channel-investigation-2026-05-05.md)
- [cross-instance-consumer-e2e-2026-05-03.md](../reports/cross-instance-consumer-e2e-2026-05-03.md)
- [remote-control-plane-alternatives-2026-05-05.md](../reports/remote-control-plane-alternatives-2026-05-05.md)
- [surface-5-tui-ui-candidates-2026-05-05.md](../reports/surface-5-tui-ui-candidates-2026-05-05.md)
- [audit-{contract-serial-reversal-investigation-2026-05-01, corpus-revalidation-2026-05-05}](../reports/) — 2
- [primitives-and-tools-audit-2026-05-05.md](../reports/primitives-and-tools-audit-2026-05-05.md)
- [punch-list-{hooks, lib, rules, skills}](../reports/) — 4
- [reduction-backlog-latest.md](../reports/reduction-backlog-latest.md)
- [debt-register-2026-04-20.md](../reports/debt-register-2026-04-20.md)
- [reconciliation-audit-2026-04-20.md](../reports/reconciliation-audit-2026-04-20.md), [global-verify-validation-2026-04-20.md](../reports/global-verify-validation-2026-04-20.md), [artifact-verification-2026-04-20.md](../reports/artifact-verification-2026-04-20.md)
- [sub-agent-context-trim-2026-04-20.md](../reports/sub-agent-context-trim-2026-04-20.md)
- [install-timing-baseline-2026-05-01.md](../reports/install-timing-baseline-2026-05-01.md), [prune-triage-2026-05-01.md](../reports/prune-triage-2026-05-01.md)
- [docs-{duplicate-latest, execution-latest}](../reports/) — 2
- [d1b-clients-todo.md](../reports/d1b-clients-todo.md)
- [primitive-harness-{coverage-latest, partials-latest}](../reports/) — 2
- [file-by-file-review-2026-05-05.md](../reports/file-by-file-review-2026-05-05.md)

---

## 5. Architecture research (10 files)

Research-flavored architecture docs in `docs/architecture/`.

| File | Topic |
|---|---|
| [cloud-worker-runtime-tooling-research-2026-05.md](../architecture/cloud-worker-runtime-tooling-research-2026-05.md) | Cloud workers |
| [cross-tool-landscape.md](../architecture/cross-tool-landscape.md) | Cross-tool landscape |
| [cross-tool-task-recovery-research-2026-05.md](../architecture/cross-tool-task-recovery-research-2026-05.md) | Task recovery cross-tool |
| [observability-backend-evaluation-2026-04-24.md](../architecture/observability-backend-evaluation-2026-04-24.md) | Phoenix vs Langfuse vs Arize |
| [primitive-coverage-backend-benchmark-2026-05.md](../architecture/primitive-coverage-backend-benchmark-2026-05.md) | Primitive coverage backends |
| [primitive-coverage-tooling-research-2026-04.md](../architecture/primitive-coverage-tooling-research-2026-04.md) | Primitive coverage tools |
| [primitive-fitness-evaluation-contract.md](../architecture/primitive-fitness-evaluation-contract.md) | Primitive fitness contract |
| [runtime-benchmark-mvp.md](../architecture/runtime-benchmark-mvp.md) | Runtime benchmark MVP |
| [service-control-plane-research-2026-05-04.md](../architecture/service-control-plane-research-2026-05-04.md) | Service control plane |
| [functional-audit/startup-baseline-2026-04-20.md](../architecture/functional-audit/startup-baseline-2026-04-20.md) | Startup baseline |

Plus topic-audits:
[claim-signature-audit](../architecture/claim-signature-audit.md) ·
[core-vs-extensions-audit-2026-04-20](../architecture/core-vs-extensions-audit-2026-04-20.md) ·
[multi-session-orchestration-audit-2026-05-02](../architecture/multi-session-orchestration-audit-2026-05-02.md) ·
[parser-coverage-audit-2026-04-24](../architecture/parser-coverage-audit-2026-04-24.md) ·
[primitive-duplication-audit](../architecture/primitive-duplication-audit.md) +
[primitive-duplication-audit-implementation-plan](../architecture/primitive-duplication-audit-implementation-plan.md) ·
[documentation-execution-audit](../architecture/documentation-execution-audit.md) ·
[reality-audit](../architecture/reality-audit.md)

---

## 6. Business research (4 files)

Research-flavored business docs in `docs/business/`.

| File | Type |
|---|---|
| [competitive-reassessment-openclaw-hermes-2026-04.md](../business/competitive-reassessment-openclaw-hermes-2026-04.md) | Competitive re-assessment |
| [conversation-reality-audit-2026-04-30.md](../business/conversation-reality-audit-2026-04-30.md) | Reality audit |
| [feature-reality-audit.md](../business/feature-reality-audit.md) | Feature reality |
| [cos-vs-vanilla-dx-review.md](../business/cos-vs-vanilla-dx-review.md) | DX review |

---

## 7. Strategy private (gitignored, 11 files)

`.cognitive-os/strategy/research/` — listed for trace; **not** linked because gitignored. Only readable on operator's filesystem.

| Order | File | Topic |
|---|---|---|
| 01 | `01-origin-archeology.md` | Origin archeology |
| 02 | `02-real-self-improvement.md` | 4 closed loops |
| 03 | `03-aspirational-dormant.md` | Top 5 aspirational claims |
| 04 | `04-telemetry-action-gap.md` | 132 streams, 64% firehose |
| 05 | `05-hermes-imitation-forensics.md` | Pattern import forensics |
| 06 | `06-external-patterns-benchmark.md` | Renovate/Argo/MLflow |
| 07 | `07-skill-ecosystem-evolution.md` | Skill maturity 2/10 |
| 08 | `08-self-improvement-roadmap.md` | ★ RL framing + roadmap |
| 09 | `09-dogfood-metrics-commercial.md` | ★ Dogfood metrics + §7 update |
| 10 | `10-competitive-landscape-commercial.md` | ★ AgentOps category + 5 wedges |
| 11 | `11-cross-stack-license-audit-tools.md` | ⚠️ SUPERSEDED by ADR-212 |

Plus 6 raw scanner artifacts (`audit/*.json`, `audit/*.csv`, `audit/secrets-and-leaks-2026-05-06.md`) — `LOCAL-ONLY-README.md` policy.

---

## 8. Other audits and measurements

| File | Type |
|---|---|
| [docs/component-audit.md](../component-audit.md) | Component audit |
| [docs/complexity-audit.md](../complexity-audit.md) | Complexity audit |
| [docs/self-usage-audit.md](../self-usage-audit.md) | Self-usage audit |
| [docs/measurements/cos-duplication-audit-2026-04-30.md](../measurements/cos-duplication-audit-2026-04-30.md) | Duplication audit |
| [docs/measurements/cos-adr-namespace-audit-2026-04-30.md](../measurements/cos-adr-namespace-audit-2026-04-30.md) | ADR namespace audit |
| [docs/manual-tests/primitive-duplication-audit.md](../manual-tests/primitive-duplication-audit.md) | Manual primitive dup audit |
| [docs/manual-tests/cross-stack-license-audit-cli.md](../manual-tests/cross-stack-license-audit-cli.md) | CLI license audit manual test |

---

## How this index stays current

- Re-run `find docs/research docs/reports docs/architecture docs/business -name '*.md'` to spot new files.
- New per-tool research → `docs/research/repo-scout/deep/<owner>__<repo>-<date>.md`.
- New per-gap research → `docs/research/<topic>-<date>.md` or `docs/research/<line-of-work>/<topic>.md`.
- New operational reports → `docs/reports/<topic>-<date>.md`.
- After re-running, append new entries to the relevant section above. **Do not rewrite — append**.

If this index drifts more than 7 days from disk reality, regenerate from `find` output and review with the operator.
