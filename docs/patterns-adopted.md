# Patterns Adopted from External Sources

> Catalog of patterns integrated into Cognitive OS from external tools, frameworks, and research.
> Author: luum | Updated: 2026-03-27

## Summary

| Source | Patterns Adopted | Category |
|--------|-----------------|----------|
| SuperClaude | 6 | Prompt engineering, quality gates |
| Sprut Agent Kit | 4 | Memory, routing, persistence |
| ClaudeClaw JS (aravhawk) | 3 | Configuration, error handling |
| QuinotoSpec | 3 | Governance, drift detection |
| Sazonia Archive (TAC) | 5 | Infrastructure, automation |
| Anthropic Engineering | 3 | Evaluation, adversarial review |
| **Total** | **24** | |

---

## From SuperClaude (MIT, 22K stars)

### 1. Confidence Check (Pre-Implementation Assessment)

**What it does**: A 5-dimension readiness assessment that agents run before starting implementation. Evaluates: requirements clarity, technical feasibility, risk awareness, test strategy, and architecture alignment.

**Where it lives**: `skills/confidence-check/SKILL.md`

**How it integrates**: Invoked via `/confidence-check` before medium+ tasks. Produces a confidence score (0-100) and a list of concerns. If score is below 60, the agent should request clarification before proceeding.

**Original pattern**: SuperClaude's `CONFIDENCE` personality trait that forces the model to assess its readiness before acting.

**Our adaptation**: Expanded from a personality trait to a full skill with structured output, 5 scored dimensions, and integration with the clarification gate.

### 2. Deep Research (Multi-Hop Reasoning)

**What it does**: Structured research methodology with configurable depth levels (quick/standard/deep/exhaustive). Each level adds more hops of investigation, source cross-referencing, and synthesis quality.

**Where it lives**: `skills/deep-research/SKILL.md`

**How it integrates**: Invoked via `/deep-research`. Uses `lib/web_crawler.py` (Crawl4AI) for web fetching, Engram for persistence, and produces structured reports with citations and confidence ratings.

**Original pattern**: SuperClaude's `RESEARCH` mode with depth configuration.

**Our adaptation**: Added multi-source synthesis, Engram persistence of findings, structured report format with the DISCOVER/ANALYZE/COMPARE/SYNTHESIZE methodology, and integration with the research-protocol meta-skill.

### 3. Self-Review (4-Question Checklist)

**What it does**: A lightweight post-implementation checklist that agents run on non-SDD work. Four questions: (1) Does it compile/run? (2) Did I test the change? (3) Did I check edge cases? (4) Would I trust this if someone else wrote it?

**Where it lives**: `skills/self-review/SKILL.md`

**How it integrates**: Invoked via `/self-review` or auto-triggered after small/medium task completion. Complements the full adversarial review (which is heavier and used for SDD verify).

**Original pattern**: SuperClaude's self-review checklist in the `COMPLETE` workflow step.

**Our adaptation**: Made it a standalone skill with structured output, integration with trust score reporting, and automatic triggering based on task complexity.

### 4. Implementation Completeness (No-TODO Rule)

**What it does**: Prohibits agents from leaving TODO, FIXME, HACK, or placeholder comments in delivered code. Every change must be complete or explicitly marked as out-of-scope with justification.

**Where it lives**: Enforced within the agent preamble template (`templates/agent-preamble.md`) and the Definition of Done checks.

**How it integrates**: Part of the quality gates chain. The auto-verify hook checks for TODO markers in changed files and flags them as incomplete work.

**Original pattern**: SuperClaude's strict "no placeholders" enforcement.

**Our adaptation**: Integrated into the existing DoD system rather than as a standalone rule. TODOs are acceptable only if accompanied by a tracking issue reference.

### 5. PDCA Mistake Template

**What it does**: Structured error documentation format based on the Plan-Do-Check-Act cycle. When an error occurs, document: what was planned, what actually happened, what the check revealed, and what action was taken.

**Where it lives**: Influences the error-learning JSONL format and the auto-repair system's remediation documentation.

**How it integrates**: The error-learning hook captures errors in a PDCA-compatible structure. The auto-repair dispatcher uses PDCA reasoning when classifying errors and selecting remediations.

**Original pattern**: SuperClaude's mistake tracking template using PDCA methodology.

**Our adaptation**: Merged PDCA structure into the existing error-learning JSONL schema rather than creating a separate tracking system. The PDCA fields map to: planned=task_description, done=error_output, check=error_type_classification, act=remediation_applied.

### 6. Error Signature Matching (Jaccard Similarity)

**What it does**: Normalizes error messages (strips timestamps, paths, line numbers, hex addresses) and computes Jaccard similarity between error signatures to find matching known errors.

**Where it lives**: `lib/error_matching.py`

**How it integrates**: Used by the error-pattern-detector hook and auto-repair dispatcher to identify recurring error patterns. When a new error arrives, it is compared against all known errors using Jaccard similarity. A match above 0.7 triggers the known-fix lookup.

**Original pattern**: SuperClaude's error fingerprinting approach.

**Our adaptation**: Built a full Python module with normalization pipeline (5 regex patterns), Jaccard similarity computation, configurable threshold, and integration with the error-learning JSONL store.

---

## From Sprut Agent Kit (MIT)

### 1. Memory Decay (Time-Based Relevance)

**What it does**: Calculates time-based relevance scores for persistent memories. Older observations naturally lose priority in search results, with different memory types decaying at different rates.

**Where it lives**: `lib/memory_decay.py`

**How it integrates**: Applied to Engram search results before presenting them to agents. Architecture decisions decay slowly (0.3% per day), bugfixes decay fast (2% per day), user preferences barely decay at all (0.1% per day).

**Original pattern**: Sprut's memory relevance decay system for content creator agents.

**Our adaptation**: Customized decay rates for software development context (architecture decisions are more durable than in content creation). Added exponential decay function, pruning threshold, and batch re-ranking of search results.

### 2. Anti-Sycophancy (Prohibit Flattery)

**What it does**: Prevents agents from producing flattering, agreeable responses that confirm the user's assumptions without critical evaluation.

**Where it lives**: Influences the trust score protocol (`rules/trust-score.md`) and the adversarial review protocol (`rules/adversarial-review.md`).

**How it integrates**: The mandatory self-doubt requirement in the Trust Report (agents must list at least one uncertainty) and the zero-findings prohibition in adversarial review both derive from anti-sycophancy. "100% confident" is flagged as a red flag.

**Original pattern**: Sprut's anti-sycophancy rule that prohibited agents from using phrases like "great idea" or "excellent choice."

**Our adaptation**: Instead of prohibiting specific phrases, we require structural evidence of critical thinking (uncertainties in Trust Report, mandatory findings in reviews). This is more robust than phrase-matching.

### 3. Skill Routing Table

**What it does**: Maps tasks to the optimal skill and model combination based on task type, complexity, and cost constraints.

**Where it lives**: `rules/model-routing.md`, `lib/model_router.py`

**How it integrates**: The orchestrator checks the routing table before delegating to sub-agents. Each task type maps to a recommended model (opus for reasoning, sonnet for implementation, haiku for documentation) with cost-aware fallback.

**Original pattern**: Sprut's content-type to agent mapping table.

**Our adaptation**: Expanded from content types to software development task types. Added multi-provider support (Anthropic, OpenAI, Google, DeepSeek, local models), cost estimation, budget-aware routing, and dynamic optimization via `/model-optimizer`.

### 4. Persistent Agent Pattern (Data Directory)

**What it does**: Creates persistent agents that maintain state across sessions through a dedicated data directory with identity profile, event log, and fixation checklist.

**Where it lives**: `skills/persistent-agent/SKILL.md`

**How it integrates**: Invoked via `/create-persistent-agent`. Creates a `data/` directory structure for the agent with identity YAML, event log JSONL, and auto-fixation prevention checklist. State persists via Engram sidecar pattern.

**Original pattern**: Sprut's agent persistence model using a local `data/` directory per agent.

**Our adaptation**: Combined with the Engram sidecar pattern (from BMAD v6) for cross-session persistence. Added auto-fixation checklist (prevents agents from repeating the same failed approach) and event-sourced history.

---

## From ClaudeClaw JS (aravhawk)

### 1. SecretRef (Configuration Secret Resolution)

**What it does**: Resolves secret references in configuration dictionaries. A SecretRef is a dict with `source` and `id` keys that references a value stored in an environment variable, file, or literal.

**Where it lives**: `lib/secret_ref.py`

**How it integrates**: Used by configuration loading code to resolve secrets at runtime without embedding them in config files. Supports three sources: `env` (environment variable), `file` (file path), `literal` (inline value for development). Includes `mask_secrets()` for safe logging.

**Original pattern**: ClaudeClaw's TypeScript `SecretRef` type with `resolveSecretRef()` function.

**Our adaptation**: Ported from TypeScript to Python. Added `resolve_config_secrets()` for recursive resolution in nested dicts, `mask_secrets()` for safe logging, and integration with the credential-management rule.

### 2. Tool Group:Ref Syntax

**What it does**: Structured syntax for referencing tool permissions and capabilities in agent definitions. Allows declaring which tools an agent can use with group-level and individual-level granularity.

**Where it lives**: Influences the agent customization system (`rules/agent-customization.md`) and agent identity protocol (`rules/agent-identity.md`).

**How it integrates**: Agent customization YAML files use `tools_allowed` and `tools_blocked` lists. The permission model follows monotonic attenuation (sub-agents can only have equal or fewer permissions than their parent).

**Original pattern**: ClaudeClaw's `group:ref` syntax for tool permission declarations.

**Our adaptation**: Simplified from the TypeScript type system to YAML-based declarations. Integrated with the agent trust level system (levels 0-3) rather than a separate permission model.

### 3. Structured Error Classifier

**What it does**: Classifies errors into structured categories with severity, domain, and recommended action. Separates error parsing from error handling.

**Where it lives**: `lib/error_classifier.py`

**How it integrates**: Used by the auto-repair dispatcher to classify incoming errors before looking up remediations. Categories include: build, test, lint, runtime, integration, configuration. Severity maps to the adversarial review tier system.

**Original pattern**: ClaudeClaw's error classification middleware in the messaging pipeline.

**Our adaptation**: Adapted from messaging errors to software development errors. Added integration with the error-learning JSONL format and the remediation registry lookup.

---

## From QuinotoSpec

### 1. Contract Drift Detection

**What it does**: Detects when implementation diverges from its specification. Compares the spec's requirements against actual code to find unimplemented features, extra features not in spec, and behavioral mismatches.

**Where it lives**: `tests/behavior/test_contract_drift.py`

**How it integrates**: Part of the SDD verify phase. When `sdd-verify` runs, contract drift detection checks that the implementation matches the spec. Drift findings are classified using adversarial review tiers.

**Original pattern**: QuinotoSpec's contract validation step in sprint planning.

**Our adaptation**: Implemented as a behavioral test rather than a runtime check. Integrated with the SDD pipeline so drift is caught during verification, not after deployment.

### 2. Proposal Conflict Detection

**What it does**: Identifies contradictions between concurrent proposals or between a new proposal and existing architecture decisions. Prevents conflicting changes from being developed in parallel.

**Where it lives**: `tests/behavior/test_proposal_conflicts.py`

**How it integrates**: When `sdd-propose` creates a new proposal, the conflict detector searches Engram for existing proposals and architecture decisions that might conflict. Conflicts are flagged before spec writing begins.

**Original pattern**: QuinotoSpec's proposal validation step that checks for conflicts with existing sprint items.

**Our adaptation**: Extended from sprint-scoped conflict detection to project-wide detection using Engram search. Added severity classification (blocking conflict vs advisory overlap).

### 3. Sprint Contracts (Verification Lines)

**What it does**: Defines verification criteria that must be satisfied before implementation begins. A sprint contract specifies what "done" looks like in measurable terms.

**Where it lives**: Influences the readiness-check skill and the acceptance criteria rule (`rules/acceptance-criteria.md`).

**How it integrates**: The readiness check (run before `sdd-apply`) verifies that specs are complete, designs are reviewed, tasks are broken down, and acceptance criteria are defined. This is the sprint contract -- no implementation without verified readiness.

**Original pattern**: QuinotoSpec's sprint contract with required verification lines.

**Our adaptation**: Merged into the existing readiness-check skill rather than creating a separate contract artifact. Verification lines became acceptance criteria in the SDD spec artifact.

---

## From Sazonia Archive (TAC Course)

### 1. ClaudeExecutor (Programmatic CLI Invocation)

**What it does**: Wraps the Claude CLI (`claude` command) in a Python class for programmatic invocation. Handles stdin/stdout, streaming, error recovery, and session management.

**Where it lives**: `lib/claude_executor.py`

**How it integrates**: Used by the batch runner, issue pipeline, and singularity controller to launch Claude sub-agents programmatically. Supports `agent_id` parameter for Agent Bus integration (heartbeats, progress tracking).

**Original pattern**: TAC course's `ClaudeExecutor` class for automating Claude CLI interactions.

**Our adaptation**: Added Agent Bus integration (heartbeat publishing, progress events), structured result parsing, token usage tracking, and error recovery with exponential backoff.

### 2. Batch Runner

**What it does**: Executes multiple agent tasks in parallel with configurable concurrency, result aggregation, and failure handling.

**Where it lives**: `lib/batch_runner.py`

**How it integrates**: Used for parallel SDD phase execution (e.g., running spec and design concurrently) and for bulk operations (e.g., scanning multiple services). Respects the resource governor's max parallel agents limit.

**Original pattern**: TAC course's batch execution pattern for running multiple Claude instances.

**Our adaptation**: Added integration with resource governance (budget checking before launch), Agent Bus monitoring, configurable concurrency limits, and structured result collection.

### 3. Resume from State

**What it does**: Persists session state (tasks, progress, decisions) to disk so work can resume after session interruption, compaction, or crash.

**Where it lives**: `lib/session_state.py`, `lib/sdd_resume.py`

**How it integrates**: The fault tolerance protocol uses session state for task registration and checkpoint management. The SDD resume module tracks which SDD phases have completed and which need re-running. Both integrate with Engram for cross-session recovery.

**Original pattern**: TAC course's state persistence model using JSON files.

**Our adaptation**: Extended with Engram integration for cross-session persistence, step-file architecture for long-running phases, and automatic recovery detection at session start.

### 4. Notifications

**What it does**: Multi-channel notification system for alerting users about task completion, failures, budget alerts, and other events.

**Where it lives**: `lib/notifications.py`

**How it integrates**: Used by the singularity controller for escalation alerts, by the auto-repair system for fix notifications, and by session-end hooks for summary delivery. Supports Telegram, Slack webhook, and generic HTTP webhook channels.

**Original pattern**: TAC course's notification system for agent completion alerts.

**Our adaptation**: Added multi-channel support (Telegram, Slack, webhook), message formatting per channel, rate limiting, and integration with the singularity controller's escalation policy.

### 5. Issue-to-PR Pipeline

**What it does**: Automated pipeline that reads a GitHub issue, analyzes it, creates a plan, implements the fix or feature, runs tests, and creates a pull request.

**Where it lives**: `lib/issue_pipeline.py`

**How it integrates**: Can be triggered by the singularity controller when new issues are detected, or manually via webhook. Uses the SDD pipeline for complex issues and direct implementation for simple bugs.

**Original pattern**: TAC course's automated issue resolution pipeline.

**Our adaptation**: Added SDD integration for complex issues, automatic complexity classification, test coverage enforcement, and PR description generation with trust score.

---

## From Anthropic Engineering (Harness Design Article)

### 1. Generator-Evaluator Loop

**What it does**: The core feedback loop where a generator agent produces output and an evaluator agent reviews it, with iterative refinement until the evaluator approves or retries are exhausted.

**Where it lives**: The SDD pipeline's `sdd-apply` (generator) and `sdd-verify` (evaluator) cycle, documented in `rules/closed-loop-prompts.md`.

**How it integrates**: After `sdd-apply` produces code, `sdd-verify` reviews it. If verify returns FAIL with CRITICAL issues, apply is re-launched with the failure context. Maximum 3 retries before escalation. DAG state tracks the loop in Engram.

**Original pattern**: Anthropic's generator-evaluator architecture for building reliable AI pipelines.

**Our adaptation**: Implemented as two SDD phases rather than a generic harness. Added DAG state persistence, phase-aware retry limits, auto-rollback on exhaustion, and integration with the adversarial review protocol.

### 2. Sprint Contracts (Verification Before Implementation)

**What it does**: Requires that verification criteria are defined and validated before any implementation begins. This prevents building the wrong thing.

**Where it lives**: The readiness-check skill and the SDD dependency graph (readiness check gate before `sdd-apply`).

**How it integrates**: The SDD pipeline enforces: `proposal -> spec -> design -> tasks -> [READINESS CHECK] -> apply`. The readiness check validates that specs are complete, designs are reviewed, tasks are broken down, and acceptance criteria are defined.

**Original pattern**: Anthropic's sprint contract methodology for engineering teams.

**Our adaptation**: Made the readiness check a formal gate in the SDD pipeline. Integrated with the plan-first protocol and the acceptance criteria rule.

### 3. Skeptical Evaluator (Adversarial Review)

**What it does**: Mandates that every review must produce at least one finding. "Looks good" and "no issues found" are prohibited responses. This prevents rubber-stamping.

**Where it lives**: `rules/adversarial-review.md`

**How it integrates**: Applied to `sdd-verify` output, code reviewer agent runs, and plan evaluation. If a reviewer produces zero findings, the orchestrator halts the review and re-launches with a prompt requiring at least one finding. Findings use the S1-S4 severity tier system.

**Original pattern**: Anthropic's skeptical evaluator concept -- evaluators that are structurally prevented from being too agreeable.

**Our adaptation**: Extended from a concept to a full protocol with severity tiers (BLOCKER, CONCERN, SUGGESTION, QUESTION), structured finding format, review quality criteria, and orchestrator enforcement with retry logic.

---

## Original Cognitive OS Patterns

### 1. Scored Skill Archive (Fitness Tracking)

**What it does**: Maintains a scored history of skill configurations over time. Every skill execution records a snapshot with the SKILL.md content hash, trust score, success/failure, tokens used, and cost. Over many executions, this builds a fitness landscape per skill: best-performing versions are preserved, degrading trends are detected, and underperforming skills are flagged for rewrite.

**Where it lives**: `lib/skill_archive.py`

**How it integrates**: The `SkillArchiveManager` records execution results to `metrics/skill-archive.jsonl`. The `/self-improve` skill consults the archive to identify underperforming skills (success rate < 60%), detect degradation trends, and recommend rollback when the current version scores 20+ points below the best known version.

### 2. Staged Verification (Fail-Fast Pipeline)

**What it does**: Runs verification checks in order from cheapest to most expensive: syntax (free, ~0.1s), lint (free, ~2s), build (free, ~5s), unit tests (free, ~10s), integration tests (free, ~30s), adversarial LLM review (~$0.03, ~60s), cross-model verification (~$0.01, ~30s). Stops at the first failure, saving all subsequent stage costs.

**Where it lives**: `lib/staged_verification.py`

**How it integrates**: Maps directly to the Definition of Done complexity levels: trivial tasks run 2 stages, critical tasks run all 7. The `run_staged_verification()` function accepts changed files and returns a structured report with pass/fail per stage, cost savings from skipped stages, and a formatted verdict.

### 3. Evolutionary Self-Improvement (Archive-Driven Optimization)

**What it does**: Extends the existing self-improvement protocol with data from the skill archive. When `/self-improve` runs, it consults the archive to make evidence-based decisions: skills with success rate below 60% are prioritised for rewrite, degrading trends trigger investigation of recent changes, and the archive enables rollback to a proven version when a skill change causes regression.

**Where it lives**: `rules/self-improvement-protocol.md` (Evolutionary Skill Archive section)

**How it integrates**: Augments the existing self-improvement triggers with archive-derived signals. The archive provides three new self-improvement triggers: (1) underperformance detection, (2) trend degradation, and (3) rollback candidates. These feed into the existing auto-apply vs human-approval workflow.

**Original concept**: Self-modifying agent systems that use execution history to evolve their own prompts, tools, and configurations toward higher performance.

**Our adaptation**: Scoped to skill-level evolution rather than full agent self-modification. Constrained by the existing safety guards (max 5 auto-improvements, test gate, blocklist, cooldown). The archive creates a verifiable record of what worked and what did not, turning skill improvement from guesswork into data-driven optimization.
