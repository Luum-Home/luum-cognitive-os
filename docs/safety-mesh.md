# Safety Mesh

> The layered defense system that prevents agent errors from propagating through the Cognitive OS pipeline.
> Author: luum | Updated: 2026-03-28 | Layers: 12
>
> See also: [docs/security-stack.md](security-stack.md) for the complete security posture including external tools, MCP security, supply chain defense, and red team capabilities.

## Motivation

A major cloud provider launched an AI coding tool that generated code without adequate safety checks. The tool occasionally produced code with security vulnerabilities, overwrote working implementations with broken ones, and expanded small fixes into large rewrites. The root cause was a single-layer quality gate: if the final check passed, everything shipped, regardless of intermediate problems.

The lesson: a single quality gate is a single point of failure. Safety must be a mesh -- multiple independent layers that catch different failure modes at different stages of the pipeline.

## The 12-Layer Safety Mesh

The Cognitive OS safety mesh consists of 12 layers arranged in a specific order. Each layer catches a distinct failure mode that other layers cannot detect.

| Layer | Hook | Type | Stage | What It Prevents | Exit Code |
|-------|------|------|-------|------------------|-----------|
| 1 | `clarification-gate.sh` | PreToolUse | Before launch | Vague, ambiguous tasks that agents interpret minimally | 2 (BLOCK) if score > 60 |
| 2 | `blast-radius.sh` | PreToolUse | Before launch | Launching large-scope tasks without awareness of impact | 0 (WARN only) |
| 3 | `dry-run-preview.sh` | PreToolUse | Before launch | Unintended execution when previewing pipelines | 2 (BLOCK) when DRY_RUN=true |
| 4 | `rate-limiter.sh` | PreToolUse | Before ALL tools | Token flooding and excessive tool/agent/write calls | 2 (BLOCK) when limits exceeded |
| 5 | `scope-proportionality.sh` | PostToolUse | After completion | Small fix expanding into large rewrite (scope creep) | 2 (BLOCK) if disproportionate |
| 6 | `claim-validator.sh` | PostToolUse | After completion | Fabricated files, hallucinated test results | 2 (BLOCK) in production if hallucination detected |
| 7 | `assumption-tracker.sh` | PostToolUse | After completion | Hidden assumptions that may be incorrect | 0 (WARN if 3+ assumptions) |
| 8 | `trust-score-validator.sh` | PostToolUse | After completion | Missing or incomplete Trust Reports | 0 (LOG only) |
| 9 | `confidence-gate.sh` | PostToolUse | After completion | Low-confidence results propagating downstream | 2 (BLOCK) in production if score < 50 |
| 10 | `clarification-interceptor.sh` | PostToolUse | After completion | Mid-task ambiguity causing incorrect assumptions | 0 (LOG + orchestrator signal) |
| 11 | `auto-rollback-trigger.sh` | PostToolUse | After retry exhaustion | Broken code accumulating after failed fix attempts | 2 (BLOCK) + revert |
| 12 | `lib/cross_verifier.py` | Library | On demand | Second model catches first model's hallucinations | N/A (library call) |

## Layer Details

### Layer 1: Clarification Gate (Pre-Launch Block)

**Purpose**: Prevents agents from launching with prompts so vague that the agent will interpret them minimally and produce incomplete results.

**How it works**: Scores prompt ambiguity on a 0-100 scale using 7 signals (no file paths, scope without counts, missing tech, action without targets, unanswered questions, short prompt, no criteria). Score > 60 blocks the launch.

**What it catches**: "Add auth to the project" (no files, no tech, no criteria = score 60+). Without this gate, the agent would pick the easiest interpretation and deliver a minimal result.

**What it does NOT catch**: A well-worded prompt that asks for the wrong thing. Clarity of expression does not guarantee correctness of intent.

**Configuration**: `hooks/clarification-gate.sh`, always active on Agent PreToolUse.

### Layer 2: Blast Radius Estimation (Pre-Launch Warning)

**Purpose**: Makes the orchestrator and user aware of the scope of what they are about to launch. High blast radius tasks need sampling, review, and careful monitoring.

**How it works**: Counts file references, directory references, cross-service keywords, and bulk operation keywords. Detects infrastructure and security keywords for automatic CRITICAL escalation.

**What it catches**: "Migrate all 47 endpoints" (score 47+, cross-service = HIGH). Ensures the user knows this is a large operation before committing resources.

**What it does NOT catch**: Tasks that are individually small but collectively large (e.g., 50 small file edits triggered by a loop). The hook analyzes the prompt, not the execution.

**Configuration**: `hooks/blast-radius.sh`, always active, advisory only (exit 0).

### Layer 3: Dry-Run Preview (Pre-Launch Block)

**Purpose**: Allows users to preview what agents would do without actually executing them. Essential for validating SDD pipelines and understanding task scope.

**How it works**: When `DRY_RUN=true` is set, intercepts all Agent/task/delegate tool calls, outputs what would execute, and blocks with exit code 2.

**What it catches**: Unintended execution when the user wants to preview a pipeline. Prevents resource consumption and side effects during planning.

**What it does NOT catch**: Nothing in normal operation (it is only active when explicitly enabled).

**Configuration**: `hooks/dry-run-preview.sh`, active only when `DRY_RUN=true`.

### Layer 4: Rate Limiter (Pre-Tool Block)

**Purpose**: Prevents token flooding, excessive agent spawning, rapid file writes, and cost overruns by enforcing per-minute and per-hour limits on all tool invocations.

**How it works**: Tracks timestamps of every tool call in a persistent state file. Before each tool call, checks if the count within the rolling window exceeds the configured limit. Limits: 30 tool calls/min, 20 agent launches/hr, 15 bash commands/min, 10 file writes/min, $5/hr cost cap.

**What it catches**: A runaway loop that spawns 50 agents in rapid succession. A tool-loop that issues bash commands faster than a human could review. Cost overruns from model-expensive operations.

**What it does NOT catch**: Slow, sustained overuse that stays within per-window limits. A single very expensive operation that costs less than the hourly cap. This is a rate limiter, not a budget governor (the resource-governance rule handles total budget).

**Configuration**: `hooks/rate-limiter.sh`, PreToolUse on Bash, Agent, Edit, Write. Library: `lib/rate_limiter.py`.

### Layer 5: Scope Proportionality (Post-Completion Block)

**Purpose**: Prevents a small fix request from expanding into a large rewrite. Agents sometimes interpret "fix this bug" as "rewrite the entire module."

**How it works**: Compares the scope of the original request against the scope of what was actually changed. If the ratio is disproportionate (e.g., 1-file fix request resulted in 15-file rewrite), blocks and escalates.

**What it catches**: An agent asked to fix a typo that rewrites the entire error handling system. The scope expansion is caught before the changes are accepted.

**What it does NOT catch**: Proportionate but incorrect changes (agent rewrites the right amount of code but introduces bugs). That is caught by layers 6-7.

**Configuration**: `hooks/scope-proportionality.sh`, PostToolUse on Agent.

### Layer 6: Assumption Tracker (Post-Completion Warning)

**Purpose**: Creates visibility into where agents made assumptions instead of working from verified requirements. High assumption counts indicate the output may contain incorrect guesses.

**How it works**: Scans agent output for assumption language patterns (HIGH: "I assume", "presumably"; MEDIUM: "I think", "probably"). Warns when 3+ assumptions are detected.

**What it catches**: An agent that says "I assume the database is PostgreSQL" -- this assumption may be wrong and the implementation based on it may need revision.

**What it does NOT catch**: Assumptions that the agent does not verbalize. An agent may silently assume something without using assumption language. This is a limitation of text-based detection.

**Configuration**: `hooks/assumption-tracker.sh`, PostToolUse on Agent.

### Layer 7: Trust Score Validator (Post-Completion Log)

**Purpose**: Ensures every agent completion includes a Trust Report with score, evidence, uncertainties, and verification steps. Without this, there is no way to assess agent confidence.

**How it works**: Extracts the Trust Report from agent output, validates its structure (score present, evidence listed, uncertainties acknowledged), and logs the score to metrics.

**What it catches**: Agent completions that claim "done" without providing evidence. The validator ensures there is always a self-assessment attached.

**What it does NOT catch**: Inflated trust scores. An agent may give itself 95/100 without adequate justification. The confidence gate (layer 7) handles threshold enforcement.

**Configuration**: `hooks/trust-score-validator.sh`, PostToolUse on Agent, advisory only.

### Layer 8: Confidence Gate (Post-Completion Block)

**Purpose**: Prevents low-confidence results from propagating downstream. In production/maintenance phases, a trust score below 50 blocks the result.

**How it works**: Extracts the trust score from the Trust Report and compares against thresholds. Phase-aware: warns in reconstruction/stabilization, blocks in production/maintenance.

**What it catches**: An agent that reports score 35/100 -- this result requires human review before being accepted. In production, it is blocked entirely.

**What it does NOT catch**: High-confidence but incorrect results. An overconfident agent (score 90 but wrong) passes the gate. The adversarial review and acceptance criteria catch this case.

**Configuration**: `hooks/confidence-gate.sh`, PostToolUse on Agent.

### Layer 9: Clarification Interceptor (Post-Completion Signal)

**Purpose**: Detects when an agent encounters ambiguity mid-task and signals the orchestrator to resolve it before the agent proceeds with assumptions.

**How it works**: Scans agent output for the `NEEDS_CLARIFICATION:` marker. When found, signals the orchestrator to search Engram for answers or ask the user. Maximum 2 clarification rounds per task.

**What it catches**: An agent working on a database integration that discovers it does not know which database engine to use. Instead of guessing, it asks.

**What it does NOT catch**: Ambiguity the agent does not recognize. If the agent does not realize something is ambiguous, it will not ask for clarification.

**Configuration**: `hooks/clarification-interceptor.sh`, PostToolUse on Agent.

### Layer 10: Auto-Rollback Trigger (Post-Retry-Exhaustion Block)

**Purpose**: When the SDD verify-apply loop exhausts all retries (default 3), automatically reverts the failed changes to restore the codebase to a known-good state.

**How it works**: Detects the "Verify-apply loop exceeded 3 retries" pattern in agent output. Creates a rollback branch, reverts commits from the failed apply, verifies the rollback builds cleanly.

**What it catches**: A failed implementation that could not be fixed after 3 automated attempts. Without rollback, broken code accumulates in the working tree.

**What it does NOT catch**: Failures that happen outside the SDD pipeline (direct edits, manual commits). The rollback only applies to SDD-tracked changes.

**Configuration**: `hooks/auto-rollback-trigger.sh`, PostToolUse on Agent. Phase-aware: auto-executes in reconstruction/stabilization, requires approval in production/maintenance.

## Execution Order

### Pre-Launch (before agent starts)

```
Agent tool call received
    |
    v
[1] clarification-gate.sh -- Is the prompt clear enough?
    |                          Score > 60: BLOCK
    v
[2] blast-radius.sh -- How big is this task?
    |                   HIGH/CRITICAL: WARN
    v
[3] dry-run-preview.sh -- Is DRY_RUN=true?
    |                      If yes: BLOCK (preview only)
    v
[4] rate-limiter.sh -- Within rate limits?
    |                   Exceeded: BLOCK + cooldown
    v
Agent launches
```

### Post-Completion (after agent finishes)

```
Agent completes
    |
    v
[5] scope-proportionality.sh -- Did it stay in scope?
    |                            Disproportionate: BLOCK
    v
[6] assumption-tracker.sh -- How many assumptions?
    |                         3+: WARN
    v
[7] trust-score-validator.sh -- Is there a Trust Report?
    |                            Missing: LOG warning
    v
[8] confidence-gate.sh -- Is confidence high enough?
    |                      Score < 50 in prod: BLOCK
    v
[9] clarification-interceptor.sh -- Does it need clarification?
    |                                NEEDS_CLARIFICATION: signal orchestrator
    v
[10] auto-rollback-trigger.sh -- Did retries exhaust?
     |                            3 retries failed: ROLLBACK
     v
Result accepted or escalated
```

## Defense-in-Depth Properties

The mesh has three critical properties:

### 1. Independence

Each layer catches a different failure mode. Removing any single layer leaves a gap that the other layers cannot fill. For example:
- Removing layer 1 (clarification gate) means vague prompts reach agents unchecked
- Removing layer 7 (confidence gate) means low-confidence results propagate in production
- Removing layer 9 (auto-rollback) means failed code accumulates

### 2. Graceful Degradation

Not every layer blocks. The mesh uses a spectrum:
- **BLOCK**: Hard stop, cannot proceed (layers 1, 3, 4, 7, 9)
- **WARN**: Advisory, agent proceeds but user is informed (layers 2, 5)
- **LOG**: Silent recording for trend analysis (layers 6, 8)

This prevents the mesh from being too restrictive while still catching critical issues.

### 3. Phase Awareness

Layer behavior adapts to the project phase:
- **Reconstruction**: Most layers warn rather than block (building fast)
- **Production**: Most layers block rather than warn (protecting stability)

This allows the same mesh to serve different development contexts without configuration changes.

## Metrics

All mesh activations are logged to their respective JSONL files in `.cognitive-os/metrics/`:

| Layer | Metrics File |
|-------|-------------|
| Clarification Gate | `clarification-events.jsonl` |
| Blast Radius | `blast-radius.jsonl` |
| Dry-Run | `dry-run.jsonl` |
| Assumption Tracker | `assumptions.jsonl` |
| Trust Score | `trust-scores.jsonl` |
| Confidence Gate | `confidence-gates.jsonl` |
| Auto-Rollback | `auto-rollback.jsonl` |
| Claim Validator | `hallucinations.jsonl` |
| Rate Limiter | `rate-limit-state.json` (state) |

Aggregate mesh effectiveness can be analyzed by comparing pre-mesh error rates against post-mesh error rates in `error-learning.jsonl`.

## Self-Pentest Verification

The safety mesh can be validated using `/pentest-self`, which actively probes each layer:

| Category | What It Tests |
|----------|---------------|
| Prompt Injection | Injected override instructions, admin mode claims, Base64 payloads |
| Permission Escalation | Readonly writes, path boundary violations, child > parent escalation |
| Secret Exfiltration | .env access, credential grep, secrets directory, env var exposure |
| Token Flooding | Rapid tool calls, agent spawn flooding, file write bursts, cost cap |
| Scope Escalation | Typo-to-rewrite, README-to-source, read-only-to-execute mismatches |
| Data Integrity | Metrics corruption, config tampering, hook deletion, settings overwrite |

Run `/pentest-self` periodically (weekly, after safety mesh changes, before production transitions) to verify no regressions. Reports are saved to `.cognitive-os/metrics/pentest-reports/`.

## Adding a New Layer

To add a new safety layer:

1. Create the hook in `hooks/{hook-name}.sh`
2. Register it in `settings.local.json` (PreToolUse or PostToolUse on Agent)
3. Define its metrics file in `.cognitive-os/metrics/`
4. Document it in this file with: purpose, mechanism, what it catches, what it does not catch
5. Add it to `rules/RULES-COMPACT.md`
6. Verify it does not conflict with existing layers (test with `/cognitive-os-test`)
7. Add pentest tests in `/pentest-self` skill for the new layer
