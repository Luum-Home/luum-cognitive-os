# Self-Improvement Loop

> How Cognitive OS learns from its own failures and automatically gets better.

> Scope note: this is operational learning through harness evidence and governed primitive updates. See [`docs/architecture/agent-training-harness.md`](architecture/agent-training-harness.md) for the canonical training contract and non-goals.

## The Problem

AI agents tend to do the minimum required, leading to:
- Tasks that pass initial checks but fail deeper verification
- Repeated iterations on the same type of mistake
- The same error patterns recurring across sessions
- No institutional memory about what went wrong and how to prevent it

## The Complete Loop

```
Execution
    |
    v
Verification (auto-refine, dod-gate, verification-before-completion)
    |
    v
Error Capture (error-learning.sh -> error-learning.jsonl)
    |
    v
Auto-Refine (up to 3x retries with refined instructions)
    |
    |--- Success? --> Done
    |
    v (if still fails after 3 retries)
Error Learning (error patterns accumulated)
    |
    v
Session Learning (session-learning.sh -> session-learnings.jsonl)
    |
    v
KPI Snapshot (kpi-trigger.sh -> kpi-history.jsonl)
    |
    |--- Thresholds OK? --> Next session continues normally
    |
    v (thresholds breached)
Self-Improve (/self-improve skill)
    |
    +--> Pattern Detection (analyze error-learning, skill-metrics, session-learnings)
    |
    +--> Improvement Proposals (concrete changes to rules/skills/templates)
    |
    +--> Auto-Apply (safe changes) or Flag for Human Review (risky changes)
    |
    v
Updated Rules / Skills / Templates
    |
    v
Next Execution (better prompts, better acceptance criteria, better patterns)
    |
    v
KPIs Improve
```

## Unified Connector: LearningPipeline

**File**: `lib/learning_pipeline.py`

`LearningPipeline` is the integration layer that connects the five previously-isolated subsystems into a single pass:

1. **`prompt_classifier`** — classifies user intent before persisting prompts
2. **`skill_archive`** — records skill executions with trust scores (feeds evolutionary archive)
3. **`consequence_engine`** — evaluates promote/degrade/disable streaks from skill archive data
4. **`error_classifier`** — classifies errors by type and service
5. **Trigger surfacing** — surfaces `LearningTrigger` signals (error patterns, skill degradation, consequence events) for injection into agent prompts

Before this, each subsystem wrote to separate JSONL files without cross-referencing each other. `LearningPipeline` processes every agent completion through all five in sequence and saves `ErrorCorrelation` records to `metrics/error-skill-correlations.jsonl` to link errors back to the skill that caused them.

---

## Components

### 1. Error Capture Layer

**File**: `hooks/error-learning.sh` (PostToolUse hook)

Captures every test, lint, and build failure automatically. Each error is logged to `metrics/error-learning.jsonl` with:
- Error type (TEST_FAILURE, LINT_ERROR, BUILD_ERROR, COMPILATION_ERROR)
- Service name
- Framework used
- Error message (truncated to 500 chars)
- Fingerprint for deduplication (60s window)

**File**: `hooks/error-pattern-detector.sh` (PreToolUse hook)

Before launching sub-agents, checks for repeated failures (3+ same type in 24h) and injects warnings into context.

### 2. Auto-Refine Layer

**File**: `hooks/auto-refine.sh` + `skills/auto-refine/SKILL.md`

When a task fails verification, auto-refine re-launches the agent with refined instructions (PITER loop). Up to 3 retries. Tracks iteration data in `metrics/auto-refine/`.

### 3. Session Learning Layer

**File**: `hooks/session-learning.sh` (Stop hook)

At session end, summarizes:
- Total errors this session
- Error types and affected services
- Skills executed vs failed
- Auto-refine iterations consumed
- Session success rate

Output: `metrics/session-learnings.jsonl`

### 4. KPI Monitoring Layer

**File**: `hooks/kpi-trigger.sh` (Stop hook)

At session end, calculates KPI snapshot:
- First-pass success rate
- Average iterations
- Architecture compliance
- Error count (24h window)

Checks against thresholds from `cognitive-os.yaml`. If breached, writes `.self-improve-recommended` flag.

Output: `metrics/kpi-history.jsonl`

**File**: `skills/agent-kpis/SKILL.md`

Full KPI dashboard with 5 OKR categories, trend analysis, and alerts.

### 5. Self-Improvement Layer

**File**: `skills/self-improve/SKILL.md`

The closing piece. Analyzes ALL accumulated data across sessions:
- Groups errors by task type, service, acceptance criteria, skill, and model
- Detects recurring patterns
- Generates concrete improvement proposals
- Auto-applies safe changes (template updates, acceptance criteria, model routing)
- Flags risky changes for human review (rule/skill/hook rewrites)
- Saves learnings to Engram for cross-session persistence

### 6. Governance Layer

**File**: `rules/self-improvement-protocol.md`

Controls what can be auto-applied vs requires human approval, how improvements are versioned, how to roll back, and safety guards.

## Data Flow

```
hooks/error-learning.sh ---------> metrics/error-learning.jsonl ----+
hooks/auto-refine.sh ------------> metrics/auto-refine/*.jsonl -----+
hooks/session-learning.sh -------> metrics/session-learnings.jsonl -+--> /self-improve
hooks/kpi-trigger.sh ------------> metrics/kpi-history.jsonl -------+    |
skills/agent-kpis/ --------------> Engram (agent-kpis/latest) -----+    |
                                                                         |
lib/learning_pipeline.py ---------> error-skill-correlations.jsonl --+  |
  (runs on every completion)         (links errors → skill that ran)  |  |
                                                                       |  |
                    +--------------------------------------------------+  |
                    +-----------------------------------------------------+
                    |
                    v
            rules/acceptance-criteria.md (updated)
            rules/model-routing.md (updated)
            templates/*.md (updated)
            hooks/architecture-compliance.sh (updated)
            Engram: cognitive-os/self-improvement/{date}
```

## Configuration

In `cognitive-os.yaml`:

```yaml
self_improvement:
  enabled: true
  auto_apply: false          # require human approval by default
  trigger_threshold:
    first_pass_success: 0.70  # below this -> suggest self-improve
    iteration_count: 3        # tasks needing >3 iterations -> flag
  schedule: session_end       # when to collect learnings
  max_auto_improvements: 5    # cap per self-improve run
```

## Examples of Real Improvements

### Example 1: Rebranding Tasks

**Pattern detected**: Rebranding tasks had 25% first-pass success rate. Agents would start replacing strings without first counting all occurrences.

**Root cause**: No pre-count step in the rebranding template.

**Fix applied**: Added mandatory grep pre-count step to `templates/rebranding-checklist.md`:
```
Before starting ANY replacement:
1. grep -rn "old_name" --include="*.go" --include="*.ts" | wc -l
2. Record the count
3. After replacement, verify count drops to 0
```

**Impact**: First-pass success rate for rebranding improved from 25% to 80%.

### Example 2: Feature Parity / Migration Tasks

**Pattern detected**: Migration tasks consistently missed endpoints. Agents would use partial endpoint lists.

**Root cause**: No exhaustive listing requirement in the migration template.

**Fix applied**: Added exhaustive-prompt requirement:
```
MANDATORY FIRST STEP for migration tasks:
List ALL endpoints/routes/handlers in the source service.
Verify the list is complete by cross-referencing with router configuration.
```

**Impact**: Endpoint coverage in migrations improved from 60% to 95%.

### Example 3: Architecture Compliance

**Pattern detected**: Go service agents used a non-standard framework instead of the project's declared framework.

**Root cause**: Models defaulted to popular Go frameworks without checking project conventions.

**Fix applied**:
1. Created `skills/go-service-patterns/` skill with framework-specific examples
2. Added framework compliance check to `hooks/architecture-compliance.sh`
3. Added contextual trigger: `*.go` files load go-architecture rule

**Impact**: Architecture violations dropped from 40% to 0%.

## Debugging Self-Improvement

### Self-improvement is not detecting patterns
1. Check that `metrics/error-learning.jsonl` is being populated (run a failing test to verify)
2. Check that `hooks/error-learning.sh` is executable and listed in hooks config
3. Verify the metrics directory path matches between hooks and the skill

### Self-improvement proposed a bad change
1. Run `/cognitive-os-test` to identify what broke
2. Revert: `git log --oneline --grep="improve(self-improve)" | head -5` then `git revert {hash}`
3. Add the pattern to `metrics/improvement-blocklist.jsonl`
4. Review the root cause analysis in the self-improvement report

### KPI thresholds are too sensitive / too lenient
1. Adjust in `cognitive-os.yaml` under `self_improvement.trigger_threshold`
2. Reasonable ranges: `first_pass_success: 0.60-0.85`, `iteration_count: 2-5`

### Session learnings are empty
1. Verify `hooks/session-learning.sh` is registered as a Stop hook
2. Check that `COGNITIVE_OS_SESSION_START` env var is set by `session-init.sh`
3. Verify `metrics/session-learnings.jsonl` exists and is writable
