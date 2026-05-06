---
report: external-tools-inventory
date: 2026-05-06
audience: operator
status: draft
generated_by: manual-grep (orchestrator-direct, no agent)
purpose: |
  Inventory every github.com URL in docs/ that was investigated ad-hoc in prior
  sessions (WebSearch / WebFetch / Sonnet bespoke prompts) WITHOUT going
  through the canonical `/repo-scout --batch` skill. Decision input for the
  operator: which URLs to feed into a formal /repo-scout --batch run.
methodology:
  - rg -oI 'https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+' docs/
  - dedup, normalize (strip trailing punctuation, .git, slashes)
  - cross-reference with deep-audit markers in docs/reports/*opus*deep-audit*
  - cross-reference with surface-5-tui-ui-candidates-2026-05-05.md
  - upstream/own-ecosystem URLs filtered out (own org, anthropics host, gentleman-programming upstream, garagon already-integrated, placeholder examples)
limitations:
  - Inventory only — does NOT measure depth of prior investigation
  - "ad-hoc" means "not via /repo-scout --batch"; a URL may have been
    investigated thoroughly via WebSearch+WebFetch but still appears as
    pending here because the canonical primitive was not used
  - Source attribution capped at first 3 docs per URL (not exhaustive)
---

# External Tools Inventory — 2026-05-06

## Summary

- **Total unique GitHub URLs in docs/**: 258
- **Already deeply audited (Opus, source-level)**: 3
- **Upstream / own ecosystem / placeholder (skip from batch)**: 17
- **Surface-5 TUI ad-hoc investigated (depth = surface, not source)**: 76
- **Pending /repo-scout --batch (genuine candidates not formally scouted)**: 162

> **Operator decision**: which buckets feed into a formal `/repo-scout --batch` run? Recommendation: pending bucket = mandatory; surface5 bucket = re-confirm with shallow scout to validate prior ad-hoc verdicts.

## Already deeply audited (skip from /repo-scout --batch) (3)

| URL | Source doc(s) |
|---|---|
| `HKUDS/CLI-Anything` | reports/primitives-and-tools-audit-2026-05-05.md · reports/cli-anything-deep-audit-2026-05-05.md |
| `HKUDS/OpenHarness` | reports/primitives-and-tools-audit-2026-05-05.md · reports/openharness-deep-audit-2026-05-05.md |
| `HKUDS/OpenSpace` | reports/primitives-and-tools-audit-2026-05-05.md · reports/openspace-deep-audit-2026-05-05.md · reports/openspace-opus-deep-audit-2026-05-05.md |

## Upstream / own ecosystem / placeholder (skip) (17)

| URL | Source doc(s) |
|---|---|
| `Gentleman-Programming/engram` | SESSION-HANDOFF-2026-04-25.md · reports/primitives-and-tools-audit-2026-05-05.md · research/engram-mcp-sharing-feasibility-2026-04-20.md |
| `Luum-Home/luum-agent-os` | onboarding-wizard-design.md |
| `Luum-Home/luum-cognitive-os` | getting-started-quick.md · SESSION-HANDOFF-2026-04-17.md · runbooks/run-cos-in-docker.md |
| `anthropics/claude-code` | global-vs-project-config.md · architecture/harness-engineering.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `garagon/aguara` | security-stack.md · component-sources.md · setup/dependencies.md |
| `garagon/mantis` | component-sources.md |
| `garagon/mcp-aguara` | security-stack.md · component-sources.md · setup/dependencies.md |
| `garagon/tero` | component-sources.md |
| `gentleman-programming/homebrew-tap` | research/engram-mcp-sharing-feasibility-2026-04-20.md |
| `luum-ai/luum-agent-os` |  |
| `luum-home/luum-agent-os.git` | quickstart.md |
| `luum-home/luum-cognitive-os.git` | business/value-proposition.md · getting-started.md · business/open-source-design.md |
| `luum/safety-mesh` | package-manager-design.md · cos-package-manager.md · roadmap.md |
| `luum/safety-mesh.git` | cos-package-manager.md |
| `org/repo` | cos-package-manager.md · roadmap.md |
| `tomyaparicio/gentleman-guardian-angel` | component-sources.md |
| `user/cognitive-os-plugin-healthcare` | business/open-source-design.md |

## Surface-5 TUI ad-hoc — re-scout shallow recommended (76)

| URL | Source doc(s) |
|---|---|
| `Aider-AI/aider` | competitive-landscape.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `ArthurSonzogni/FTXUI` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `ClementTsang/bottom` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `HKUDS/nanobot` | reports/remote-control-plane-alternatives-2026-05-05.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `Pythagora-io/gpt-pilot` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `RooCodeInc/Roo-Code` | competitive-landscape.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `Textualize/rich` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `Textualize/textual` | onboarding-wizard-design.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `TheR1D/shell_gpt` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `TinyAGI/tinyagi` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `aaif-goose/goose` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `akavel/up` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `allinurl/goaccess` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `anomalyco/opencode` | reports/multi-provider-agent-delegation-research-2026-05-05.md · reports/remote-control-plane-alternatives-2026-05-05.md · reports/surface-5-tui-ui-candidates-2 |
| `anomalyco/opentui` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `antonmedv/fx` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `aristocratos/btop` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `charmbracelet/bubbles` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `charmbracelet/bubbletea` | cos-package-manager.md · onboarding-wizard-design.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `charmbracelet/crush` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `charmbracelet/glamour` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `charmbracelet/gum` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `charmbracelet/huh` | onboarding-wizard-design.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `charmbracelet/lipgloss` | cos-package-manager.md · onboarding-wizard-design.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `charmbracelet/soft-serve` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `charmbracelet/vhs` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `cline/cline` | competitive-landscape.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `code-yeongyu/oh-my-openagent` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `coder/coder` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `continuedev/continue` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `crossterm-rs/crossterm` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `dankamongmen/notcurses` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `darrenburns/posting` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `derailed/k9s` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `dlvhdr/gh-dash` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `fdehau/tui-rs` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `gcla/termshark` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `gdamore/tcell` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `gitui-org/gitui` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `gptme/gptme` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `gptscript-ai/gptscript` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `gui-cs/Terminal.Gui` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `gyscos/cursive` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `hatoo/oha` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `helix-editor/helix` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `heypinchy/pinchy` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `jarun/nnn` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `jesseduffield/lazydocker` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `jesseduffield/lazygit` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `jonas/tig` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `junegunn/fzf` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `nanobot-ai/nanobot` | reports/remote-control-plane-alternatives-2026-05-05.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `nearai/ironclaw` | reports/remote-control-plane-alternatives-2026-05-05.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `nullclaw/nullclaw` | reports/remote-control-plane-alternatives-2026-05-05.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `openagen/zeroclaw` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `openclaw/openclaw` | reports/multi-provider-agent-delegation-research-2026-05-05.md · reports/remote-control-plane-alternatives-2026-05-05.md · business/competitive-reassessment-ope |
| `openinterpreter/open-interpreter` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `qhkm/zeptoclaw` | reports/remote-control-plane-alternatives-2026-05-05.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `qwibitai/nanoclaw` | reports/remote-control-plane-alternatives-2026-05-05.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `ranger/ranger` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `ratatui/ratatui` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `sachaos/viddy` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `saulpw/visidata` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `sigoden/aichat` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `simonw/llm` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `sipeed/picoclaw` | reports/remote-control-plane-alternatives-2026-05-05.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `superset-sh/superset` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `sxyazi/yazi` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `tstack/lnav` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `vadimdemedes/ink` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `wagoodman/dive` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `warengonzaga/tinyclaw` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `wtfutil/wtf` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `yorukot/superfile` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `zellij-org/zellij` | reports/surface-5-tui-ui-candidates-2026-05-05.md |
| `zeroclaw-labs/zeroclaw` | reports/remote-control-plane-alternatives-2026-05-05.md · reports/surface-5-tui-ui-candidates-2026-05-05.md |

## Pending /repo-scout --batch — formal scout missing (162)

| URL | Source doc(s) |
|---|---|
| `Ar9av/obsidian-wiki` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md |
| `Arize-ai/phoenix` | testing-cognitive-os.md |
| `AutoMaker-Org/automaker` | tool-stack.md |
| `BeehiveInnovations/pal-mcp-server` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `BerriAI/litellm` | component-sources.md |
| `CamiloAndresGTRUniandes/lucy-ai` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `ClickHouse/ClickHouse` | component-sources.md |
| `CodeGraphContext/CodeGraphContext` | reports/primitive-coverage-backend-benchmark-2026-05-01.md · architecture/primitive-coverage-backend-benchmark-2026-05.md |
| `ComposioHQ/agent-orchestrator` | competitive-landscape.md · reports/primitives-and-tools-audit-2026-05-05.md |
| `D4Vinci/Scrapling` | reports/primitives-and-tools-audit-2026-05-05.md |
| `DEEP-PolyU/Awesome-GraphMemory` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md |
| `DavidAnson/markdownlint-cli2` | architecture/primitive-coverage-tooling-research-2026-04.md |
| `FoundationAgents/MetaGPT` | competitive-landscape.md |
| `GAIR-NLP/AgencyBench` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `Gitlawb/openclaude` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `HKUDS/LightRAG` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md · research/llm-wiki-v2-engram-evolution-2026-04-27.md |
| `InternLM/WildClawBench` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `JackChen-me/open-multi-agent` | reports/primitives-and-tools-audit-2026-05-05.md |
| `JuliusBrussee/caveman` | component-sources.md · reports/plugin-caveman-review-2026-04-20.md |
| `MaximeRobeyns/self_improving_coding_agent` | competitive-landscape.md |
| `MemPalace/mempalace` | reports/primitives-and-tools-audit-2026-05-05.md |
| `Mibayy/token-savior` | reports/primitives-and-tools-audit-2026-05-05.md |
| `MiniMax-AI/MiniMax-M2` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `Mirix-AI/MIRIX` | reports/primitives-and-tools-audit-2026-05-05.md |
| `NVIDIA/NeMo-Guardrails` | component-sources.md |
| `NVIDIA/garak` | component-sources.md · architecture/agentic-mastery-license-weight-dx-matrix.md |
| `NousResearch/hermes-agent` | competitive-landscape.md · reports/primitives-and-tools-audit-2026-05-05.md · component-sources.md |
| `NousResearch/hermes-agent-self-evolution` | reports/primitives-and-tools-audit-2026-05-05.md |
| `OSU-NLP-Group/HippoRAG` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md · research/llm-wiki-v2-engram-evolution-2026-04-27.md |
| `OpenAutoCoder/Agentless` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `OpenClaw/OpenClaw` | vs-alternatives.md |
| `OpenHands/OpenHands` | competitive-landscape.md · architecture/agentic-mastery-license-weight-dx-matrix.md |
| `Pi-agent/pi` | competitive-landscape.md · component-sources.md · reports/docs-execution-latest.md |
| `Pratiyush/llm-wiki` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md |
| `QwenLM/qwen-code` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `SWE-agent/SWE-agent` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `SWE-bench/SWE-bench` | testing-cognitive-os.md |
| `SWE-bench/sb-cli` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `THUDM/AgentBench` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `Vasallo94/ObsidianRAG` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md |
| `Vexp-ai/vexp-swe-bench` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `aaronsb/obsidian-mcp-plugin` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md |
| `affaan-m/everything-claude-code` | reports/primitives-and-tools-audit-2026-05-05.md |
| `agent0ai/a0-plugins` | ecosystem-comparison.md · cos-package-manager.md · component-sources.md |
| `agent0ai/agent-zero` | ecosystem-comparison.md · component-sources.md · reports/remote-control-plane-alternatives-2026-05-05.md |
| `agentgateway/agentgateway` | component-sources.md |
| `agentscope-ai/agentscope` | reports/primitives-and-tools-audit-2026-05-05.md |
| `agentsmd/agents.md` | competitive-landscape.md |
| `aider-ai/aider` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `aimasteracc/tree-sitter-analyzer` | architecture/primitive-coverage-tooling-research-2026-04.md |
| `arize-ai/phoenix` | architecture/observability-backend-evaluation-2026-04-24.md |
| `augmentcode/augment-swebench-agent` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `awslabs/agent-squad` | competitive-landscape.md |
| `basicmachines-co/basic-memory` | research/llm-wiki-v2-engram-evolution-2026-04-27.md |
| `benchflow-ai/skillsbench` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `bitbonsai/mcpvault` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md |
| `block/goose` | competitive-landscape.md |
| `brianpetro/obsidian-smart-connections` | research/llm-wiki-v2-engram-evolution-2026-04-27.md |
| `codeking-ai/cligate` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `coder/agentapi` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `coleam00/Archon` | component-sources.md |
| `coleam00/context-engineering-intro` | component-sources.md · research/wisc-framework-analysis.md |
| `comet-ml/opik` | component-sources.md |
| `confident-ai/deepeval` | testing-cognitive-os.md · component-sources.md · tool-stack.md |
| `crewAIInc/crewAI` | testing-cognitive-os.md |
| `cursor/cursor` | security/cognitive-os-agent-security-research-2026-05-05.md |
| `cxcscmu/General-AgentBench` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `daijro/camoufox` | reports/primitives-and-tools-audit-2026-05-05.md |
| `daveshap/AgentZero` | vs-alternatives.md |
| `deepseek-ai/DeepSeek-Coder` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `devwhodevs/engraph` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md |
| `dmgrok/agent_skills_directory` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `dollspace-gay/OpenClaudia` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `drewburchfield/obsidian-graph` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md |
| `e2b-dev/E2B` | component-sources.md |
| `e2b-dev/infra` | component-sources.md |
| `e2b-dev/mcp-server` | component-sources.md |
| `egdev6/engram-monitor` | reports/primitives-and-tools-audit-2026-05-05.md |
| `endorhq/rover` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `epistates/turbovault` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md |
| `explodinggradients/ragas` | component-sources.md · tool-stack.md |
| `floci-io/floci` | reports/primitives-and-tools-audit-2026-05-05.md |
| `forrestchang/andrej-karpathy-skills` | reports/primitives-and-tools-audit-2026-05-05.md |
| `garrytan/gbrain` | reports/primitives-and-tools-audit-2026-05-05.md |
| `gepa-ai/gepa` | reports/primitives-and-tools-audit-2026-05-05.md |
| `getzep/graphiti` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md · research/llm-wiki-v2-engram-evolution-2026-04-27.md |
| `github/markdownlint-github` | architecture/primitive-coverage-tooling-research-2026-04.md |
| `github/spec-kit` | competitive-landscape.md |
| `gnekt/My-Brain-Is-Full-Crew` | reports/primitives-and-tools-audit-2026-05-05.md |
| `google-research/android_world` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `gsd-build/get-shit-done` | reports/primitives-and-tools-audit-2026-05-05.md |
| `invariantlabs/mcp-scan` | component-sources.md |
| `jayminwest/overstory` | competitive-landscape.md |
| `jgravelle/jcodemunch-mcp` | reports/primitive-coverage-backend-benchmark-2026-05-01.md · architecture/primitive-coverage-tooling-research-2026-04.md · architecture/primitive-coverage-backe |
| `kirodotdev/Kiro` | competitive-landscape.md |
| `kittors/CliRelay` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `koalaman/shellcheck-precommit` | architecture/cross-platform-ci.md |
| `kuberstar/qartez-mcp` | reports/primitive-coverage-backend-benchmark-2026-05-01.md · architecture/primitive-coverage-backend-benchmark-2026-05.md |
| `langchain-ai/agentevals` | tool-stack.md · architecture/agentic-mastery-license-weight-dx-matrix.md |
| `langfuse/langfuse` | component-sources.md |
| `letta-ai/letta` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md · research/llm-wiki-v2-engram-evolution-2026-04-27.md |
| `lgcyaxi/oh-my-claude` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `lhr-present/tokenshrink` | reports/primitives-and-tools-audit-2026-05-05.md |
| `lightpanda-io/browser` | reports/primitives-and-tools-audit-2026-05-05.md |
| `littlebearapps/untether` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `luongnv89/claude-howto` | reports/primitives-and-tools-audit-2026-05-05.md |
| `lycheeverse/lychee` | architecture/primitive-coverage-tooling-research-2026-04.md |
| `lycheeverse/lychee-action` | architecture/primitive-coverage-tooling-research-2026-04.md |
| `mattpocock/skills` | reports/primitives-and-tools-audit-2026-05-05.md |
| `maximhq/bifrost` | adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md · gateway-architecture.md |
| `mco-org/mco` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `memvid/memvid` | reports/primitives-and-tools-audit-2026-05-05.md |
| `meta-llama/PurpleLlama` | component-sources.md |
| `microsoft/agent-framework` | competitive-landscape.md |
| `microsoft/graphrag` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md · research/llm-wiki-v2-engram-evolution-2026-04-27.md |
| `midudev/autoskills` | reports/primitives-and-tools-audit-2026-05-05.md · component-sources.md |
| `mindfold-ai/Trellis` | reports/primitives-and-tools-audit-2026-05-05.md |
| `mindsdb/anton` | reports/primitives-and-tools-audit-2026-05-05.md |
| `msdanyg/smart-connections-mcp` | research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md |
| `multica-ai/multica` | reports/primitives-and-tools-audit-2026-05-05.md |
| `musistudio/claude-code-router` | reports/multi-provider-agent-delegation-research-2026-05-05.md · research/claude-code-router-evaluation-2026-04-21.md |
| `nashsu/opencli-rs` | component-sources.md |
| `nashsu/opencli-rs-skill` | component-sources.md |
| `obra/superpowers` | reports/primitives-and-tools-audit-2026-05-05.md |
| `oktsec/oktsec` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `onecli/onecli` | component-sources.md |
| `openai/codex` | competitive-landscape.md · architecture/cross-tool-task-recovery-research-2026-05.md · adrs/ADR-081-codex-harness-adapter.md |
| `openai/procgen` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `opencode-ai/opencode` | competitive-landscape.md · architecture/agentic-mastery-license-weight-dx-matrix.md |
| `praetorian-inc/augustus` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `projectdiscovery/katana` | reports/primitives-and-tools-audit-2026-05-05.md |
| `promptfoo/promptfoo` | testing-cognitive-os.md · component-sources.md · tool-stack.md |
| `pyca/cryptography` | upstream-blockers.md |
| `qodo-ai/pr-agent` | competitive-landscape.md |
| `repowise-dev/repowise` | reports/primitive-coverage-backend-benchmark-2026-05-01.md · architecture/primitive-coverage-backend-benchmark-2026-05.md |
| `rohitg00/agentmemory` | research/llm-wiki-v2-engram-evolution-2026-04-27.md |
| `safishamsi/graphify` | reports/primitives-and-tools-audit-2026-05-05.md |
| `seaweedfs/seaweedfs` | component-sources.md |
| `semgrep/semgrep` | component-sources.md |
| `sethlford/claude-mem` | research/llm-wiki-v2-engram-evolution-2026-04-27.md |
| `shanraisshan/claude-code-best-practice` | reports/primitives-and-tools-audit-2026-05-05.md |
| `sickn33/antigravity-awesome-skills` | component-sources.md |
| `sickn33/antigravity-awesome-skills.git` | component-sources.md |
| `sinewaveai/agent-security-scanner-mcp` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `smykla-skalski/klaudiush` | architecture/cos-dispatch/README.md |
| `snyk/agent-scan` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `stanfordnlp/dspy` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `syntax-syndicate/engram-agent-memory` | reports/adr-137-plus-implementation-review-2026-05-04.md |
| `testcontainers/testcontainers-python` | component-sources.md |
| `topoteretes/cognee` | component-sources.md · research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md · research/llm-wiki-v2-engram-evolution-2026-04-27.md |
| `trailofbits/skills` | component-sources.md |
| `tree-sitter/tree-sitter` | architecture/primitive-coverage-tooling-research-2026-04.md |
| `unclecode/crawl4ai` | component-sources.md |
| `vaporif/parry` | component-sources.md |
| `vercel-labs/coding-agent-template` | reports/multi-provider-agent-delegation-research-2026-05-05.md |
| `vitali87/code-graph-rag` | architecture/primitive-coverage-tooling-research-2026-04.md |
| `volcengine/OpenViking` | reports/primitives-and-tools-audit-2026-05-05.md |
| `wrale/mcp-server-tree-sitter` | architecture/primitive-coverage-tooling-research-2026-04.md |
| `xcrawl-api/xcrawl-skills` | reports/primitives-and-tools-audit-2026-05-05.md |
| `xlang-ai/OSWorld` | architecture/agentic-mastery-license-weight-dx-matrix.md |
| `yamadashy/repomix` | component-sources.md |
| `yifanfeng97/Hyper-Extract` | reports/primitives-and-tools-audit-2026-05-05.md |

## Methodology note

This inventory was produced manually (no agent) via:

```bash
rg -oI 'https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+' docs/ \
  | sed 's/[.,;:)]*$//' | sed 's|/$||' | sort -u
```

Classification rules (applied in order):

1. **Deep audited**: URL slug appears in a `docs/reports/*-opus-deep-audit-*.md` filename
2. **Upstream / own**: URL is in own org (Luum-Home, luum-ai, luum-home, luum), is the harness host (anthropics/claude-code), is upstream of an integration already absorbed (Gentleman-Programming/engram, gentleman-programming/homebrew-tap, garagon/*), or is a placeholder example (org/repo, user/cognitive-os-plugin-healthcare)
3. **Surface-5 TUI ad-hoc**: URL appears in `docs/reports/surface-5-tui-ui-candidates-2026-05-05.md` — these were investigated via ad-hoc WebSearch on 2026-05-05 for Surface-5 (TUI candidates), NOT via `/repo-scout --batch`. Depth = surface only (README + repo metadata, no source-level audit).
4. **Pending**: everything else.

Bucket (4) is the primary backlog for a formal `/repo-scout --batch` invocation.

## Cross-references

- `docs/reports/cli-anything-opus-deep-audit-2026-05-05.md`
- `docs/reports/openharness-opus-deep-audit-2026-05-05.md`
- `docs/reports/openspace-opus-deep-audit-2026-05-05.md`
- `docs/reports/surface-5-tui-ui-candidates-2026-05-05.md`
- `skills/repo-scout/SKILL.md` — canonical primitive that should have been used for buckets (3) and (4)

## Open questions for the operator

1. Bucket (3) `surface5_adhoc` — re-scout via `/repo-scout --batch level=shallow` to ratify or refute the prior ad-hoc TUI verdicts? Or accept the surface-only investigation as sufficient for the TUI decision?
2. Bucket (4) `pending_repo_scout` — single batch run or split by topic cluster (memory / agent-frameworks / observability / etc.)?
3. Some URLs in bucket (4) may already be **adopted** silently in `pyproject.toml` / `packages/*/pyproject.toml`. A future pass should cross-reference declared dependencies and exempt those URLs as "already a dependency, no scout needed".
