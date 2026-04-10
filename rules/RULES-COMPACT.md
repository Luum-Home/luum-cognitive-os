# COS Rules Index

> Compressed index. Full rules loaded on trigger via `[ref-key]`. Hook-enforced rules are excluded from context (see `hooks/self-install.sh:EXCLUDED_RULES`).

## Always Active

### 1. Adaptive Workflow
Classify complexity BEFORE workflow [`adaptive-bypass`]. Trivial(<3 files): direct. Small(1-3): delegate if needed. Medium+: plan/SDD. Phase modifies bypass: reconstruction=speed, production=governance. 5 DoD levels [`definition-of-done`] [`phase-aware-agents`]. Readiness gate before `sdd-apply` on large+.

### 2. Quality Gates
Prompts MUST have numbered `ACCEPTANCE CRITERIA:` with verifiable commands [`acceptance-criteria`]. Agents do minimum — fix: criteria, auto-verify, `/exhaustive-prompt` [`agent-quality`]. Clarification gate [`clarification-gate`]: >60 BLOCK, 30-60 WARN (hook-enforced). Reviews MUST produce findings [`adversarial-review`]. No sycophancy, no TODO/stubs in committed code. Broken windows [`broken-window-policy`]: fix what you find.

### 3. Verification
Trust Report mandatory: score(0-100) = evidence(40%)+criteria(30%)+self-awareness(20%)+proportionality(10%) [`trust-score`]. 1+ uncertainty required. Confidence gate [`confidence-gate`]: <50 WARN(recon)/BLOCK(prod). Claim-validator hook enforces ground truth. Staged verification: SYNTAX→LINT→BUILD→UNIT→INTEGRATION→ADVERSARIAL, stop on first fail.

### 4. Cost Governance
5 principles [`token-economy`]: transparency, worthiness, decomposition, memory-first, optimize-by-default. >$1 tasks decompose to <$0.50 [`decomposition`]. Routing [`model-routing`]: opus=propose/design/debug, sonnet=impl/verify, haiku=archive. Model directive [`model-directive`]: dispatch-gate emits MODEL_DIRECTIVE — MUST follow; MODEL_DISABLED blocks. Queue drain [`queue-drain`]+advisor [`queue-advisor`]: drain on completion, dynamic reorder. Budget [`resource-governance`]: >80%=sonnet, >95%=haiku, >100%=BLOCK. Rate limits hook: 30 tools/min, 20 agents/hr. Non-blocking retry [`non-blocking-retry`]: CronCreate.

### 5. Impact Assessment
Blast radius [`blast-radius`]: LOW(1-5), MEDIUM(6-20), HIGH(21-50), CRITICAL(50+/infra/security) (hook-enforced). Proportionality [`scope-proportionality`]: fixes must not delete(BLOCK prod), >20 files=WARN. Impact analysis [`impact-analysis`] MUST run before large/critical sdd-apply. >100 files MUST sample [`sandbox-sampling`]. Scout [`scout-pattern`]: recon before medium+ implementation.

### 6. Self-Healing
Errors to `error-learning.jsonl` [`error-learning`], deduped 60s; 3+ same=warning. Auto-repair hook enforces capture→classify→fix→verify. Auto-rollback [`auto-rollback`] on 3x verify fail. Crash-recovery: 5min checkpoints (hook-enforced).

### 7. Agent Governance
Audit trail [`agent-identity`], trust 0-3, monotonic attenuation. Least-privilege [`agent-security`]: TTL 120min; blocked: `.env`,`*.key`,secrets. KPIs [`agent-kpis`]: quality>90%, efficiency -20% MoM. Overrides [`agent-customization`]. Sidecars [`agent-sidecars`]. Bus [`agent-communication`] Valkey(OFF).

### 8. Prompt Engineering
Prompts: criteria+verification+fallback [`closed-loop-prompts`]. Escalation [`agent-escalation`]: stuck→diagnose; 5-15% rate, max 3 retries. HALT for multi-service/migration/auth. Templates [`prompt-composition`]. Responsiveness [`responsiveness`]: no silence >10s; max 15 agents/sprint. Clarification [`split-and-resume`]: `NEEDS_CLARIFICATION:`, max 2 rounds.

### 9. Context Efficiency
Thresholds [`context-management`]: 50%=concise, 70%=save+reduce, 85%=stop+summary. Progressive loading [`context-optimization`]: L1 catalog, L2 on-demand, L3 rare; max 5 active. Result truncation hook: >5K chars. Agent output [`agent-output-reading`]: use `<result>` first, then Engram — NEVER Read JSONL. Capability levels [`capability-levels`]: L3 disables context-mgmt, L4 disables clarification/confidence/blast-radius.

### 10. Security
Credentials in env only [`credential-management`]. Content policy + confidentiality: hooks block prohibited terms and IP leaks. License [`license-policy`]: BLOCK AGPL/SSPL/BSL; ALLOW MIT/BSD/Apache. Supply chain [`supply-chain-defense`]: digest pinning. Aguara [`aguara-integration`]: 189 rules.

### 11. Skill Lifecycle
Priority: project>global>auto [`skill-management`]. Skill-rewrite hook fires on 3+ fails. Auto-skill-generation hook fires on complex tasks. Consequence [`consequence-system`]: >=85%(5x)=PROMOTE, <60%=WARN/DEGRADE/DISABLE. Dynamic tools [`dynamic-tool-creation`]: mid-task creation, promote if useful. Task DAG [`task-dag`]: declarative dependency graph for multi-agent workflows.

## Contextual (loaded on trigger)

**Team**: Squads [`squad-protocol`] auto-reconfig <0.80. Estimation [`estimation-calibration`] medium+. Self-improvement [`self-improvement-protocol`] weekly, max 5 changes.

**Infra**: Docker check [`infra-health`]. Singularity [`singularity`] MAPE-K(inactive). Performance [`performance-monitoring`] p50/p95/p99.

**Persistence**: 4-tier resilience [`fault-tolerance`]. Engram prefixes [`engram-organization`]. Sessions [`session-concurrency`]. Step files [`step-files`] for long phases.

**Change Safety**: Security profiles [`hook-security-profiles`] minimal/standard/paranoid. Capability snapshot [`capability-protection`] before cleanup. Plan-first [`cognitive-os-changes`] for OS mods. Dogfooding [`dogfooding`] SDD for substantial changes. Component classification [`component-classification`] CORE vs PACKAGE.

**Modes & Tools**: Dry run [`dry-run`] `DRY_RUN=true`. Private [`private-mode`] `/private`. Ecosystem [`ecosystem-tools`]: parry, semgrep, aguara, e2b, trailofbits, context7. [`library-selection`] license+downloads+maintenance. [`reinvention-prevention`] check upstream first.

**Pre-Development**: Pre-dev readiness hook enforces required artifacts (docs/01-context, 04-security, 09-execution-plan). Audit hooks: git-context-capture + session-changelog + audit-id-enricher. Skills: `/context-analysis`, `/threat-model`, `/execution-plan`, `/audit-report`.

## Project-Specific
Rules in `{project}/.claude/rules/`, generated by `/cognitive-os-init`.
