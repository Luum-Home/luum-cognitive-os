<!-- SCOPE: both -->
---
name: deepeval-integration
description: >
  Configure and use DeepEval for LLM unit testing, agent trajectory evaluation,
  and skill/hook quality assurance. Pytest-native with 60+ metrics.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-26
license: MIT
metadata:
  author: luum
  tool: confident-ai/deepeval
  tool-license: Apache-2.0
  tool-ring: ADOPT
  tool-score: 8.08
audience: os-dev
---

## Purpose

DeepEval is the primary evaluation framework for Cognitive OS. It provides pytest-style unit testing for LLM applications with 60+ built-in metrics covering faithfulness, hallucination, tool correctness, and conversational quality.

## Invocation

`/deepeval-setup` — Initial configuration
`/deepeval-test <skill>` — Run eval tests for a specific skill
`/deepeval-red-team` — Run red team evaluation against skills

## Setup

### Prerequisites
- Python 3.10+
- `pip install deepeval`

### Configuration
```bash
# Set your LLM provider for evaluation
export DEEPEVAL_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=<your-key>

# Optional: Confident AI platform for dashboards
# export DEEPEVAL_API_KEY=<your-confident-ai-key>
```

## What to Do

### Step 1: Test Skills with Metrics

Each skill can be tested with appropriate metrics:
```python
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric, HallucinationMetric

def test_sdd_apply_quality():
    test_case = LLMTestCase(
        input="Implement task 1.1: Create auth middleware",
        actual_output=agent_output,
        expected_output="JWT validation middleware",
        retrieval_context=["spec scenarios", "design decisions"]
    )
    assert_test(test_case, [
        AnswerRelevancyMetric(threshold=0.7),
        HallucinationMetric(threshold=0.5),
    ])
```

### Step 2: Test Agent Trajectories (SDD Phases)

Use ConversationalTestCase for multi-step SDD validation:
```python
from deepeval.test_case import ConversationalTestCase

def test_sdd_phase_ordering():
    test_case = ConversationalTestCase(
        turns=[
            {"input": "propose change", "output": proposal},
            {"input": "write spec", "output": spec},
            {"input": "create design", "output": design},
            {"input": "break into tasks", "output": tasks},
            {"input": "implement", "output": code},
            {"input": "verify", "output": report},
        ]
    )
    # Assert trajectory quality
```

### Step 3: Red Team Skills

Test all 51 skills for prompt injection vulnerabilities:
```python
from deepeval.red_teaming import RedTeamer

red_teamer = RedTeamer(model="claude-sonnet-4-5-20250514")
results = red_teamer.scan(
    target_model=skill_under_test,
    attacks=["prompt_injection", "jailbreak", "pii_leakage"]
)
```

### Step 4: Test Hook Decision Logic

Wrap bash hooks in Python for evaluation:
```python
import subprocess

def run_hook(hook_name, stdin_json):
    result = subprocess.run(
        ["bash", f"hooks/{hook_name}"],
        input=stdin_json, capture_output=True, text=True
    )
    return result.stdout, result.returncode

def test_dod_gate_detects_complexity():
    output, rc = run_hook("dod-gate.sh", '{"tool_response": "implemented critical feature"}')
    assert "critical" in output.lower() or rc == 0
```

## Integration with Cognitive OS

| Component | DeepEval Feature | Use Case |
|-----------|-----------------|----------|
| Skills (51) | AnswerRelevancy, Faithfulness | Quality regression per skill |
| Hooks (42) | Custom metrics + subprocess | Decision logic validation |
| SDD Phases | ConversationalTestCase | Phase ordering + quality |
| Engram Memory | ContextPrecision, ContextRecall | Retrieval quality |
| MAPE-K Loop | @observe decorator | Self-healing path tracing |
| Red Teaming | 40+ vulnerability categories | Security scanning |

## Rules

- Run `pytest tests/eval/ --deepeval` for full evaluation suite
- Set quality thresholds per skill category (not global)
- Red team scans MUST run before any skill goes to ADOPT
- Track eval metrics over time — regressions block merges
- Use `--deepeval-cache` for deterministic re-runs in CI
