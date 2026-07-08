---
type: reference-synthesis
source: docs/08-References/root/piter-framework.md
provenance: "Explains the PITER (Plan-Implement-Test-Evaluate-Refine) autonomy loop from Tactical Agentic Coding and maps it onto Cognitive OS's SDD phases and auto-refine mechanism."
---

## What it is

Reference documentation for PITER, a 5-step loop (sourced from IndyDevDan's "Tactical Agentic Coding") that lets agents work AFK (away from keyboard) without human supervision between steps, and a mapping of each step to existing Cognitive OS components.

## Key mechanics

- **The 5 steps** (cyclic: Refine loops back to Plan or Implement): Plan (requirements -> actionable steps -> success criteria); Implement (execute plan, write code/configs, follow conventions); Test (unit/integration/e2e, linters, type checkers); Evaluate (compare against step-1 success criteria, check regressions, assess quality); Refine (if pass: exit; if fail: analyze gaps, loop back — max 3 iterations, then escalate to human).
- **Mapping table** to COS: Plan -> SDD (`sdd-propose`/`sdd-spec`/`sdd-design`/`sdd-tasks`); Implement -> `sdd-apply` + sub-agent delegation; Test -> auto-test-on-edit hook + test commands; Evaluate -> `sdd-verify` + verification-before-completion skill; Refine -> `auto-refine` hook/skill + closed-loop-prompts. All five marked "Implemented."
- **Automatic Refinement Loop** (described as the gap that used to exist and is now closed): previously the pipeline stopped at Evaluate and reported to a human; now it loops via: `auto-refine.sh` (PostToolUse hook on Agent, detects failures, tracks retries per task up to 3, phase-aware — auto-retry in reconstruction/stabilization, suggest-only in production/maintenance), the closed-loop prompt protocol (every agent prompt must include auto-refine instructions), the `/auto-refine` skill (manual/orchestrator-driven structured root-cause analysis + re-launch), a refinement budget (max 3 iterations tracked per task fingerprint in `.cognitive-os/metrics/auto-refine/`), and escalation criteria (max retries reached, repeated identical error, architectural-change-required error, or broken test infrastructure).
- **PITER-in-ADW-pipelines example**: shows PITER embedded as an inner loop wrapping `sdd-apply`+`sdd-verify` within a larger `feature-pipeline` YAML (propose -> spec -> design -> tasks -> piter-loop[max_iterations: 3] -> archive).
- **Implementation-priority table**: closed-loop prompts rule (High/Low effort), refinement budget config (Medium/Low), gap-analysis template (Medium/Low), PITER workflow wrapper (Low priority/Medium effort, depends on ADW pipelines).
- **Relationship to ZTE**: frames PITER as a building block toward Zero-Touch Engineering — each successful unattended PITER loop moves the system closer to full ZTE (cross-references `zero-touch-engineering.md`).

## Relations & where used

- Directly implements/documents `rules/closed-loop-prompts.md`, `hooks/auto-refine.sh` (PostToolUse on Agent), `skills/auto-refine`, and the readiness-check/sdd-verify chain.
- Referenced conceptually by `docs/08-References/root/patterns-adopted.md`'s "Generator-Evaluator Loop" pattern (Anthropic Engineering source), which describes the same sdd-apply/sdd-verify retry cycle from a different origin framing.
- Cross-references `zero-touch-engineering.md` for the broader autonomy roadmap this loop serves.

## Status / caveats

- No internal date on the document; given it describes the auto-refine mechanism as already "IMPLEMENTED," it is presented as current-state documentation rather than a proposal, but no version/date evidence is present in the source to confirm currency.
- No inconsistencies found within the document itself.
