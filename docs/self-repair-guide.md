# Self-Repair System — What You'll See

> Cognitive OS monitors every agent that runs and automatically adjusts its own behavior. This guide explains what you'll see in your terminal when the feedback loops are active.

---

## What is Self-Repair?

After each agent completes a task, COS reads its output, extracts a quality score (the **trust score**), and decides whether to reward or penalize that agent type. No configuration needed — it runs automatically in the background via hooks wired into Claude Code.

The system has three feedback loops:

1. **Consequence Engine** — promotes well-performing agents, degrades or disables poor ones
2. **Error Learning** — detects repeating failure patterns and warns future agents
3. **Self-Improvement** — at session end, flags if your overall KPIs dipped and suggests running `/self-improve`

The key thing to understand: self-repair affects **agent behavior** (which model gets used, whether a skill is allowed to launch), never your project code directly.

---

## What You'll See in Your Terminal

### When an agent completes — the Trust Report

Every agent completion produces a trust report on the first line of its output:

```
TRUST_REPORT: SCORE=88 STATUS=MEDIUM EVIDENCE=4 UNCERTAINTIES=1
```

The fields:
- `SCORE` — 0 to 100. Think of it as "how well did the agent back up its claims with evidence?"
- `STATUS` — HIGH (90+), MEDIUM (70-89), LOW (50-69), CRITICAL (<50)
- `EVIDENCE` — how many concrete checks the agent actually ran (tests, builds, greps)
- `UNCERTAINTIES` — how many things the agent admitted it wasn't sure about

A score of 50 when the agent produces no trust report at all is the honest default — "we don't know yet."

---

### When an agent performs well (score ≥ 85, five times in a row)

You'll see:

```
DISPATCH GATE: Slot 2/5 allocated.
MODEL_DIRECTIVE: sonnet
  Model: sonnet (task: implementation, budget: ok)
```

After the 5th consecutive high score for the same skill:

```
CONSEQUENCE: PROMOTE — skill snapshot saved
  Promoted sdd-apply — saving best-version snapshot
```

What this means: COS saved a fingerprint of the skill's current state as its "best known version." If the skill degrades later, COS can recommend reverting to this version.

---

### When an agent performs poorly (score < 60)

**First occurrence — WARN:**

```
TRUST_REPORT: SCORE=42 STATUS=LOW EVIDENCE=1 UNCERTAINTIES=3
---
...
CONSEQUENCE: WARN — skill under observation
  Warning for flaky-parser: Score 42% below 60% threshold
```

The skill still launches normally next time. COS is watching.

**Second consecutive low score — DEGRADE:**

```
TRUST_REPORT: SCORE=38 STATUS=LOW EVIDENCE=1 UNCERTAINTIES=4
---
...
CONSEQUENCE: DEGRADE — model downgraded
  Degraded flaky-parser — downgrade sonnet -> haiku
```

What you'll see on the next launch of this skill:

```
DISPATCH GATE: Skill 'flaky-parser' is DEGRADED — use model 'haiku' (one tier down).
  MODEL_DIRECTIVE: haiku
```

The skill still runs, but on a cheaper/faster model. This is intentional — if quality is low anyway, spending opus tokens on it wastes money.

**Third consecutive low score — DISABLE:**

```
TRUST_REPORT: SCORE=29 STATUS=CRITICAL EVIDENCE=0 UNCERTAINTIES=5
---
...
CONSEQUENCE: DISABLE — skill temporarily disabled
  Disabled flaky-parser after consecutive failures — suggest /optimize-skill rewrite
```

---

### When a disabled skill tries to launch

The next time anything tries to use that skill, the dispatch gate blocks it before it even starts:

```
DISPATCH GATE: Skill 'flaky-parser' is DISABLED by consequence engine.
  Run /optimize-skill flaky-parser to fix it, then re-enable via ConsequenceEngine.re_enable_skill().
```

The agent launch is blocked (exit code 2). Nothing runs. You need to fix the skill first.

---

### When errors repeat on the same service

After 3+ errors of the same type on the same service within 24 hours, the next agent working on that service sees an automatic warning injected before it starts:

```
WARNING: KNOWN ERROR PATTERN: auth-service has had 3 TEST_FAILURE errors in the last 24h.
  Common cause: missing mock configuration
  Recommended: check test fixtures before running tests
```

This appears in the agent's context automatically — you don't have to do anything. The goal is to prevent the agent from repeating the same failed approach.

---

### When an agent fails and the retry loop kicks in

If an agent reports completion but acceptance criteria checks fail, or if build/test failures are detected in its output:

```
=== COMPLETION-GATE: RETRY 1/3 ===
ORCHESTRATOR ACTION REQUIRED: Re-launch the agent with this context:
---
PITER REFINEMENT (attempt 2/3)
Previous attempt failed with TEST_FAILURE:
  FAIL: TestGetEntity (expected 200, got 500)
  FAIL: TestCreateOrder (panic: nil pointer)
Instructions:
1. Analyze WHY the previous attempt failed
2. Fix the root cause (not just symptoms)
3. Re-run verification to confirm the fix
---
=== END COMPLETION-GATE ===
```

On the third failure:

```
=== COMPLETION-GATE: ESCALATION REQUIRED ===
Agent task failed after 3 attempts. Human intervention needed.
Task: implement-user-endpoint
Failure type: TEST_FAILURE
Latest error:
  FAIL: TestGetEntity
  FAIL: TestCreateOrder
=== END ESCALATION ===
```

At this point the agent's failure is sent to the Dead Letter Queue and the circuit breaker records a failure for this task type.

---

### When the circuit breaker trips

If a task type fails repeatedly (2+ consecutive failures), COS opens the circuit breaker for that type:

```
DISPATCH GATE: Circuit breaker OPEN for 'implementation' tasks. Cooldown in effect.
  Too many consecutive failures for this task type. Wait for cooldown or run different task type.
```

Launches are blocked for that task type for 1 hour. Run a different kind of task in the meantime, or use `/repair-status` to see the state.

---

### When budget pressure triggers model downgrade

COS tracks spend against your configured budget. When approaching limits:

```
DISPATCH GATE: Slot 3/5 allocated.
MODEL_DIRECTIVE: haiku
  Model: haiku (budget at 87% — auto-downgrade active)
```

Or more explicitly from the resource governor:

```
MODEL_DIRECTIVE: sonnet (budget at 82% — opus downgraded to sonnet)
```

This happens silently. Agents still run, just on cheaper models.

---

### When slots are full — the dispatch queue

When all agent slots are in use (`max_parallel_agents` from `cognitive-os.yaml`):

```
DISPATCH GATE: Agent launch blocked (5/5 slots in use).
  Agent enqueued — position 2 of 3 in dispatch queue.
  Queue ID: a3f21b-...
  Will launch when a slot frees up. Orchestrator: check queue on next task completion.
```

When a slot frees up (on the next agent completion), you'll see:

```
QUEUE DRAIN: 1 agent ready to dispatch:
  [1] implement-auth-endpoint (model: sonnet, priority: 5)
  → Launch now or run: from lib.queue_drainer import QueueDrainer; QueueDrainer().get_ready_agents()
```

---

### At session end — KPI flag for next session

If your session's quality metrics dropped below thresholds:

```
SELF-IMPROVE RECOMMENDED: KPIs below threshold last session
  first_pass_success_rate: 0.62 (target: 0.70)
  Consider running /self-improve
```

This appears at the start of your *next* session (not the one that generated the bad metrics). It's advisory — you can ignore it.

---

## The Full Feedback Cycle

```
Agent completes a task
        │
        ▼
completion-gate.sh fires (PostToolUse)
        │
        ├── Checks acceptance criteria → PASS/FAIL
        ├── Checks Definition of Done  → PASS/WARN/BLOCK
        └── Detects failures (tests, build, lint)
                │
                ├── No failures → record_completion.py feeds learning pipeline
                │                        │
                │                        ▼
                │                 ConsequenceEngine.evaluate(trust_score)
                │                        │
                │       ┌────────────────┴─────────────────┐
                │       │                                   │
                │   score ≥ 85                         score < 60
                │   (5x in a row)                           │
                │       │                    ┌──────────────┼──────────────┐
                │       ▼                    │              │              │
                │   PROMOTE              1st time       2nd time       3rd time
                │   snapshot                │              │              │
                │   saved                  WARN         DEGRADE        DISABLE
                │                                      model ↓        blocked
                │
                └── Failures → retry loop (max 3 attempts)
                                    │
                              3rd failure
                                    │
                                    ▼
                          Dead Letter Queue + circuit breaker
                                    │
                              circuit open?
                                    │
                                    ▼
                          dispatch-gate blocks that task type
                                    │
                                   1h
                                    │
                                    ▼
                          circuit half-open → 1 test attempt allowed


/optimize-skill {name}
        │
        ▼
ConsequenceEngine.re_enable_skill() → cycle restarts
```

---

## How to Monitor

| What | File | Quick look |
|------|------|------------|
| Trust scores per agent | `.cognitive-os/metrics/trust-scores.jsonl` | `tail -5 .cognitive-os/metrics/trust-scores.jsonl \| jq .` |
| Consequence decisions | `.cognitive-os/metrics/consequence-history.jsonl` | `tail -10 .cognitive-os/metrics/consequence-history.jsonl \| jq .` |
| Error patterns | `.cognitive-os/metrics/error-learning.jsonl` | `cat .cognitive-os/metrics/error-learning.jsonl \| jq -s 'group_by(.service)'` |
| Cost events | `.cognitive-os/metrics/cost-events.jsonl` | `tail -5 .cognitive-os/metrics/cost-events.jsonl \| jq .` |
| Active agents | `.cognitive-os/tasks/active-tasks.json` | `cat .cognitive-os/tasks/active-tasks.json \| jq '.tasks[] \| select(.status=="in_progress")'` |
| KPI history | `.cognitive-os/metrics/kpi-history.jsonl` | `tail -1 .cognitive-os/metrics/kpi-history.jsonl \| jq .` |
| Skill archive | `.cognitive-os/metrics/skill-archive.jsonl` | `cat .cognitive-os/metrics/skill-archive.jsonl \| jq -s 'group_by(.skill_name)'` |
| Dispatch gate log | `.cognitive-os/metrics/dispatch-gate.jsonl` | `tail -20 .cognitive-os/metrics/dispatch-gate.jsonl \| jq .` |
| Langfuse UI | `http://localhost:3100` | Browser — full trace history with scores |

For a formatted dashboard, run `/agent-kpis` inside Claude Code.

---

## How to Intervene

| Situation | What to do |
|-----------|-----------|
| A skill was disabled but you think it's fine | Run `/optimize-skill {name}` — it rewrites the skill based on failure history, then auto-re-enables. Or manually: `python3 -c "from lib.consequence_engine import ConsequenceEngine; ConsequenceEngine().re_enable_skill('{name}')"` |
| A skill was degraded to haiku but needs opus | Override at launch with `model: "opus"` in the agent prompt. The consequence-based downgrade is advisory on launch. |
| Circuit breaker is open but you need to run | Wait the 1-hour cooldown, or check `/repair-status` for the exact state. For emergencies: `python3 -c "from lib.circuit_breaker import CircuitBreaker; CircuitBreaker().reset()"` |
| Too many error pattern warnings | Run `/error-analyzer` to group patterns and get recommendations. |
| Overall quality is declining | Run `/self-improve` — it reads error patterns, skill archive trends, and KPI history and proposes targeted changes. |
| Want the full quality dashboard | Run `/agent-kpis` inside Claude Code. |
| Want to start fresh | Delete `.cognitive-os/metrics/consequence-history.jsonl` (consequence engine resets) and `.cognitive-os/metrics/skill-archive.jsonl` (skill archive resets). |
| Disable self-repair entirely | Remove `hooks/completion-gate.sh` and `hooks/dispatch-gate.sh` from the `PostToolUse` and `PreToolUse` arrays in `.claude/settings.json`. |

---

## FAQ

**Will COS change my project code without asking?**

No. Self-repair affects agent behavior — which model gets used, whether a skill is allowed to run, which error patterns get warned about. It never modifies your project's source files directly. Running `/self-improve` may suggest changes to skills and rules (in `.cognitive-os/`), but those require your approval before applying.

**Can I disable self-repair?**

Yes. Remove `hooks/consequence-evaluator.sh` from `.claude/settings.json` hooks (or remove `hooks/completion-gate.sh` to disable the entire completion pipeline). The rest of COS continues working normally.

**What if a promoted skill starts failing?**

The streak resets immediately on the next low score. A single WARN doesn't undo a promotion — the skill keeps its snapshot — but two more consecutive low scores will degrade it. The system self-corrects in both directions.

**Does DEGRADE mean my tasks will fail?**

No. A degraded skill runs on a cheaper model (e.g., sonnet instead of opus). The task still executes. You'll see lower quality output in some cases, which is expected — that's the signal that the skill needs work.

**Does this cost extra?**

No. DEGRADE actually reduces cost. PROMOTE just saves a file snapshot (a few bytes). The only additional infrastructure cost is Langfuse storage if you have it running, which is minimal.

**Why is the trust score 50 when I don't see a TRUST_REPORT in the output?**

50 is the honest default for "unknown." If an agent doesn't emit a `TRUST_REPORT:` line, the system can't grade it, so it assumes middle-of-the-road quality. This triggers a WARN after one occurrence and a DEGRADE after two consecutive ones — which nudges agents to include trust reports.

**What's a "good" trust score?**

Consistently above 85 is the promotion threshold. 70+ is fine — no automatic action. Below 60 starts the warning/degrade/disable cycle. Most well-written agents land in the 72-88 range.

**The dispatch queue keeps growing. What do I do?**

Increase `max_parallel_agents` in `cognitive-os.yaml` under `resources.compute.max_parallel_agents`. The default is 5. Or run fewer parallel tasks. The queue drains automatically as agents complete.
