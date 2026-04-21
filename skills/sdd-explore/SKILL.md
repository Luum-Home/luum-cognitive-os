<!-- SCOPE: both -->
---
name: sdd-explore
command: /sdd-explore
description: Explore and investigate ideas before committing to a change — deep feasibility analysis
trigger: When the orchestrator launches you to think through a feature, investigate the codebase, or clarify requirements
inputs:
  - topic: What to explore (feature idea, technical question, codebase area)
  - scout-report (optional): Scout report from a prior /scout run
  - change-name (optional): SDD change name if part of a pipeline
outputs:
  - exploration: Structured feasibility analysis with approach recommendation
  - risks: Identified risks and open questions
  - recommendation: Proceed/pivot/abandon with reasoning
version: 1.0.0
audience: project
last-updated: 2026-03-28
summary_line: Explore and investigate ideas before committing to a change — deep feasibility…
# ADR-050 per-skill routing: exploration needs frontier reasoning for risk
# analysis and feasibility. Prefer Claude; allow Qwen fallback on Claude
# rate-limit but not on other errors (we want real signal, not a weaker
# model silently taking over).
routing:
  tier: frontier
  need_long_context: true
  providers_preferred: [claude, qwen]
  fallback_on_rate_limit: true
  fallback_on_any_error: false
  budget_max_usd_per_call: 1.50

---

# SDD Explore -- Deep Feasibility Analysis

## Purpose

Explore is the SDD pipeline's first thinking phase. It goes beyond terrain mapping (which `/scout` handles) to perform deep feasibility analysis: Can this be built? How should it be built? What are the risks?

## Relationship to Scout

| Aspect | Scout | Explore |
|--------|-------|---------|
| Purpose | Map terrain (data gathering) | Analyze feasibility (judgment) |
| Output | Structured report with counts and file lists | Feasibility analysis with recommendations |
| Token budget | 2K-10K | 10K-30K |
| Reads full files? | No (headers only) | Yes (selectively, guided by scout report) |
| Makes decisions? | No | Yes (recommends approach) |
| Required for | Medium+ tasks | Large+ tasks or SDD pipeline |
| Persisted | Optional (engram) | Always (engram) |

If a scout report exists, use it as the starting point. If not, perform lightweight discovery yourself before diving into analysis.

## Process

### Step 1: Gather Context

If a scout report was provided:
- Read the scout report for terrain data (file counts, importers, constraints)
- Use scout findings to focus your exploration

If no scout report:
- Run targeted discovery: `find`, `grep`, `tree` on the relevant directories
- Read file headers (first 20-30 lines) of key files to understand structure
- Map the relevant architecture layer (domain, application, infrastructure)

### Step 2: Analyze Feasibility

For the proposed change, evaluate:

1. **Technical feasibility**: Can this be built with the current stack and architecture?
2. **Existing patterns**: What patterns does the codebase already use for similar features?
3. **Dependencies**: What external or internal dependencies are involved?
4. **Constraints**: What architectural, performance, or security constraints apply?
5. **Alternatives**: Are there simpler approaches that achieve the same goal?

### Step 3: Assess Risk

Identify and classify risks:

| Risk Level | Criteria |
|------------|----------|
| LOW | Well-understood change, existing patterns, good test coverage |
| MEDIUM | New pattern needed, or moderate blast radius, or partial test coverage |
| HIGH | Cross-service change, security implications, or no existing patterns |
| CRITICAL | Data migration, auth changes, or payment flow modifications |

### Step 4: Recommend Approach

Based on analysis, recommend one of:

- **PROCEED**: Change is feasible with the proposed approach
- **PROCEED WITH MODIFICATIONS**: Feasible but approach should be adjusted (explain how)
- **PIVOT**: Original approach is not feasible, suggest alternative
- **ABANDON**: Change is not worth the cost/risk (explain why)
- **NEEDS CLARIFICATION**: Cannot assess without more information (list questions)

### Step 5: Persist to Engram

Save the exploration to engram for the pipeline:

```
mem_save(
  title: "SDD Explore: {topic}",
  type: "decision",
  scope: "project",
  topic_key: "planning/{change-name}/explore",
  content: "{exploration report}"
)
```

## Output Format

```
EXPLORATION: {topic}
Change: {change-name}

FEASIBILITY:
  Technical: {feasible|challenging|infeasible} -- {reasoning}
  Patterns: {existing patterns found, or new patterns needed}
  Dependencies: {list of key dependencies}
  Constraints: {architectural and technical constraints}

RISK ASSESSMENT:
  Overall: {LOW|MEDIUM|HIGH|CRITICAL}
  Risks:
    1. [{severity}] {risk description}
    2. [{severity}] {risk description}

APPROACH:
  Recommendation: {PROCEED|PROCEED WITH MODIFICATIONS|PIVOT|ABANDON|NEEDS CLARIFICATION}
  Summary: {1-2 paragraphs describing the recommended approach}
  Key decisions:
    - {decision 1 with rationale}
    - {decision 2 with rationale}

OPEN QUESTIONS:
  - {question that should be resolved before spec phase}

SCOPE ESTIMATE:
  Files affected: ~{N}
  Services: {list}
  Complexity: {trivial|small|medium|large|critical}
  Estimated effort: {min}-{max} hours
```

## Rules

- Do NOT implement anything. Explore is for thinking, not coding.
- Read selectively. Use scout data or targeted searches, not full file reads.
- Be honest about unknowns. "I don't know" is better than a guess.
- Explore alternatives. The first approach is rarely the best.
- Persist findings. Future phases depend on this exploration.
- Stay within token budget (~10K-30K). Report partial results if budget exhausted.

## Integration

- **Input from**: `/scout` report (optional), user request, orchestrator delegation
- **Output to**: `sdd-propose` (uses exploration as context for formal proposal)
- **Engram key**: `planning/{change-name}/explore`
- **Model routing**: sonnet (default) -- exploration needs good reasoning but not opus-level
