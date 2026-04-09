# Cognitive OS Trust Model

> What the system does, what it asks permission for, and what it never does.
> Last updated: 2026-04-09

## For Leaders (Executive Summary)

- The Cognitive OS automates code quality checks, cost tracking, and error recovery so developers ship faster with fewer defects.
- It **never** pushes code to production, modifies databases, or changes authentication without explicit human approval.
- Every automated action is logged. Agent work includes a Trust Score (0-100) that forces the agent to disclose what it is uncertain about.
- If the Trust Score falls below 50, the system automatically blocks the result in production environments.
- A session report summarizes what was done autonomously versus what required human input, including cost spent.

---

## Autonomy Levels

### Level 1: Fully Autonomous

These actions happen without asking. They are protective guardrails, not creative decisions.

| What it does | Why | Reference |
|---|---|---|
| Limits how fast agents can launch | Prevents runaway cost and API flooding | `rate-limiter.sh` |
| Detects and logs errors from tests, builds, and linting | Builds a learning database so the same mistake is not repeated | `error-pipeline.sh`, `error-learning.sh` |
| Checks that acceptance criteria are met before marking work "done" | Prevents agents from claiming completion without evidence | `completion-gate.sh` |
| Scans every file write for leaked secrets (API keys, passwords) | Stops credentials from entering version control | `secret-detector.sh` |
| Enforces content policy (prohibited terms, branding rules) | Prevents policy violations from reaching code | `content-policy.sh` |
| Creates a recoverable git checkpoint every 5 minutes | Ensures uncommitted work survives crashes or power loss | `auto-checkpoint.sh` |
| Detects orphaned work from crashed sessions on startup | Lets the developer recover exactly where they left off | `crash-recovery.sh` |
| Tracks cost per agent, per session, per day | Provides budget visibility without manual effort | `resource-check.sh` |
| Monitors context window usage and warns before capacity is exhausted | Prevents data loss from context compaction | `context-watchdog.sh` |

**Key point:** None of these actions modify your code or make decisions about what to build. They observe, log, and enforce boundaries.

### Level 2: Autonomous with Audit Trail

These actions involve judgment calls. The system acts on its own but logs every decision so a human can review after the fact.

| What it does | Why | Reference |
|---|---|---|
| Selects which AI model to use for each sub-task (cheaper vs. smarter) | Optimizes cost without sacrificing quality where it matters | `dispatch-gate.sh` |
| Estimates the "blast radius" of a change (how many files are affected) | Flags large-scope changes before they happen | `blast-radius.sh` |
| Warns when a code change is disproportionate to the task (e.g., a "bug fix" that deletes files) | Catches scope creep early | `scope-proportionality.sh` |
| Tracks how many assumptions an agent made instead of working from verified facts | Highlights where requirements were unclear | `assumption-tracker.sh` |
| Calculates a Trust Score for every completed task | Quantifies how much evidence backs each result | `trust-score-validator.sh` |
| Suggests skill rewrites when a skill fails repeatedly | Self-healing: the system identifies its own weak points | `consequence-evaluator.sh` |

**Key point:** Every decision in this category is written to a log file (`*.jsonl`) that can be queried, audited, or exported.

### Level 3: Requires Human Approval

The system detects these situations, presents a plan, and **stops**. It does not proceed until a human says "yes."

| Situation | Why it stops | Reference |
|---|---|---|
| Changes that span multiple services | Cross-service changes have cascading risk | HALT protocol (`closed-loop-prompts.md`) |
| Data migrations | Data loss is irreversible | HALT protocol |
| Authentication or security modifications | Security regressions are critical | HALT protocol |
| API contract changes | Breaks downstream consumers | HALT protocol |
| Deleting or overwriting files at scale | Destructive operations need confirmation | HALT protocol |
| Infrastructure configuration changes | Wrong config can cause outages | HALT protocol |
| Retrying a failed automated fix in production | Conservative mode: humans decide recovery strategy | `auto-refine` phase rules |
| Rewriting a skill definition in production | Changing agent behavior in production needs oversight | `skill-rewrite.md` |
| Publishing or pushing to a remote repository | Deployment is a human decision | Git safety rules |

**Key point:** The system shows you exactly what it plans to do, what files it will touch, and what could go wrong. You approve or redirect.

### Level 4: Never Autonomous

These actions are **prohibited** regardless of project phase, configuration, or user instructions. The system will refuse and instruct the human to perform the action themselves.

| What the system will never do | Why |
|---|---|
| Push to remote repositories | Deployment decisions belong to humans |
| Run database migrations | Schema changes are irreversible in production |
| Modify `.env` files or secrets | Credential handling requires human accountability |
| Change authentication or authorization code without HALT | Security-critical paths are never auto-modified |
| Force-push or rewrite git history | Destroys audit trail and teammates' work |
| Delete branches | Irreversible without careful recovery |
| Modify payment or billing code without security review | Financial operations demand human oversight |
| Accept terms, agreements, or licenses | Legal commitments require human judgment |
| Send messages on behalf of the user | Communication is a human responsibility |
| Create accounts or enter passwords | Identity and access are human-controlled |

---

## How to Verify the OS is Working

### Quick Check (30 seconds)

Ask the system: *"What did you do autonomously this session?"*

It must answer with specifics: "Launched 4 agents, blocked 1 for low confidence, spent $0.42, detected 2 assumption warnings." Vague answers like "everything went well" indicate the system is not tracking properly.

### Session Report

At the end of any session, the orchestrator produces a summary covering:
- Decisions made autonomously and decisions that required approval
- Number of agents launched and their trust scores
- Total cost and model usage breakdown
- What was **not** verified (honest about gaps)

### Audit Trail

All actions are logged to machine-readable files in `.cognitive-os/metrics/`:

| Log file | What it contains |
|---|---|
| `trust-scores.jsonl` | Trust Score for every completed task, including uncertainty disclosures |
| `cost-events.jsonl` | Cost per agent launch with model, token count, and estimated USD |
| `error-learning.jsonl` | Every test, build, and lint failure with deduplication |
| `escalation-events.jsonl` | When agents got stuck and how the situation was resolved |
| `assumptions.jsonl` | Every assumption an agent made instead of working from verified facts |

---

## What "Trust Score" Means

The Trust Score is a number from 0 to 100 assigned to every piece of agent work. It is **not** a grade of the code. It is a measure of **how well the agent verified its own work**.

| Score | What it means | What you should do |
|---|---|---|
| 90-100 | Agent ran verification commands, showed evidence, and admitted specific uncertainties | Minimal review needed |
| 70-89 | Agent verified most claims but has gaps in evidence | Spot-check the areas the agent flagged as uncertain |
| 50-69 | Agent has significant uncertainty or incomplete verification | Thorough human review required |
| 0-49 | Agent does not trust its own work | **Automatically blocked in production.** Human must review and decide |

### Why "100% Confident" is a Red Flag

Every Trust Score report requires the agent to list at least one thing it is unsure about. An agent claiming perfect confidence is not being thorough -- it is failing to think critically. The system treats "I am 100% confident" as a warning sign, not a positive indicator.

---

## The Adoption Risk

The biggest risk is not that the OS makes mistakes. Every system makes mistakes. The risk is adopting the OS without understanding what it does and does not protect against.

A leader who sees "Trust Score: 92" and assumes everything is perfect has misunderstood the system. A Trust Score of 92 means the agent provided strong evidence for its work -- but it does not guarantee the business logic is correct, the architecture is optimal, or the feature matches what customers need.

This document exists so that any stakeholder can:

1. Know **exactly** what the OS does without asking
2. Know **exactly** what requires their approval
3. Know **how** to verify the OS is working correctly
4. Know **what** the OS cannot protect against

---

## Deterministic vs Non-Deterministic Guarantees

The Cognitive OS has two layers. Understanding the difference is critical for calibrating trust.

### The Deterministic Layer (Hooks)

Hooks are bash scripts that execute the same way every time. They are safety interlocks — like the ground proximity warning in an aircraft.

| Guarantee | Mechanism | Always the same? |
|---|---|---|
| Secrets never committed to code | Pattern matching (`secret-detector.sh`) | **Yes** — same regex, same result |
| Agent launches stay within rate limits | Counter arithmetic (`rate-limiter.sh`) | **Yes** — math doesn't vary |
| Commits blocked if tests fail | Exit code check (`pre-commit-gate.sh`) | **Yes** — pass or fail |
| Budget blocks over threshold | Arithmetic comparison (`resource-check.sh`) | **Yes** — numbers are numbers |
| Content policy violations blocked | Pattern matching (`content-policy.sh`) | **Yes** — same patterns, same blocks |
| HALT on auth/migration/multi-service keywords | Keyword detection in prompts | **Yes** — keyword is present or not |

**These guarantees are absolute.** They do not depend on the AI model's judgment.

### The Non-Deterministic Layer (LLM Decisions)

The AI model (the "orchestrator") makes judgment calls that can vary between sessions, even with identical inputs.

| Decision | Why it varies |
|---|---|
| How to break a task into sub-tasks | The model may choose different decompositions |
| Which approach to take for implementation | Multiple valid approaches exist; the model picks one |
| When to declare work "done" | Judgment call on completeness |
| How to write acceptance criteria | The model authors them differently each time |
| When to escalate vs. retry | Situational judgment, not a fixed rule |
| Trust Score self-assessment | The model evaluates its own work (inherent conflict of interest) |

**These decisions are not guaranteed to be identical across runs.** The same task, with the same instructions, may produce different (but valid) results.

### How Aviation Solved This

The aviation industry faced the same problem: human pilots are non-deterministic decision-makers operating safety-critical systems.

Aviation did not make pilots deterministic. Instead:
- **Interlocks** prevent catastrophic outcomes regardless of pilot decisions (ground proximity alarm fires at altitude < X, always)
- **Checklists** reduce variability in routine procedures
- **Flight recorders** capture everything that happened for post-hoc audit
- **Two-pilot rule** adds adversarial review to every critical decision

The Cognitive OS follows the same model:
- **Hooks** are the interlocks — deterministic, always enforced
- **Acceptance criteria** are the checklists — reduce but do not eliminate variability
- **JSONL metrics** are the flight recorder — every action is logged
- **Adversarial review** is the copilot — a second evaluation of every significant result

### What This Means for Leaders

The system **does not guarantee** it will make the same decisions twice. It **does guarantee** that certain outcomes (secret leaks, budget overruns, unauthorized deployments) are prevented by deterministic checks that the AI model cannot override.

Trust the interlocks. Audit the judgment calls.

---

## What the OS Cannot Protect Against

Transparency requires honesty about limitations.

- **Business logic correctness.** The OS checks that code compiles, tests pass, and patterns are followed. It does not know whether the feature solves the right problem.
- **Novel security vulnerabilities.** Static analysis (Semgrep, Aguara) catches known vulnerability patterns. It cannot detect zero-day exploits or novel attack vectors.
- **Strategic architecture mistakes.** The OS follows the rules it is given. If the rules encode a bad architecture, the OS will faithfully implement that bad architecture.
- **Vendor lock-in decisions.** The OS executes library selections based on license, downloads, and maintenance health. It does not evaluate long-term business trade-offs of vendor dependency.
- **Team health.** The OS cannot detect if a team is burned out, under-resourced, or working on the wrong priorities.
- **Requirements quality.** If the requirements are wrong, the OS will build the wrong thing correctly. Garbage in, garbage out -- faster.
