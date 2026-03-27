# Skill Auto-Optimization — Research and Proposal

> Based on [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) and [Claude's Skill Creator](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills)

---

## 1. Karpathy's Autoresearch — What It Is

A framework where an AI agent runs experiments autonomously:

```
Infinite loop:
  1. Modify train.py (a single variable: the code)
  2. Run training (fixed 5 min)
  3. Measure result (val_bpb — a single metric)
  4. If improved → commit (git)
  5. If not improved → git reset
  6. Repeat without asking permission
```

**Key principles**:
- **A single editable file** (train.py)
- **A single metric** (val_bpb — lower is better)
- **Fixed budget** (5 min per experiment)
- **Full autonomy** — the agent doesn't ask, it just iterates
- **Git as history** — each improvement is a commit, each failure is a reset
- **results.tsv** — log of all experiments with results

In 2 days it ran ~700 experiments and found ~20 real improvements.

---

## 2. Claude's Skill Creator — What It Proposes

A framework for testing, measuring, and refining Claude Code skills:

### Eval/measure/refine loop:

```
1. TEST: Define test cases (prompt + files + success criteria)
2. MEASURE: Run benchmark with metrics:
   - Eval pass rate (% of tests that pass)
   - Elapsed time (how long it takes)
   - Token consumption (how many tokens it uses)
3. REFINE: Modify the skill based on results
4. COMPARE: A/B test between previous and new version
5. Repeat
```

**Key principles**:
- **Isolated parallel agents** — each test runs in its own context
- **Blind comparator** — evaluates outputs without knowing which version produced them
- **Description optimization** — improves the skill description for more precise triggering
- **Evolution**: from skills as "detailed instructions" to "specifications of what to do"

---

## 3. Synthesis: Skill Auto-Optimization

### Concept

Apply the "Karpathy Loop" to Claude Code skills:

```
Loop:
  1. Run skill against test cases
  2. Measure: pass rate, tokens, time, quality
  3. Modify the SKILL.md (the skill's "train.py")
  4. If improved → commit
  5. If not → revert
  6. Repeat
```

### Proposed Architecture

```
.claude/
├── skills/
│   └── {skill-name}/
│       ├── SKILL.md              # The skill (editable file — like train.py)
│       ├── evals/                # Test cases (like prepare.py — fixed)
│       │   ├── test-001.md       # Input + expected behavior
│       │   ├── test-002.md
│       │   └── ...
│       └── results/              # History (like results.tsv)
│           └── benchmark.tsv     # date | version | pass_rate | tokens | time | score
│
├── skill-optimizer/              # The "autoresearch" for skills
│   ├── SKILL.md                  # Optimizer instructions
│   ├── program.md                # Loop config (like Karpathy's program.md)
│   └── optimizer-log.md          # Log of changes and results
```

### Test Case Format (eval)

```markdown
# evals/test-001.md
---
name: health-check-all-services-running
description: Verify that /check-health reports all services correctly
setup: docker-compose up -d  # pre-condition
---

## Input
/check-health

## Expected Behavior
- [ ] Lists all services from docker-compose.yml and cognitive-os.yaml
- [ ] Shows OK/FAIL status for each service
- [ ] Suggests corrective actions for FAIL services
- [ ] Verifies infrastructure containers (databases, caches, message brokers)
- [ ] Does not exceed 10 tool calls

## Scoring
- pass_rate: all checkmarks
- max_tokens: 5000
- max_time: 30s
- quality: output is a well-formatted table
```

### results.tsv Format

```tsv
timestamp	skill	version	test	pass_rate	tokens	time_ms	score	notes
2026-03-20T10:00:00	check-health	v1	test-001	0.80	3200	15000	0.75	missing RabbitMQ check
2026-03-20T10:05:00	check-health	v2	test-001	1.00	2800	12000	0.95	added RabbitMQ check
```

### Metrics to Track

| Metric | Description | Weight |
|--------|-------------|--------|
| `pass_rate` | % of eval criteria that pass | 40% |
| `token_efficiency` | Tokens used vs. max allowed | 20% |
| `time_efficiency` | Time vs. max allowed | 15% |
| `output_quality` | Format, clarity, completeness | 15% |
| `tool_calls` | Number of tool calls (fewer = better) | 10% |

**Composite score** = weighted average normalized to [0, 1]

### The skill-optimizer (equivalent to Karpathy's program.md)

```markdown
# Skill Optimizer Instructions

## Mission
Iteratively optimize a Claude Code skill, measuring improvements
with predefined evals.

## Constraints
- ONLY edit the target skill's SKILL.md
- DO NOT modify evals (they are the ground truth)
- DO NOT modify other skills
- Each iteration is a separate commit

## Loop
1. Read current SKILL.md
2. Read all evals/test-*.md
3. Execute the skill against each eval (in isolated context)
4. Measure pass_rate, tokens, time
5. Calculate composite score
6. If score > previous_best_score:
   - Commit with message: "skill({name}): v{N} score={score}"
   - Update benchmark.tsv
7. If score <= previous_best_score:
   - Revert changes
   - Note in optimizer-log.md what was attempted and failed
8. Analyze failure patterns
9. Propose next modification
10. Repeat from 1

## Optimization Strategies (in order)
1. Clarify ambiguous instructions
2. Add concrete examples
3. Remove unnecessary steps
4. Reorder steps for efficiency
5. Improve description for triggering
6. Reduce verbosity without losing precision
```

---

## 4. Practical Implementation

### Phase 1: Manual (now)
- Write evals for each existing skill
- Run manually and record results
- Refine skills based on observations

### Phase 2: Semi-automated (next)
- Create the `/optimize-skill` skill that:
  1. Receives the skill name
  2. Runs the evals
  3. Suggests improvements
  4. The user approves or rejects
- Use `/loop` to run it every X minutes

### Phase 3: Autonomous (future)
- The optimizer runs without intervention
- Uses git branches to isolate experiments
- Automatically compares A vs B
- Only commits validated improvements
- Generates daily optimization reports

### Example: Optimizing /check-health

```bash
# Phase 2: Semi-automated
claude "/optimize-skill check-health"

# Phase 3: Autonomous (future)
claude "/loop 10m /optimize-skill check-health"
```

---

## 5. Key Differences from Autoresearch

| Aspect | autoresearch | skill-optimizer |
|--------|-------------|-----------------|
| Editable file | train.py (Python code) | SKILL.md (Markdown prompt) |
| Metric | val_bpb (single, numeric) | Composite score (multi-dimensional) |
| Execution | 5 min GPU training | 10-30s skill execution |
| Evaluation | Automatic (number) | Semi-automatic (qualitative criteria) |
| Iterations/hour | ~12 | ~60-120 |
| Risk | Low (only changes one file) | Low (only changes one SKILL.md) |

---

## 6. Next Steps

1. **Write evals** for the 4 existing skills (start-stack, start-service, check-health, add-mock-provider)
2. **Create the `/optimize-skill` skill** that executes the loop
3. **Run baseline benchmark** with the current skills
4. **Iterate** and measure improvements
