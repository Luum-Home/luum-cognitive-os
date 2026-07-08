---
type: reference-synthesis
source: docs/08-References/business/sdd-harness-consumer-workflow-audit.md
provenance: "Comparative audit against the small betta-tech/harness-sdd reference harness, written to extract a first-class consumer SDD lane recommendation while preserving Cognitive OS's governance/portability strengths."
---

## What it is

A comparative product/workflow audit that benchmarks Cognitive OS against a small, deliberately simple reference implementation (`betta-tech/harness-sdd`) of Spec-Driven Development. It evaluates Cognitive OS both as a project building itself and as a layer serving consumer projects, then proposes a concrete, first-class "consumer SDD lane" to close the clarity gap without losing COS's governance/portability differentiators.

## Key mechanics

- **Reference pattern strengths** (from `harness-sdd`): durable task memory (`feature_list.json`), specs written before code (`requirements.md`/`design.md`/`tasks.md`), progress files that survive context resets, a human `spec_ready` approval gate, and strict role separation (leader/spec author/implementer/reviewer) so agents never self-approve. Core operational pattern: "anti-telephone-game" context passing — durable artifacts, not chat history.
- **What COS does well while building itself**: stronger product thesis (governance/verification/portability vs. "more agents"), durable kernel-vs-adapter boundary, evidence-first culture (trust reports, claim validation, hook receipts), externalized memory beyond files (Engram), and a genuine author-once/project-through-drivers cross-harness doctrine.
- **What COS does poorly while building itself**: too many visible centers of gravity that obscure the user promise; the architecture is more legible than the "what should my project do tomorrow" happy path; internal jargon (kernel, driver, control plane, primitive) doesn't translate to first-contact value; governance risks becoming overkill for small tasks; the project sometimes optimizes subsystems before the workflow.
- **Recommended task-scale lanes**: Trivial (direct + compile/lint), Small (direct + existing tests), Medium (SDD req/design/tasks + review), Large (+ new tests, traceability, human gates), Critical (+ security/audit/rollback review).
- **Recommended consumer SDD lane**: canonical artifact tree under `.cognitive-os/workflows/sdd/<feature>/` (requirements, design, tasks, traceability, review, history), a state machine (`pending → spec_drafting → spec_ready → approved → in_progress → review_ready → done/rejected`), pluggable task-state adapters (local JSON/Markdown, GitHub Issues, Linear, Jira), and a mandatory **requirement-to-test traceability gate** — reviewer rejects completion if a requirement lacks a test, a test can't be mapped back, a task is unchecked without explanation, implementation diverges from design, or prohibited boundaries were touched.
- **Cross-harness projection requirement**: the SDD lane's source of truth must not be `.claude/agents/*.md` — canonical contract → harness capability map → per-harness projection (Claude, Codex, Cursor/OpenCode) → runtime/proof receipts.
- Lists 7 acceptance criteria for the future SDD lane and 6 immediate follow-up actions (ADR draft, local task-state adapter, templates, traceability gate, cross-harness projection tests, 5-minute demo).

## Relations & where used

Positions COS relative to `betta-tech/harness-sdd` (external GitHub reference) and to the existing COS SDD skill chain (propose → spec → design → tasks → apply → verify → archive). Recommends a new ADR for the canonical consumer SDD workflow lane; ties into existing acceptance-criteria/Definition-of-Done doctrine already present in COS.

## Status / caveats

This is a **recommendation/audit document with an embedded self-reported Trust Report** (`TRUST_REPORT: SCORE=82 STATUS=HIGH EVIDENCE=4 UNCERTAINTIES=2`), not a record of implementation — the "Recommended Cognitive OS SDD Lane" and "Immediate Follow-Up Work" sections describe proposed, not yet built, structures (workflow.yaml, adapters/, gates/ directories). The two named uncertainties in the source are preserved faithfully: (1) the exact SDD-lane implementation shape needs validation against installer/projection internals before ADR acceptance, and (2) external task-system adapter priority should be demand-driven, not assumed. No evidence in this document confirms whether the recommended lane was subsequently built.
