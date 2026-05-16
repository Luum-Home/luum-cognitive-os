---
name: product-answer
description: Use when the user asks a Cognitive OS product/commercial question such
  as differentiator, moat, wedge, ICP, pricing, competitors, pitch, positioning, or
  what claims are safe. Always prefer the cached ADR-282 product answer cards before
  reading broad docs.
version: 1.0.0
user-invocable: true
audience: os-dev
tags:
- product
- commercial
- evidence
- positioning
- token-efficiency
summary_line: Answer whether COS helps developers and teams, and answer COS product/commercial
  questions from cached evidence cards, not broad repo research.
platforms:
- claude-code
- codex
- shell
prerequisites: []
routing_patterns:
- pattern: \bproduct[- ]?answer\b
  confidence: 0.99
- pattern: /product-answer\b
  confidence: 0.99
routing_intents:
- intent: product_capability_question
  description: User asks what Cognitive OS can do, whether it is useful for their
    situation, or whether it can help a developer or team with limited expertise
    in best practices, clean architecture, security, tests, documentation, or
    agentic primitives.
  confidence: 0.88
- intent: value_proposition_question
  description: User asks who Cognitive OS is for, what problems it solves, why to
    use it, or what differentiates it from alternatives.
  confidence: 0.88
- intent: commercial_positioning_question
  description: User asks about Cognitive OS positioning, ICP, buyer, pricing, competitors,
    pitch, landing page claims, moat, wedge, or safe product claims.
  confidence: 0.88
- "can this system help a developer"
- "help a developer without experience using this system"
- "useful for developers without architecture experience"
- "helps developers with limited experience adopt better practices"
- "answer whether this OS helps developers"
- "can this OS help developers with limited knowledge of best practices code architecture security tests documentation and agentic primitives"
- "can help a developer with limitations in knowledge of best practices code clean architecture security test construction documentation and agent primitives"
triggers:
- product-answer
- /product-answer
- Product Answer
- Answer COS product/commercial questions from cached evidence cards, not broad repo
  research
---
<!-- SCOPE: os-only -->
# Product Answer

## Purpose

Answer Cognitive OS product and commercial questions from the ADR-280/ADR-282
product-answer primitives instead of re-investigating the full SO documentation.

This is an **OS-only** skill. It is for Cognitive OS maintainers answering
questions about this SO's positioning, commercial story, claim safety, or product
wedge. It is not a project-facing adopter skill.

## Use when

- The user asks: "what is our differentiator?", "what is our moat/wedge?",
  "what do we say about competitors?", "pricing", "ICP", "pitch", "landing".
- The user asks about already-analyzed external tools, competitors, or adjacent
  agent frameworks such as Hermes, Agent Zero, OpenClaw, Langfuse, AgentOps,
  Datadog, Dynatrace, or Galileo.
- The user asks when to use vanilla IDE/agent configuration instead of COS, what
  COS is useful for, whether it has CLI/UI/service/headless surfaces, or whether
  COS is complementary to a tool/framework.
- The user asks whether a product/commercial claim is safe.
- The user asks what primitives answer a product or commercial question.
- The answer should be short, evidence-backed, and token-efficient.

## Do not use when

- The user asks to edit product-answer code or manifests; use normal coding flow.
- The user asks for fresh competitor facts or current market research **and**
  the local Tech Radar / external-tool corpus has already been checked. ADR-282
  cards flag named-competitor claims as freshness-sensitive, but the first move
  is the local radar, not internet search.
- The question is about a consumer project's product positioning, not Cognitive
  OS itself.


## Tool and competitor grounding order

For questions about external tools or competitors, avoid spending tokens on web
research before checking local evidence. Inspect these compact/local surfaces in
order:

1. `docs/06-Daily/reports/external-tools-radar-INDEX.md` — chronological entry point for
   analyzed tools and radar editions.
2. `manifests/external-tools-adoption.yaml` and
   `manifests/feature-tool-due-diligence.yaml` — machine-readable adoption and
   BUILD-vs-tool decisions.
3. `docs/08-References/root/vs-alternatives.md`, `docs/04-Concepts/root/component-sources.md`, and
   `docs/08-References/business/competitive-reassessment-openclaw-hermes-2026-04.md` — local
   positioning for Hermes, Agent Zero, OpenClaw, and adjacent alternatives.
4. Relevant repo-scout or deep-research reports under `docs/03-PoCs/research/` and
   `docs/06-Daily/reports/external-tools-*`.
5. Only then browse, and only for volatile facts: current stars, current feature
   claims, licensing changes, pricing, acquisitions, or publication-grade named
   comparisons.

When the local corpus already contains an analysis, answer from it and state the
freshness boundary instead of re-researching the tool.

If the tool is not present in the local corpus, then use the existing research
pipeline instead of ad-hoc browsing:

1. Check Engram for `tech-radar/<tool>` and `research/<tool>/...`.
2. For GitHub repositories, map `https://github.com/<owner>/<repo>` to
   `https://deepwiki.com/<owner>/<repo>` and run the `/repo-scout` pattern.
3. Clone only into the external source cache / reference scratch path described
   by the radar skills, not into product docs.
4. If the shallow verdict is non-REJECT and COS may extract patterns or vendor
   code, escalate to `/deep-tool-research`.
5. Persist the conclusion back to Tech Radar/Engram before using it in future
   product answers.

## Fast path

1. From the SO repo root, answer through the cached primitive:

   ```bash
   scripts/cos-product-answer "<user question>" --format markdown
   ```

2. If the output includes:

   ```text
   Cache
   Using fresh product answer card
   Source freshness: fresh
   ```

   then use that answer. Do **not** read broad docs.

3. If the output falls back to live mode, refresh cards and retry:

   ```bash
   scripts/cos-product-answer-refresh --all
   scripts/cos-product-answer "<user question>" --format markdown
   ```

4. If a specific card is enough:

   ```bash
   scripts/cos-product-answer-refresh --question-id differentiator
   scripts/cos-product-answer --question-id differentiator --format markdown
   ```

## Available question IDs

The current question bank is in `manifests/product-question-bank.yaml`. Common
IDs:

- `differentiator`
- `non_differentiators`
- `existing_primitives`
- `automation_gap`
- `landing_pitch`
- `icp`
- `pricing`
- `competitors`
- `vanilla_usage`
- `runtime_surfaces`
- `alternatives_choice`
- `architecture_map`

## Output discipline

When responding to the user:

- Prefer the `Short answer` and `Recommended pitch` sections.
- Include caveats from `Gaps` when the answer is `warn` or `partial`.
- Mention cache freshness when relevant.
- Do not upgrade `partial`, `partial-real`, or `warn` claims into universal
  claims.
- Do not publish private strategy wording verbatim; the card is a maintainer
  answer, not automatic public copy.

## Manual safety check for external copy

Before using wording externally, run:

```bash
scripts/cos-public-claim-gate --json
```

For named competitor comparisons, refresh external research first.

## Validation

```bash
python3 -m pytest tests/unit/test_product_answer.py tests/behavior/test_product_answer_cli.py -q
scripts/cos-product-answer-refresh --all --json
scripts/cos-product-answer "what is our differentiator" --json
```
