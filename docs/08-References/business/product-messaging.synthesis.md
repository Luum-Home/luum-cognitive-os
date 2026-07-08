---
type: reference-synthesis
source: docs/08-References/business/product-messaging.md
provenance: "Sets the recommended positioning voice for Cognitive OS — sophisticated on the inside, simple on the outside — so README/docs/pitch copy doesn't read as expert-only or platform-heavy."
---

## What it is

A messaging-standards document defining the core positioning ("sophisticated
on the inside, simple on the outside"), a recommended primary line and
supporting lines, five citable "shippable wedge" claims tied to specific ADRs
and file paths, five messaging principles, an explicit avoid-list, and a
single target user reaction as the product standard.

## Key mechanics

- **Core position**: not "for experts only" — should feel low-friction by
  default, safe for non-experts, powerful when deeper control is needed,
  opinionated enough to guide, flexible enough to scale.
- **Recommended primary line**: "Cognitive OS is the operational layer for
  coding agents that makes governance, verification, and portability
  accessible to real teams, not just agent infrastructure experts." Six
  supporting lines reinforce the same "easy to adopt, hard to outgrow"
  framing.
- **Five specific shippable wedges** (post-2026-05-07), each citable because
  it maps to a real file path in `main`: cycle-deduplication vs. MAST 2025's
  41–87% multi-agent failure rate (ADR-230, `lib/handoff_dispatcher.py`);
  the $47K-incident class made structurally impossible via a sync pre-call
  budget gate (ADR-228, `lib/dispatch_gate.py`); replay timeline + restore-
  by-checkpoint without a hypervisor (ADR-227, `lib/shadow_git.py` + `cos
  rollback`); six contradictory retry magic numbers collapsed to one
  classifier plus idempotency keys eliminating 15–30% silent side-effect
  duplication (ADR-228 + `manifests/retry-contract.yaml`); native MCP server
  giving every MCP-aware tool governance access without per-harness adapters
  (ADR-231, `packages/mcp-server/`).
- **Five messaging principles**: lead with safety/clarity/adoption speed;
  avoid power-user-only language; avoid language that trivializes the system;
  emphasize scaling from straightforward adoption to advanced control; keep
  tone serious, accessible, operationally credible.
- **Explicit avoid-list**: don't imply the product is only valuable to agent
  infrastructure specialists, don't imply deep vendor-specific expertise is
  required, don't present the product as a giant platform before an
  adoptable operational layer, don't equate simplicity with reduced rigor.
- **Product standard** (the target reaction): "This feels easy to start, but
  serious enough to trust in a real repository."

## Relations & where used

- Cross-references `developer-confidence.md` for the developer-experience
  framing by project maturity.
- Its primary line and north star are functionally identical to the north
  star defined in `product-answer-playbook.md`, and its "avoid... a giant
  platform before it is an adoptable operational layer" principle directly
  operationalizes the demotion recommendations in `feature-reality-audit.md`
  (which explicitly names squad/organization/control-plane framing and the
  "13-layer operating system" framing as things to demote from top-level
  messaging) — and stands in direct tension with the platform-forward,
  control-plane-heavy narrative of `kubernetes-for-agents.md`.
- Its shippable-wedge citations (ADR-227/228/230/231) are the same
  orchestration-substrate ADRs tracked in `master-plan-checklist.md` §9 and
  the ADR table in `open-source-design.md`'s §10 addendum.

## Status / caveats

- Positioning/style-guide document, not a status report; the "shippable
  wedges" claims are dated "post-2026-05-07" and depend on the referenced
  ADRs/files remaining accurate — cross-check against
  `master-plan-checklist.md` §9 for current slice-completion state of those
  ADRs before reusing the wedge claims verbatim in new copy.
- No internal inconsistency found within the document.
