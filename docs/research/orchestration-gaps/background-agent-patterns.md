# Background Agent Patterns: Detached Execution in Modern AI Tooling

**Research Date:** 2026-05-06
**Author:** Cognitive OS Research (Claude Agent, Sonnet 4.6)
**Status:** Complete — no code modifications
**Word Count:** ~4 800

---

## 1. Executive Summary

Every major AI coding platform has shipped or is shipping a "background agent" primitive: a task you hand off, walk away from, and receive results from later — without holding a terminal session open. Cursor Background Agents run in dedicated Ubuntu VMs on AWS. Devin spawns per-task cloud machines and hands off from terminal to cloud. Replit Agent 3/4 parallelises tasks inside its managed execution environment for up to 200 minutes autonomously. OpenAI Codex ships a background-mode API wrapper with webhook completion. Primitives like E2B, Daytona, and Modal provide the infrastructure layer others build on.

Cognitive OS has none of this. The current `run_in_background: true` Bash flag and the Agent `Task` tool are the closest approximations, but they are both process-synchronous from the orchestrator's perspective: the orchestrator blocks, or the shell subprocess escapes supervision. There is no persisted agent identity, no lifecycle state machine, no cancellation API, and no completion notification beyond the calling process.

The verdict is: **ship a detached agent capability**. A local-first design based on tmux sessions as the process runtime, launchd/systemd as the supervisor, a flat JSONL state file as the lifecycle log, and a poll-plus-inotify completion-detection mechanism is defensible, incrementally deliverable, and avoids the cloud-VM cost and privacy overhead that competitors carry.

---

## 2. Per-System Deep Dives

### 2.1 Cursor Background Agents

**Infrastructure.** Each background agent runs in a fresh, isolated Ubuntu VM on AWS. As of February 2026, each VM ships with a full desktop environment, a browser, and computer-use capabilities so agents can verify UI state visually. The container is configured from a `.cursor/Dockerfile` the project checks in; Cursor clones the repository into the VM's filesystem at startup. There is no shared state between concurrent agent runs.

**Lifecycle.** Trigger is `Ctrl+E` in the Cursor UI. The agent clones the repo, works on a new branch, and opens a pull request when it determines the task is complete. The PR creation event is what signals completion back to the user — there is no separate completion webhook; the notification is the PR appearing in the user's GitHub feed and a Cursor UI notification. Cancellation is available from the Cursor UI panel at any time, though partial-state branches are not automatically cleaned up.

**Scheduling and parallelism.** Multiple agents can run simultaneously; no documented per-account concurrency cap was found. Tasks are independent — each gets its own VM, not shared resources.

**Cost model.** Agents run under Cursor MAX mode with a 20% surcharge on credit costs. Practical costs: $4–5 per simple task, $60–100/month for regular users, $200+/month for power users. Cursor bears the AWS compute cost and passes it through credits.

**Security boundary.** Privacy Mode must be disabled because code is sent to remote VMs. The VM has internet access by default. CVE-2026-22708 demonstrated that shell built-ins (`export`) could bypass terminal allowlists, enabling indirect prompt injection. CVE-2025-59944 showed case-insensitive filesystem attacks on macOS/Windows could overwrite MCP config files. The attack surface is materially higher than local-only execution.

**Debugging overnight failures.** There is no explicit "agent died" log surface beyond a failed/incomplete PR or a stalled UI indicator. The product documentation acknowledges "agents hanging, failing to complete, or producing inconsistent results" as known stability issues.

**Key gotcha.** "Premature completion" — the agent opens a PR that claims done but has partial implementation — is the dominant failure mode. There is currently no programmatic API to trigger agents from external systems (CI, Jira, Slack).

---

### 2.2 Devin (Cognition)

**Infrastructure.** Devin 2.0 operates a per-task cloud VM: each active session gets its own isolated virtual machine with full internet access, a browser, and a shell. The Devin for Terminal feature (announced late 2025) allows the developer to prototype locally, then hand the session to a cloud agent with "its own computer." The handoff is explicitly described as a session state transfer, not a re-run.

**Lifecycle.** Devin is explicitly positioned as an asynchronous delegation tool: you assign a task, Devin works independently, and you review results when notified. The architecture supports multi-agent dispatch — one Devin instance can spawn sub-tasks to others for concurrent execution, making it the only shipping system in this survey with first-class multi-agent tree orchestration.

**Async handoff mechanism.** The terminal client is built with a custom Rust rendering library. The handoff protocol promotes a local working session to a cloud environment; the exact transport (checkpoint snapshot, event log replay, or session serialisation) is not publicly documented. The terminal client reconnects to the remote VM's session state.

**Cost model.** Devin charges per agent-hour or per task depending on tier. Cloud compute is Cognition's infrastructure cost; users pay SaaS subscription or credits.

**Security.** Per-VM isolation means cross-project contamination is contained by the VM boundary. Long-lived sessions hold whatever API keys were injected at session start — Devin's documentation does not describe automatic key rotation within a session.

**Debugging.** Devin surfaces a session timeline and a replay log so users can step through what the agent did. This is the strongest post-hoc debugging UX in the survey.

---

### 2.3 Replit Agent 3 / Agent 4

**Infrastructure.** Replit Agents run inside Replit's managed execution environment (Nix-based containers). Agent 3 introduced up to 200 minutes of autonomous runtime. Agent 4 (2026) splits requests into discrete parallel tasks that run concurrently in the background; users track status, review results, and approve before merging.

**Lifecycle.** Agent 3 implements a self-test loop: generate code → execute → identify errors → fix → re-run until tests pass. This is the only surveyed system where the completion condition is explicitly a test pass/fail gate rather than a timer or a "looks done" model judgment. Agent 4 uses a fork-and-merge approach: tasks are split, executed in parallel forks, then merged into the main project.

**Scheduled automations.** Agent 3/4 can build agents that themselves have scheduled tasks — cron-style triggers for daily emails, weekly reports, Slack/Telegram integrations. This is the most complete scheduled-execution story in the survey: the agent creates the automation, and the automation runs on the platform's cron infrastructure.

**Cost model.** Replit provides Cycles (credits). Agent runtime costs per minute. Agent 3 benchmarked at one-tenth the cost of earlier computer-use models.

**Debugging.** Replit's always-on console and real-time execution logs provide visibility. Because everything runs in a Replit Repl (a persistent online container), the "morning after" debugging experience is straightforward: open the Repl, read the output log.

---

### 2.4 OpenAI Codex (CLI + Cloud)

**CLI.** The Codex CLI (`openai/codex`, built in Rust) is a local agent runner. It is not itself detached — it runs in your terminal and blocks. The Background Mode discussion thread in the OpenAI forum confirmed that "background mode" as a CLI feature may have been a user misreading; what exists is background mode in the **Responses API** (not the CLI).

**Responses API background mode.** The Responses API supports long-running responses without holding a client connection open. The pattern: submit a task, receive a task ID, webhook fires on completion. This is the canonical REST-async pattern: submit → poll or wait for webhook → retrieve result. Batch completion and background completion are the two supported async primitives.

**Codex App (cloud).** OpenAI's cloud Codex interface allows launching tasks and monitoring progress in real time or letting them run in the background. External agent session import and background imports were added in 2025.

**Lifecycle.** Completion is detected server-side; clients receive webhook events or poll `FunctionCall.get()`. OpenAI stores results for up to 7 days post-completion.

**Cost model.** API token pricing (input/output tokens). No separate compute charge; the model inference is the cost.

---

### 2.5 E2B (Sandbox Primitive)

**Architecture.** E2B provides fast, secure Linux VMs created on demand — each sandbox starts in under 90ms and runs any agent-generated code in isolation. The core abstraction is: Sandbox (a Linux VM) + Template (what the VM starts with). The agent runs on your server; when it needs to execute code, it calls E2B's API. The sandbox is just another tool in the agent's toolbox.

**Two patterns (per LangChain blog).** (1) Sandbox-as-Tool: agent runs locally, calls sandbox remotely for execution, API keys stay outside sandbox. (2) Agent-in-Sandbox: the entire agent runs inside the sandbox for maximum isolation. The first is more common for coding agents; the second for security-critical use cases.

**Lifecycle.** Sandboxes support pause/resume for stateful operations across sessions. SDK methods: `sandbox.create()`, `sandbox.pause()`, `sandbox.resume()`, `sandbox.kill()`. Completion is detected in-process by the caller polling or awaiting the execution result.

**Cost model.** E2B charges per sandbox-second. Sandbox runtime duration grew more than 10x from 2024 to 2025 as agents ran longer tasks.

**Security.** Each sandbox has its own Linux namespaces (process, network, filesystem, IPC). No cross-sandbox communication by default. Sensitive keys stay outside the sandbox when using the Sandbox-as-Tool pattern.

---

### 2.6 Daytona (Sandbox Primitive)

**Architecture.** Daytona is a three-plane system: Interface Plane (SDKs, CLI, MCP, SSH), Control Plane (NestJS API, Redis, PostgreSQL, Auth0, snapshot manager, sandbox manager), and Compute Plane (runners, daemon, snapshot store, volumes). Runners are compute nodes that poll the control plane for jobs.

**Sandbox execution model.** Each sandbox is a full composable computer with its own Linux namespaces. The sandbox daemon inside each sandbox exposes a Toolbox API covering filesystem/Git operations, process execution, computer use, log streaming, and terminal sessions. External access routes through the proxy via `{port}-{sandboxId}.{proxy-domain}`.

**Key differentiation.** Daytona supports stateful environment snapshots — a sandbox can be snapped, stored to S3-compatible storage, and resumed exactly where it left off. This enables persistent agent operations across sessions, which E2B's pause/resume also supports but Daytona makes part of its core RL-agent use case story.

**Deployment.** Fully hosted, open-source self-hosted, or hybrid. Startup time under 90ms.

**Security.** Kernel-level isolation via Linux namespaces. No documented automatic key rotation; that is the operator's responsibility.

---

### 2.7 Modal (Serverless Compute Primitive)

**Architecture.** Modal is a Python-native serverless compute platform. The key primitives for background agents are `.spawn()` (fire-and-forget, returns a `FunctionCall` ID immediately), `.spawn_map()` (batch spawn), and `FunctionCall.get()` (poll for result, blocking or with timeout). With the `--detach` flag, an App continues running even after the CLI exits.

**Async execution.** The spawn-and-poll model: submit returns a call ID; results are retrievable via `FunctionCall.get()` for up to 7 days post-completion. HTTP status 202 = pending, 404 = expired. There is no native webhook push; polling is the standard pattern, though a thin webhook wrapper can be built with a Modal web endpoint.

**Cost model.** Per-second compute pricing based on container size. Containers start in milliseconds and scale to zero when idle. Users pay only for actual runtime.

**Security.** Function execution is container-isolated. Secrets are injected at invocation time via Modal's secrets system, not baked into images.

---

### 2.8 Anthropic Agent SDK / Managed Agents

**Agent SDK.** The Claude Agent SDK (formerly Claude Code SDK, renamed 2025) exposes the same agent loop that powers Claude Code. It is a library — the agent loop runs in your process. It supports subagent orchestration (spawn specialised agents via the `Agent` tool), lifecycle hooks (`PreToolUse`, `PostToolUse`, `Stop`, `SessionStart`, `SessionEnd`), session persistence via JSONL on the local filesystem, and MCP server integration.

The Task tool executes sub-agents **synchronously** — it blocks the orchestrator until all spawned agents complete. There is a GitHub issue (anthropics/claude-code #9905) requesting `Task` async support with a `run_in_background`-equivalent for agent tasks. This feature is not yet shipped.

**Managed Agents.** Anthropic's Managed Agents is a hosted REST API where Anthropic runs the agent and the sandbox. Key properties: agents work on a managed sandbox per session, session state is an Anthropic-hosted event log, completions are streamed via SSE, and long-running/asynchronous sessions are explicitly listed as the primary use case (vs. Agent SDK's local prototyping use case). This is Anthropic's answer to the detached agent problem — but it requires using Anthropic's infrastructure, not local-first.

**Headless CLI.** `claude -p` (formerly "headless mode") runs Claude non-interactively. With `--output-format stream-json` it emits newline-delimited JSON events. `--bare` skips hooks, MCP discovery, and CLAUDE.md loading for reproducible CI runs. Completion is detected by process exit (exit code 0 = success, non-zero = failure). Session IDs can be captured and used with `--resume` to continue conversations. This is effectively "headless agent" in the OpenCode sense: no TTY, log-only, exit-code-driven.

---

### 2.9 Headless Agent Pattern (OpenCode / Claude Code SDK)

The headless pattern — `agent -p "task" > output.log 2>&1 &` — is the simplest form of background execution. Key properties across implementations:

- **No TTY.** The agent writes to stdout/stderr only. Structured output (`--output-format json`) turns logs into machine-readable events.
- **Exit-code as completion signal.** The process exiting with code 0 means success; the caller monitors via `wait`, `waitpid`, or a file sentinel.
- **Session state as file.** Claude Code stores session state in JSONL files in `~/.claude/`. Session IDs are resumable across processes.
- **Observability gap.** Without a wrapper like `claude_telemetry`, headless runs produce no cost metrics, no distributed traces, and no structured error attribution. The agent is a black box until it exits.
- **Supervisor pattern.** OpenTelemetry wrappers (e.g., `claude_telemetry`) address this by acting as a thin shim: intercept the Claude Code process, emit OTEL spans, forward all flags unchanged. This is the best available production observability pattern for headless Claude Code today.

---

## 3. Cross-Cutting Analysis

### 3.1 Lifecycle: How Is "Agent Finished" Detected?

| Pattern | Mechanism | Latency | Reliability |
|---|---|---|---|
| PR creation (Cursor) | GitHub event / UI poll | Seconds | Dependent on git push success |
| Test pass gate (Replit) | In-process assertion | Immediate | High — code must actually pass |
| Process exit code (Claude headless) | POSIX `wait()` | Immediate | High — OS-level |
| Webhook + result polling (Codex, Modal) | HTTP callback + GET | Seconds | Medium — needs stable endpoint |
| tmux pane hash change (community tools) | Periodic capture-pane hash | 10ms–500ms | Medium — false positives on spinner output |
| File sentinel | `inotifywait` / `kqueue` | Sub-ms | High — filesystem events are reliable |

The most robust local-first pattern is **process exit + file sentinel**: the agent writes a `done.json` file when it finishes (success or failure), and the host watches via inotify/kqueue. This avoids polling and works across process boundaries.

### 3.2 Cancellation: How to Kill a Runaway Agent

**Cloud systems.** Cursor provides a UI cancel button; Devin provides session termination; Managed Agents supports DELETE on the session resource. All of these ultimately SIGTERM the container or VM.

**Local-first.** The cleanest approach is a named pipe or PID file. The agent writes its PID to `~/.cognitive-os/agents/{id}/pid`. The orchestrator sends `SIGTERM` to that PID. For tmux-based runners, `tmux kill-session -t {id}` is reliable. The key invariant: **the agent must handle SIGTERM** and write a partial-result sentinel before exiting, otherwise cancellation leaves no trace.

**Runaway detection.** Modal supports configurable timeouts and max retries at the function level. The local equivalent is a watchdog process that reads the agent's last-heartbeat timestamp from a shared file and kills the PID if it has not updated within a threshold.

### 3.3 Debugging: What Do You See in the Morning?

**Cloud (Devin, best case).** A full replay timeline of every action, tool call, file change, and LLM turn. You can step through what happened and see where it went wrong.

**Cloud (Cursor, worst case).** A failed or incomplete PR on a branch. No structured error log. The user must read the diff and infer what the agent attempted.

**Local headless (current COS state).** A JSONL file in `~/.claude/` containing the raw conversation turns. No cost breakdown, no structured error events, no operation timeline. To recover context you must read the JSONL manually or run `claude --resume {session_id}`.

**Local with OTEL wrapper.** Structured spans in Logfire/Honeycomb/Datadog. Cost per turn. Tool call sequence with timing. This is the feasible upgrade path for COS.

**tmux-based (community pattern).** Attach to the session and read the terminal buffer. The most intuitive debugging experience for a human operator, but no programmatic introspection.

### 3.4 Cost: Who Pays Compute?

| System | Compute model | Transparency |
|---|---|---|
| Cursor | Credits (20% MAX surcharge) on AWS VMs | Opaque per-task |
| Devin | SaaS subscription / credits | Opaque |
| Replit | Cycles per minute of agent runtime | Reasonably transparent |
| Modal | Per-second container pricing | Highly transparent |
| E2B | Per sandbox-second | Highly transparent |
| Codex API | Token pricing | Per-call metadata |
| Claude Managed Agents | Token pricing (hosted) | Per-session via API |
| Local (COS) | Your hardware + LLM API tokens | `--output-format json` includes `total_cost_usd` |

For local-first COS the cost model is simple: hardware is yours (zero marginal cost for CPU), LLM API tokens are the only variable cost. The `--output-format json` flag already emits `total_cost_usd` per invocation — this should be captured and logged to a cost ledger in every background agent run.

### 3.5 Security: Long-Lived Auth Tokens in Detached Agents

This is the most underexplored problem in the space. Key findings:

**The core problem.** Detached agents hold API tokens for their entire runtime. Major SDKs require token injection at client initialisation and cache them in memory for the session. If an external rotation event (e.g., vault rotates the GitHub token) happens mid-task, the agent continues using the stale token until a 401 causes failure — and the failure is often silent rather than clean.

**Recommended patterns (from GitGuardian research):**
1. **JIT provisioning.** Request short-lived tokens at task start, scoped to only the services needed. The token TTL matches the expected task duration plus a safety margin. The token self-destructs after use. This eliminates the rotation problem entirely for short tasks.
2. **Dual refresh.** Proactive refresh at 70–80% of token lifetime (prevents expiry), combined with reactive refresh on 401 responses (catches anything that slips through). Essential for tasks longer than token TTL.
3. **Tool-runtime isolation.** Tokens live outside the agent process; each tool call requests a fresh short-lived token from an identity layer. The agent never holds a persistent token — it holds a capability reference.
4. **Per-agent identity.** Each background agent should have a unique identity (not shared with other agents), enabling attribution and fast revocation.

**Minimum viable for local-first COS.** At a minimum: store tokens in environment variables scoped to the agent subprocess (not inherited from the parent environment), use `ANTHROPIC_API_KEY` only (not repo tokens) for the LLM calls, and document the expected token TTL alongside the agent task definition. Do not hard-code or log tokens anywhere in the agent's output path.

---

## 4. Comparative Table

| Dimension | Cursor | Devin | Replit | Codex | E2B | Daytona | Modal | Claude Managed | COS (current) |
|---|---|---|---|---|---|---|---|---|---|
| **Isolation unit** | Ubuntu VM | VM | Container | Container (API) | Linux VM | Linux namespace | Container | Managed sandbox | Process (none) |
| **Startup time** | Seconds | Seconds | Seconds | N/A | <90ms | <90ms | Milliseconds | Seconds | Immediate |
| **Completion signal** | PR + UI notify | Session timeline | Test gate / UI | Webhook / poll | In-process return | In-process return | `FunctionCall.get()` | SSE stream | Process exit |
| **Cancellation** | UI button | Session terminate | UI | HTTP DELETE | SDK `kill()` | SDK kill | `.cancel()` | HTTP DELETE | SIGTERM (manual) |
| **Scheduling** | Manual trigger | Manual + multi-agent | Cron automations | Manual / API | Manual | Manual | `.spawn()` + cron | API | None |
| **Parallel agents** | Yes (unlimited?) | Yes | Yes (fork) | API batch | Yes | Yes | Yes (spawn_map) | API | Ad hoc |
| **Debug surface** | Partial PR diff | Full replay timeline | Console logs | Event log | In-process | Log streaming | Function result store | Session event log | JSONL (raw) |
| **Cost transparency** | Opaque credits | Opaque | Cycles/min | Token metadata | Per-sandbox-sec | Per-sandbox-sec | Per-container-sec | Token metadata | `total_cost_usd` |
| **Local-first possible** | No | No | No | CLI yes, cloud no | API dependency | Self-host option | No | No | Native |
| **Privacy** | Privacy Mode must off | Cloud only | Cloud only | Cloud only | Cloud only | Self-host option | Cloud only | Cloud only | Full local |

---

## 5. Verdict for COS: Ship a Detached Agent Capability

### 5.1 Should COS Ship This?

**Yes.** The gap is real, the patterns are well-understood, and local-first gives COS a structural advantage over all cloud-only competitors. A developer who runs COS locally does not want to send their code to AWS to run a background task. The tmux + launchd/systemd architecture lets agents run detached without leaving the machine.

The risk of not shipping: orchestrators currently block on long tasks, or use `run_in_background: true` on Bash commands with no lifecycle management. As tasks grow longer (refactor a module overnight, run a full test suite), the absence of proper detached execution becomes a capability gap.

### 5.2 Local-First Design

**Runtime layer: tmux.**

tmux is the right choice for the process runtime because:
- Session persistence: agents keep running when the terminal closes
- Real-time attach: `tmux attach -t cos-agent-{id}` gives instant human visibility
- Output capture: `tmux capture-pane -t {id} -p` enables programmatic monitoring
- Zero overhead: no daemon, no port, no Docker
- Limitation: no filesystem isolation or resource limits — these require supplementary controls (allowlisted commands, restricted shell, `ulimit` in the launch script)

**Supervisor layer: launchd (macOS) / systemd user units (Linux).**

Neither launchd nor systemd should be the _process supervisor_ for individual agent tasks — they are too heavyweight for ephemeral tasks. Instead, use them for the **agent daemon**: a lightweight COS background service (`cos-agent-daemon`) that:
- Reads a task queue from `~/.cognitive-os/agent-queue.jsonl`
- Spawns tmux sessions for each task
- Monitors heartbeat files
- Writes completions to `~/.cognitive-os/agent-results.jsonl`
- Sends a desktop notification on completion (macOS: `osascript`, Linux: `notify-send`)

launchd plist (`~/Library/LaunchAgents/com.cognitivos.agent-daemon.plist`):
```xml
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
<key>ProgramArguments</key>
<array><string>python3</string><string>/path/to/cos-agent-daemon.py</string></array>
<key>StandardOutPath</key><string>~/.cognitive-os/logs/daemon.log</string>
<key>StandardErrorPath</key><string>~/.cognitive-os/logs/daemon-error.log</string>
```

systemd user unit (`~/.config/systemd/user/cos-agent-daemon.service`):
```ini
[Unit]
Description=COS Background Agent Daemon
[Service]
ExecStart=python3 /path/to/cos-agent-daemon.py
Restart=on-failure
StandardOutput=append:%h/.cognitive-os/logs/daemon.log
[Install]
WantedBy=default.target
```

**State machine for each agent task:**

```
QUEUED → STARTING → RUNNING → (COMPLETED | FAILED | CANCELLED)
                    ↕ heartbeat writes every 30s
                    ↕ watchdog kills if heartbeat >5min stale
```

State is written to `~/.cognitive-os/agents/{task-id}/state.json`. This file is the single source of truth for task lifecycle.

**Completion detection: file sentinel + inotify/kqueue.**

The agent script writes `~/.cognitive-os/agents/{task-id}/done.json` as its last act (success or failure). The daemon watches for this file using `inotifywait` (Linux) or `FSEvents` / `kqueue` (macOS). This is sub-millisecond latency and requires no polling.

**Notification on completion:**

macOS: `osascript -e 'display notification "Agent {id} finished: {summary}" with title "COS Agent"'`

Linux: `notify-send "COS Agent" "Task {id} finished: {summary}"`

Both can be extended to send to a Slack webhook or write to a status file that the COS dashboard reads.

**Security for local-first.**

- Agent subprocesses inherit only the environment variables explicitly passed in the launch command — not the parent shell's full environment.
- `ANTHROPIC_API_KEY` is passed; repository-specific tokens are not passed by default.
- The agent's working directory is a temporary copy (or a git worktree) of the project — not the live workspace — so destructive changes are isolated.
- File writes are confined to the worktree and `~/.cognitive-os/agents/{id}/` by an allowlist in the launch script.
- A max-runtime `ulimit -t` or SIGKILL-after-timeout watchdog caps runaway agents.

**What this does NOT cover (scope for v2):**

- Filesystem namespace isolation (would require Docker or nsjail)
- Multi-machine distribution
- Cross-session agent-to-agent communication (Valkey queue is the COS ADR path)
- GUI / web dashboard for monitoring running agents

---

## 6. Sources

1. Cursor Background Agents official docs — https://cursor.com/docs (background-agent section; 308-redirected from docs.cursor.com)
2. Morph LLM — Cursor Background Agents complete guide — https://www.morphllm.com/cursor-background-agents
3. Agent Safehouse — Cursor Agent security analysis (CVE-2026-22708, CVE-2025-59944) — https://agent-safehouse.dev/docs/agent-investigations/cursor-agent
4. Digital Applied — Cursor 2.0 Agent-First Architecture — https://www.digitalapplied.com/blog/cursor-2-0-agent-first-architecture-guide
5. Cognition AI — Devin for Terminal blog — https://cognition.ai/blog/devin-for-terminal
6. Medium (Takafumi Endo) — Agent-Native Development: Devin 2.0 Technical Design — https://medium.com/@takafumi.endo/agent-native-development-a-deep-dive-into-devin-2-0s-technical-design-3451587d23c0
7. InfoQ — Replit Agent 3 extended autonomous coding — https://www.infoq.com/news/2025/09/replit-agent-3/
8. Replit — Agent 4 product page — https://replit.com/agent4
9. OpenAI — Introducing Codex — https://openai.com/index/introducing-codex/
10. OpenAI — Codex CLI features — https://developers.openai.com/codex/cli/features
11. OpenAI Community — Codex CLI background mode discussion — https://community.openai.com/t/codex-cli-background-mode/1274043
12. E2B — GitHub repository and documentation — https://github.com/e2b-dev/E2B
13. LangChain Blog — Two patterns by which agents connect sandboxes — https://blog.langchain.com/the-two-patterns-by-which-agents-connect-sandboxes/
14. Daytona — Architecture documentation — https://www.daytona.io/docs/en/architecture/
15. Daytona — Sandbox infrastructure for RL agents — https://www.daytona.io/dotfiles/sandbox-infrastructure-for-reinforcement-learning-agents
16. Modal Labs — Job queue documentation — https://modal.com/docs/guide/job-queue
17. Anthropic — Agent SDK overview — https://code.claude.com/docs/en/agent-sdk/overview
18. Anthropic — Run Claude Code programmatically (headless) — https://code.claude.com/docs/en/headless
19. GitHub — anthropics/claude-code issue #9905 (Task tool async support) — https://github.com/anthropics/claude-code/issues/9905
20. GitGuardian — Short-lived credentials in agentic systems — https://blog.gitguardian.com/short-lived-credentials-in-agentic-systems-a-practical-trade-off-guide/
21. GitGuardian — AI agents authentication — https://blog.gitguardian.com/ai-agents-authentication-how-autonomous-systems-prove-identity/
22. DEV Community (battyterm) — How tmux became the runtime for AI agent teams — https://dev.to/battyterm/how-tmux-became-the-runtime-for-ai-agent-teams-gmi
23. ikangai — tmux as Agent Habitat — https://www.ikangai.com/tmux-as-agent-habitat/
24. GitHub (samleeney) — tmux-agent-status — https://github.com/samleeney/tmux-agent-status
25. TechNickAI — claude_telemetry OTEL wrapper — https://github.com/TechNickAI/claude_telemetry

---

*Uncertainty notes: Devin's internal handoff protocol is not publicly documented; the description here is inferred from product announcements. Anthropic Managed Agents docs returned 404 at time of research — the overview table is based on the Agent SDK overview comparison table which describes Managed Agents as the counterpart. Cursor concurrency limits are undocumented. All cost figures are estimates from community reports and may not reflect current pricing.*
