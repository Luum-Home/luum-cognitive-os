---
type: concept-synthesis
source: docs/04-Concepts/architecture/external-tool-adoption-doctrine.md
status: accepted
provenance: "The tech-radar corpus showed a recurring risk of COS drifting from governing the agentic ecosystem into rebuilding every interesting agentic subsystem (LangGraph/AutoGen/CrewAI/RAG/TUI/observability clones)."
---

## What it is

Doctrine that turns the external-tools tech radar into a pre-implementation decision rule: **adopt commodity mechanisms, build governance semantics.** Ratified as accepted by ADR-254 for the External Tool Intelligence Plane.

## Key mechanics

- Decision vocabulary: **ADOPT** (depend on/call directly, behind version+rollback contract), **INTEGRATE** (adapter/policy wrapper, tool never becomes source of truth), **BUILD** (COS owns — governance/policy/evidence/product semantics), **DEFER** (track in radar, no dependency/roadmap commitment), **REJECT** (blocked/rejected ledger with rationale).
- Core rule: COS should adopt/integrate a mechanism when the external ecosystem is better at it, but must always build the layer answering: is this action allowed now, who owns this file/task/surface, what evidence proves the claim, what is the budget/blast radius, is the tool active/opt-in/blueprint/rejected, can the behavior travel across Claude Code/Codex/Cursor/OpenCode/CLI/service-mode/containers.
- Domain-matrix sample verdicts: Graphiti INTEGRATE -> possible ADOPT after benchmark; LightRAG INTEGRATE/DEFER-core; HippoRAG DEFER runtime/ADOPT benchmark idea; DSPy INTEGRATE (skill/prompt optimization only, never a router replacement); Aider repo-map ADOPT-concept/BUILD-COS-layer; agentapi INTEGRATE; Superpowers INTEGRATE selectively; Bubble Tea ADOPT; FastMCP ADOPT; Bubblewrap/Seatbelt/E2B INTEGRATE; Phoenix/MLflow/OTel ADOPT-standards/INTEGRATE-backends; capability/claims ledger BUILD; approval policy BUILD-now/DEFER-OPA; Temporal/NATS/Firecracker/OPA-by-default DEFER.
- Anti-reinvention guardrail: before adding a custom subsystem, a proposal must answer 5 questions — which existing tool solves the mechanism, is the missing value actually governance semantics, can the tool sit behind an adapter without becoming source of truth, what is the license/footprint/fallback, what audit proves the tool is active not blueprint.
- Acceptance criteria for future adoptions: every adoption declares an explicit type (dependency/cli-adapter/schema-port/algorithm-port/testdata-vendor/operator-installed/pattern-only), states license/footprint/default-install-impact/owner/tests/rollback, and every custom-feature proposal includes an anti-reinvention answer. COS stays local-first by default; heavy infra is opt-in or deferred.

## Relations & where used

ADR-058, ADR-065, ADR-192, ADR-212, ADR-247, ADR-250, ADR-251, ADR-252, ADR-253, ADR-254 (ratifies doctrine). Sourced from `docs/06-Daily/reports/external-tools-radar-INDEX.md` and 5 cross-check reports (memory, sandbox-mcp, orchestration, codegen/skills/TUI, observability-debt).

## Status / caveats

Status: accepted. New runtime adoption still requires the ADR-254 manifest/audit/research-check path.
