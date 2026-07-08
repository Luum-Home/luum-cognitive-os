---
type: concept-synthesis
source: docs/04-Concepts/architecture/gentle-ai-comparative-audit-2026-06-15.md
provenance: "Evaluate Gentleman-Programming/gentle-ai as an external benchmark for COS token efficiency, SDD discipline, persistent process state, multi-agent orchestration, and cross-IDE/CLI projection — a source-level audit and adoption plan, not a code import."
---

## What it is

Comparative audit of `Gentleman-Programming/gentle-ai` (MIT-licensed Go CLI, commit `7f3c8103aed1f60651102a35018b9ccd30653e90`) against Cognitive OS across every functional domain (not just SDD), producing an ordered system-wide adoption backlog.

## Key mechanics

- License/adoption policy: pattern-only by default; several embedded skills declare `Apache-2.0` even though the root repo is MIT, so text/code reuse stays license-sensitive; no prompt/code copying without an explicit attribution decision.
- Validation performed: external `go test` passed on 8 packages (`internal/sddstatus`, `skillregistry`, `pipeline`, etc.); COS's own related suite (SDD transitions/governance, skill router, SO-impact-eval) passed 187 tests after the addendum.
- Strongest transferable design: `internal/sddstatus/status.go` — one computable `Status` schema (`schemaName`, `dependencies`, `applyState`, `nextRecommended`, `blockedReasons`, etc.) that routes SDD continuation from computed state instead of prose inference.
- Other Gentle-AI strengths cataloged: orchestrator/executor split, mandatory delegation triggers (4-file/multi-file/PR/incident/long-session gates), SDD preflight (pace/artifact-store/PR-strategy/review-budget), capability-gated strict TDD (RED/GREEN/TRIANGULATE/REFACTOR + safety-net evidence, verified not just "tests passed"), skill registry as a lightweight path index (`.atl/skill-registry.md`, never copies full skill bodies), per-phase model/effort routing across harness adapters, post-injection projection self-checks, pipeline rollback substrate, review-size economics (400-line budget).
- Scale comparison: Gentle-AI 804 files / 173 Go test files / 29 `SKILL.md` assets / 12 orchestrator assets, vs COS 21,419 files / 2,074+ Python test files (plus Go/Bash/TS) / 409 `SKILL.md` surfaces / 23 orchestrator/process-loop surfaces — COS is broader but carries more projection-closure risk (primitive can exist as a script while lifecycle/ACC/tests lag).
- System-wide adoption backlog (ordered): typed adapter capability registry, transactional projection pipeline (prepare/apply/verify/rollback receipts), projection postcheck primitive, unified `cos status` dispatcher family, compact skill-registry path index, stack-detected strict-TDD plane, `cos doctor`/`status` UX consolidation before any TUI, self-upgrade/install health (backup/checksum/rollback), review workload forecast, and an SO-wide measured-adoption loop via `cos-so-impact-eval` for every adopted pattern.
- Recommended first slice: `cos-sdd-status` — a COS-owned SDD/process status dispatcher with `nextRecommended`/dependencies/blockers/task-progress, required to interoperate with (not duplicate) `cos-process-loop`.

## Relations & where used

`scripts/cos-process-loop`, `scripts/cos-so-impact-eval`, `skills/sdd-*`, `lib/skill_router.py`, `scripts/cos-loop-run/-report/-guard/-replay/-eval`, `lib/execution_profile.py`.

## Status / caveats

Explicitly an audit + adoption plan, not a ratified decision. Claim boundary: Gentle-AI's own token-savings claim is architecturally plausible (delegation, registry indexing, phase routing, cached capabilities) but the audited snapshot has no controlled A/B benchmark; any COS adoption must be measured via `cos-so-impact-eval` or real provider telemetry before claiming savings. Explicit "what not to copy": no vendoring of prompt/Go text without a separate license decision; don't collapse COS's lifecycle/ACC/projection governance into Gentle-AI's single-binary mental model.
