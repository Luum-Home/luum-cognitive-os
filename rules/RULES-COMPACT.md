<!-- SCOPE: both -->
<!-- TIER: 0 -->
# COS Rules Index

> Compressed index. Full rules loaded on trigger via `[ref-key]`. Hook-enforced rules excluded (see `hooks/self-install.sh:EXCLUDED_RULES`).

## Always Active

### 1. Adaptive Workflow
Classify complexity BEFORE workflow [`adaptive-bypass`]. Trivial(<3 files): direct. Small(1-3): delegate if needed. Medium+: plan/SDD. Phase modifies bypass: reconstruction=speed, production=governance. 5 DoD levels [`definition-of-done`] [`phase-aware-agents`]. Readiness gate before `sdd-apply` on large+.

### 2. Quality Gates
Prompts MUST have `ACCEPTANCE CRITERIA:` with verifiable commands [`acceptance-criteria`]. Agents do minimum — fix: criteria, auto-verify, `/exhaustive-prompt` [`agent-quality`]. Clarification gate hook-enforced [`clarification-gate`]. Reviews MUST produce findings [`adversarial-review`] [`agent-audit-before-commit`]. No sycophancy, no TODO/stubs. Broken windows [`broken-window-policy`]. [`prompt-quality`] [`anti-hallucination`] [`assumption-tracking`] [`scope-creep-detection`].

### 3. Verification
Trust Report mandatory: evidence(40%)+criteria(30%)+self-awareness(20%)+proportionality(10%) [`trust-score`]. 1+ uncertainty required. Confidence gate hook-enforced [`confidence-gate`]. Staged: SYNTAX→LINT→BUILD→UNIT→INTEGRATION→ADVERSARIAL, stop on first fail.

### 4. Cost Governance
[`token-economy`] + [`language-token-economy`]: transparency, worthiness, decomposition, memory-first, optimize-by-default; preserve user language while compacting internal artifacts. >$1→decompose <$0.50 [`decomposition`]. [`model-routing`]: opus=propose/design, sonnet=impl/verify, haiku=archive. [`model-directive`]: MUST follow; MODEL_DISABLED blocks. Queue [`queue-drain`]+[`queue-advisor`]. [`resource-governance`]: >80%=sonnet, >95%=haiku, >100%=BLOCK. Rate limits: [`rate-limiting`] [`rate-limit-protection`]. [`non-blocking-retry`]: CronCreate. [`retry-contract`]: ADR-228 retry taxonomy and attempt limits. [`cost-prediction`] [`workload-scheduling`]. Cost estimates grounded in project history via `/cost-predict` (`scripts/cost_predict.py` + `lib/cost_predictor.py`) [`cost-predictor`]. [`llm-dispatch`] (ADR-049): `scripts/orchestrator.py` + `lib/dispatch.py` default `--providers qwen,claude` (Qwen primary preserves Claude Max). Kill-switches: `COS_DISABLE_LLM_FALLBACK=1`, `COS_FORCE_CLAUDE_PRIMARY=1`. Skill model hints (opus/sonnet/haiku) mapped to Qwen bundle. Metrics→`llm-dispatch.jsonl`.

### 5. Impact Assessment
Blast radius hook-enforced [`blast-radius`]. Scope proportionality hook-enforced [`scope-proportionality`]. Decision depth gate [`decision-depth-gate`] prevents shallow fixes when blast radius is high. Impact analysis [`impact-analysis`] MUST run before large/critical sdd-apply. >100 files sample [`sandbox-sampling`]. Scout [`scout-pattern`]: recon before medium+.

### 6. Self-Healing
Errors to `error-learning.jsonl` [`error-learning`], deduped 60s; 3+ same=warning. Auto-rollback hook-enforced [`auto-rollback`]. [`crash-recovery`] [`auto-repair`].

### 7. Agent Governance
Audit trail hook-enforced [`agent-identity`]. [`agent-security`]: TTL 120min; blocks `.env`,`*.key`,secrets. [`agent-kpis`]: quality>90%, efficiency -20% MoM. [`agent-customization`] overrides. [`agent-sidecars`]. [`agent-communication`] Valkey(OFF). Harness-agnostic event capture [ADR-033]: canonical schema in `lib/harness_adapter/`; CC adapter preserves legacy `agent-heartbeat.jsonl`, new harnesses add one adapter file.

### 8. Prompt Engineering
[`closed-loop-prompts`]: criteria+verification+fallback. [`agent-escalation`]: stuck→diagnose; 5-15% rate, max 3 retries. HALT for multi-service/migration/auth. [`prompt-composition`] templates. [`responsiveness`]: no silence >10s, `run_in_background` for >5s cmds, 10-15 agents/sprint. [`split-and-resume`]: `NEEDS_CLARIFICATION:`, max 2 rounds. [`orchestrator-prompt-compose`] (ADR-032): pipe draft through `scripts/compose_agent_prompt.py` before Agent call when task touches settings.json/lib/*.py/packages/efficiency-profile.

### 9. Context Efficiency
[`context-management`]: 50%=concise, 70%=save+reduce, 85%=stop+summary. [`context-optimization`]: L1 catalog, L2 on-demand, L3 rare; max 5 active. Result truncation hook-enforced: >5K chars [`result-management`] [`response-compression`]. [`agent-output-reading`]: `<result>` first, then Engram — NEVER Read JSONL. [`capability-levels`]: L3 disables context-mgmt, L4 disables clarification/confidence/blast-radius. [`cognitive-load`].

### 10. Security
Credentials in env only [`credential-management`]. cosd remote API requires explicit `--allow-remote` plus bearer-token auth [`cosd-secure-api`]. Content policy + confidentiality hook-enforced [`content-policy`] [`confidentiality-protection`]. AI-provider invented emails/trailers blocked [`ai-provider-identity`]. License [`license-policy`]: BLOCK AGPL/SSPL/BSL; ALLOW MIT/BSD/Apache. Supply chain [`supply-chain-defense`]: digest pinning. Aguara [`aguara-integration`]: 189 rules. [`security-scanning`] [`pentesting-readiness`] [`audit-trail`].

### 11. Skill Lifecycle
Priority: project>global>auto [`skill-management`]. [`skill-rewrite`]+[`auto-skill-generation`] hooks active. Consequence hook-enforced [`consequence-system`]. Dynamic tools [`dynamic-tool-creation`]: mid-task creation, promote if useful. Task DAG [`task-dag`]: dependency graph for multi-agent workflows. High-confidence skill suggestions are mandatory or require audited bypass [`skill-invocation-mandatory`]. [`doc-sync`] [`user-prompt-capture`] [`routing-pattern-authoring`].

### 12. Research & Decision Protocols
Score task risk on 4 dimensions (AC clarity, blast radius, reversibility, decision count) before launching agents. Score 5-8 → research-first 3-phase cycle: Phase 0 read-only agent → Phase 1 operator triage → Phase 2 implementation. Reports land at `docs/06-Daily/reports/<topic>-YYYY-MM-DD.md` (git-tracked). Operator decisions persisted via `lib/decision_tracker.record_decision()` to Engram under `decision/<topic>`. Template: `templates/agent-research-only.md`. [`research-first-protocol`] [`recommendation-grounding`]: P1/P2/P3 priority tables in research reports MUST cite an operator signal (explicit ask, prior decision, or recorded preference) before assigning priority — ungrounded recommendations are flagged for operator triage, not auto-actioned.

### 13. Naming Conventions
[`python-naming`]: Python scripts in `scripts/`, `lib/`, `packages/*/lib/` MUST use snake_case (underscores). Hyphens break pytest collection and require `importlib` hacks. Enforced by `tests/audit/test_python_naming.py`. [`bash-naming`]: Bash scripts in `scripts/`, `hooks/`, `packages/*/hooks/`, `packages/*/scripts/` MUST use kebab-case filenames; functions inside MUST use snake_case. Enforced by `tests/audit/test_bash_naming.py`.

### 14. Language Quality Gates (CI-enforced)
Polyglot drift caught in PRs (ADR-066). Three tiers:
- **Python** (live): snake_case via `rules/python-naming.md` + `tests/audit/test_python_naming.py`
- **Go** (local-first): `gofmt -l` (no unformatted files) + `go vet ./...` (no issues); the former GitHub workflow is preserved as `.github/workflows/go-quality.yml.disabled` while ADR-131 local CI is authoritative — covers root module, `cmd/cos`, `cmd/cos-test`; existing gofmt debt on HEAD is pre-existing
- **Bash** (future): `shellcheck` enforcement — tracked as follow-up; current state: advisory only via `scripts/lint-shell.sh --new-only`

### 15. Test Lane Taxonomy
Lane registry at `.cognitive-os/test-lanes.yaml` is single source of truth (read by Go+Python; bash receives scalars per ADR-066). Auto-marker injection in `tests/conftest.py` (additive, idempotent). Escalation ladder via `cos-test focused/cluster/broad`. New test dirs MUST register a lane with written parallel-safety reason. [`lane-taxonomy`] — see ADR-072.

### 16. Session-Close Documentation-Truth Discipline
Every documentation contradiction discovered during a session MUST terminate in (a) pointwise fix + claim added to `manifests/documentation-truth-claims.yaml`, OR (b) explicit debt entry in the pending-truth ledger — never as a comment/bullet alone. Enforced at `/session-wrapup` Step 2b (sub-step 6), at `cos-adr-close` lifecycle transitions, and via the control-plane `documentation_truth` audit. Criterion for what goes in documentation-truth (volatile facts only: coverage, harnesses, gaps, authority, reports, ADR status, manifest-derived lists) at [`session-close-doc-truth`] — see ADR-277 + ADR-275.

## Contextual (loaded on trigger)

**Team**: [`squad-protocol`] auto-reconfig <0.80. [`estimation-calibration`] medium+. [`self-improvement-protocol`] weekly, max 5 changes. SO self-build maturity tracked via `/dogfood-score` (`scripts/dogfood_score.py` + `lib/dogfood_scorer.py`; ADR-059 §KPI ledger) [`dogfood-score`].

**Infra**: [`infra-health`] Docker check. [`singularity`] MAPE-K(inactive). [`performance-monitoring`] p50/p95/p99. [`observability`] MLflow. [`so-slo`] ADR-028 SLO catalogue + error budget + cadence. [`infra-intent`] [`model-compatibility`].

**Persistence**: [`fault-tolerance`] 4-tier. [`engram-organization`] prefixes. [`engram-api-safety`] sandbox mutating API probes. [`session-concurrency`]. [`step-files`] long phases. [`memory-governance`] typed memory policies (ADR-261).

**Change Safety**: [`hook-security-profiles`] minimal/standard/paranoid. [`capability-protection`] snapshot before cleanup. [`clean-room-detection-limits`] AST-similarity tier-2 detection boundary (ADR-271). [`plan-first`] [`cognitive-os-changes`] plan-first for OS mods. [`dogfooding`] SDD for substantial changes. [`eas-evidence-artifact`] executable acceptance evidence for SDD changes. [`component-classification`] CORE vs PACKAGE. REAL/DORMANT/ASPIRATIONAL classification via `/component-reality-check` (`scripts/aspirational_audit.py`) [`component-reality-check`]. [`cross-harness-authoring`] (os-only) 5-item self-check before touching SO paths/settings/scripts — see `docs/04-Concepts/architecture/cross-harness-authoring.md` §Agent Self-Check. [`stash-mutation-reversibility`] ADR-117 and [`stash-quarantine`] require named stash ops, apply-by-name (no positional `pop`), JSONL audit, bounded budget, and conflict-safe restoration.

**Modes & Tools**: [`dry-run`] `DRY_RUN=true`. [`private-mode`] `/private`. [`ecosystem-tools`] [`library-selection`] [`reinvention-prevention`]. [`parry-integration`] [`e2b-integration`] [`tero-integration`] [`repomix-integration`] [`trailofbits-skills`] [`hcom-integration`] [`context7-auto-trigger`].

**Pre-Dev**: [`startup-protocol`] [`ROADMAP`] [`pre-dev-readiness-gate`] [`pre-commit-gate`]. Audit: git-context-capture + session-changelog. [`orchestrator-mode`] [`os-vs-project`].

## Project-Specific
Rules in `{project}/.claude/rules/`, generated by `/cognitive-os-init`.
