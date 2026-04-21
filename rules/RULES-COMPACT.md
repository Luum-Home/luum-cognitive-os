<!-- SCOPE: both -->
# COS Rules Index

> Compressed index. Full rules loaded on trigger via `[ref-key]`. Hook-enforced rules excluded (see `hooks/self-install.sh:EXCLUDED_RULES`).

## Always Active

### 1. Adaptive Workflow
Classify complexity BEFORE workflow [`adaptive-bypass`]. Trivial(<3 files): direct. Small(1-3): delegate if needed. Medium+: plan/SDD. Phase modifies bypass: reconstruction=speed, production=governance. 5 DoD levels [`definition-of-done`] [`phase-aware-agents`]. Readiness gate before `sdd-apply` on large+.

### 2. Quality Gates
Prompts MUST have `ACCEPTANCE CRITERIA:` with verifiable commands [`acceptance-criteria`]. Agents do minimum — fix: criteria, auto-verify, `/exhaustive-prompt` [`agent-quality`]. Clarification gate hook-enforced [`clarification-gate`]. Reviews MUST produce findings [`adversarial-review`]. No sycophancy, no TODO/stubs. Broken windows [`broken-window-policy`]. [`prompt-quality`] [`anti-hallucination`] [`assumption-tracking`] [`scope-creep-detection`].

### 3. Verification
Trust Report mandatory: evidence(40%)+criteria(30%)+self-awareness(20%)+proportionality(10%) [`trust-score`]. 1+ uncertainty required. Confidence gate hook-enforced [`confidence-gate`]. Staged: SYNTAX→LINT→BUILD→UNIT→INTEGRATION→ADVERSARIAL, stop on first fail.

### 4. Cost Governance
[`token-economy`]: transparency, worthiness, decomposition, memory-first, optimize-by-default. >$1→decompose <$0.50 [`decomposition`]. [`model-routing`]: opus=propose/design, sonnet=impl/verify, haiku=archive. [`model-directive`]: MUST follow; MODEL_DISABLED blocks. Queue [`queue-drain`]+[`queue-advisor`]. [`resource-governance`]: >80%=sonnet, >95%=haiku, >100%=BLOCK. Rate limits: [`rate-limiting`] [`rate-limit-protection`]. [`non-blocking-retry`]: CronCreate. [`cost-prediction`] [`workload-scheduling`]. [`llm-dispatch`] (ADR-049): `scripts/orchestrator.py` + `lib/dispatch.py` default `--providers qwen,claude` (Qwen primary preserves Claude Max). Kill-switches: `COS_DISABLE_LLM_FALLBACK=1`, `COS_FORCE_CLAUDE_PRIMARY=1`. Skill model hints (opus/sonnet/haiku) mapped to Qwen bundle. Metrics→`llm-dispatch.jsonl`.

### 5. Impact Assessment
Blast radius hook-enforced [`blast-radius`]. Scope proportionality hook-enforced [`scope-proportionality`]. Impact analysis [`impact-analysis`] MUST run before large/critical sdd-apply. >100 files sample [`sandbox-sampling`]. Scout [`scout-pattern`]: recon before medium+.

### 6. Self-Healing
Errors to `error-learning.jsonl` [`error-learning`], deduped 60s; 3+ same=warning. Auto-rollback hook-enforced [`auto-rollback`]. [`crash-recovery`] [`auto-repair`].

### 7. Agent Governance
Audit trail hook-enforced [`agent-identity`]. [`agent-security`]: TTL 120min; blocks `.env`,`*.key`,secrets. [`agent-kpis`]: quality>90%, efficiency -20% MoM. [`agent-customization`] overrides. [`agent-sidecars`]. [`agent-communication`] Valkey(OFF). Harness-agnostic event capture [ADR-033]: canonical schema in `lib/harness_adapter/`; CC adapter preserves legacy `agent-heartbeat.jsonl`, new harnesses add one adapter file.

### 8. Prompt Engineering
[`closed-loop-prompts`]: criteria+verification+fallback. [`agent-escalation`]: stuck→diagnose; 5-15% rate, max 3 retries. HALT for multi-service/migration/auth. [`prompt-composition`] templates. [`responsiveness`]: no silence >10s, `run_in_background` for >5s cmds, 10-15 agents/sprint. [`split-and-resume`]: `NEEDS_CLARIFICATION:`, max 2 rounds. [`orchestrator-prompt-compose`] (ADR-032): pipe draft through `scripts/compose-agent-prompt.py` before Agent call when task touches settings.json/lib/*.py/packages/efficiency-profile.

### 9. Context Efficiency
[`context-management`]: 50%=concise, 70%=save+reduce, 85%=stop+summary. [`context-optimization`]: L1 catalog, L2 on-demand, L3 rare; max 5 active. Result truncation hook-enforced: >5K chars [`result-management`] [`response-compression`]. [`agent-output-reading`]: `<result>` first, then Engram — NEVER Read JSONL. [`capability-levels`]: L3 disables context-mgmt, L4 disables clarification/confidence/blast-radius. [`cognitive-load`].

### 10. Security
Credentials in env only [`credential-management`]. Content policy + confidentiality hook-enforced [`content-policy`] [`confidentiality-protection`]. License [`license-policy`]: BLOCK AGPL/SSPL/BSL; ALLOW MIT/BSD/Apache. Supply chain [`supply-chain-defense`]: digest pinning. Aguara [`aguara-integration`]: 189 rules. [`security-scanning`] [`pentesting-readiness`] [`audit-trail`].

### 11. Skill Lifecycle
Priority: project>global>auto [`skill-management`]. [`skill-rewrite`]+[`auto-skill-generation`] hooks active. Consequence hook-enforced [`consequence-system`]. Dynamic tools [`dynamic-tool-creation`]: mid-task creation, promote if useful. Task DAG [`task-dag`]: dependency graph for multi-agent workflows. [`doc-sync`] [`user-prompt-capture`].

## Contextual (loaded on trigger)

**Team**: [`squad-protocol`] auto-reconfig <0.80. [`estimation-calibration`] medium+. [`self-improvement-protocol`] weekly, max 5 changes.

**Infra**: [`infra-health`] Docker check. [`singularity`] MAPE-K(inactive). [`performance-monitoring`] p50/p95/p99. [`observability`] MLflow. [`so-slo`] ADR-028 SLO catalogue + error budget + cadence. [`infra-intent`] [`model-compatibility`].

**Persistence**: [`fault-tolerance`] 4-tier. [`engram-organization`] prefixes. [`session-concurrency`]. [`step-files`] long phases.

**Change Safety**: [`hook-security-profiles`] minimal/standard/paranoid. [`capability-protection`] snapshot before cleanup. [`cognitive-os-changes`] plan-first for OS mods. [`dogfooding`] SDD for substantial changes. [`component-classification`] CORE vs PACKAGE.

**Modes & Tools**: [`dry-run`] `DRY_RUN=true`. [`private-mode`] `/private`. [`ecosystem-tools`] [`library-selection`] [`reinvention-prevention`]. [`parry-integration`] [`e2b-integration`] [`tero-integration`] [`repomix-integration`] [`trailofbits-skills`] [`hcom-integration`] [`context7-auto-trigger`].

**Pre-Dev**: [`pre-dev-readiness-gate`] [`pre-commit-gate`]. Audit: git-context-capture + session-changelog. [`orchestrator-mode`] [`os-vs-project`].

## Project-Specific
Rules in `{project}/.claude/rules/`, generated by `/cognitive-os-init`.
