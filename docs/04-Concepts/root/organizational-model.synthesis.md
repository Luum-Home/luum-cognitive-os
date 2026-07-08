---
type: concept-synthesis
source: docs/04-Concepts/root/organizational-model.md
---

## What it is
An explanatory analogy mapping every Cognitive OS component to a role in an autonomous software company, clarifying responsibilities and escalation paths.

## Key mechanics
- Executive: CEO = Orchestrator (`CLAUDE.md`, coordinates/delegates, never executes); Constitution/Board = 7 immutable Constitutional Rules; COO = `cognitive-os.yaml` (thresholds, phases, policies).
- Product Dept (SDD pipeline): Product Discovery=`sdd-explore`, PM=`sdd-propose`, Business Analyst=`sdd-spec`, Architect=`sdd-design`, Tech Lead=`sdd-tasks`, Developer=`sdd-apply`, QA Lead=`sdd-verify`, Release Manager=`sdd-archive`.
- Engineering Dept: Developers=sub-agents (Agent tool, ephemeral), DevOps=Hooks (41 scripts), Infrastructure=Docker Compose (17 services: Langfuse, LiteLLM, ClickHouse, Cognee, Opik, etc.).
- SRE/Ops Dept: Incident Commander=`auto-repair-dispatcher.sh`, SRE On-Call=MAPE-K loop, Incident KB=`remediation-registry.jsonl`, Circuit Breaker=`circuit-breaker.sh` (trips after 3+ consecutive repair failures), Error Analyst=`error-learning.sh`.
- Data/BI Dept: Data Analyst=`agent-kpis` skill (20+ KPIs, 5 OKRs), BI Dashboard=`kpi-trigger.sh`, Data Engineer=`metrics-rotation.sh` (30-day retention), Threshold Optimizer=`metrics-calibrator` skill.
- Security/Compliance Dept: CISO=Constitutional gates, Compliance Officer=license checker (AGPL/SSPL/ELv2 detection), Security Guard=`block-prod-urls.sh`, Auditor=OKR 5 Security KPIs (target 0 violations, CRITICAL alert on any).
- HR/Talent Dept: HR Manager=Squads (YAML), Performance Review=`skill-metrics-tracker.sh`, Training=`skill-feedback-tracker.sh` (rewrite suggestion after 3+ failures), Recruiter=Tech Radar (ADOPT/TRIAL/ASSESS/HOLD).
- Corporate Memory: Knowledge Manager=Engram, Archivist=`session-learnings.jsonl`, Wiki=56+ skill files.
- Escalation path: Agent -> Squad Manager -> Organization -> Human.

## Relations & where used
Links to `overview.md`, `rules.md`, `skills.md`, `hooks.md`, `automation.md`, `persistence-map.md`. Key insight: all "employees" (sub-agents) are ephemeral with no state between invocations; only the orchestrator is permanent, and institutional memory persists via Engram + JSONL metrics + skills.

## Status / caveats
Pure conceptual/organizational analogy document; no implementation status or caveats stated in the source.
