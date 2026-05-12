---
adr: 15
title: Rules-to-Hooks Migration -- From Context to Enforcement
status: accepted
implementation_status: partial
date: '2026-04-10'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-015: Rules-to-Hooks Migration -- From Context to Enforcement

**Date:** 2026-04-10
**Status:** Accepted
**Commits:** 93b56f2, 1ee19a4, 8dc4a6e, 7b13d25, 5739bd4
**Engram IDs:** 2946, 2968, 3220

## Context

Cognitive OS loaded ~94 rules as markdown files into the agent's context window, consuming approximately 73,000 tokens per session. The WISC framework research (arxiv 2507.11538) confirmed that loading more than 150 instructions degrades LLM performance. Rules are passive documents -- they rely on the agent remembering and following them. If the context window compacts or the agent is distracted, rules can be forgotten. Meanwhile, hooks enforce behavior automatically with zero token cost because they run as external processes.

## Decision

Migrate rules from passive context documents to active enforcement mechanisms using a 3-tier architecture:

- **Tier 1: Hooks** (~50 rules converted to hooks). Enforcement runs automatically, costs 0 tokens. Examples: rate limiting, content policy, secret detection, registration checks.
- **Tier 2: Skills** (~20 rules converted to on-demand skills). Loaded only when invoked, not kept in persistent context. Examples: release procedures, evaluation workflows.
- **Tier 3: RULES-COMPACT** (~10-15 irreducible rules, target ~500 tokens). Behavioral contracts that cannot be mechanically enforced -- they require the agent to internalize guidelines. Examples: commit message style, communication tone.

**EXCLUDED_RULES mechanism**: `self-install.sh` maintains an array of ~22 rules that are fully mechanically enforced by registered hooks. These rules are excluded from symlink installation, removing them from agent context entirely. The symlink loop skips excluded rules and auto-removes stale symlinks.

**Result**: Context reduced from 92 loaded rules to 20 (78% reduction). RULES-COMPACT trimmed from 73K tokens to under 1.5K tokens (5,494 characters, ~1,374 tokens).

## Alternatives Considered

- **Keep all rules in context but compress them**: Shorter rules still consume tokens and still rely on agent memory. Rejected because the fundamental problem is passive vs active enforcement.
- **Remove rules entirely, rely only on hooks**: Not all behavioral guidelines can be mechanically enforced. Tone, style, and decision-making principles require agent internalization.
- **Dynamic rule loading based on task**: Load only relevant rules per task. Partially adopted (the contextual rule loader exists), but the primary strategy is eliminating the need for rules where hooks can enforce instead.

## Consequences

- Per-agent context cost dropped from ~$1.50-$7.50 to ~$0.15-$0.75 (10x reduction at Opus pricing).
- Agent throughput increased because less context means faster processing.
- The EXCLUDED_RULES array in self-install.sh became a maintenance point -- adding a new hook requires updating the exclusion list.
- Rules that were converted to hooks gained deterministic enforcement: they cannot be forgotten, skipped, or interpreted differently by the agent.
- RULES-COMPACT with "(enforced by hook)" annotations serves as documentation of what the hook system guarantees, even though agents no longer need to act on those rules.
