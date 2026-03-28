# Cognitive OS Rules — Thematic Index

> Compressed thematic index. Full rules loaded contextually via reference keys.

## Always Active

### 1. Adaptive Workflow

Classify task complexity BEFORE choosing workflow [`adaptive-bypass`]. Read `cognitive-os.yaml` for the CURRENT project's `phase` and `efficiency.profile` — these determine how aggressively to bypass. Trivial (<3 files, obvious fix): work directly, no delegation, no SDD. Small (1-3 files): delegate if needed, no SDD. Medium+: plan first [`plan-first`] or full SDD. In production/maintenance phase, bias TOWARD governance (small tasks may still need delegation). In reconstruction, bias TOWARD speed (even small tasks can be done directly). 5 DoD levels (trivial/small/medium/large/critical) — agents MUST classify before starting, cannot mark done without ALL criteria passing [`definition-of-done`] [`phase-aware-agents`]. Readiness gate required before `sdd-apply` on large+ tasks. Research shows context files reduce task success rates for simple tasks (arxiv.org/abs/2602.11988) — the bypass improves both efficiency AND effectiveness.

### 2. Quality Gates

Every agent prompt MUST include numbered `ACCEPTANCE CRITERIA:` with verifiable commands [`acceptance-criteria`]. Agents do minimum not maximum — fix with: (1) mandatory criteria, (2) auto-verify hook, (3) `/exhaustive-prompt` for scope enumeration, (4) completeness-check hook [`agent-quality`]. Clarification gate [`clarification-gate`] scores prompt ambiguity 0-100; >60 BLOCK, 30-60 WARN. Every review MUST produce at least one finding — "looks good" is PROHIBITED [`adversarial-review`]. Pre-commit hook blocks on test failure, warns on coverage <80% [`pre-commit-gate`]. Prompt quality [`prompt-quality`] scores prompts on 5 dimensions (advisory, never blocks). Scope creep detection [`scope-creep-detection`] PostToolUse hook flags edits outside approved scope. Anti-sycophancy: no flattery openers, lead with substance, disagree openly. No TODO/stubs/commented-out code in committed work. Broken window policy [`broken-window-policy`]: if you find something broken, fix it — no "pre-existing" excuses.

### 3. Verification

Every agent completion MUST include Trust Report: score (0-100) = evidence(40%) + criteria(30%) + self-awareness(20%) + proportionality(10%) [`trust-score`]. Mandatory self-doubt: at least 1 uncertainty; "100% confident" is a RED FLAG. Confidence gate [`confidence-gate`] enforces minimum thresholds: score <50 WARN in reconstruction, BLOCK in production. 3-layer anti-hallucination [`anti-hallucination`]: ground truth extraction, cross-verification (mandatory for large/critical), claim-validator hook. Staged verification runs cheap-first: SYNTAX->LINT->BUILD->UNIT_TEST->INTEGRATION->ADVERSARIAL->CROSS_VERIFY, stopping at first failure.

### 4. Cost Governance

5 token principles [`token-economy`]: transparency, worthiness, decomposition, memory-first, optimize by default. Tasks >$1 MUST be decomposed into <$0.50 sub-tasks [`decomposition`]. Model routing [`model-routing`]: opus for propose/design/debug, sonnet for spec/tasks/apply/verify, haiku for archive. Budget enforcement [`resource-governance`]: alert >$1/run, daily cap $10; >80% monthly forces sonnet, >95% forces haiku, >100% BLOCK. Rate limits [`rate-limiting`]: 30 tool calls/min, 20 agents/hr, 15 bash/min, 10 writes/min, $5/hr cap; phase-aware (reconstruction 1.5x, production 0.75x). Token consumption monitoring [`rate-limit-protection`]: 50% INFO, 80% WARN, 95% BLOCK with auto-save. Cost prediction [`cost-prediction`] from historical Jaccard similarity before medium+ tasks. Baseline model: claude-opus-4-6 (1M) [`model-compatibility`].

### 5. Impact Assessment

Blast radius [`blast-radius`] estimates task impact before launch: LOW (1-5 files), MEDIUM (6-20), HIGH (21-50), CRITICAL (50+ or infra/security keywords). Proportionality [`scope-proportionality`]: fix tasks must not delete files (BLOCK in production), >20 files = WARN, >5 deletions = WARN. Impact analysis [`impact-analysis`] checks direct importers, test coverage, config deps, Docker services — MUST run before `sdd-apply` on large/critical. Tasks >100 files MUST sample first [`sandbox-sampling`]: classify->sample->sandbox->verify->scale. Docs NEVER use sed (contextual agent only).

### 6. Self-Healing

Errors auto-captured to `error-learning.jsonl` [`error-learning`], deduped 60s; 3+ same type in 24h triggers warning injection. Auto-repair chain [`auto-repair`]: capture->classify->registry lookup->worktree fix->verify->merge/discard. Circuit breaker: 2 consecutive failures=OPEN, 10/hr cap, 1h cooldown. NEVER auto-repairs: DB migrations, auth, payments, .env, docker-compose, git history. When sdd-verify fails 3x, auto-rollback [`auto-rollback`] reverts commits on a `rollback/{change}` branch; auto-execute in reconstruction, HALT in production. Crash recovery [`crash-recovery`]: auto-checkpoint every 5min via git stash; SessionStart hook detects orphaned stashes.

### 7. Agent Governance

WHO/WHAT/WHEN/WHERE/WHY audit trail [`agent-identity`], trust levels 0-3, monotonic permission attenuation. Least-privilege access [`agent-security`]: 6 levels (NONE-ADMIN), 5 profiles, TTL max 120min; always-blocked: `.env`, `*.key`, `*.pem`, `secrets/*`, `.git/config`. KPIs calculated at session end [`agent-kpis`]: quality >90%, efficiency -20% MoM, 0 security violations; weekly review Mondays. Per-agent overrides [`agent-customization`] in `customizations/{name}.yaml`: model, tools, budget, phase behavior. Agent sidecars [`agent-sidecars`] inject per-agent learnings from Engram on launch. Communication bus [`agent-communication`] via Valkey pub/sub (OFF by default): heartbeat 5s, progress tracking, clarification Q&A.

### 8. Prompt Engineering

Every prompt: success criteria + verification command + fallback action [`closed-loop-prompts`]. Max 3 retries then escalation. HALT-and-WAIT for multi-service, data migration, API contracts, auth/security changes. Compose prompts from reusable templates [`prompt-composition`] in `.cognitive-os/templates/`. Assumption tracker [`assumption-tracking`] scans for "I assume", "probably", "it seems"; 3+ triggers WARNING. Never appear stuck [`responsiveness`]: state what you're running before >5s commands, use `run_in_background` for long tasks, max 10-15 agents per sprint, save to Engram if context heavy. Mid-task clarification [`split-and-resume`]: agents output `NEEDS_CLARIFICATION:`, orchestrator searches Engram then asks user, max 2 rounds.

### 9. Context Efficiency

Capacity thresholds [`context-management`]: 50% be concise, 70% MUST save to Engram and reduce verbosity, 85% stop new work and call `mem_session_summary`. Progressive loading [`context-optimization`]: L1 catalog (~2K tokens) always, L2 full skill on demand, L3 references rare; max 5 skills active. Dual-search: complete file->sharded->Engram. Result truncation [`result-management`] for outputs >5K chars, preserving critical patterns (FAIL, ERROR, PASS). Auto-disable components by model capability [`capability-levels`]: level 3 disables context-management, level 4 disables clarification-gate/assumption-tracking/confidence-gate/blast-radius.

### 10. Security

Credentials never in code [`credential-management`], always env vars, validate at startup. Content policy [`content-policy`] enforced by PostToolUse hook on Edit|Write — BLOCK on prohibited terms. License policy [`license-policy`]: BLOCK AGPL/SSPL/BSL/ELv2/Commons Clause/FSL; ALLOW MIT/BSD/Apache/ISC; CAUTION LGPL/MPL. Auto-enforced on dependencies via `lib/license_guard.py`. Semgrep SAST [`security-scanning`] auto-scans after `sdd-apply` (OFF by default, enable with `SEMGREP_ENABLED=true`). Pentesting readiness [`pentesting-readiness`]: 7 critical test cases covering secret access, hook modification, permission escalation, prompt injection. Active self-pentest via `/pentest-self` skill: 6 categories of security validation. Supply chain defense [`supply-chain-defense`]: Docker digest pinning, git commit pinning, per-file integrity validation.

### 11. Skill Lifecycle

Loading priority: project > global > auto-generated [`skill-management`]. Skill routing table maps task types to primary/fallback skills. Before exec: search Engram for feedback; after fail: save feedback; 3+ fails: suggest `/skill-creator`. Auto-generated from complex tasks (10+ tool uses OR 8000+ chars) [`auto-skill-generation`], saved to `auto-generated/`, opt-out: `NO_AUTO_SKILL=true`. Consequence system [`consequence-system`]: score >=85% (5x) PROMOTE, <60% WARN/DEGRADE/DISABLE. Evolutionary archive (via `lib/skill_archive.py`) tracks content hash, trust score, success rate per execution; flags <60% for rewrite, recommends rollback when >20 points below best.

## Contextual (loaded on trigger)

### 12. Team Governance

Squad protocol [`squad-protocol`] (trigger: `/squad-report`/`/retrospective`): repo-to-squad mapping, evaluation schedule, auto-reconfig on successRate<0.80 or compliance<0.90, 24h cooldown, 4-level escalation. Estimation calibration [`estimation-calibration`] (trigger: estimation, task complexity): pre-task estimates required for medium+, post-task actuals mandatory, 5 anti-bias layers, auto-applied after 10+ data points. Self-improvement [`self-improvement-protocol`] (trigger: weekly Monday, KPI breach, 3+ failures, `/self-improve`): detect patterns, auto-apply safe changes (templates, criteria, routing), human approval for rule/skill rewrites, max 5 per run.

### 13. Infrastructure

SessionStart hook [`infra-health`] checks Docker services vs `cognitive-os.yaml` expected; `INFRA_AUTO_START=true` auto-starts. Infra intent detector [`infra-intent`] suggests stack components from config on infrastructure keywords (advisory). Executor mode [`orchestrator-mode`]: `ORCHESTRATOR_MODE=executor` enables subprocess delegation with heartbeat, progress streaming, file lock coordination. Performance monitoring [`performance-monitoring`] tracks p50/p95/p99 latency, throughput, component health (healthy/degraded/unhealthy); hooks opt in via `timing.sh`. Singularity [`singularity`] (trigger: `/singularity`): autonomous MAPE-K control loop, inactive by default, budget-capped, phase-dependent event types.

### 14. Persistence

4-tier resilience [`fault-tolerance`]: connection, LLM call, context, agent. Register tasks pre-launch in `active-tasks.json`, idempotent re-launch. Engram topic keys [`engram-organization`] use prefixed paths: `planning/`, `implementation/`, `docs/`, `agent/`, `sre/`, `architecture/`, `sprint/`, `config/`, `bugfix/`; legacy `sdd/` fallback. Multi-session support [`session-concurrency`]: isolated tasks/metrics per `sessions/{id}/`, shared skills/rules/Engram (SQLite WAL), advisory file locking. Step files [`step-files`] (trigger: long phases): break into discrete resumable checkpoints. Doc sync [`doc-sync`]: detect stale docs after code changes via PostToolUse hook on Edit|Write.

### 15. Change Safety

Before any `.cognitive-os/` cleanup: `/capability-snapshot save`, after: `/capability-snapshot diff` [`capability-protection`]. OS modifications MUST follow plan-first [`cognitive-os-changes`]: create plan in `plans/`, run `/cognitive-os-test`. luum-agent-os MUST use its own tools [`dogfooding`]: substantial changes require full SDD pipeline; self-installed via `self-install.sh`. Cognitive OS is universal [`os-vs-project`]: project-specific content belongs in `{project}/.claude/`, never in `.cognitive-os/`. Component classification [`component-classification`]: CORE vs PACKAGE classification protocol with independent versioning rules for packages.

### 16. Library Selection

[`library-selection`] (trigger: new library adoption) — Mandatory checks: license compatibility, >1000 weekly downloads (npm) / >500 monthly (PyPI), last publish <6 months, TypeScript support, existing dependency overlap. Use `/recommend-library`.

### 17. Dry Run

[`dry-run`] — Set `DRY_RUN=true` to preview agent actions without executing. Hook intercepts Agent/task/delegate calls, outputs description, exits BLOCK. Useful for SDD pipeline preview.

### 18. Private Mode

[`private-mode`] (trigger: `/private`) — Disable all persistence (Engram, metrics, errors). Safety rules remain active. Flag at `/tmp/claude-private-mode-active`.

### 19. Ecosystem Tools

External tool integrations [`ecosystem-tools`] [`parry-integration`] [`hcom-integration`] [`repomix-integration`] [`trailofbits-skills`] [`context7-auto-trigger`] — optional external tool configs, loaded when tools are installed. See `rules/ecosystem-tools.md` for overview.

## Project-Specific

Project-specific rules (architecture, constitutional gates, service configs) live in `{project}/.claude/rules/`, generated by `/cognitive-os-init` or created manually.
