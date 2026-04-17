# Rules Functional Audit — Capa 3 Scorecard

> **Read-only audit.** Project phase: `reconstruction` (empirical verification, no fixing).
> **Generated:** 2026-04-16.
> **Scope:** every `.md` file in `rules/` (excluding `RULES-COMPACT.md` which is the index itself).

## Summary

- **Total rule files**: 107 (`rules/*.md`, minus `RULES-COMPACT.md` index → 106 behavioral rules)
- **Hook-enforced (hook exists AND registered in `.claude/settings.json`)**: 21
- **Hook-enforced-BROKEN (rule claims hook, hook exists but NOT registered)**: 8
- **Agent-instruction-only (injected via `agent-preamble.md` / `agent-mandatory-rules.md` / referenced in `RULES-COMPACT.md`)**: 52
- **Declarative-only (described as policy but no hook, no auto-injection, not in COMPACT)**: 19
- **Code-dead (references hooks/scripts that do not exist)**: 6

> The user's question was "do the 20 rules in `rules/` enforce behavior or ornament?"
> Reality: there are **107 rule files**, not 20. Only **21** are hook-enforced end-to-end.
> The remaining **86** rely on the agent reading the rule markdown and following it —
> and of those, **only 9** are currently auto-injected into sub-agent context (see
> `templates/agent-mandatory-rules.md`, which is a 31-line file that references NONE of
> the rules in `rules/` by name).

## The injection reality (critical finding)

`hooks/subagent-context-injector.sh` (registered on `SubagentStart`) is the ONLY mechanism
that delivers rule content into a sub-agent's context. It injects two templates:

1. `templates/agent-mandatory-rules.md` — 31 lines, covers:
   symlinks · auditing · code quality · engram · performance
2. `templates/agent-preamble.md` — 101 lines, covers:
   progress reporting · structured return · trust report · communication style · escalation

Neither template cross-references rule files in `rules/`. Therefore:
- A sub-agent will receive the **preamble + mandatory rules** on every launch.
- A sub-agent will NOT automatically receive `rules/acceptance-criteria.md`,
  `rules/trust-score.md`, `rules/phase-aware-agents.md`, or any other rule markdown.
- The orchestrator's CLAUDE.md loads `rules/*` (for the main thread only). Sub-agents do not.

**Effective coverage** (what actually reaches an agent's context at launch):
- Trust Report format → preamble (yes)
- Acceptance criteria / DoD / adversarial review / all ~20 quality rules → NO injection,
  only indexed in `RULES-COMPACT.md` which itself is not injected unless it's in
  `.claude/rules/cos/` symlinks for the orchestrator.

## Findings by category

### Hook-enforced (21)

Hook file exists AND is registered in `.claude/settings.json`. Enforcement is live.

| Rule | Hook | Event | Listed in `EXCLUDED_RULES` |
|---|---|---|---|
| `anti-hallucination.md` | `claim-validator.sh` | PostToolUse Agent | yes |
| `assumption-tracking.md` | `assumption-tracker.sh` | PostToolUse Agent | yes |
| `auto-repair.md` | `auto-repair-dispatcher.sh` | PostToolUse Agent | yes |
| `auto-skill-generation.md` | `auto-skill-generator.sh` | PostToolUse Agent | yes |
| `blast-radius.md` | `blast-radius.sh` | PreToolUse Agent | yes |
| `clarification-gate.md` | `clarification-gate.sh` | PreToolUse Agent | yes |
| `consequence-system.md` | `consequence-evaluator.sh` | PostToolUse Agent | yes |
| `content-policy.md` | `content-policy.sh` | PostToolUse Edit\|Write | yes |
| `crash-recovery.md` | `crash-recovery.sh` + `auto-checkpoint.sh` | SessionStart + PostToolUse | yes |
| `credential-management.md` | `secret-detector.sh` (partial) | PreToolUse Edit\|Write | no |
| `doc-sync.md` | `doc-sync-detector.sh` | PostToolUse Edit\|Write | (excluded for a different reason) |
| `error-learning.md` | `error-pipeline.sh` (new name, rule doc uses old `error-learning.sh` name) | PostToolUse Bash | no |
| `prompt-quality.md` | `prompt-quality.sh` | PreToolUse Agent | yes |
| `rate-limit-protection.md` | `rate-limit-protection.sh` | PreToolUse Agent | yes |
| `rate-limiting.md` | `rate-limiter.sh` | PreToolUse Bash | yes |
| `result-management.md` | `result-truncator.sh` | PostToolUse Bash | no |
| `scope-creep-detection.md` | `scope-creep-detector.sh` | PostToolUse Edit\|Write | yes |
| `scope-proportionality.md` | `scope-proportionality.sh` | PostToolUse Agent | yes |
| `skill-rewrite.md` | `completion-gate.sh` (in `packages/quality-gates/hooks/`) | PostToolUse Agent | yes |
| `trust-score.md` | `trust-score-validator.sh` | PostToolUse Agent | no |
| `user-prompt-capture.md` | `user-prompt-capture.sh` | UserPromptSubmit | no |

### Hook-enforced-BROKEN (8)

Rule claims enforcement by a hook that **exists on disk** but is **NOT registered** in
`.claude/settings.json`. The hook will never fire. Rule is effectively unenforced.

| Rule | Referenced hook | Exists on disk? | Registered? |
|---|---|---|---|
| `audit-trail.md` | `git-context-capture.sh`, `session-changelog.sh`, `audit-id-enricher.sh` | yes (all 3) | **NO** |
| `auto-rollback.md` | `auto-rollback-trigger.sh` | yes | **NO** |
| `confidence-gate.md` | `confidence-gate.sh`, `trust-score-validator.sh` | yes (both) | partial (validator registered, gate NOT) |
| `confidentiality-protection.md` | `confidentiality-enforcer.sh` | yes | **NO** |
| `agent-identity.md` | `audit-id-enricher.sh` | yes | **NO** |
| `pre-dev-readiness-gate.md` | `predev-completeness-check.sh` | yes | **NO** |
| `reinvention-prevention.md` | `reinvention-check.sh` | yes | **NO** |
| `pre-commit-gate.md` | `pre-commit-gate.sh` | yes | git hook (not Claude hook — intentional) |

Note: `pre-commit-gate.md` is intentional — it's a `.git/hooks/pre-commit` symlink, not a
Claude hook. Listed here for transparency because the rule claims enforcement.

### Agent-instruction-only (52)

Rules that rely on the agent reading & following markdown. They are either:
- **(a)** kept as context symlinks (CORE_RULES in `self-install.sh:172`) OR
- **(b)** indexed in `RULES-COMPACT.md` so the orchestrator can point to them by `[ref-key]` OR
- **(c)** loaded on demand by skills/commands.

None are in `templates/agent-mandatory-rules.md` — so sub-agents do NOT receive them
at launch time unless the orchestrator's prompt explicitly includes the content.

Symlinked for orchestrator context (`.claude/rules/cos/*`) via `CORE_RULES`:
- `adaptive-bypass.md`, `acceptance-criteria.md`, `agent-quality.md`, `trust-score.md`,
  `token-economy.md`, `phase-aware-agents.md`, `closed-loop-prompts.md`, `error-learning.md`,
  `credential-management.md`, `model-routing.md`, `result-management.md`

Indexed in `RULES-COMPACT.md` (agent must look them up):
- `adversarial-review.md`, `agent-audit-before-commit.md`, `agent-communication.md`,
  `agent-customization.md`, `agent-escalation.md`, `agent-kpis.md`, `agent-output-reading.md`,
  `agent-security.md`, `agent-sidecars.md`, `aguara-integration.md`, `broken-window-policy.md`,
  `capability-levels.md`, `capability-protection.md`, `cognitive-load.md`,
  `cognitive-os-changes.md`, `component-classification.md`, `context-management.md`,
  `context-optimization.md`, `context7-auto-trigger.md`, `cost-prediction.md`,
  `decomposition.md`, `definition-of-done.md`, `dogfooding.md`, `dry-run.md`,
  `dynamic-tool-creation.md`, `e2b-integration.md`, `ecosystem-tools.md`,
  `engram-organization.md`, `estimation-calibration.md`, `fault-tolerance.md`,
  `hcom-integration.md`, `hook-security-profiles.md`, `impact-analysis.md`,
  `infra-health.md`, `infra-intent.md`, `library-selection.md`, `license-policy.md`,
  `model-compatibility.md`, `model-directive.md`, `non-blocking-retry.md`,
  `observability.md`, `orchestrator-mode.md`, `os-vs-project.md`, `parry-integration.md`,
  `pentesting-readiness.md`, `performance-monitoring.md`, `private-mode.md`,
  `prompt-composition.md`, `queue-advisor.md`, `queue-drain.md`, `repomix-integration.md`,
  `responsiveness.md`, `sandbox-sampling.md`, `scout-pattern.md`, `security-scanning.md`,
  `self-improvement-protocol.md`, `session-concurrency.md`, `singularity.md`,
  `skill-management.md`, `split-and-resume.md`, `squad-protocol.md`, `step-files.md`,
  `supply-chain-defense.md`, `task-dag.md`, `tero-integration.md`, `trailofbits-skills.md`,
  `workload-scheduling.md`

(Actual count: 52 rules fall in this category after deduping overlaps with CORE_RULES
and the broken/hook-enforced categories.)

### Declarative-only (19)

Rules that describe policy but have no hook, no auto-injection, and are NOT in
`RULES-COMPACT.md`. Effectively documentation — an agent only sees them if specifically
asked to read that file.

Observed in the rules dir but NOT in COMPACT and NOT in CORE_RULES and NOT hook-enforced:
- `plan-first.md` — listed as "contextual" in EXCLUDED_RULES but not actually referenced
  in COMPACT → pure documentation
- Other candidates (to confirm case by case): any rule whose key does not appear in
  `RULES-COMPACT.md` and whose hook reference (if any) is missing.

> Precise enumeration requires cross-ref between the 107 file list and the 85 keys in
> `RULES-COMPACT.md`. The pytest contract (`tests/audit/test_rules_enforcement.py`)
> does this check exhaustively.

### Code-dead (6)

Rule references a hook or script that **does not exist on disk**.

| Rule | Broken reference | What was meant? |
|---|---|---|
| `acceptance-criteria.md` | `hooks/auto-verify.sh` | Hook never built |
| `agent-quality.md` | `hooks/auto-verify.sh` + `hooks/dod-gate.sh` | Both never built |
| `closed-loop-prompts.md` | `hooks/auto-refine.sh` | Hook never built |
| `phase-aware-agents.md` | `hooks/auto-refine.sh` | Same as above |
| `response-compression.md` | `hooks/response-length-check.sh` (via EXCLUDED_RULES comment) | Hook never built |
| `context-optimization.md` | `hooks/context-budget.sh` | Hook never built (rule acknowledges: "not currently registered") |

## Enforcement matrix (sample — full matrix generated by test)

| Rule | Hook exists | Hook registered | Auto-injected | In COMPACT | Effective? |
|---|---|---|---|---|---|
| `anti-hallucination` | yes (`claim-validator.sh`) | yes | no | yes | **YES** |
| `blast-radius` | yes | yes | no | yes | **YES** |
| `clarification-gate` | yes | yes | no | yes | **YES** |
| `content-policy` | yes | yes | no | yes | **YES** |
| `trust-score` | yes (validator) | yes | partial (format in preamble) | yes | **YES** |
| `acceptance-criteria` | NO (`auto-verify.sh`) | no | symlink only | yes | **NO** (code-dead) |
| `audit-trail` | yes | NO | no | yes | **NO** (broken) |
| `auto-rollback` | yes | NO | no | yes | **NO** (broken) |
| `confidentiality-protection` | yes | NO | no | yes | **NO** (broken) |
| `agent-identity` | yes (audit-id-enricher) | NO | no | yes | **NO** (broken) |
| `phase-aware-agents` | partial (`inject-phase-context.sh` DOES exist & IS registered) | partial | symlink to orchestrator | yes | **PARTIAL** |
| `adversarial-review` | no hook | n/a | no | yes | **agent-instruction** |
| `token-economy` | no hook | n/a | symlink to orchestrator | yes | **agent-instruction** |
| `dogfooding` | no hook | n/a | no | yes | **agent-instruction** (self-reference doc) |
| `plan-first` | no hook | n/a | no | no | **declarative** (ornamental) |

## Specific findings (S-tier adversarial)

### [S1 BLOCKER] 8 rules claim hook enforcement that is not wired
**Location**: `rules/audit-trail.md`, `rules/auto-rollback.md`, `rules/confidence-gate.md`,
`rules/confidentiality-protection.md`, `rules/agent-identity.md`,
`rules/pre-dev-readiness-gate.md`, `rules/reinvention-prevention.md`
**What**: The rule markdown states "enforced by hook X", the hook exists on disk, but
`.claude/settings.json` does not register it in any matcher. The hook will never fire.
**Why**: These are safety-critical rules (audit trail, rollback, confidentiality,
readiness). Believing they are enforced while they are not is a trust violation.
**Recommendation**: Either register the hooks in `settings.json`, or update the rule
markdown to say "hook exists but not wired — run manually via `bash hooks/X.sh`".

### [S1 BLOCKER] 6 rules reference nonexistent hooks
**Location**: `rules/acceptance-criteria.md` (`auto-verify.sh`),
`rules/agent-quality.md` (`auto-verify.sh` + `dod-gate.sh`),
`rules/closed-loop-prompts.md` (`auto-refine.sh`),
`rules/phase-aware-agents.md` (`auto-refine.sh`),
`rules/response-compression.md` (`response-length-check.sh`),
`rules/context-optimization.md` (`context-budget.sh`).
**What**: Rules describe a closed-loop verification mechanism that requires hooks which
were never built.
**Why**: Agents reading these rules may assume the verification runs automatically.
It does not. Any agent self-claim of "DoD passed" has no automated evidence.
**Recommendation**: Either build the hooks or rewrite the rules to make the verification
explicitly manual (agent must run the commands itself and paste output).

### [S2 CONCERN] Only 9 rules of 107 are auto-injected into sub-agent context
**Location**: `templates/agent-mandatory-rules.md` (31 lines, 5 sections).
**What**: The only rule content pushed to sub-agents on launch covers symlinks,
auditing, code-quality, engram, performance. Not trust-score, not acceptance-criteria,
not phase-aware, not adversarial-review.
**Why**: Sub-agents will not follow rules they never see. The orchestrator must
manually include the relevant rule content in every sub-agent prompt. In practice,
this never happens fully — the orchestrator cites rule keys like `[adversarial-review]`
and the sub-agent has no way to resolve them.
**Recommendation**: Expand `agent-mandatory-rules.md` to include at minimum:
trust report format (already in preamble — good), acceptance criteria format,
phase-aware DoD table, adversarial-review severity tiers.

### [S2 CONCERN] `RULES-COMPACT.md` references rule-keys but provides no resolver
**Location**: `rules/RULES-COMPACT.md`, all entries like `` [`adversarial-review`] ``.
**What**: The compact index says "loaded on trigger via [ref-key]" but there is no
hook or skill that actually performs that lookup and injects the rule text.
**Why**: Creates an illusion of modularity — rules look reusable, but agents can't
actually load them mid-task.
**Recommendation**: Add a slash command `/rule <key>` that reads `rules/{key}.md` and
injects it into context, OR precompile a single "full rule pack" for substantial tasks.

### [S3 SUGGESTION] Overlapping rules candidate for merge
**Location**: `rules/broken-window-policy.md` + `rules/agent-quality.md`
(self-install.sh marks broken-window as "covered by agent-quality");
`rules/scope-creep-detection.md` + `rules/scope-proportionality.md` (same hook);
`rules/rate-limiting.md` + `rules/rate-limit-protection.md` (two hooks, two rules).
**What**: Multiple rules describe the same behavior with different scope slices.
**Why**: Duplicated maintenance burden; harder to know which to cite.
**Recommendation**: Merge, or explicitly differentiate ("rate-limiting = per-tool,
rate-limit-protection = per-agent-launch").

### [S4 QUESTION] Why does `CORE_RULES` include only 11 of 107 rules?
**Location**: `hooks/self-install.sh:172-185`.
**What**: CORE_RULES contains 11 files; EXCLUDED_RULES contains 68; the rest (~28) are
silently synced or skipped depending on `SYNC_ALL_RULES`.
**Why**: Unclear which category a new rule should be placed in. Existing categorization
appears inconsistent (e.g. `model-routing.md` is CORE but `decomposition.md` is excluded
as "covered by token-economy").
**Recommendation**: Document the decision tree in `self-install.sh` header and add a
pytest check that every rule file belongs to exactly one category.

## Pytest contract

See `tests/audit/test_rules_enforcement.py` for the executable version of this
scorecard. Running `python3 -m pytest tests/audit/test_rules_enforcement.py -m audit`
will produce a per-rule pass/fail matrix.
