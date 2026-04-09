# COS Rules Index

> Compressed index. Full rules loaded on trigger via `[ref-key]`.

## Always Active

> Hook set depends on efficiency profile in `cognitive-os.yaml`. Lean=7 hooks, standard=18, full=all.

### 1. Adaptive Workflow
Classify complexity BEFORE workflow [`adaptive-bypass`]. Trivial(<3 files): direct. Small(1-3): delegate if needed. Medium+: plan/SDD. Phase modifies bypass: reconstruction=speed, production=governance. 5 DoD levels [`definition-of-done`] [`phase-aware-agents`]. Readiness gate before `sdd-apply` on large+.

### 2. Quality Gates
Prompts MUST have numbered `ACCEPTANCE CRITERIA:` with verifiable commands [`acceptance-criteria`]. Agents do minimum — fix: criteria, auto-verify, `/exhaustive-prompt`, completeness-check [`agent-quality`]. Clarification gate [`clarification-gate`]: >60 BLOCK, 30-60 WARN. Reviews MUST produce findings [`adversarial-review`]. Pre-commit blocks on test failure [`pre-commit-gate`]. Prompt quality [`prompt-quality`] scores 5 dimensions (advisory). Scope creep [`scope-creep-detection`] flags out-of-scope edits. No sycophancy, no TODO/stubs in committed code. Broken windows [`broken-window-policy`]: fix what you find.

### 3. Verification
Trust Report mandatory: score(0-100) = evidence(40%)+criteria(30%)+self-awareness(20%)+proportionality(10%) [`trust-score`]. 1+ uncertainty required. Confidence gate [`confidence-gate`]: <50 WARN(recon)/BLOCK(prod). Anti-hallucination [`anti-hallucination`]: ground truth + cross-verify(large/critical) + claim-validator. Staged verification: SYNTAX->LINT->BUILD->UNIT->INTEGRATION->ADVERSARIAL->CROSS_VERIFY, stop on first fail.

### 4. Cost Governance
5 principles [`token-economy`]: transparency, worthiness, decomposition, memory-first, optimize-by-default. >$1 tasks MUST decompose to <$0.50 [`decomposition`]. Routing [`model-routing`]: opus=propose/design/debug, sonnet=spec/tasks/apply/verify, haiku=archive. Budget [`resource-governance`]: >80% monthly=sonnet, >95%=haiku, >100%=BLOCK. Rate limits [`rate-limiting`]: 30 tools/min, 20 agents/hr, $5/hr. Token monitoring [`rate-limit-protection`]: 50%=INFO, 80%=WARN, 95%=BLOCK+auto-save. Cost prediction [`cost-prediction`] via Jaccard similarity. Baseline: claude-opus-4-6(1M) [`model-compatibility`]. Workload scheduling [`workload-scheduling`]: >3 agents use WorkloadScheduler. Non-blocking retry [`non-blocking-retry`]: CronCreate, not sleep.

### 5. Impact Assessment
Blast radius [`blast-radius`]: LOW(1-5), MEDIUM(6-20), HIGH(21-50), CRITICAL(50+/infra/security). Proportionality [`scope-proportionality`]: fixes must not delete(BLOCK prod), >20 files=WARN. Impact analysis [`impact-analysis`] MUST run before large/critical sdd-apply. >100 files MUST sample [`sandbox-sampling`]. Docs never use sed. Scout [`scout-pattern`]: recon before medium+ implementation; quick/standard/deep.

### 6. Self-Healing
Errors to `error-learning.jsonl` [`error-learning`], deduped 60s; 3+ same=warning. Auto-repair [`auto-repair`]: capture->classify->fix->verify. Circuit breaker: 2 fails=OPEN, 10/hr, 1h cooldown. NEVER: DB migrations, auth, payments, .env, git history. Auto-rollback [`auto-rollback`] on 3x verify fail. Crash recovery [`crash-recovery`]: 5min git stash checkpoints.

### 7. Agent Governance
Audit trail [`agent-identity`], trust 0-3, monotonic attenuation. Least-privilege [`agent-security`]: 6 levels, TTL 120min; blocked: `.env`,`*.key`,`*.pem`,`secrets/*`. KPIs [`agent-kpis`]: quality>90%, efficiency -20% MoM. Per-agent overrides [`agent-customization`]. Sidecars [`agent-sidecars`]. Bus [`agent-communication`] via Valkey(OFF default).

### 8. Prompt Engineering
Prompts: criteria+verification+fallback [`closed-loop-prompts`]. Escalation [`agent-escalation`]: detect stuck(loop/no-progress/error-repeat), escalate with diagnosis; 5-15% rate. Max 3 retries. HALT for multi-service/migration/auth. Templates [`prompt-composition`]. Assumption tracker [`assumption-tracking`]: 3+=WARNING. Responsiveness [`responsiveness`]: no silence >10s. Clarification [`split-and-resume`]: `NEEDS_CLARIFICATION:`, max 2 rounds.

### 9. Context Efficiency
Thresholds [`context-management`]: 50%=concise, 70%=save+reduce, 85%=stop+summary. Cognitive load [`cognitive-load`]: detect degradation. Progressive loading [`context-optimization`]: L1 catalog, L2 skill on-demand, L3 refs rare; max 5 active. Result truncation [`result-management`]: >5K chars. Capability levels [`capability-levels`]: L3 disables context-mgmt, L4 disables clarification/assumption/confidence/blast-radius.

### 10. Security
Credentials in env only [`credential-management`]. Content policy [`content-policy`] BLOCK on prohibited terms. License [`license-policy`]: BLOCK AGPL/SSPL/BSL; ALLOW MIT/BSD/Apache. Semgrep [`security-scanning`] OFF default. Pentesting [`pentesting-readiness`]: 7 test cases. Supply chain [`supply-chain-defense`]: digest pinning. Aguara [`aguara-integration`]: 189 rules, 14 categories.

### 11. Skill Lifecycle
Priority: project>global>auto [`skill-management`]. Search Engram before exec; 3+ fails=suggest rewrite. Auto-generate from complex tasks [`auto-skill-generation`]. Consequence [`consequence-system`]: >=85%(5x)=PROMOTE, <60%=WARN/DEGRADE/DISABLE. Skill archive tracks versions. Dynamic tools [`dynamic-tool-creation`]: mid-task creation, promote if useful.

## Contextual (loaded on trigger)

### 12. Team Governance
Squads [`squad-protocol`]: auto-reconfig on <0.80 success. Estimation [`estimation-calibration`]: medium+ need estimates, 5 anti-bias layers. Self-improvement [`self-improvement-protocol`]: weekly, max 5 auto-changes.

### 13. Infrastructure
Health [`infra-health`]: Docker check on start. Intent [`infra-intent`]: advisory. Executor [`orchestrator-mode`]: subprocess delegation. Performance [`performance-monitoring`]: p50/p95/p99. Singularity [`singularity`]: MAPE-K loop(inactive default).

### 14. Persistence
4-tier resilience [`fault-tolerance`]. Engram prefixes [`engram-organization`]: planning/implementation/docs/agent/sre/architecture/sprint/config/bugfix. Sessions [`session-concurrency`]: isolated tasks, shared Engram. Step files [`step-files`] for long phases. Doc sync [`doc-sync`]. Prompt capture [`user-prompt-capture`].

### 15. Change Safety
Security profiles [`hook-security-profiles`]: minimal/standard/paranoid. Capability snapshot [`capability-protection`] before cleanup. Plan-first [`cognitive-os-changes`] for OS mods. Feature planning [`plan-first`]: plan required for medium+ tasks. Dogfooding [`dogfooding`]: SDD for substantial changes. OS universal [`os-vs-project`]. Component classification [`component-classification`]: CORE vs PACKAGE.

### 16. Library Selection
[`library-selection`]: license, downloads, maintenance, TypeScript, overlap. [`reinvention-prevention`]: check upstream before building.

### 17-19. Modes & Tools
Dry run [`dry-run`]: `DRY_RUN=true`. Private [`private-mode`]: `/private`. Ecosystem [`ecosystem-tools`]: parry, hcom, repomix, tero, e2b, trailofbits. Parry [`parry-integration`]: ML injection scanner. Hcom [`hcom-integration`]: cross-terminal comms. Repomix [`repomix-integration`]: repo context packing. Tero [`tero-integration`]: HTTP chaos testing. E2B [`e2b-integration`]: sandbox code execution. Trail of Bits [`trailofbits-skills`]: 62 security audit skills. Context7 [`context7-auto-trigger`]: library doc lookup.

## Project-Specific
Rules in `{project}/.claude/rules/`, generated by `/cognitive-os-init`.
