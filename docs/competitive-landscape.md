# Competitive Landscape: AI Coding Agent Frameworks & Tools (March 2026)

> Last updated: 2026-03-27

> **Note**: Pricing, valuations, and market data in this document are as of March 2026 and may be outdated. Verify current information from official sources.

## Executive Summary

The AI coding agent market has exploded in 2025-2026. What started as autocomplete copilots has evolved into autonomous multi-agent orchestration systems. The landscape splits into five categories: (1) Terminal/CLI agents, (2) IDE-native agents, (3) Multi-agent orchestrators, (4) Spec-driven development frameworks, and (5) Standards/protocols. Our Cognitive OS competes primarily in categories 3-5.

---

## Category 1: Terminal/CLI Coding Agents

### Claude Code (Anthropic)
- **GitHub**: Closed-source CLI, open CLAUDE.md/AGENTS.md standard
- **Stars**: N/A (proprietary)
- **License**: Proprietary ($20-200/mo)
- **What it does**: Terminal-native agentic coding tool. Reads repos, makes multi-file changes, runs tests, iterates. Supports subagents (up to 10 concurrent), hooks (lifecycle events), skills (reusable markdown-based capabilities), MCP integration, and persistent memory via CLAUDE.md.
- **Key differentiator vs our Cognitive OS**: Native subagent spawning, hooks lifecycle system (PreToolUse, PostToolUse, SessionStart, etc.), built-in memory directory per subagent. Our Cognitive OS runs ON TOP of Claude Code -- we are the orchestration/quality layer.
- **What we can learn**: Their hooks system (11 lifecycle points) is more granular than anything we have. Their subagent memory isolation pattern is clean.

### OpenAI Codex CLI
- **GitHub**: https://github.com/openai/codex
- **Stars**: ~50k+ (open source, Rust-based)
- **License**: Apache 2.0
- **What it does**: Terminal agent built in Rust. Full-screen TUI, reads repos, edits files, runs commands. Supports subagents for parallel tasks, MCP integration, web search, image input, AGENTS.md. Recently added GPT-5.4 mini for subagents.
- **Key differentiator**: Rust-based (fast), desktop app with worktree isolation for parallel agents, cloud automations (CI/CD triggers), Skills system for reusable workflows.
- **What we can learn**: Their "Automations" concept -- agents triggered by cloud events without human prompt. Their worktree-per-agent isolation is production-grade.

### OpenCode
- **GitHub**: https://github.com/opencode-ai/opencode
- **Stars**: 126,000+
- **License**: MIT
- **What it does**: Open-source terminal coding agent. Model-agnostic (75+ providers). Native TUI, desktop app, and IDE extension. LSP integration for deeper code understanding. "Zen" mode with curated model selection. Privacy-first (no code storage).
- **Key differentiator**: Massive community (5M+ users), model flexibility, LSP integration gives structural code understanding beyond text.
- **What we can learn**: LSP integration is powerful -- agents understand code structure, not just text. Their model-agnostic approach means zero vendor lock-in.

### Aider
- **GitHub**: https://github.com/Aider-AI/aider
- **Stars**: ~4,000+ (but heavily used)
- **License**: Apache 2.0
- **What it does**: Terminal-based AI pair programming. Works directly with Git. Proposes/applies code changes as tracked diffs. Supports 100+ languages, auto-commits, voice input, runs tests/linters automatically.
- **Key differentiator**: Deep Git integration (auto-commits with good messages), repo-map for large codebases, linter/test auto-fix loop.
- **What we can learn**: Their test-and-fix loop is elegant -- run tests, detect failures, fix automatically, commit. We should formalize this pattern.

### Goose (Block)
- **GitHub**: https://github.com/block/goose
- **Stars**: 29,400+
- **License**: Apache 2.0
- **What it does**: Open-source extensible AI agent from Block (Square/CashApp). Goes beyond code -- installs packages, runs tests, debugs, orchestrates workflows. Desktop app + CLI. Multi-model support. MCP-native.
- **Key differentiator**: Fully free, backed by Block. MCP-first architecture. Part of Linux Foundation's Agentic AI Foundation (AAIF) alongside AGENTS.md and MCP.
- **What we can learn**: Their MCP-first approach means tools are portable. Being part of AAIF gives standards credibility.

### Gemini CLI (Google)
- **GitHub**: Open source
- **Stars**: N/A
- **License**: Apache 2.0
- **What it does**: Google's terminal agent. Free tier with Gemini 2.5 Pro (1M context), 1000 req/day. Pairs with Jules (autonomous async agent) for background work. AGENTS.md support.
- **Key differentiator**: Free generous tier, 1M context window, Jules integration for async background tasks.
- **What we can learn**: The sync (Gemini CLI) + async (Jules) split is a useful pattern. Users do focused work in terminal while background agents handle separate tasks.

---

## Category 2: IDE-Native Agents

### Cursor
- **GitHub**: Closed source
- **Stars**: N/A (proprietary)
- **License**: Proprietary ($20/mo+)
- **What it does**: AI-first IDE (VS Code fork). Tab completion, multi-file agentic edits, .cursorrules for project config. Valued at $29.3B in 2026. In March 2026, launched Cloud Agents: isolated VM-per-agent execution with full desktop environment, terminal, and browser. Agents clone repos, setup environments, write code, test, fix bugs, record screen videos, and create PRs. Self-hosted option via `agent worker start` with Kubernetes operator for enterprise scale. Multi-trigger support (Slack, GitHub, Linear, webhooks, API, schedule). 30% of Cursor's own code is now agent-written. Salesforce reports 90% of 20K developers using Cursor. Over half of Fortune 500 in production.
- **Key differentiator**: IDE-native experience plus cloud agent execution engine. Video proof of agent work enables 30-second review instead of 500-line code review. Self-hosted workers keep code on customer infrastructure. Many devs use Cursor + Claude Code together.
- **What we can learn**: .cursorrules showed the market wants project-level AI configuration. Cloud agents with video proof change the review paradigm. Self-hosted workers address enterprise data sovereignty concerns. The execution engine is powerful but lacks governance, memory, and quality gates -- a natural complementarity with Cognitive OS.

### Windsurf (Cognition/Codeium)
- **GitHub**: Closed source
- **Stars**: N/A
- **License**: Proprietary ($15-60/mo)
- **What it does**: Agentic IDE acquired by Cognition AI (Devin makers) for ~$250M. Cascade agent for multi-step edits with deep repo context. Turbo Mode for autonomous terminal execution. Ranked #1 in LogRocket AI Dev Tool Power Rankings (Feb 2026).
- **Key differentiator**: Cascade's multi-step planning + Cognition's Devin integration. Turbo Mode autonomy.
- **What we can learn**: Their Cascade plan-then-execute pattern aligns with our SDD approach. The Cognition acquisition shows the market values agent+IDE convergence.

### Cline
- **GitHub**: https://github.com/cline/cline
- **Stars**: High (5M+ users, Apache 2.0)
- **License**: Apache 2.0
- **What it does**: VS Code extension. Plan/Act mode separates strategy from execution. Browser automation, terminal commands, MCP integration. Human approval at each step.
- **Key differentiator**: Plan/Act mode is their killer feature. The human-in-the-loop at every step builds trust.
- **What we can learn**: Plan/Act separation is exactly our SDD spec-then-apply pattern, but at the individual task level.

### Roo Code
- **GitHub**: https://github.com/RooCodeInc/Roo-Code
- **Stars**: 22,000+
- **License**: Apache 2.0
- **What it does**: VS Code extension that turns editor into an AI dev team. Plans refactoring, identifies affected files, makes coherent edits, auto-commits. SOC 2 Type 2 compliant.
- **Key differentiator**: SOC 2 compliance for enterprise. Multi-file coherent refactoring.
- **What we can learn**: SOC 2 compliance is table stakes for enterprise. We should consider compliance implications.

### PearAI
- **GitHub**: https://github.com/trypear
- **Stars**: Moderate
- **License**: Open source (VS Code fork)
- **What it does**: Open-source VS Code fork integrating Roo Code/Cline and Continue. Curates best open-source AI tools into one editor.
- **Key differentiator**: Aggregator approach -- best-of-breed open source tools in one package.
- **What we can learn**: The aggregator model works. Users want curated, not fragmented.

---

## Category 3: Multi-Agent Orchestrators

### Composio Agent Orchestrator
- **GitHub**: https://github.com/ComposioHQ/agent-orchestrator
- **Stars**: Growing rapidly
- **License**: Open source
- **What it does**: Manages fleets of parallel coding agents. Each agent gets its own git worktree, branch, and PR. Dual-layer architecture: Planner (task decomposition) + Executor (tool interaction). Auto-handles CI fixes, merge conflicts, code reviews. Agent-agnostic (Claude Code, Codex, Aider), runtime-agnostic (tmux, Docker), tracker-agnostic (GitHub, Linear).
- **Key differentiator**: Production-grade fleet management. Just-in-Time context management reduces token waste. Stateful orchestration with audit trails. 43k lines with 3,288 test cases.
- **What we can learn**: Their JIT context management is smart -- only route relevant tool definitions. Their error recovery (404/500 handling) is built-in. We should adopt their agent-agnostic approach.

### Overstory
- **GitHub**: https://github.com/jayminwest/overstory
- **Stars**: Early stage
- **License**: Open source
- **What it does**: Multi-agent orchestrator using git worktrees + tmux. SQLite mail system for inter-agent communication (WAL mode, 1-5ms). FIFO merge queue with 4-tier conflict resolution. Tiered watchdog (mechanical daemon, AI triage, monitor agent). Pluggable runtime adapters (Claude Code, Pi, Gemini CLI).
- **Key differentiator**: SQLite-based inter-agent messaging is clever and fast. 4-tier conflict resolution for merges. Watchdog system for fleet health.
- **What we can learn**: Their inter-agent messaging via SQLite is elegant. Their merge conflict resolution tiers are well-thought-out. Watchdog pattern for agent health monitoring.

### Microsoft Agent Framework
- **GitHub**: https://github.com/microsoft/agent-framework
- **Stars**: Growing
- **License**: MIT
- **What it does**: Multi-language framework (Python + .NET) for building, orchestrating, and deploying AI agents. Graph-based orchestration. From simple chat to complex multi-agent workflows.
- **Key differentiator**: Microsoft backing, .NET support, Azure integration.
- **What we can learn**: Enterprise needs multi-language support. Graph-based orchestration is a proven pattern.

### AWS Agent Squad
- **GitHub**: https://github.com/awslabs/agent-squad
- **Stars**: Moderate
- **License**: Apache 2.0
- **What it does**: Lightweight framework for orchestrating multiple specialized AI agents. Handles complex conversations with agent routing.
- **Key differentiator**: AWS backing, minimal overhead, conversation routing.
- **What we can learn**: Lightweight is valuable. Not every orchestrator needs to be heavy.

---

## Category 4: Spec-Driven Development Frameworks

### GitHub Spec Kit
- **GitHub**: https://github.com/github/spec-kit (GitHub official)
- **Stars**: 72,700+
- **License**: MIT
- **What it does**: Structured process for spec-driven development. Supports 22+ AI agent platforms. Generates requirements, design, and task specs. Works with Copilot, Claude Code, Gemini CLI.
- **Key differentiator**: GitHub official backing. Cross-platform (22+ agents). 110 releases. Largest SDD community.
- **What we can learn**: Their cross-agent compatibility is the gold standard. We should ensure our SDD artifacts are Spec Kit compatible.

### Kiro (AWS)
- **GitHub**: https://github.com/kirodotdev/Kiro
- **Stars**: Growing
- **License**: Proprietary (with open elements)
- **What it does**: Agentic IDE + CLI from AWS. Three-file spec system: requirements.md (EARS format), design.md, tasks.md. Agent Hooks for filesystem-event automation. Agent Steering for project-level behavior control. AWS-native (Bedrock, Lambda, CDK). Available in GovCloud.
- **Key differentiator**: AWS ecosystem integration. Agent Hooks react to filesystem events (save, create, delete). GovCloud availability for government clients.
- **What we can learn**: Their Agent Hooks (filesystem-triggered automation) is powerful. EARS format for requirements is structured. GovCloud shows regulated industries need agent tools too.

### Tessl
- **GitHub**: Available (Tessl Framework + Registry)
- **Stars**: Growing
- **License**: Open source
- **What it does**: Agent enablement platform with Spec Framework and Spec Registry (10,000+ pre-built specs). Specs live in codebase as long-term memory. Skills with eval scores, GitHub badges, watch mode for auto-monitoring.
- **Key differentiator**: Spec Registry with 10k+ specs prevents API hallucinations. Quality scoring for specs/skills.
- **What we can learn**: A registry of pre-built specs/skills is a distribution advantage. Eval scoring for quality is smart. We should consider a skill marketplace.

### BMAD Method v6
- **Already known** - 12+ personas, Party Mode, file-based context passing, strict role boundaries across full SDLC.
- **Stars**: Growing
- **What we can learn**: Persona specialization (PM, Architect, Developer, QA, DevOps) maps cleanly to SDD phases.

### Intent (Augment Code)
- **Website**: augmentcode.com/product/intent
- **Stars**: N/A (proprietary, Mac-only beta)
- **License**: Proprietary
- **What it does**: Desktop workspace for spec-driven development with multi-agent orchestration. Living specs that update as agents work. Coordinator/specialist/verifier architecture. BYOA model supports Claude Code, Codex, OpenCode. Context Engine processes 400k+ files. SOC 2 Type II + ISO 42001 certified.
- **Key differentiator**: Living specs (specs update to reflect what was actually built). Context Engine at 400k+ files. Enterprise compliance (SOC 2, ISO 42001). Zero-retention architecture.
- **What we can learn**: Living specs (auto-updating specs) is a powerful concept we don't have. Their Context Engine at 400k files shows enterprise scale needs. Zero-retention for privacy-sensitive orgs.

---

## Category 5: Autonomous Platforms & Cloud Agents

### Devin 2.0 (Cognition AI)
- **Website**: devin.ai
- **Stars**: N/A (proprietary)
- **License**: Proprietary ($20-500/mo)
- **What it does**: Autonomous AI software engineer. Plans, executes, debugs, deploys, monitors. Cloud-based IDE with parallel Devins. 83% more tasks completed per compute unit vs v1. Integrates with Windsurf IDE.
- **Key differentiator**: Full autonomy -- end-to-end from plan to deploy. Cloud-based parallel instances. Now affordable at $20/mo entry.
- **What we can learn**: The price drop from $500 to $20 shows the market pressure. Parallel agent instances in cloud is the future.

### OpenHands
- **GitHub**: https://github.com/OpenHands/OpenHands
- **Stars**: 65,000+
- **License**: MIT
- **What it does**: Open-source autonomous software engineering platform. Agents modify code, run commands, browse web, call APIs. GitHub/GitLab/Slack/CI-CD integrations. Docker/Kubernetes isolated environments. SDK for building custom agents. Auto-generates PRs from logs, summarizes PRs, generates test suites and docs.
- **Key differentiator**: Cloud-native (Docker/K8s isolation). SDK for custom agent building. 65k stars = massive community.
- **What we can learn**: Their SDK approach (composable Python library) is extensible. Docker isolation per agent is production-ready. Their auto-PR-from-logs feature is creative.

### MetaGPT
- **GitHub**: https://github.com/FoundationAgents/MetaGPT
- **Stars**: 64,100+
- **License**: MIT
- **What it does**: Multi-agent collaboration simulating a software company. Built-in roles (PM, architect, project manager, engineer). SOP-driven processes. Natural language to user stories, data structures, APIs. Data Interpreter for autonomous data analysis. MGX product launched as "first AI agent development team."
- **Key differentiator**: SOP-driven (Standard Operating Procedures reduce hallucination). Complete team simulation. Data Interpreter with state-of-the-art ML scores.
- **What we can learn**: SOP-driven execution reduces agent deviation. Their team simulation with distinct roles is mature. AFlow paper (ICLR 2025 oral) shows automated workflow generation is possible.

### Factory AI
- **Website**: factory.ai
- **Stars**: N/A (proprietary)
- **License**: Proprietary
- **What it does**: Agent-native development platform. "Droids" for specific tasks (feature dev, code review, debugging). Triggered from issue assignment or mentions. Auto-creates PRs with traceability from ticket to code. Parallel scripting at scale for CI/CD, migrations, maintenance. Integrates with GitHub, GitLab, Jira, Notion, Sentry.
- **Key differentiator**: Ticket-to-code traceability. Auto-triggered from issue systems. Scale-out for migrations/maintenance.
- **What we can learn**: Auto-triggering from issue trackers is a workflow gap we have. Ticket-to-code traceability is valuable for audit.

### GitHub Copilot (Coding Agent mode)
- **Website**: github.com/features/copilot
- **Stars**: N/A (proprietary)
- **License**: Proprietary ($10-39/mo)
- **What it does**: Autonomous coding agent that works from GitHub issues. Creates branches, commits, PRs autonomously. Reviews its own code before opening PR. Runs security scanning (code scanning, secrets, dependency vulnerabilities). Agentic code review architecture (March 2026). 60M+ code reviews completed.
- **Key differentiator**: GitHub-native. Self-review before PR. Security scanning built-in. Largest installed base.
- **What we can learn**: Self-review before PR is a quality gate we should adopt. Security scanning as default (not opt-in) is smart.

### Amazon Q Developer
- **Website**: aws.amazon.com/q/developer
- **Stars**: N/A (proprietary)
- **License**: Proprietary ($19/mo)
- **What it does**: Full-lifecycle AI coding with 25+ languages. Code transformations (Java 8->17, .NET upgrades, Oracle->PostgreSQL SQL). Vulnerability scanning. AWS infrastructure expertise. IDE support (VS Code, JetBrains, Eclipse). 50% code acceptance rate at NAB.
- **Key differentiator**: Code transformation agents (language upgrades). AWS expertise built-in. Enterprise migration automation.
- **What we can learn**: Code transformation/migration agents are a distinct category we don't address. Language upgrade automation is high-value enterprise work.

---

## Category 6: Standards & Protocols

### AGENTS.md
- **GitHub**: https://github.com/agentsmd/agents.md
- **Stars**: High adoption (60k+ repos)
- **License**: Open (Linux Foundation / AAIF)
- **What it does**: Open standard for AI coding agent configuration. Machine-readable project instructions for build, test, conventions. Supported by every major AI coding tool (Copilot, Cursor, Windsurf, Claude Code, Codex, Gemini CLI, etc.).
- **Key differentiator**: Industry standard. Linux Foundation backing. Universal adoption.
- **What we can learn**: We should generate AGENTS.md from our Cognitive OS config so our rules work with ANY tool, not just Claude Code.

### Model Context Protocol (MCP)
- **Origin**: Anthropic
- **License**: Open
- **What it does**: Standardized protocol for connecting AI agents to tools, data sources, and services. Eliminates need for bespoke connectors. Adopted across all major frameworks.
- **What we can learn**: MCP is the USB of AI tools. Our Cognitive OS should expose skills as MCP servers for portability.

### Qodo (formerly CodiumAI)
- **GitHub**: https://github.com/qodo-ai/pr-agent
- **Stars**: Significant (PR Agent is open source)
- **License**: Proprietary (with open-source PR Agent)
- **What it does**: AI code quality platform. Qodo Cover generates autonomous regression tests. Qodo 2.0 (Feb 2026) introduced multi-agent code review architecture. Highest F1 score in AI code review benchmarks. GitHub/GitLab/Bitbucket/Azure DevOps integration.
- **Key differentiator**: Quality-first approach. Autonomous regression test generation. Multi-agent review architecture. Benchmark leadership.
- **What we can learn**: Autonomous test generation is a gap in our Cognitive OS. Their multi-agent review architecture (multiple reviewers with different focuses) is sophisticated.

---

## Category 7: Self-Improving & Learning Agents

### OpenClaw
- **Already known** - 247k+ stars, messaging-first architecture.

### Hermes Agent (Nous Research)
- **Already known** - Self-improving architecture.

### Superpowers
- **Already known** - 103k stars, TDD/debugging skills.

### Self-Improving Coding Agent (Robeyns)
- **GitHub**: https://github.com/MaximeRobeyns/self_improving_coding_agent
- **Stars**: Small
- **License**: Open source
- **What it does**: Agent framework that works on its own codebase. Generates, tests, refines code in a loop. Uses execution feedback for learning.
- **What we can learn**: Self-modification is the ultimate agent capability. Our Cognitive OS should track its own failure patterns.

---

## Competitive Matrix

| Dimension | Our Cognitive OS | Spec Kit | BMAD v6 | Superpowers | OpenClaw | Hermes | Kiro | Intent | MetaGPT | OpenHands | Composio Orch | Overstory | Devin | Factory | Copilot Agent | Qodo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Memory/Persistence** | Engram (cross-session) | None | File-based | File-based | Message store | Self-improving memory | Agent Steering files | Living specs | SOP state | Session state | Stateful orchestration | SQLite mail | Cloud state | Cloud state | GitHub context | PR history |
| **Multi-Agent Orchestration** | Agent Teams Lite (delegate/task) | None | 12+ personas | Single agent | Messaging swarm | Single agent | Single + Hooks | Coordinator/Specialist/Verifier | Team simulation (PM, Arch, Dev) | SDK-based | Fleet management (worktrees) | Worktrees + tmux + SQLite | Parallel cloud instances | Droids (specialized) | Single agent per issue | Multi-agent review |
| **Quality Enforcement** | Constitutional gates, SDD verify | Spec validation | Role boundaries | TDD-first | Community review | Self-correction | Agent Hooks (auto-test/lint) | Verifier agent | SOP reduces hallucination | Auto-test generation | CI fix auto-handling | 4-tier merge resolution | Self-review | Auto-review | Self-review + security scan | Autonomous test gen, F1 benchmark leader |
| **Self-Improvement** | Manual skill updates | None | None | Skill library updates | Community-driven | Core design | None | Spec updates | AFlow (automated workflow gen) | None | Error recovery logic | Watchdog system | Cloud learning | None | None | Benchmark-driven |
| **Observability** | None (gap) | None | None | None | None | None | None | None | None | None | Audit trails | Fleet dashboard | Cloud IDE | Ticket-to-code tracing | GitHub UI | Review dashboards |
| **Cost Control** | None (gap) | Free | Free | Free | Free | Free | Proprietary | Proprietary | Free (MIT) | Free (MIT) | Free | Free | $20-500/mo | Proprietary | $10-39/mo | Freemium |
| **Portability (Multi-IDE)** | Claude Code only | 22+ agents | Any LLM | Claude-focused | Any LLM | Any LLM | Kiro IDE only | Mac only, BYOA (4 agents) | Any LLM | Any LLM | Agent-agnostic | Runtime adapters | Web IDE | Multi-IDE | GitHub-native | Multi-platform |
| **Security/Guardrails** | Constitutional gates, prohibited zones | None | Role boundaries | None | None | None | GovCloud, AWS IAM | SOC 2 + ISO 42001 | None | Docker/K8s isolation | None | None | Cloud isolation | Enterprise SSO | Code/secret scanning | None |
| **Workflow Automation (CI/CD)** | Hooks (manual) | None | None | None | None | None | Agent Hooks (filesystem) | None | None | CI/CD integration | Auto CI fix | None | Deploy + monitor | Auto-triggered from issues | GitHub Actions native | PR Agent (auto-review) |
| **Squad/Team Management** | Agent Teams Lite | None | Party Mode (12+) | None | Swarm | None | None | BYOA orchestration | Full team (5+ roles) | None | Fleet management | Fleet with watchdog | Parallel Devins | Droids fleet | Single per issue | None |
| **Phase System** | SDD phases (7 phases) | 3 phases (req/design/tasks) | Full SDLC | Dev-focused | None | None | 3 specs (req/design/tasks) | Spec lifecycle | Full SDLC simulation | None | Plan + Execute | None | Plan/Execute/Deploy | Ticket-to-PR | Issue-to-PR | Review phases |
| **Benchmark/Testing of Tool** | stress-test-strategy.md | GitHub CI | None | SWE-Bench | None | Self-eval | None | None | AFlow (ICLR top 1.8%) | SWE-Bench evaluated | 3,288 test cases | None | ACU efficiency metrics | None | 60M reviews | F1 score benchmark |

---

## Key Gaps in Our Cognitive OS

### Critical Gaps (address immediately)

1. **Observability**: Zero telemetry, tracing, or dashboards. Composio has audit trails, Overstory has fleet dashboards, VoltAgent has VoltOps Console. We fly blind.
2. **Cost Control**: No token tracking, no budget limits. Every competitor with a paid tier tracks compute. We should at minimum track token usage per phase.
3. **Portability**: Locked to Claude Code. Spec Kit supports 22+ agents, Composio is agent-agnostic, Overstory has pluggable runtimes. We should output AGENTS.md and support at least Codex/Gemini CLI.
4. **Autonomous Test Generation**: Qodo generates regression suites autonomously. Our Gate 3 says "test before merge" but we don't generate the tests.
5. **CI/CD Integration**: Copilot and Factory auto-trigger from issues/PRs. Our hooks are lifecycle-based but not CI/CD-integrated.

### Important Gaps (address in next quarter)

6. **Living Specs**: Intent's specs auto-update to reflect what was built. Our SDD specs are static after creation.
7. **Self-Review Before PR**: Copilot reviews its own code before opening the PR. We should add a self-review step to sdd-verify.
8. **Agent Health Monitoring**: Overstory's tiered watchdog system monitors agent health. We have no equivalent.
9. **Spec/Skill Registry**: Tessl has 10k+ pre-built specs. We have no marketplace or registry for reusable specs/skills.
10. **Error Recovery**: Composio has built-in error recovery for API failures. Our agents fail silently.

### Nice-to-Have Gaps (future consideration)

11. **Code Transformation Agents**: Amazon Q can upgrade Java 8->17 automatically. Migration automation is high-value.
12. **Browser Automation**: Cline and OpenHands include browser interaction. Not core to our mission but useful.
13. **Voice Input**: Aider supports voice programming. Accessibility feature.

---

## Strategic Insights

### Market Trends

1. **SDD is winning**: Spec-driven development has gone from niche to mainstream. GitHub Spec Kit at 72k stars, Kiro from AWS, Intent from Augment, Martin Fowler writing about it. Our early bet on SDD was correct.

2. **Multi-agent is table stakes**: Every serious tool now supports parallel agents. The question is no longer "can AI write code?" but "how do I run multiple agents without chaos?"

3. **Standards convergence**: AGENTS.md (Linux Foundation), MCP (Anthropic), and CLAUDE.md are the three standards. All three are complementary. Our Cognitive OS should interop with all three.

4. **Agent-agnostic is the future**: Composio, Overstory, Intent all support multiple agent runtimes. Being Claude-only is a competitive weakness.

5. **Quality over speed**: The market is shifting from "how fast can AI code" to "how do I ensure AI code is correct." Qodo, Copilot self-review, and quality gates are winning features.

### Competitive Position

**Our strengths:**
- Engram cross-session memory is more sophisticated than most competitors
- Constitutional gates are a unique security/quality layer
- SDD phase system is well-structured with clear dependency graph
- Agent Teams delegation pattern prevents context bloat
- Integration with real project workflows (not just toy demos)

**Our weaknesses:**
- Zero observability
- Claude Code lock-in
- No CI/CD integration
- No autonomous test generation
- No skill/spec registry or marketplace
- No cost tracking

### Recommended Priorities

1. **AGENTS.md export**: Generate AGENTS.md from our config for cross-tool compatibility
2. **Observability layer**: Token tracking, phase timing, success/failure rates
3. **Self-review gate**: Add automated self-review before PR in sdd-verify
4. **Spec Kit compatibility**: Ensure our SDD artifacts can be consumed by Spec Kit
5. **Agent-agnostic runtime**: Abstract agent spawning to support Codex/Gemini CLI

---

## Tool Reference Quick-Lookup

| Tool | Category | Stars | License | URL |
|------|----------|-------|---------|-----|
| OpenCode | CLI Agent | 126k | MIT | github.com/opencode-ai/opencode |
| OpenHands | Autonomous Platform | 65k | MIT | github.com/OpenHands/OpenHands |
| MetaGPT | Multi-Agent Platform | 64k | MIT | github.com/FoundationAgents/MetaGPT |
| Spec Kit | SDD Framework | 72.7k | MIT | github.com/github/spec-kit |
| Goose | CLI Agent | 29.4k | Apache 2.0 | github.com/block/goose |
| Cline | IDE Agent | High | Apache 2.0 | github.com/cline/cline |
| Roo Code | IDE Agent | 22k | Apache 2.0 | github.com/RooCodeInc/Roo-Code |
| Composio Orchestrator | Multi-Agent | Growing | Open Source | github.com/ComposioHQ/agent-orchestrator |
| Overstory | Multi-Agent | Early | Open Source | github.com/jayminwest/overstory |
| VoltAgent | Agent Framework | Growing | MIT | github.com/VoltAgent/voltagent |
| Codex CLI | CLI Agent | 50k+ | Apache 2.0 | github.com/openai/codex |
| Aider | CLI Agent | 4k+ | Apache 2.0 | github.com/Aider-AI/aider |
| AGENTS.md | Standard | 60k+ repos | AAIF/LF | github.com/agentsmd/agents.md |
| Qodo PR Agent | Quality | Significant | Open Source | github.com/qodo-ai/pr-agent |
| Kiro | SDD IDE | Growing | Proprietary | github.com/kirodotdev/Kiro |
| Tessl | Spec Registry | Growing | Open Source | tessl.io |
| MS Agent Framework | Multi-Agent | Growing | MIT | github.com/microsoft/agent-framework |
| AWS Agent Squad | Multi-Agent | Moderate | Apache 2.0 | github.com/awslabs/agent-squad |

---

## Cursor Cloud Agents — Execution Layer (March 2026)

### What Cursor Shipped

Cursor launched self-hosted cloud agents that fundamentally change how code gets built:

- **Isolated VM per agent**: Each agent gets its own virtual machine, terminal, browser, full desktop environment
- **End-to-end workflow**: Clone repo -> setup env -> write code -> test -> fix bugs -> record video -> create PR
- **Video proof**: Agents record screen videos of what they built, enabling 30-second review instead of 500-line code review
- **Self-hosted option**: `agent worker start` — one command, agents run on YOUR infrastructure, code never leaves
- **Enterprise scale**: Kubernetes operator + Helm chart for thousands of workers
- **Multi-trigger**: Slack, GitHub, Linear, webhooks, API, schedule, events
- **Real results**: 30% of Cursor's own code is now agent-written. Salesforce: 90% of 20K developers use Cursor. Over half of Fortune 500 in production.

### What Cursor Doesn't Have

| Capability | Cursor | Cognitive OS |
|-----------|--------|--------------|
| Isolated execution | VM per agent | Delegates to sub-agents |
| Video proof | Screen recording | Trust Reports with evidence |
| Persistent memory | None — each agent starts fresh | Engram with topic keys |
| Quality gates | None — human reviews PR | 18 thematic rules, staged verification |
| Cost governance | None — agents run until done | Budget enforcement, rate limiting, model routing |
| Pipeline discipline | None — single task per agent | SDD: spec -> design -> tasks -> apply -> verify |
| Self-healing | None | Error learning, auto-repair, circuit breakers |
| Phase awareness | None | reconstruction/stabilization/production/maintenance |
| Multi-agent coordination | Parallel agents, no coordination | Squads with KPIs and escalation |
| Adaptive complexity | None — treats all tasks the same | Adaptive bypass: trivial=direct, critical=full SDD |

### Complementarity: COS as Governance Layer for Cursor Agents

Cursor provides the execution engine. Cognitive OS provides the governance brain. Together:

```
Human gives task
    |
    v
Cognitive OS (Layer 2)
  - Classifies complexity (adaptive bypass)
  - Reads project phase and profile
  - Checks budget and rate limits
  - Selects appropriate workflow (direct / delegate / SDD)
  - Loads relevant rules and skills
    |
    v
Cursor Cloud Agent (Layer 1)
  - Gets isolated VM
  - Writes code, tests, records video
  - Returns merge-ready PR
    |
    v
Cognitive OS (Layer 2)
  - Validates claims (anti-hallucination)
  - Runs acceptance criteria
  - Checks trust score
  - Saves learnings to Engram
  - Tracks cost
    |
    v
Human reviews video + Trust Report, approves or gives feedback
```

The "1 person directing 10 agents" scenario that Cursor envisions requires governance at scale:
- Without COS: 10 agents running in parallel with no cost tracking, no quality gates, no shared memory. Chaos.
- With COS: Each agent governed by phase rules, cost-tracked, quality-gated, memory-sharing. Orchestrated.

### Integration Points

| Trigger | COS Role | Cursor Role |
|---------|----------|-------------|
| Linear ticket arrives | Classify complexity, select workflow, check budget | Spin up agent VM, execute task |
| Agent completes PR | Validate claims, run acceptance criteria, save to Engram | Record video, create PR |
| Budget exceeded | Block new agents, downgrade model | N/A — COS controls the gate |
| Agent fails 3 times | Auto-rollback, escalate to human | N/A — COS manages retry loop |
| Cross-service change | Route to correct squad, check blast radius | Execute in isolated VMs per service |

---

## Agent Skills Ecosystem (March 2026)

Anthropic launched Agent Skills as an open standard on December 18, 2025. A skill is a directory with a SKILL.md file that teaches AI agents how to handle specific tasks. As of March 2026, 16+ major tools support the standard.

### Major Skill Registries

| Platform | Skills | Installs | Model | URL |
|----------|--------|----------|-------|-----|
| SkillsMP | 351,349 | -- | Crawls GitHub for SKILL.md, semantic search | skillsmp.com |
| Skills.sh (Vercel) | 83,627 | 8M+ | Curated registry with CLI, 18+ agent support | skild.sh |
| ClawHub (OpenClaw) | 15,000+ | 1.5M+ | Marketplace for OpenClaw framework | clawhub.ai |
| MCP Registry | 100+ servers | -- | Official Anthropic registry for MCP servers | registry.modelcontextprotocol.io |

### What Registries DON'T Provide (Cognitive OS's Moat)

- **Composed packages**: skill + rule + hook + config as an interdependent unit
- **Governance layer**: quality gates, acceptance criteria, verification pipelines
- **Orchestration**: SDD pipeline, multi-agent coordination, squads
- **Memory**: Persistent cross-session memory (Engram)
- **Self-healing**: Error learning, auto-repair, circuit breakers
- **Cost governance**: Token economy, rate limiting, budget enforcement
- **Efficiency profiles**: lean/standard/full configurations

### Strategic Position

Skills registries = npm (individual packages). Cognitive OS = Linux distribution (composed, configured, orchestrated system). The gap: no one offers "distro-level" composition for AI agents.

```
Layer 3: Skills Registries (Skills.sh, SkillsMP, ClawHub, MCP Registry)
         ^ individual skills, MCP servers
Layer 2: Cognitive OS (governance, orchestration, memory, self-healing)
         ^ rules, hooks, profiles, pipelines
Layer 1: AI Model (Claude, GPT, Gemini, local models)
         ^ raw intelligence
```

Like Astro with React/Svelte/Vue -- Cognitive OS doesn't replace the skills ecosystem, it orchestrates it.

---

## Engram vs AutoDream: Memory Architecture Comparison

Claude Code launched AutoDream (March 2026), a built-in memory consolidation feature that compresses agent memory files while idle — marketed as "REM sleep for AI." The approach has fundamental flaws that Engram solves by design.

### How AutoDream Works

AutoDream runs a sub-agent that reads all session transcripts and memory files, decides what is important, enforces a 200-line cap, and deletes everything else. The model compresses 80-90% of existing tokens. This happens automatically and invisibly.

### The Problem (per Karpathy)

> "The LLM is a CPU and the context window is RAM. Every call starts from zero except what you explicitly put in."

AutoDream gives the model responsible for performance degradation the responsibility for its own memory compression. Compression is invisible and fails silently — hours of architecture decisions can be reduced to a tag like "discussed architecture", losing all nuance.

### Engram vs AutoDream

| Dimension | AutoDream | Engram (Cognitive OS) |
|-----------|-----------|----------------------|
| Storage philosophy | Compress and delete | Store everything, retrieve selectively |
| Who decides what to keep | The model (invisible) | The user/agent explicitly (topic keys) |
| Data loss | 80-90% compressed away permanently | Zero — all observations persist |
| Retrieval | Load entire compressed file at session start | Selective: `mem_search` -> `mem_get_observation` |
| Organization | Single .md file, unstructured | Prefixed topic keys (`planning/`, `bugfix/`, `architecture/`) |
| Auditability | No audit trail — deleted data is gone | Full audit trail — every save timestamped |
| Cross-project | Per-project only | Shared Engram with project-scoped namespaces |
| Control | Model modifies its own memory | Model writes, never deletes without instruction |
| Failure mode | Silent context loss | Explicit — search returns nothing if not saved |

### Why This Matters

The paper "Evaluating AGENTS.md" (arxiv.org/abs/2602.11988) found that context files reduce task success rates. AutoDream tries to solve this by compressing context. Engram solves it differently: store everything externally, load only what the current task needs. This is context engineering — "the delicate art of filling the context window with exactly the right information" (Karpathy) — not context destruction.

### Cognitive OS Memory Architecture

```
Session N (active)
  |
  v
mem_save() -- explicit, structured, topic-keyed
  |
  v
Engram (SQLite, persistent, never compressed)
  |
  v
Session N+1 (new session)
  |
  v
mem_search() -- selective retrieval, only what's needed
  |
  v
Context window -- filled with exactly the right information
```

No sleep metaphors. No invisible compression. No silent data loss. Just structured storage with selective retrieval — the way databases have worked for 50 years.

---

### Sources

- [SkillsMP](https://skillsmp.com/) | [Skills.sh](https://skild.sh/) | [MCP Registry](https://registry.modelcontextprotocol.io/)
- [Agent Skills Are the New npm](https://www.buildmvpfast.com/blog/agent-skills-npm-ai-package-manager-2026)
- [AI Agent Skills Guide 2026](https://serenitiesai.com/articles/agent-skills-guide-2026)
- [Paper: Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988) — ETH Zurich
- Claude Code AutoDream — Anthropic, March 2026 (experimental feature)
