# Multi-Provider Agent Delegation Research — 2026-05-05

## Question

The working question was whether Cognitive OS had already researched and built
ways to avoid tying agent execution to Claude Code, Codex, or a single IDE/model
surface, and how the broader ecosystem delegates tasks to Qwen, DeepSeek,
MiniMax, Kimi, and similar providers by task type.

This report extends the prior local research with a fresh web pass over 51
source pages. It is a research and continuity artifact, not a runtime support
claim.

## Current local answer

Cognitive OS has not reduced the problem to "use OpenClaw" or "use Claude Code
with a different model." The current implementation is split across three
layers:

1. **Harness projection**: project-local structural support exists for Claude,
   Codex, OpenCode, Cursor, VS Code Copilot, Qwen Code, Kimi Code CLI, Gemini
   CLI, Warp, Amp, Junie, Qoder, Factory Droid, Cline, Continue, Kilo, Zed,
   Augment, Goose, and Aider. This means COS can project files such as rules,
   instructions, MCP placeholders, and settings into those tools without
   account-backed runtime claims.
2. **Provider/model routing**: `lib/model_catalog.py`, `lib/model_router.py`,
   `lib/model_recommender.py`, and related tests implement capability-centric
   routing across model families. This is currently model metadata and dispatch
   policy, not proof that each external provider can perform a full agentic loop
   in this repo.
3. **Service control plane**: ADR-139, ADR-161, ADR-162, the service-control
   plane plan, and the provider-executor contracts define a future `cosd`
   boundary where tasks are queued, leased, executed by adapters, redacted, and
   returned as propose-only artifacts. Kimi, MiniMax, and DeepSeek remain lab
   provider placeholders until auth probes and output contracts are proven.

## What was already documented and implemented

| Area | Local artifacts | Status |
|---|---|---|
| Qwen Code structural projection | `docs/adrs/ADR-156-qwen-code-structural-harness-projection.md`, `docs/manual-tests/qwen-code-structural-projection.md`, `scripts/cos_init.py`, `manifests/harness-projection.yaml` | Implemented structural projection, no account-backed runtime smoke. |
| Kimi Code CLI structural projection | `docs/adrs/ADR-157-kimi-code-cli-structural-harness-projection.md`, `docs/manual-tests/kimi-code-cli-structural-projection.md`, `scripts/cos_init.py` | Implemented structural projection, no account-backed runtime smoke. |
| Broad harness landscape | `docs/adrs/ADR-158-ai-agent-harness-landscape-and-proof-backlog.md`, `docs/reports/ai-agent-harness-landscape-2026-05-04.md`, `manifests/ai-agent-harness-landscape.yaml` | Candidate backlog and proof-level discipline. |
| AGENTS.md and rules/MCP batches | ADR-159, ADR-160, manual tests, ACC contract tests | Structural support for multiple IDE/CLI surfaces. |
| Multi-provider runtime posture | `docs/adrs/ADR-139-account-agnostic-multi-provider-runtime.md`, `manifests/provider-executor-contracts.yaml` | Credential and billing policy implemented as contracts. |
| Remote/headless boundary | `docs/adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md`, `docs/reports/remote-control-plane-alternatives-2026-05-05.md` | Remote ingress separated from provider execution. |
| Headless worker proof | `docs/manual-tests/headless-docker-service-runtime.md`, `scripts/cos-headless-service-drill`, `tests/integration/test_headless_service_drill.py` | Local no-model queue/worker proof; provider-backed smoke still open. |
| Model routing code | `lib/model_catalog.py`, `lib/model_router.py`, `lib/model_recommender.py`, `lib/openai_compatible_agent_loop.py`, `lib/qwen_agent_loop.py` | Local selection/loop code exists; catalog prices/capabilities need current re-verification before product claims. |

## Ecosystem findings from the web pass

### 1. The ecosystem is converging on adapters, not hard rewrites

OpenClaw, OpenCode, AgentAPI, Pal MCP, oh-my-claude, CliRelay, Cligate,
OpenClaude, and multiple newer routers all separate the user-facing coding tool
from provider selection. The most common implementation shapes are:

- **protocol proxy**: translate Claude/OpenAI/Codex/Gemini protocols and route
  to another provider;
- **MCP coworker**: keep the main tool, but launch external providers or CLIs as
  coworker agents;
- **headless server**: expose an HTTP or management API around coding-agent
  sessions;
- **project-local structural projection**: write rules, instructions, MCP config,
  and settings into the target harness without owning its auth.

This validates COS's existing separation of harness projection, provider
executor adapters, and remote ingress.

### 2. Qwen and Kimi are real first-class CLI/harness surfaces

Qwen Code has official project settings and MCP configuration docs. Kimi Code
CLI has official command and customization docs, including project-level
`AGENTS.md` and MCP config file flags. COS correctly promoted Qwen and Kimi to
structural harnesses rather than treating them only as raw models.

The open work is runtime proof: install/authenticate the CLIs in a temporary
repo and record a redacted smoke without claiming native lifecycle parity.

For Qwen specifically, "runtime proof" means more than the existing structural
projection and more than `offline_dispatch_smoke` metrics. The missing proof
ladder is:

- `cos-auth-probe --provider qwen --mode api-key --json` for the
  `ALIBABA_QWEN_API_KEY` direct API path;
- a separate Qwen Code CLI/account probe if the CLI is the runtime being tested;
- a temp-repo smoke that writes redacted artifacts;
- a real `qwen_agent_loop` tool smoke that exercises `read_file`, `edit_file`,
  and harmless `run_bash`;
- `.cognitive-os/metrics/llm-dispatch.jsonl` evidence with `provider_used=qwen`
  or `provider_used=qwen-code`, not `offline_dispatch_smoke`; and
- an explicit report field distinguishing Qwen API-key dispatch from Qwen Code
  CLI account/session dispatch.

### 3. DeepSeek and MiniMax are stronger today as providers than as COS harnesses

DeepSeek official docs focus on integrating the API with existing AI tools and
OpenAI-compatible behaviors such as function calling. MiniMax docs and repo
material are stronger for model/provider integration, including Anthropic- and
OpenAI-compatible endpoints and specific coding-tool recipes. They are relevant
for `proxy-gateway` or provider adapters, but they should stay lab until COS has
provider-specific auth probes and artifact redaction drills.

### 4. OpenClaw is comparable prior art, but Lucy is not the whole answer

The Lucy repo linked by the user is a bot configuration and skills repository
for OpenClaw. It is useful evidence that OpenClaw ecosystems package bot
behavior as repo artifacts, but it is not a replacement for COS's portability
work. COS already has a different product boundary: governable agentic
primitives, proof levels, credential-safe adapters, and propose-only service
execution.

### 5. The strongest near-term implementation path is not another proxy first

The web pass found many proxy/router projects, but the prior local
`claude-code-router` evaluation already warned against adopting a large external
proxy as the core sub-agent routing layer. The safer COS path remains:

1. keep structural harness projection;
2. add provider adapter contracts and auth probes;
3. add one lab runtime smoke at a time;
4. route by execution profile and evidence, not by brand preference;
5. keep all remote or account-backed execution propose-only until redaction,
   leases, and artifact contracts pass.

## Provider-task delegation matrix

| Task shape | Candidate provider/runtime | Why | COS proof needed before promotion |
|---|---|---|---|
| Cheap formatting, doc trims, catalog updates | local Qwen/Ollama, OpenRouter free, MiniMax cheap tiers | Low consequence, cost-sensitive, easy to verify deterministically. | Fake-provider tests plus one redacted artifact smoke. |
| Long-context repository reading | Gemini, Qwen long-context tiers, Kimi | Strong context windows and ecosystem docs. | CLI/API auth probe, context-size smoke, truncation evidence. |
| Coding implementation | Codex, OpenCode providers, Qwen Coder, Kimi coding models, MiniMax M-series | Coding-tool support and provider recipes exist. | Temp repo edit smoke with patch bundle and tests. |
| Complex debugging/root-cause | Claude/Codex/Gemini/DeepSeek reasoner or multi-model reviewer | Higher reasoning need and benefit from independent opinions. | Multi-output comparison harness and failure taxonomy. |
| Independent reviewer/adversarial pass | DeepSeek reasoner, Gemini, Qwen/Kimi second opinion | Cheap diversity can catch first-model blind spots. | Deterministic reviewer prompt, structured verdict schema, false-positive sampling. |
| Remote/headless execution | OpenCode server, official Codex/Claude CLI, future Kimi CLI adapter | Existing service-control-plane direction. | `auth_probe`, no credential scraping, queue/lease/artifact proof. |

## Recommended continuation

1. **Create a provider proof queue** for `qwen-api-runtime`, `qwen-code-runtime`,
   `kimi-code-runtime`, `minimax-provider`, `deepseek-provider`, and
   `opencode-server` with explicit auth modes and expected artifacts.
2. **Add `cos-auth-probe` coverage** for Qwen API-key dispatch, Qwen Code CLI
   account/session dispatch, Kimi, MiniMax, DeepSeek, and OpenCode server without
   reading vendor credential stores.
3. **Run one temp-repo smoke per provider** only when credentials/CLIs are
   available, with stdout/stderr redaction, propose-only patch bundles, and a
   metric row that names the real provider rather than `offline_dispatch_smoke`.
4. **Add a real Qwen loop tool smoke** that proves `read_file`, `edit_file`, and
   harmless `run_bash` through `qwen_agent_loop` in a disposable workspace.
5. **Refresh `lib/model_catalog.py`** because its pricing and model names are
   dated and should not drive current cost claims without re-verification.
6. **Keep Lucy/OpenClaw as comparison input**, not a dependency. If OpenClaw
   interop is useful, model it as a harness/executor adapter with the same proof
   gates as OpenCode.

## Sources visited

The following 51 pages were fetched or opened during the 2026-05-05 pass. One
Kimi legacy URL returned 404; the canonical Kimi docs were also fetched and used.

| # | Source | Relevance |
|---:|---|---|
| 1 | [CamiloAndresGTRUniandes/lucy-ai](https://github.com/CamiloAndresGTRUniandes/lucy-ai) | User-linked OpenClaw bot config/skills repo. |
| 2 | [OpenClaw GitHub](https://github.com/openclaw/openclaw) | Comparable OpenClaw runtime and gateway. |
| 3 | [OpenClaw docs](https://docs.openclaw.ai/) | Official OpenClaw concepts. |
| 4 | [OpenClaw architecture](https://openclaw-ai.net/en/architecture) | OpenClaw gateway/runtime architecture. |
| 5 | [oh-my-claude](https://github.com/lgcyaxi/oh-my-claude) | Claude Code multi-provider MCP/background agents. |
| 6 | [claude-code-router](https://github.com/musistudio/claude-code-router) | Prior proxy/router comparison. |
| 7 | [Pal MCP server](https://github.com/BeehiveInnovations/pal-mcp-server) | CLI-to-CLI subagent bridge across Claude/Codex/Gemini/Qwen. |
| 8 | [CliRelay](https://github.com/kittors/CliRelay) | Unified proxy for AI CLIs and compatible APIs. |
| 9 | [Cligate](https://github.com/codeking-ai/cligate) | Multi-protocol proxy for Claude Code, Codex, Gemini CLI, OpenClaw. |
| 10 | [OpenClaudia](https://github.com/dollspace-gay/OpenClaudia/) | Universal multi-provider coding harness. |
| 11 | [Rover](https://github.com/endorhq/rover) | Manager for Claude, Codex, Gemini, Qwen agents. |
| 12 | [OpenClaude](https://github.com/Gitlawb/openclaude) | Multi-provider Claude-like coding agent and agent routing. |
| 13 | [Vercel coding-agent-template](https://github.com/vercel-labs/coding-agent-template) | Multi-agent sandbox template. |
| 14 | [coder/agentapi](https://github.com/coder/agentapi) | HTTP API for multiple coding agents. |
| 15 | [Untether](https://github.com/littlebearapps/untether) | Telegram bridge for coding agents. |
| 16 | [OpenCode GitHub](https://github.com/anomalyco/opencode) | Open-source coding agent. |
| 17 | [OpenCode product page](https://dev.opencode.ai/) | Current OpenCode model/provider positioning. |
| 18 | [OpenCode config docs](https://opencode.ai/docs/config/) | Config surface. |
| 19 | [OpenCode providers docs](https://opencode.ai/docs/providers/) | Provider abstraction. |
| 20 | [OpenCode server docs](https://opencode.ai/docs/server/) | Headless/server candidate. |
| 21 | [Qwen Code settings](https://qwenlm.github.io/qwen-code-docs/en/users/configuration/settings/) | Project settings proof. |
| 22 | [Qwen Code MCP](https://qwenlm.github.io/qwen-code-docs/en/users/features/mcp/) | MCP proof. |
| 23 | [Qwen Code GitHub](https://github.com/QwenLM/qwen-code) | Qwen coding agent source. |
| 24 | [Kimi legacy CLI URL](https://www.kimi.com/code/docs/en/kimi-cli.html) | Returned 404; replaced by canonical docs. |
| 25 | [Kimi command docs](https://www.kimi.com/code/docs/en/kimi-code-cli/reference/kimi-command.html) | CLI flags and MCP config proof. |
| 26 | [Kimi customization help](https://www.kimi.com/help/kimi-code/cli-customization) | Project customization proof. |
| 27 | [Moonshot Kimi CLI mirror](https://moonshotai.github.io/kimi-cli/en/reference/kimi-command.html) | Alternate CLI command reference. |
| 28 | [DeepSeek coding-agent integrations](https://api-docs.deepseek.com/guides/coding_agents) | Provider integration proof. |
| 29 | [DeepSeek pricing docs](https://api-docs.deepseek.com/quick_start/pricing) | Cost/provider currentness input. |
| 30 | [DeepSeek API upgrade](https://api-docs.deepseek.com/news/news0725/) | Function-calling/OpenAI-compatible input. |
| 31 | [DeepSeek Coder GitHub](https://github.com/deepseek-ai/DeepSeek-Coder) | Model/code prior art. |
| 32 | [MiniMax AI coding tools](https://platform.minimax.io/docs/guides/text-ai-coding-tools) | Coding-tool recipes. |
| 33 | [MiniMax other tools](https://platform.minimax.io/docs/token-plan/other-tools) | Anthropic/OpenAI-compatible setup. |
| 34 | [MiniMax-M2 GitHub](https://github.com/MiniMax-AI/MiniMax-M2) | Agentic/coding model and tool calling. |
| 35 | [MiniMax CLI docs](https://platform.minimax.io/docs/token-plan/minimax-cli) | Provider CLI surface. |
| 36 | [MiniMax Mini-Agent docs](https://platform.minimax.io/docs/coding-plan/mini-agent) | Hosted/provider-agent surface. |
| 37 | [Cline model selection](https://docs.cline.bot/core-features/model-selection-guide) | Ecosystem provider recommendations. |
| 38 | [Kilo DeepSeek V4](https://kilo.ai/landing/deepseek-v4) | DeepSeek as coding-provider integration. |
| 39 | [Kilo model leaderboard](https://kilo.ai/models) | Provider/model comparison input. |
| 40 | [Factory docs](https://docs.factory.ai/) | Droid and provider-key positioning. |
| 41 | [AgentPipe](https://agentpipe.ai/) | Multi-agent CLI orchestration landscape. |
| 42 | [Crewswarm](https://crewswarm.ai/) | Multi-agent platform landscape. |
| 43 | [AnyModel](https://anymodel.dev/) | Any-model proxy landscape. |
| 44 | [ClawRouter](https://clawrouter.org/) | Intelligent model selection landscape. |
| 45 | [altcode](https://altcode.io/) | Multi-provider coding CLI landscape. |
| 46 | [go-llm-proxy](https://go-llm-proxy.com/) | Protocol translation/proxy landscape. |
| 47 | [OpenDray](https://opendray.dev/) | Remote control of coding agents. |
| 48 | [BitRouter](https://bitrouter.ai/) | LLM agent router landscape. |
| 49 | [Aivo](https://getaivo.dev/) | Any-model bridge for coding agents. |
| 50 | [Task-stratified coding-agent PR study](https://arxiv.org/abs/2602.08915) | Evidence that agents vary by task type. |
| 51 | [Claude Code design-space paper](https://arxiv.org/abs/2604.14228) | Agent-system design-space context. |
