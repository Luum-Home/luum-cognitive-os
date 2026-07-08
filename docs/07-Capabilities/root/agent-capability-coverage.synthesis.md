---
type: capability-synthesis
source: docs/07-Capabilities/root/agent-capability-coverage.md
provenance: "Architecture specification for the Agent Capability Coverage (ACC) metric, the core contract that the acc_pipeline.py implementation (ADR-147) and its generated reports must satisfy."
---

## What it is
The architecture specification for Agent Capability Coverage (ACC): a metric and portable contract for measuring how completely a system's real capabilities are represented to the agentic primitives (tools, skills, rules, hooks, MCP schemas) an AI coding agent can use.

## Key mechanics
- Core thesis: "if a capability is not structurally modeled, an agent cannot use it predictably, securely, or efficiently." ACC is distinct from unit-test coverage, SAST, or agent evaluation — it measures structural alignment between the real system and its agent-facing representation.
- Defines canonical capability kinds (endpoint, event, job, integration, business_rule, workflow, hook, skill, rule) each with a discovery signal, and mapping statuses (`aligned`, `missing`, `partial`, `stale`, `overexposed`, `unverified`).
- Metric formulas: `ACC = aligned_weight / total_weight`; `ACC_effective = (aligned + 0.5*partial - stale_penalty - overexposed_penalty) / total_weight`, with default kind weights (business_rule 5, endpoint/workflow/integration 4, event/job/hook 3, rule/skill 2).
- Core Portable Contract requires: a machine-readable capability manifest (`schema_version: acc.v1`) with required fields (id, kind, source, risk, signature, represented_by, mapping_status, confidence, evidence); an `acc.json`/`acc.md` report pair; deterministic gate semantics (block on critical missing/stale/overexposed, block if ACC_effective under threshold); and explicit portability boundaries (no GitHub/LLM-provider/agent-framework/MCP-registry/parser/SaaS lock-in required by core).
- Optional Adapters section separates static-code adapters (TS/Go/Python AST, IaC scanners) from representation adapters (MCP, Skills, Rules, Hooks, Workflows), plus an ecosystem-references table (Figra, PydanticAI, VoltAgent, Microsoft Agent Governance Toolkit, SWE-CI, AST-hallucination research, AI SAST vendors) explicitly marked as non-core inspiration.
- Integrates with existing COS subsystems (skill registry, rules index, hooks profile, Engram) via read-only, deterministic, provenance-preserving, failure-isolated adapter contracts.
- Subsumes `component-reality-check` / `aspirational_audit.py`: every ACC capability carries a `lifecycle_status` (real/dormant/aspirational) sourced from that audit; `aspirational_audit.py` becomes a discovery adapter feeding `C_total` rather than a parallel report, with a reconstruction-phase coexistence period and a production-phase migration to ACC-only.
- Storage model: four persistence layers — Engram canonical manifest (mutable, incremental), `docs/07-Capabilities/acc/acc-{revision}.{json,md}` reviewable snapshots (append-only), `docs/07-Capabilities/acc/latest.json` drift baseline, and per-capability Engram evidence trail (append-only).
- Pipeline: Phase 1 discover real capabilities -> Phase 2 discover represented capabilities -> Phase 3 map/classify (exact id, exact schema, structural, semantic-with-confidence, human override; low-confidence semantic matches become `unverified`, never silently `aligned`) -> Phase 4 calculate/report/gate.
- Documents 11 acceptance criteria for a compliant implementation and two future audit/behavior test contracts (`tests/audit/test_agent_capability_coverage_doc.py`, `tests/behavior/test_agent_capability_coverage_mapping.py`).
- "Implementation Status — 2026-05-04" addendum: ADR-147 implements the first orchestrator (`scripts/acc_pipeline.py`), covering COS's own agentic primitives first (scripts, hooks, skills, rules, docs claims, consumer accessibility); app-level adapters (endpoints/events/jobs/integrations/workflows) remain future work.
- Documents the operational CLI surface: `cos-coverage` (human/`--json`/`--brief`/`--refresh`, 30s cache, p95 <300ms) and the opt-in `statusline-coverage.sh` segment (reads cache only, <50ms, `COS_COVERAGE_STALE_MAX` override).

## Relations & where used
Defines the contract that `docs/07-Capabilities/acc/latest.md` (the generated report) and `docs/07-Capabilities/capabilities/MATRIX.md` (the per-ADR ledger) both instantiate. References `component-reality-check` / `scripts/aspirational_audit.py`, `dogfood_score` (`scripts/dogfood_score.py`), and the skill registry / rules index / hooks profile / Engram integration points.

## Status / caveats
Primarily a forward-looking specification: several referenced test files (`tests/audit/test_agent_capability_coverage_doc.py`, `tests/behavior/test_agent_capability_coverage_mapping.py`) are described as "future" / "suggested," not confirmed as existing. The "Implementation Status" section confirms a real, working pipeline (`scripts/acc_pipeline.py`, ADR-147) but scopes it explicitly to COS's own primitives, with application-level adapters (endpoints, events, workflows) still unimplemented per this doc's own wording.
