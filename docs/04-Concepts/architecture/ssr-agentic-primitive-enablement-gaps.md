# SSR Developer Primitive Enablement Gap Backlog

<!-- SCOPE: OS -->

## Purpose

Cognitive OS has the building blocks to help a senior-ish developer who does not
want to keep architecture, agent governance, primitive creation, and
self-improvement rules in memory. The current gap is not absence of primitives;
it is the path that turns a natural-language question into the right primitive,
evidence, script, and next action without requiring maintainer-level repo
knowledge.

This backlog captures the missing or weak slices surfaced by the question:

> If I am an SSR developer with limited architecture/governance context, does
> this SO help me create and improve agentic primitives the way Agent Zero,
> OpenClaw, or Hermes feel like they do through repeated chat usage?

## Current supported path

```text
conversation / repeated task / failure / learning
→ prompt capture, metrics, Engram/session learning, key-learning capture
→ primitive-harvester / analyze-improvements / product-answer
→ draft primitive or improvement proposal
→ primitive fitness and governed self-improvement evaluation
→ human-approved promotion
→ reuse and measurement
```

The architecture exists, but the developer journey is still too fragmented.

## Gap summary

| ID | Gap | Impact on SSR developer | Existing related primitive | Proposed fix | Priority |
|---|---|---|---|---|---|
| G1 | No single "which COS primitive answers my question?" router for meta/product/architecture questions. | User must know whether to invoke `product-answer`, `primitive-harvester`, `primitive-authoring`, `analyze-improvements`, or `primitive-usage-map`. | `skills/product-answer`, `skills/catalog-full`, `skills/primitive-usage-map` | Add a question-router skill/script that maps natural-language questions to skill, script, evidence docs, and safe claims. | P0 |
| G2 | Docs explain the system by internal artifact family, not by developer jobs-to-be-done. | An SSR developer sees many ADRs but not the shortest safe path. | `docs/00-MOCs/entrypoints/README.md`, `docs/08-References/root/adoption-tiers.md` | Add a "primitive enablement for developers" guide with examples: repeated request → skill; risky gate → hook; policy → rule; evidence question → product-answer. | P0 |
| G3 | Conversation-to-primitive is advisory and not routinely invoked when repeated intent appears in chat. | The system can classify primitive opportunities, but the user may need to ask explicitly. | `scripts/cos_primitive_harvester.py`, `skills/primitive-harvester` | Add a lightweight trigger/checklist in relevant answering skills and session wrap-up: "should this become a primitive?" with no auto-mutation. | P1 |
| G4 | Governed self-improvement is documented but feels less automatic than Agent Zero/OpenClaw/Hermes. | Product promise may be misunderstood as autonomous mutation. | ADR-083, ADR-201, primitive fitness, `scripts/cos_governed_self_improvement.py` | Expose a plain-language self-improvement status answer: what is automatic, what is draft-only, what requires approval, and what is missing. | P0 |
| G5 | Key Learnings capture is evidence, not behavior, and this boundary is easy to miss. | User may expect a chat learning to instantly change a skill. | `scripts/cos-key-learnings-capture`, key-learning docs | Surface "memory vs evidence vs promoted primitive" in product-answer and developer guide. | P1 |
| G6 | Primitive fitness ledger can be under-populated even when evaluation machinery exists. | Hard to prove whether a candidate primitive is better without current reports. | `scripts/cos-primitive-fitness`, `scripts/cos-primitive-fitness-ledger` | Add smoke/report generation to self-improvement review lanes and dashboard summaries. | P1 |
| G7 | Skill catalog is searchable by maintainers but not task-centric for consumers. | User asks "how do I do X?" but catalog is mostly a list of skills. | `skills/CATALOG.md`, `skills/CATALOG-COMPACT.md` | Add task-oriented index: question type → skill/script/docs. | P0 |
| G8 | Harness parity remains nuanced. | A developer may assume every primitive works identically in Claude, Codex, shell, and future IDEs. | primitive harness coverage, ADR-256/258 | Include projection fidelity in every answer about primitive availability. | P1 |
| G9 | Product-answer currently covers commercial/adoption questions, but not enough "how does the SO help me as a dev?" questions. | Questions like the one that triggered this doc require repo synthesis. | ADR-280/282 manifests | Add a question-bank entry for SSR/dev primitive enablement and its gaps. | P0 |
| G10 | No owner cadence is obvious for reviewing accumulated proposals. | Drafts/evidence can pile up without becoming useful behavior. | ADR-201 maintainer-agent gap, self-improvement loop | Add scheduled maintainer review or explicit automation heartbeat for proposal queues. | P1 |
| G11 | "Create vs improve vs use existing" decision exists, but authoring follow-through is scattered. | A user can get classification without a concrete edit/test plan. | `primitive-harvester`, `primitive-authoring`, `add-skill` | Make harvester output link directly to authoring checklist, tests, and registry update commands. | P1 |
| G12 | Some docs still present as implementation inventory rather than safe claims. | Can overclaim autonomous self-improvement or universal support. | ADR-206, product claim evidence | Keep unsafe-claim boundaries attached to every generated answer. | P0 |

## Recommended tool and primitive adjustments

### Add or extend question-answering tools

1. **Extend `scripts/cos-product-answer` question bank** with a developer-facing
   question: "How does COS help an SSR developer create and improve primitives?"
2. **Add a future `cos-question-router` primitive** that returns:
   - recommended skill;
   - backing script;
   - approved docs;
   - whether the answer is product, architecture, adoption, implementation, or
     primitive-authoring;
   - confidence and trust report.
3. **Add a task-centric catalog view** generated from skill frontmatter and
   routing patterns.

### Adjust existing skills

1. `product-answer`: include developer enablement and gaps, not only commercial
   messaging.
2. `primitive-harvester`: emphasize that it is the practical answer to "should
   this conversation become a primitive?" and that it is advisory by design.
3. `primitive-authoring`: add a shorter SSR path before the full governance
   checklist.
4. `analyze-improvements`: make "question-answering/documentation clarity" a
   first-class proposal type when repeated user questions appear.
5. `catalog-full`: support targeted extraction by job-to-be-done, not only by
   catalog section.

### Add scripts or script modes

1. `scripts/cos-question-router` — thin deterministic wrapper over manifests and
   skill metadata.
2. `scripts/cos-skill-task-index` — generate a task-centric skill index from
   `routing_patterns`, tags, and descriptions.
3. `scripts/cos-primitive-gap-report` — aggregate primitive-readiness, harness
   coverage, primitive fitness, product-answer gaps, and self-improvement queue
   status into one operator report.
4. `scripts/cos-harvest-current-thread` — optional helper that accepts a saved
   conversation excerpt and runs the harvester plus authoring plan. It must stay
   propose-only.

### Add docs

1. `docs/05-Methodology/guides/primitive-enablement-for-developers.md` — friendly path for
   SSR/senior developers.
2. `docs/05-Methodology/guides/which-primitive-should-i-use.md` — question-to-skill lookup.
3. `docs/06-Daily/reports/primitive-enablement-gap-review-<date>.md` — periodic review of
   this backlog.

### Add tests and gates

1. Behavior test that a Spanish SSR/developer question routes to the new
   product-answer entry.
2. Contract test that every product-answer question has at least one evidence
   source and one unsafe-claim boundary when maturity is partial.
3. Smoke test for future question-router: unknown questions fail closed with
   suggested next skill, not hallucinated answers.
4. Primitive-harvester regression test for conversations asking repeated
   "can this be automatic?" questions.

## Safe answer boundary

The safe external wording is:

> Cognitive OS helps developers turn repeated agent work into governed, tested,
> reusable agentic primitives. It can detect and propose improvements from
> conversations and telemetry, but promotion remains evidence-gated and
> human-approved unless a project explicitly opts into narrower automation.

Avoid saying:

- "COS autonomously rewrites itself from chat."
- "Every harness gets identical primitive behavior."
- "All repeated requests automatically become skills."
- "A Key Learning is already a runtime behavior change."

## Acceptance criteria

1. Product answer can route the Spanish SSR primitive-enablement question to a
   dedicated evidence-backed answer.
2. The gap backlog is linked from `docs/00-MOCs/entrypoints/README.md`.
3. The execution backlog is visible from `docs/08-References/business/master-plan-checklist.md`.
4. The answer preserves the governed self-improvement boundary: detect/propose
   can be automatic; runtime mutation is gated.
