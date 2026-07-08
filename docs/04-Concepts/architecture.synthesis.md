---
type: concept-synthesis
source: docs/04-Concepts/architecture.md
---

## What it is
Top-level system architecture: primitive inventory (hooks/rules/skills/squads/agents/libs), the MAPE-K autonomous control loop, the issue-to-PR pipeline, and the technology stack.

## Key mechanics
- Core components: Claude Code (interactive) + Singularity Controller (autonomous loop) both feed the Orchestrator, which coordinates Hooks/Rules/Skills; these write to Engram (SQLite) and Metrics (JSONL); ClaudeExecutor (lib/py) drives Issue Pipeline/Webhook Trigger/Batch Runner/Notifications; Agent Bus (`lib/agent_bus.py`, Valkey pub/sub, 5s heartbeat/15s timeout, `AGENT_BUS_ENABLED=true`, file-based fallback under `.cognitive-os/agent-bus/`) + `lib/agent_dashboard.py` terminal dashboard.
- MAPE-K loop: Monitor (`error-learning.sh`, `skill-tracker.sh`, `kpi-trigger.sh`, `doc-sync-detector.sh`) -> Analyze (`error-pattern-detector.sh`, `epic-task-detector.sh`, `singularity.py` classification) -> Plan (`singularity.py` routing, `sdd_resume.py`, `domain_router.py`) -> Execute (`claude_executor.py`, `issue_pipeline.py`, `batch_runner.py`) -> Knowledge (Engram, metrics JSONL, remediation registry).
- Issue-to-PR pipeline (8 steps): webhook trigger (HMAC validated) -> issue pipeline (git worktree isolation) -> SDD pipeline (explore->propose->spec->design->tasks) -> apply (PITER loop) -> verify (adversarial review, retry max 3) -> `gh pr create` -> notification (Telegram/Slack/webhook) -> archive to Engram.
- Primitive counts: 46 registered hooks / 94 scripts (SessionStart 3, PreToolUse 9, PostToolUse 24, Stop 5, Other 5); 16 core always-loaded rules (RULES-COMPACT, adaptive-bypass, acceptance-criteria, agent-quality, trust-score, token-economy, phase-aware-agents, closed-loop-prompts, error-learning, rate-limiting, credential-management, content-policy, result-management, blast-radius, clarification-gate, model-routing) of 150+ total; 72 skills across 12 categories; 4 squads (platform/payments/mobile/infra-team) + organization.yaml; 3 named agents (service-health-checker, stack-validator, test-coverage-enforcer); 79 Python lib modules (key ones: agent_bus, batch_runner, capability_levels, claude_executor, domain_router, impact_analysis, model_router, singularity, etc.); 2 git submodules (hermes-agent, pi-mono) under `.claude/plugins/`.
- Tech stack: Bash hooks (<100ms), Markdown rules/skills, Python 3.9+ libs (stdlib-preferred, FastAPI only for webhook server), Go CLI (cos-test TUI), SQLite/Engram (WAL), JSONL metrics, pytest+testcontainers, promptfoo, GitHub Actions, optional Langfuse/LiteLLM/NeMo Guardrails.
- Multi-tool adapter: Cognitive OS core -> adapters/cc (Claude Code), adapters/oc (OpenCode), adapters/cursor (Aider/Cursor), converging on Python libs (agnostic), MCP (universal), Docker infra (agnostic). Portability table: libs/MCP/Docker = fully portable; hooks = need adapter; rules/skills = partially portable (content universal, invocation/path varies).
- Engram topic hierarchy: `planning/{change}/{proposal,spec,design,tasks,state,verify-report}`, `implementation/{service}/patterns`, `implementation/{change}/apply-progress`, `architecture/{topic}`, `bugfix/{service}/{issue}`, `agent/{agent-name}/sidecar`, `config/{project}/sdd-init`, `sre/{container}/{error-type}`.
- Config: `cognitive-os.yaml` is single source of truth; key sections: project.phase, project.infrastructure, phases.*, environment.tool, resources.budget/compute/tokens, skills.loading, rules.loading, sessions, self_improvement.
- Self-improvement loop: Capture (error-learning.sh) -> Detect (error-pattern-detector.sh, 3+ same error/24h) -> Analyze (`/error-analyzer`) -> Improve (`/self-improve`) -> Validate (`/cognitive-os-test`) -> Apply or revert. Safety guards: max 5 improvements/run, mandatory test gate, no deletions, 24h cooldown, improvement blocklist.

## Relations & where used
Cross-references `docs/04-Concepts/architecture/agent-training-harness.md` for the MAPE-K agent-training interpretation; `docs/04-Concepts/root/rules-loading-architecture.md` for rule-loading detail.

## Status / caveats
No explicit status field; describes current system state (counts as of doc date) rather than a historical decision. Some skill names noted as renamed (e.g. model-optimizer "now called resource-governor", skill-creator "now called compose-prompt").
