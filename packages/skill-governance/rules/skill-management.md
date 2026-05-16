<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Skill Management — Unified Protocol

## Loading Priority

1. **Project skills** (`.claude/skills/`) — highest priority, project-specific
2. **Global skills** (`~/.claude/skills/`) — shared across projects
3. **Auto-generated skills** — created when coverage is missing

## Skill Registry

- `/skill-registry` scans all skills and creates `.atl/skill-registry.md`
- Registry saved to Engram for cross-session access
- Sub-agents consult registry to know which skills to load
- Version tracked in frontmatter (`name`, `version`, `last-updated`, `auto-generated`, `tech`)
- Refresh when Context7 shows breaking changes; auto-generated skills can be regenerated safely; manual skills NEVER auto-overwritten

## Auto-Loader (session start)

1. Read `.claude/detected-stack.json` (from stack-detector.sh)
2. Verify skills exist per detected technology
3. If missing: suggest generation (do NOT auto-generate without user confirmation)
4. Auto-generated skills marked with `auto-generated: true` in frontmatter
5. After generation, run `/skill-registry` to update index

## Skill Adaptation (always active)

### Before executing any skill
1. Search feedback: `mem_search(query: "skill-feedback/{skill-name}", project: "{project}")`
2. If feedback exists, read full content and adapt execution

### After skill failure
Save feedback to Engram immediately:
```
mem_save(title: "Skill feedback: {name} failed", type: "discovery",
  project: "{project}", topic_key: "skill-feedback/{skill-name}",
  content: "**Skill**: {name}\n**Context**: ...\n**Error**: ...\n**Correction**: ...")
```

### After recovery (with prior failures)
Update feedback to note the successful approach.

### Auto-improvement trigger (3+ failures)
1. Announce: "Skill {name} has failed {N} times. Proposing improvements."
2. Read ALL failure observations
3. Invoke `/skill-creator` with failure context
4. Run `/skill-registry` to update index

## Skill Routing Table

When the orchestrator receives a task, consult this routing table to select the most appropriate skill.
Auto-selection is handled by `lib/skill_router.py` — the `SkillRouter` class matches user messages
to skills using regex intent detection plus optional semantic fallback.

### Core Routing Table

| Context Signal | Primary Skill | Fallback | Confidence |
|---|---|---|---|
| GitHub URL in message | `/repo-forensics` | `/repo-scout` | 0.95 |
| "evaluate repo", "scout repo", "tech radar" | `/repo-scout` | -- | 0.85 |
| "fix bug", "fix the bug", "there is an error" | `/plan-bug` | `/systematic-debugging` | 0.90 |
| "debug", "doesn't work", "failure" | `/systematic-debugging` | -- | 0.85 |
| "new feature", "add", "I need to create" | `/sdd-new` | `/plan-feature` | 0.85 |
| "plan feature", "feature plan" | `/plan-feature` | -- | 0.85 |
| "run tests", "execute tests", "pytest" | `/run-tests` | -- | 0.95 |
| "write tests", "TDD", "red-green-refactor" | `/test-driven-development` | -- | 0.85 |
| "coverage report", "coverage" | `/coverage-report` | -- | 0.80 |
| "security audit", "review security" | `/security-audit` | `/pentest-self` | 0.90 |
| "pentest", "penetration test" | `/pentest-self` | -- | 0.90 |
| "red team", "prompt injection test" | `/red-team` | `/vulnerability-scan` | 0.85 |
| "vulnerability scan", "garak" | `/vulnerability-scan` | -- | 0.85 |
| "semgrep", "SAST", "static analysis" | `/semgrep-scan` | `tob-static-analysis` | 0.85 |
| "secret audit", "scan for secrets" | `/secret-audit` | -- | 0.85 |
| "trail of bits", "tob audit", "tob security" | `tob-static-analysis` | `tob-insecure-defaults` | 0.90 |
| "audit github actions", "actions injection", "agentic actions" | `tob-agentic-actions-auditor` | -- | 0.90 |
| "supply chain audit", "dependency risk", "typosquatting" | `tob-supply-chain-risk-auditor` | -- | 0.90 |
| "insecure defaults", "fail-open", "fail open config" | `tob-insecure-defaults` | `tob-static-analysis` | 0.85 |
| "variant analysis", "bug propagation", "bug pattern" | `tob-variant-analysis` | `tob-static-analysis` | 0.85 |
| "KPIs", "agent health", "métricas de agente" | `/agent-kpis` | `/model-optimizer` | 0.85 |
| "model optimizer", "model routing" | `/model-optimizer` | -- | 0.85 |
| "trust audit", "trust score analysis" | `/trust-audit` | -- | 0.85 |
| "performance dashboard", "cos perf" | `cos perf` | -- | 0.85 |
| "research", "research", "deep research" | `/deep-research` | `/tool-discovery` | 0.80 |
| "find tools", "discover tools" | `/tool-discovery` | -- | 0.85 |
| "create skill", "nueva skill" | `/skill-creator` | -- | 0.95 |
| "optimize skill", "mejorar skill" | `/optimize-skill` | -- | 0.90 |
| "release", "versión", "tag new version" | `/release-os` | -- | 0.90 |
| "scout", "explore the code", "reconnaissance" | `/scout` | `/sdd-explore` | 0.85 |
| "sdd explore", "feasibility" | `/sdd-explore` | -- | 0.75 |
| "document feature", "write docs" | `/document-feature` | `/doc-sync` | 0.85 |
| "doc sync", "stale docs", "sync documentation" | `/doc-sync` | -- | 0.85 |
| "review code", "review the code" | `/self-review` | `/sdd-verify` | 0.85 |
| "stress test", "degradación", "cognitive load" | `/agent-stress-test` | -- | 0.90 |
| "recommend library", "which library" | `/recommend-library` | -- | 0.85 |
| "planning poker", "estimate cost" | `/planning-poker` | `/cost-predict` | 0.85 |
| "cost predict", "predict cost" | `/cost-predict` | -- | 0.85 |
| "status", "how is it going", "health check" | `/cognitive-os-status` | -- | 0.80 |
| "sprint", "sprint plan/status/retro" | `/sprint` | -- | 0.80 |
| "SRE", "monitor services", "container down" | `/sre-agent` | -- | 0.80 |
| "error analyzer", "analyze errors" | `/error-analyzer` | -- | 0.85 |
| "impact analysis", "blast radius" | `/impact-analysis` | -- | 0.85 |
| "issue to PR", "issue #123" | `/issue-to-pr` | -- | 0.80 |
| "contract drift", "OpenAPI mismatch" | `/contract-drift` | -- | 0.85 |
| "resource governor", "budget check" | `/resource-governor` | -- | 0.80 |
| "self improve", "improve the system" | `/self-improve` | -- | 0.80 |
| "retrospective", "squad report" | `/retrospective` | `/squad-report` | 0.90 |
| "singularity", "autonomous loop" | `/singularity` | -- | 0.95 |
| "readiness check", "ready to implement" | `/readiness-check` | -- | 0.80 |
| "DoD check", "definition of done" | `/dod-check` | -- | 0.85 |
| "confidence check" | `/confidence-check` | -- | 0.80 |
| "web crawler", "crawl page" | `/web-crawler` | -- | 0.80 |
| "audit website", "SEO audit" | `/audit-website` | -- | 0.80 |
| "batch run", "run multiple SDD" | `/batch-run` | -- | 0.80 |
| "sandbox sample", "sample before scaling" | `/sandbox-sample` | -- | 0.80 |
| "resume tasks", "what was left" | `/resume-tasks` | -- | 0.80 |
| "GPU sandbox", "Jupyter", "run Python ML" | `/gpu-sandbox` | `/jupyter-exec` | 0.75 |
| "conversation memory", "search past sessions" | `/conversation-memory` | -- | 0.85 |
| "exhaustive prompt", "enumerate scope" | `/exhaustive-prompt` | -- | 0.80 |
| "validate config" | `/validate-config` | -- | 0.80 |
| "smoke test" | `/smoke-test` | -- | 0.95 |
| "sdd continue" | `/sdd-continue` | -- | 0.85 |
| "sdd resume" | `/sdd-resume` | -- | 0.85 |
| "repair status", "circuit breaker" | `/repair-status` | -- | 0.80 |
| "capability snapshot" | `/capability-snapshot` | -- | 0.95 |
| "persistent agent" | `/create-persistent-agent` | -- | 0.95 |
| "auto rollback", "rollback failed change" | `/auto-rollback` | -- | 0.80 |
| "arena", "benchmark comparison" | `/arena` | -- | 0.75 |
| "simulation", "simulate scenario" | `/simulate` | -- | 0.80 |
| "resolve blockers" | `/resolve-blockers` | -- | 0.85 |
| "estimation report", "calibration accuracy" | `/estimation-report` | -- | 0.80 |
| "session manager", "active sessions" | `/sessions` | -- | 0.75 |
| "COS init", "initialize cognitive os" | `/cognitive-os-init` | -- | 0.90 |
| "COS test", "test cognitive os" | `/cognitive-os-test` | -- | 0.85 |
| "checkpoint", "save environment state" | `/checkpoint` | -- | 0.75 |
| "webhook trigger" | `/webhook-trigger` | -- | 0.95 |
| "private mode" | `/private` | -- | 0.90 |

Note: This table COMPLEMENTS model-routing (which picks the MODEL). Skill routing picks the SKILL/WORKFLOW.

### Auto-Selection Protocol

The orchestrator uses `lib/skill_router.py` to auto-select skills:

1. On every user message, call `router.best_match(message)`
2. If confidence >= 0.80: suggest the skill to the user (do not auto-invoke without confirmation)
3. If confidence 0.50-0.79: mention as a possibility
4. If confidence < 0.50 or None: proceed normally without suggestion
5. Baseline regex patterns handle common task phrasing (e.g., "research", "fix", "I need")

```python
from lib.skill_router import SkillRouter

router = SkillRouter()
match = router.best_match(user_message)
if match and match.confidence >= 0.80:
    print(router.format_suggestion([match]))
```

## System Layers

```
Registry (knows what exists) -> Engram (remembers what worked)
  -> Hooks (detect failures in real-time) -> skill-creator (applies improvements)
```

## Contextual Trigger

- When work relates to Skill Management — Unified Protocol.
