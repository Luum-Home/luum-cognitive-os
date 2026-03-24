# Cognitive OS Rules (Compact)

> Compressed rule index. Full rules loaded contextually. Target: ~1,500 tokens vs ~5,500 full.

## Always Active

- **Phase** [`phase-aware-agents`]: Read from `cognitive-os.yaml`. reconstruction: rewrite > patch, follow standard strictly, break backwards compat OK, auto-remediate architecture violations as blockers.
- **License** [`license-policy`]: BLOCK AGPL, SSPL, BSL, ELv2, Commons Clause, FSL. ALLOW MIT, BSD, Apache 2.0, ISC. CAUTION LGPL (dynamic only), MPL 2.0. Check transitives.
- **Errors** [`error-learning`]: Auto-captured to `.cognitive-os/metrics/error-learning.jsonl`. Deduped 60s. 3+ same type in 24h triggers warning injection. Run `/error-analyzer` on patterns.
- **Fault Tolerance** [`fault-tolerance`]: Register tasks pre-launch in `active-tasks.json`. Checkpoint on complete. Session-resume on restart. Idempotent agents (check before redo). Pre-compaction flush to Engram.
- **Cost** [`cost-tracking`]: opus for reasoning ($15/$75), sonnet for implementation ($3/$15), haiku for docs ($0.25/$1.25). Alert >$1/run, critical >$2/run, daily cap $10.
- **Model Routing** [`model-routing`]: Check routing table before delegating. opus: propose/design/debug. sonnet: spec/tasks/apply/verify/tdd. haiku: archive.
- **Credentials** [`credential-management`]: Never in code. Always env vars. Validate at startup. Local creds OK for dev only.
- **Skill Management** [`skill-management`]: Loading priority: project > global > auto-generated. Before skill exec: search feedback in Engram. After fail: save feedback. After recovery: update. 3+ fails: suggest `/skill-creator`. Auto-loader reads `detected-stack.json` at session start.
- **Agent Identity** [`agent-identity`]: WHO/WHAT/WHEN/WHERE/WHY audit trail. Trust levels 0-3. Sub-agents inherit at most parent permissions.
- **Agent KPIs** [`agent-kpis`]: Calculate at session end. OKR targets: quality >90%, efficiency -20% MoM, 0 security violations. Weekly review Mondays.
- **Context Management** [`context-management`]: Manage context window efficiently. Track token usage. Unload stale context. Max 5 skills active simultaneously.
- **Context Optimization** [`context-optimization`]: Progressive 3-level loading: L1 catalog (~2K tokens), L2 full skill (on demand), L3 references (rare). ~96% token savings. Dual-search protocol: complete file -> sharded version -> Engram.
- **Doc Sync** [`doc-sync`]: Detect stale docs after code changes. Auto-trigger doc-sync skill. Track doc freshness.
- **Plan First** [`plan-first`]: Plan before executing. Use evaluate-plan skill for scoring. Complex tasks require plan approval.
- **Prompt Composition** [`prompt-composition`]: Use centralized prompt templates. compose-prompt skill for reusable fragments. Template types defined in `.cognitive-os/templates/`.
- **Resource Governance** [`resource-governance`]: Budget enforcement, infra auto-scale, model downgrade chain. 5 efficiency metrics.
- **Result Management** [`result-management`]: Truncate large results. result-truncator hook for outputs >10K chars. Preserve structure.
- **Closed Loop Prompts** [`closed-loop-prompts`]: Self-correcting agents: success criteria + verification + fallback in every prompt. Max 3 retries, then escalation. HALT-and-WAIT for ambiguous/high-risk tasks (multi-service, data migration, API contracts, auth/security). In reconstruction: HALT only for data-destructive ops.
- **Agent Quality** [`agent-quality`]: Agents do MINIMUM not MAXIMUM. Fix: (1) mandatory acceptance criteria in every prompt, (2) auto-verify hook runs verification commands on completion, (3) `/exhaustive-prompt` enumerates scope before launch, (4) completeness-check hook warns on vague prompts. Never launch without measurable criteria.
- **Acceptance Criteria** [`acceptance-criteria`]: EVERY agent prompt MUST include `ACCEPTANCE CRITERIA:` with numbered checks using `\`command\` = value` or `\`command\` exits 0` or `\`command\` >= threshold`. If missing, agent must define them before starting. Templates for rebrand, migration, feature, cleanup tasks.
- **Engram Organization** [`engram-organization`]: Prefixed topic keys: `planning/`, `implementation/`, `docs/`, `agent/`, `sre/`, `architecture/`, `sprint/`, `config/`, `bugfix/`. Legacy `sdd/` keys map to `planning/`. Gradual migration on read.
- **Agent Customization** [`agent-customization`]: Per-agent overrides in `customizations/{agent-name}.yaml`. Deep merge onto base definition. Override: model, temperature, tools, skills, budget, phase behavior. Survives Cognitive OS updates.
- **Trust Score** [`trust-score`]: Every agent completion MUST include Trust Report: score (0-100), evidence provided, uncertainties, human verification steps. Score = evidence(40%) + criteria(30%) + self-awareness(20%) + proportionality(10%). Thresholds: 90+ high, 70-89 medium, 50-69 low, <50 very low. Mandatory self-doubt: at least 1 uncertainty. "100% confident" is a RED FLAG. Logged to `.cognitive-os/metrics/trust-scores.jsonl`. Hook `trust-score-validator.sh` (PostToolUse on Agent) validates presence and alerts on low scores. Run `/trust-audit` for trend analysis.
- **Definition of Done** [`definition-of-done`]: 5 complexity levels (trivial/small/medium/large/critical). Agents MUST classify BEFORE starting. Cannot mark done without ALL criteria passing. Phase-dependent enforcement: reconstruction/stabilization=WARN, production/maintenance=BLOCK. Run `/dod-check` to verify. Hook `dod-gate.sh` auto-checks on Agent completion.
- **Capability Protection** [`capability-protection`]: Before any .cognitive-os/ cleanup/refactor, MUST run `/capability-snapshot save`. After changes, MUST run `/capability-snapshot diff`. REMOVED items require justification or restoration. Hook `pre-cleanup-snapshot.sh` auto-detects cleanup intent on Agent launches.
- **Session Concurrency** [`session-concurrency`]: Multi-session support. Isolated: tasks, metrics (per `sessions/{id}/`). Shared: skills, rules, Engram (SQLite WAL). Advisory file locking via `concurrent-write-guard.sh` on Edit|Write. Lock timeout 300s. Hooks: `session-init.sh` (SessionStart), `session-cleanup.sh` (Stop). Manage with `/sessions`.
- **OS vs Project** [`os-vs-project`]: Cognitive OS files are UNIVERSAL. Project-specific content belongs in `{project}/.claude/`. Never put project-specific infrastructure, services, or architecture in `.cognitive-os/`. Use `/cognitive-os-init` to generate project-specific files from config.
- **Sandbox Sampling** [`sandbox-sampling`]: Tasks >100 files MUST sample first. Tasks >20 files SHOULD sample. Docs NEVER sed (contextual agent only). Code can use sed after sample validation. Config must validate parse after apply. Hook `epic-task-detector.sh` (PreToolUse on Agent) detects large-scope tasks. Run `/sandbox-sample` for classify->sample->sandbox->verify->scale workflow.
- **Auto-Repair** [`auto-repair`]: Monitors errors and applies known fixes autonomously. Chain: error-learning.sh captures → auto-repair-dispatcher.sh classifies → remediation-registry lookup → worktree fix → verify → merge/discard. Phase gates: reconstruction/stabilization=full (code+lint+test+infra+llm), production/maintenance=infra-only. Circuit breaker: 2 consecutive failures → OPEN, 10/hour global cap, 1h cooldown. NEVER auto-repairs: DB migrations, auth changes, payment code, .env files, docker-compose, git history, security files. Metrics: `repair-outcomes.jsonl`, `remediation-registry.jsonl`, `circuit-breaker/`.

- **Metrics Calibration** (contextual: metrics, KPI, threshold, calibration)
Static thresholds decay. Weekly `/metrics-calibrator` analyzes 30-day KPI distributions. Auto-adjusts if threshold < p10 (too easy) or > p90 (too hard). Derived metrics: cost_per_fix, repair_roi, skill_efficiency, error_velocity, health_score.

## Contextual (loaded on trigger)

- **SRE Protocol** [`sre-protocol`] -- trigger: error/failure/crash/restart -- classify error, search Engram for known fix, apply if safe (restart/prune), escalate if unsafe (code/config/data changes). Topic key: `sre-fix/{container}/{error-type}`.
- **Squad Protocol** [`squad-protocol`] -- trigger: `/squad-report`/`/retrospective` -- repo-to-squad mapping, evaluation schedule, auto-reconfig triggers (successRate<0.80, compliance<0.90), cooldown 24h min, escalation 4-level.
- **Auto-Skill Gen** [`auto-skill-generation`] -- trigger: complex task completion -- 10+ tool uses OR 8000+ chars = auto-generate SKILL.md draft. Saved to `auto-generated/`. Opt-out: `NO_AUTO_SKILL=true`.
- **Private Mode** [`private-mode`] -- trigger: `/private` -- Disable all persistence (Engram, metrics, errors). Safety rules remain active. Flag at `/tmp/claude-private-mode-active`.
- **Secret Hygiene** [`secret-hygiene`] -- trigger: env var/secret/credential work -- Every new env var must be in `.env.example`. Never hardcode secrets. Use `PROVIDER_*` naming. PostToolUse hook `secret-detector.sh` auto-scans on Edit|Write. `/secret-audit` for full cross-reference scan.
- **Adversarial Review** [`adversarial-review`] -- trigger: code review/PR review -- Every review MUST produce at least one finding. "Looks good" is PROHIBITED.
- **Agent Sidecars** [`agent-sidecars`] -- trigger: agent launch -- Inject learnings/preferences from engram sidecar on agent launch. Accumulate per-agent context across sessions.
- **Infra Intent** [`infra-intent`] -- trigger: infrastructure keywords in prompts -- Advisory detection of infra needs, suggests stack components from cognitive-os.yaml. Never blocks.
- **Library Selection** [`library-selection`] -- trigger: new library adoption -- Mandatory checks: license, maintenance, security, alternatives. Use `/recommend-library` skill.
- **Model Compatibility** [`model-compatibility`] -- trigger: model change/selection -- Baseline: claude-opus-4-6 (1M). Run `/cognitive-os-compat-test` for smoke test.
- **Step Files** [`step-files`] -- trigger: long-running phases -- Break phases into discrete resumable steps. Each step = checkpoint. Enables resumption without re-doing.

## Project-Specific (loaded from .claude/rules/)

Project-specific rules (architecture patterns, constitutional gates, service configs, testing setups) are NOT part of Cognitive OS. They live in `{project}/.claude/rules/` and are generated by `/cognitive-os-init` or created manually.
