---
type: capability-synthesis
source: docs/07-Capabilities/root/agent-quality.md
provenance: "Design note for the Agent Quality System, documenting four interlocking fixes for the observed failure mode of agents doing the minimum instead of the maximum on ambiguous prompts."
---

## What it is
Design documentation for the Agent Quality System: four interlocking mechanisms (mandatory acceptance criteria, auto-verification loop, exhaustive prompt generator, completeness validator) that address agents delivering minimal results on vague prompts.

## Key mechanics
- Problem table with concrete examples: "Rebrand old-name to new-name" -> agent renames 3 files instead of 203 occurrences across 37 files; "Migrate endpoints to Go" -> 10 of 317 endpoints; "Fix lint errors" -> 5 of 45. Root causes: ambiguous prompts interpreted minimally, no measurable "done," agents optimize for speed, no automated verification.
- **Fix 1 — Mandatory Acceptance Criteria** (`rules/acceptance-criteria.md`): every agent prompt must include an `ACCEPTANCE CRITERIA:` block with verification commands (`command = expected`, `exits 0`, `>= threshold`).
- **Fix 2 — Auto-Verification Loop** (`hooks/auto-verify.sh`, PostToolUse on Agent, runs before `dod-gate.sh`): extracts criteria from the prompt, parses backtick-wrapped verification commands, runs them with a timeout, reports PASS/FAIL; on FAIL the orchestrator re-launches with failure context, max 3 retries (`quality.verification_retries` in `cognitive-os.yaml`).
- **Fix 3 — Exhaustive Prompt Generator** (`skills/exhaustive-prompt/SKILL.md`, `/exhaustive-prompt`): runs discovery commands to enumerate exact scope, lists every file with expected changes, generates acceptance criteria, sets complexity-appropriate DoD — to be used before launching agents on medium/large/critical tasks.
- **Fix 4 — Completeness Validator** (`hooks/completeness-check.sh`, PreToolUse on Agent, advisory only): flags red flags like "all files" without a list, migrations without item counts, "follow patterns" without naming which, missing acceptance criteria — suggests `/exhaustive-prompt` but does not block.
- Documents hook registration order in `.claude/settings.json` (PreToolUse: `completeness-check.sh` then `agent-prelaunch.sh`; PostToolUse: `auto-verify.sh` then `dod-gate.sh` then `auto-refine.sh` — order matters so verification precedes DoD checks) and the `quality.*` config block (`auto_verify`, `exhaustive_prompts`, `completeness_check`, `verification_retries: 3`).
- Defines metrics schemas for `auto-verify.jsonl` (status, agent snippet, checks/passed/failed) and `completeness-check.jsonl` (warnings count, agent snippet), with target KPIs: verification pass rate >80%, criteria coverage >90%, completeness warnings trending down, retry rate <20%.
- Full workflow diagram: user task -> `/exhaustive-prompt` -> agent launch (completeness-check advisory) -> agent works -> `auto-verify.sh` -> FAIL loops back (up to 3x) or PASS -> `dod-gate.sh` -> confirmed complete.

## Relations & where used
Direct source for the "Quality Gates" section of `rules/RULES-COMPACT.md` (acceptance-criteria, agent-quality, clarification-gate, adversarial-review, prompt-quality entries). Cross-references `rules/definition-of-done.md`, `hooks/dod-gate.sh`, and `hooks/auto-refine.sh` (PITER retry loop).

## Status / caveats
None of the referenced hooks/rules/skills are marked with explicit implementation status in this document — it reads as a stable, in-place design rather than a proposal, but faithfulness requires noting the source gives no explicit "implemented"/"planned" markers for cross-checking against actual hook files.
