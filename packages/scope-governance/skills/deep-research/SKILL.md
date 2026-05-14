---
name: deep-research
description: 'Multi-hop research skill for deep investigation of topics. Executes
  structured research with configurable depth levels (quick/standard/deep/exhaustive),
  multi-hop reasoning chains, confidence self-assessment, and Engram persistence.

  '
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-27
license: MIT
metadata:
  author: luum
audience: project
effort: opus
summary_line: Multi-hop research skill for deep investigation of topics.
platforms:
- claude-code
prerequisites: []
triggers:
- deep-research
- /deep-research
- 'Research Report: {topic}'
- Multi-hop research skill for deep investigation of topics
---
<!-- SCOPE: both -->
## Purpose

Conduct structured, multi-hop research on any topic with configurable depth.
Produces a comprehensive research report with citations, confidence scores,
and cross-referenced findings. Results are persisted to Engram for future
reference.

## Invocation

`/deep-research <topic> [--depth quick|standard|deep|exhaustive]`

Default depth: `standard`

## What to Do

### Step 1: Define Research Question and Scope

Parse the user's topic and any flags:

```
Input: /deep-research "React Server Components" --depth deep
  -> topic: "React Server Components"
  -> depth: deep
```

Formulate 1-3 precise research questions from the topic:

```
Primary:   "What are React Server Components and how do they work?"
Secondary: "What are the trade-offs and limitations?"
Tertiary:  "How do they compare to existing patterns?"
```

State the scope boundaries explicitly:
- What IS in scope (the topic and closely related concepts)
- What is NOT in scope (tangential topics, unrelated frameworks)

### Step 2: Choose Depth Level and Plan Sources

| Depth | Sources | Analysis | Hop Chains | Time Budget |
|-------|---------|----------|------------|-------------|
| quick | 1-2 | Surface scan, key facts only | 1 chain, 2 hops max | ~2 min |
| standard | 3-5 | Moderate analysis, pros/cons | 2 chains, 3 hops max | ~5 min |
| deep | 5-10 | Cross-reference, verify claims | 3 chains, 4 hops max | ~10 min |
| exhaustive | 10+ | Systematic review, full synthesis | 4+ chains, unlimited hops | ~20 min |

Plan the source strategy:

1. Use **WebSearch** to find relevant sources (documentation, articles, discussions)
2. Use **WebFetch** to retrieve and analyze specific pages
3. Use **Read** to examine local project files when the topic relates to the codebase

For each depth level, plan the number and type of searches before starting.

### Step 3: Execute Multi-Hop Reasoning

Multi-hop reasoning follows linked questions where each answer opens new questions.
Use one or more of these hop types based on the research questions:

#### Hop Type A: Entity Expansion

Follow the chain of related entities outward:

```
Hop 1: "What is X?"
  -> Answer: X is a {concept} created by {entity}
Hop 2: "Who/what is {entity}?"
  -> Answer: {entity} is known for {related work}
Hop 3: "What else did {entity} create that relates to X?"
  -> Answer: {entity} also created Y and Z, which share {pattern}
```

Use when: researching a technology, library, or concept with known creators/maintainers.

#### Hop Type B: Temporal Progression

Follow the evolution of a concept through time:

```
Hop 1: "When was X introduced and why?"
  -> Answer: X was introduced in {year} to solve {problem}
Hop 2: "What came before X? What did X replace?"
  -> Answer: Before X, the standard was {predecessor}, which had {limitations}
Hop 3: "What is the current state of X? Has anything superseded it?"
  -> Answer: X is currently {status}, with {successor} emerging as {alternative}
```

Use when: understanding the history and trajectory of a technology or practice.

#### Hop Type C: Conceptual Deepening

Drill down from surface understanding to internals:

```
Hop 1: "What is X at a high level?"
  -> Answer: X is {surface description}
Hop 2: "How does X work internally?"
  -> Answer: X uses {mechanism} involving {components}
Hop 3: "What are the limitations of X's approach?"
  -> Answer: Because X relies on {mechanism}, it cannot {limitation}
Hop 4: "What alternatives address those limitations?"
  -> Answer: {alternative} solves {limitation} by {approach}
```

Use when: evaluating a technology for adoption or understanding failure modes.

#### Hop Type D: Causal Chains

Trace cause and effect to find root causes and preventions:

```
Hop 1: "Why does X happen?"
  -> Answer: X happens because of {cause}
Hop 2: "What causes {cause}?"
  -> Answer: {cause} is triggered by {deeper cause}
Hop 3: "How can {deeper cause} be prevented?"
  -> Answer: Prevent by {action}, which requires {prerequisite}
```

Use when: investigating errors, performance issues, or design decisions.

#### Execution Protocol

For each hop:
1. Formulate the question based on previous hop's answer
2. Search for the answer using WebSearch or WebFetch
3. Record the source URL and key finding
4. Assess whether another hop adds value (diminishing returns check)
5. Stop the chain when: answer is definitive, sources disagree (note the disagreement), or depth budget is exhausted

Track all hops in a structured log:

```
Chain 1 (Conceptual Deepening):
  Hop 1: "What are RSC?" -> [source1] React Server Components allow...
  Hop 2: "How do RSC work internally?" -> [source2] RSC use a streaming protocol...
  Hop 3: "What are RSC limitations?" -> [source3] RSC cannot use client-side state...
```

### Step 4: Self-Assess Confidence

After completing all hop chains, calculate a confidence score:

| Factor | Weight | Scoring |
|--------|--------|---------|
| Source agreement | 40% | 100 = all sources agree, 50 = mixed, 0 = contradictory |
| Source quality | 30% | 100 = official docs/papers, 50 = reputable blogs, 0 = forums/comments |
| Coverage completeness | 20% | 100 = all questions answered, 50 = partial, 0 = mostly unanswered |
| Recency | 10% | 100 = current year, 75 = last year, 50 = 2-3 years, 25 = older |

**Composite confidence = weighted sum of all factors**

Decision logic:
- **Confidence >= 80%**: Proceed to report generation
- **Confidence 60-79%**: Proceed but flag low-confidence areas explicitly
- **Confidence < 60%**: REPLAN — choose a different hop type or search strategy, then re-execute one more round. If still < 60% after replan, proceed with explicit low-confidence warnings.

### Step 5: Generate Structured Report

Produce the research report in this format:

```markdown
# Research Report: {topic}

## Meta
- **Depth**: {quick|standard|deep|exhaustive}
- **Confidence**: {score}/100
- **Sources consulted**: {count}
- **Hop chains executed**: {count}
- **Date**: {ISO date}

## Executive Summary
{2-3 sentence summary of key findings}

## Key Findings

### Finding 1: {title}
{description with evidence}
**Source**: {url or reference}
**Confidence**: {high|medium|low}

### Finding 2: {title}
...

## Analysis

### What We Know (High Confidence)
- {fact supported by multiple sources}

### What We Think (Medium Confidence)
- {conclusion with some supporting evidence}

### What We Don't Know (Low Confidence / Gaps)
- {unanswered questions or contradictory information}

## Hop Chain Log
{structured log from Step 3}

## Sources
1. {url} — {brief description of what was learned}
2. ...

## Recommendations
- {actionable recommendation based on findings}
```

### Step 6: Persist to Engram

Save the research report to Engram:

```
mem_save(
  title: "Research: {topic} ({depth})",
  topic_key: "docs/03-PoCs/research/{topic-slug}",
  type: "discovery",
  scope: "project",
  content: "{full research report}"
)
```

Where `{topic-slug}` is the topic converted to kebab-case, truncated to 50 characters.

### Step 7: Return Result

Return the structured envelope:

```yaml
status: success|partial|failed
executive_summary: "{2-3 sentence summary}"
artifacts:
  - type: research-report
    location: "Engram: docs/03-PoCs/research/{topic-slug}"
next_recommended:
  - "Review findings and validate against project context"
  - "If adopting a technology: run /recommend-library for license check"
risks:
  - "{any low-confidence findings that could mislead decisions}"
```

## Rules

- NEVER fabricate sources or citations — only reference URLs actually visited
- NEVER claim high confidence when sources disagree — flag disagreements explicitly
- If a search returns no useful results, try rephrasing before giving up
- Each hop MUST add new information — stop chains that produce redundant answers
- The replan step (confidence < 60%) happens AT MOST once — do not loop endlessly
- For `quick` depth, skip the formal hop chain structure — do a direct search and summarize
- For `exhaustive` depth, use ALL four hop types and cross-reference findings across chains
- Local file reads (Read tool) are preferred when the topic relates to the current codebase
- WebSearch and WebFetch are the primary tools for external research — do NOT reference any MCP-specific search tools
- Return a structured envelope with: `status`, `executive_summary`, `artifacts`, `next_recommended`, and `risks`
