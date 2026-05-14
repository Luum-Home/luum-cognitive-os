---
name: ragas-integration
description: 'Configure and use RAGAS for memory quality testing, retrieval evaluation,
  and synthetic test generation for agent scenarios.

  '
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-26
license: MIT
metadata:
  author: luum
  tool: explodinggradients/ragas
  tool-license: Apache-2.0
  tool-ring: ADOPT
  tool-score: 8.3
audience: os-dev
summary_line: Configure and use RAGAS for memory quality testing, retrieval evaluation,
  and…
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bragas[- ]?integration\b
  confidence: 0.95
- pattern: \bintegrat\w*\s+ragas\b
  confidence: 0.85
triggers:
- ragas-integration
- /ragas-integration
- Configure evaluation LLM
- Configure and use RAGAS for memory quality testing, retrieval evaluation, and…
---
<!-- SCOPE: both -->
## Purpose

RAGAS is the core evaluation framework for testing memory quality (engram + cognee), retrieval accuracy, and generating synthetic test scenarios. It provides 40+ metrics and a knowledge-graph-based test generator.

## Invocation

`/ragas-setup` — Initial configuration
`/ragas-eval-memory` — Evaluate engram/cognee retrieval quality
`/ragas-generate-tests` — Generate synthetic test scenarios from skills

## Setup

### Prerequisites
- Python 3.10+
- `pip install ragas`

### Configuration
```python
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

# Configure evaluation LLM
evaluator_llm = LangchainLLMWrapper(ChatAnthropic(model="claude-sonnet-4-5-20250514"))
```

## What to Do

### Step 1: Test Memory Retrieval Quality

Evaluate engram `mem_search` results:
```python
from ragas.metrics import ContextPrecision, ContextRecall, Faithfulness
from ragas import evaluate

dataset = SingleTurnSample(
    user_input="How did we solve the auth bug?",
    response=agent_response,
    retrieved_contexts=engram_results,
    reference="JWT middleware was missing token refresh logic"
)

results = evaluate(dataset, metrics=[
    ContextPrecision(),   # Are retrieved contexts relevant?
    ContextRecall(),      # Did we retrieve all needed context?
    Faithfulness(),       # Is the response grounded in retrieved context?
])
```

### Step 2: Test Cognee Knowledge Graph Quality

Evaluate relationship-aware retrieval:
```python
from ragas.metrics import ContextEntityRecall

# Test that cognee returns the right entities and relationships
dataset = SingleTurnSample(
    user_input="How does auth middleware relate to the API gateway?",
    response=cognee_response,
    retrieved_contexts=cognee_graph_results,
    reference_contexts=expected_relationships
)
```

### Step 3: Generate Synthetic Test Scenarios

Create test data from our skills and rules:
```python
from ragas.testset import TestsetGenerator
from ragas.testset.graph import KnowledgeGraph

# Feed skill files as knowledge sources
generator = TestsetGenerator(llm=evaluator_llm)
testset = generator.generate_with_langchain_docs(
    documents=load_skills("skills/"),  # All 51 skill files
    testset_size=100,
)
# Produces 100 synthetic agent scenarios for regression testing
```

### Step 4: Test Agent Trajectories

Use MultiTurnSample for SDD phase evaluation:
```python
from ragas.metrics import AgentGoalAccuracy, ToolCallAccuracy
from ragas.dataset_schema import MultiTurnSample

sample = MultiTurnSample(
    user_input=[goal_message],
    response=final_output,
    reference_tool_calls=expected_sdd_phases,
)

results = evaluate(sample, metrics=[
    AgentGoalAccuracy(),     # Did the agent achieve the goal?
    ToolCallAccuracy(),      # Were the right tools called in order?
])
```

## Integration with Cognitive OS

| Component | RAGAS Metric | Use Case |
|-----------|-------------|----------|
| Engram memory | ContextPrecision, ContextRecall | Retrieval quality |
| Cognee graph | ContextEntityRecall, Faithfulness | Knowledge graph accuracy |
| SDD phases | ToolCallAccuracy, AgentGoalAccuracy | Trajectory validation |
| Skill prompts | TestsetGenerator | Synthetic test generation |
| Agent output | Faithfulness, AnswerRelevancy | Response quality |

## Rules

- Generate synthetic tests from skills on every skill change
- Memory quality thresholds: Precision > 0.8, Recall > 0.7, Faithfulness > 0.8
- Track cost via CostCallbackHandler — evaluation LLM spend matters
- Use `@experiment` decorator for versioned evaluation runs
- Store evaluation results in engram with topic_key `eval/ragas/{date}`
