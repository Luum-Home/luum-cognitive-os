---
adr: 16
title: Context Diet -- Token Optimization Strategy
status: accepted
implementation_status: partial
date: '2026-03-31'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-016: Context Diet -- Token Optimization Strategy

**Date:** 2026-03-31
**Status:** Accepted
**Commits:** 8e30af5, 3d6c0d7
**Engram IDs:** 2031, 2034

## Context

Each sub-agent launch loaded approximately 100,000 tokens of context: 20K system prompt, 5K CLAUDE.md, 73K rules, plus the task itself. At Opus 4.6 pricing, this cost $1.50-$7.50 per agent just for context loading, before any work was done. The WISC paper (arxiv 2507.11538) confirmed that loading more than 150 instructions degrades performance. Cognitive OS was loading 94 rules, well within degradation range. Most sub-agents needed only 2-4 rules relevant to their specific task.

## Decision

Implement a 3-level agent efficiency strategy:

**Level 1 -- Model Routing** (5x cost reduction):
- Route sub-agents to the cheapest capable model: Sonnet for implementation, Opus for architecture/debug, Haiku for formatting/renaming.
- Enforce via explicit `model: select_model(task)` in every agent launch.

**Level 2 -- Context Diet** (20x context reduction):
- Switch to `efficiency.profile: lean` in `cognitive-os.yaml`, which strips all rules except RULES-COMPACT.md.
- Set `model_capability.level: 4` to auto-disable 5 redundant hooks (clarification-gate, assumption-tracking, confidence-gate, model-routing, blast-radius) that are unnecessary for Opus 4.6.
- Implementation in `lib/context_diet.py` with functions: `estimate_rules_tokens`, `get_minimal_rules`, `format_diet_report`.
- Result: 73K tokens reduced to ~2K tokens per agent (97% reduction).

**Level 3 -- Prompt Cache Manager** (78.5% input cost reduction):
- Reuse cached prompt prefixes across agent launches to avoid re-tokenizing identical system prompts.

Combined target: 10-20x per-agent cost reduction, 5-8x session throughput increase.

## Alternatives Considered

- **Keep full context, use cheaper models**: Cheaper per-token but the volume of wasted tokens remains. Sonnet reading 73K irrelevant tokens is still slower and costlier than Sonnet reading 2K relevant tokens.
- **Dynamic per-task rule selection**: Analyze each task and load only matching rules. Partially implemented via the contextual rule loader, but the overhead of selection logic approaches the cost of just loading a small compact ruleset.
- **Compress rules into a single dense document**: RULES-COMPACT already exists as this compressed form. The diet strategy is the enforcement of using it exclusively for sub-agents.

## Consequences

- The lean efficiency profile became the recommended default for sub-agent launches.
- The orchestrator's CLAUDE.md was updated with mandatory model routing rules (Sonnet default, Opus for complex tasks, Haiku for trivial work).
- 42 unit tests were created for the context diet library.
- The preamble template was compressed from 7176 to 3027 characters (58% reduction) as part of the diet effort.
- Combined with the SDD fast path (ADR-014), Opus-driven workflows became both faster (fewer phases) and cheaper (less context per phase).
