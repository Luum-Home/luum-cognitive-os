---
name: agent-stress-test
description: "Stress-test agent cognitive health to detect context-induced degradation"
triggers: ["/agent-stress-test", "/stress-test", "/cognitive-stress"]
audience: os-dev
version: 1.0.0
---

# /agent-stress-test

> Diagnostic skill that stress-tests agent quality to find the degradation point.


## Instructions

Run a structured stress test that measures agent quality across four phases of increasing cognitive load. Uses `lib/cognitive_load_monitor.py` to track degradation in real time.

### Background

The WISC framework (arxiv 2507.11538) found that >150 instructions degrade LLM performance. Cognitive OS loads ~88 rules (~73K tokens). This skill empirically measures where YOUR agent starts degrading in the current session.

### Prerequisites

- `lib/cognitive_load_monitor.py` must be importable
- Session should be relatively fresh (< 30% context used) for accurate baseline

### Protocol

Execute the four phases sequentially. For each task, measure:

1. **Preamble compliance**: Did the agent include PROGRESS markers, FILES_CREATED/FILES_MODIFIED, structured result summary?
2. **Instruction following**: Did the agent do exactly what was asked, no more, no less?
3. **Hallucination check**: Run `lib/ground_truth.py` claim validation on the output
4. **Output proportionality**: Is the response length reasonable for the task complexity?
5. **Tool call success**: Did all tool calls succeed?

### Phase 1: Baseline (3 tasks)

Simple, well-defined tasks to establish quality baseline.

**Task 1** (trivial): Read a single file and report its line count.
- Expected: exact line count, correct file path, no extra analysis.

**Task 2** (trivial): Check if a specific function exists in a specific file.
- Expected: yes/no answer with the function signature. No refactoring suggestions.

**Task 3** (small): Create a simple Python function that reverses a string, with a docstring.
- Expected: function code, docstring, no over-engineering.

Record each result as a `CognitiveSnapshot` in the monitor.

### Phase 2: Load (5 tasks)

Progressively increase complexity while context accumulates.

**Task 4** (small): Fix a specific lint issue in a file (provide the file and line).
**Task 5** (medium): Write a unit test for an existing function (specify which).
**Task 6** (medium): Refactor a function to extract a helper (specify the function).
**Task 7** (medium): Add error handling to an existing endpoint.
**Task 8** (large): Implement a new use case following clean architecture patterns.

Record each result. Watch for quality drops starting at task 6-8.

### Phase 3: Saturation (3 tasks)

Complex tasks at high context usage. This is where degradation typically appears.

**Task 9** (large): Multi-file refactor affecting 3+ files with tests.
**Task 10** (large): Debug a simulated integration issue across services.
**Task 11** (critical): Design and implement a new feature with acceptance criteria.

Record each result. Expect noticeable quality drops here.

### Phase 4: Recovery (2 tasks)

Return to simple tasks. Measures whether quality recovers or is permanently degraded.

**Task 12** (trivial): Read a file and count lines (same as task 1).
**Task 13** (trivial): Check function existence (same as task 2).

Compare results with Phase 1 baseline.

### Measurement Protocol

After each task, record a snapshot:

```python
from lib.cognitive_load_monitor import CognitiveLoadMonitor

monitor = CognitiveLoadMonitor()

# After each task:
snap = monitor.record_snapshot(
    tool_call_number=current_tool_call,
    output_length=len(agent_response),
    task_complexity="medium",  # match the task
    preamble_compliance=0.9,  # score 0-1
    hallucination_count=0,  # from ground_truth check
    instruction_following=0.95,  # score 0-1
    tool_call_success=1.0,  # score 0-1
)
```

### Output Format

After all phases complete, generate the report:

```
AGENT STRESS TEST RESULTS
=========================

Phase 1 - Baseline (3 tasks):
  Average quality: XX/100
  Preamble compliance: XX%
  Hallucination rate: X%
  Context usage at end: ~X%

Phase 2 - Load (5 tasks):
  Average quality: XX/100 (+/-N from baseline)
  Preamble compliance: XX% (note any drop point)
  Hallucination rate: X%
  Context usage at end: ~X%

Phase 3 - Saturation (3 tasks):
  Average quality: XX/100 (+/-N from baseline)
  Preamble compliance: XX% (note any drop point)
  Hallucination rate: X%
  Context usage at end: ~X%
  [ALERT if degradation detected] Degradation point: task N (context ~X%)

Phase 4 - Recovery (2 tasks):
  Average quality: XX/100 (vs baseline)
  Recovery: full / partial / none

FULL HEALTH REPORT:
[output from monitor.format_health_report()]

DIAGNOSIS: [summary of where degradation starts]
RECOMMENDATION: [actionable advice based on findings]
```

### Post-Test Actions

1. Save metrics: `monitor.save_metrics()`
2. Save findings to Engram:
   ```
   mem_save(
     title="Stress test results: degradation at ~X% context",
     type="discovery",
     topic_key="architecture/cognitive-degradation",
     content="..."
   )
   ```
3. If degradation detected before 50% context, recommend reviewing loaded rules count.

### Interpreting Results

| Degradation Point | Interpretation | Action |
|---|---|---|
| No degradation | Agent handles full load well | Current config is optimal |
| >70% context | Normal degradation | Current context-management thresholds are correct |
| 50-70% context | Early degradation | Reduce loaded rules, increase progressive loading |
| <50% context | Severe degradation | Audit rule count, enforce strict context budget |

### Limitations

- Results vary by model (Opus vs Sonnet vs Haiku)
- Results vary by session state (fresh vs mid-work)
- Task selection affects measurements
- This is a diagnostic tool, not a production gate
