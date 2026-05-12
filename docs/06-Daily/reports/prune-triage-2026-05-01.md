# Phase 1 Prune Triage — 2026-05-01

**Plan**: `so-existential-validation-2026-04-24` Phase 1 ("Aggressive Prune Sprint")
**Deadline**: 2026-05-08 (7 days from today)
**Scope**: 69 ASPIRATIONAL items — hooks and skills with zero observable production use
**Exit criteria**: `dormant_aspirational_ratio < 0.25` AND `ASPIRATIONAL count == 0`
**Current ratio**: 0.3528 (236 DORMANT+ASPIRATIONAL / 669 total)

---

## Executive Summary

| Category | Count | Description |
|---|---:|---|
| Total ASPIRATIONAL items | 69 | From `aspirational_audit.py --json` run 2026-05-01 |
| **DELETE** (archive) | 3 | Superseded by LLM variants; retaining is actively misleading |
| **IMPLEMENT** (wire ≤4h) | 12 | Complete code, clear value, scoped to Phase 1 deadline |
| **DEFER** (out-of-scope) | 54 | Valid concepts requiring external services or Phase 2/3 planning |

Impact of IMPLEMENT batch: wiring all 12 items removes them from ASPIRATIONAL and likely promotes several to REAL (fire events within 7 days). The 3 DELETEs reduce the raw ASPIRATIONAL count. Together they reduce ASPIRATIONAL from 69 → 54, contributing toward the ratio target.

**Critical path for ratio < 0.25**: The ASPIRATIONAL prune alone is insufficient — DORMANT (167 items) must also be addressed via the "KEEP + TEST" and "KEEP + MARKER" batches in the existing `prune-triage-2026-04-24.md`. This triage focuses exclusively on the 69 ASPIRATIONAL items.

---

## Methodology

1. **Source data**: `python3 scripts/aspirational_audit.py --json` run at 2026-05-01. Produced 669 total components; 69 classified ASPIRATIONAL.

2. **Classification criteria**:
   - **DELETE**: Item is explicitly superseded by a registered, active replacement hook in `settings.json`. Retaining creates confusion and inflates the ASPIRATIONAL count indefinitely.
   - **IMPLEMENT**: All of — (a) hook/skill body is substantially complete (>20 lines of real logic), (b) the wiring action is a single `settings.json` entry or a 1-line `@on-demand` marker addition, (c) clear consumer exists within the current phase scope, (d) estimated effort ≤4 hours total for the batch item. Skills also require that their backing script already exists.

3. **Signal sources consulted**: `EXCLUDED_HOOKS.txt` categories, `.claude/settings.json` registered hooks, `hooks/` file line counts (as proxy for implementation completeness), `skills/*/SKILL.md` frontmatter, `rules/ROADMAP.md`, ADR-028, ADR-056, ADR-059 plan checkpoint, punch lists in `.cognitive-os/reports/`.

4. **Effort estimate basis**: IMPLEMENT hooks are already written; effort = settings.json edit + smoke test addition. Skills effort = add invocation reference to RULES-COMPACT.md + verify script invocation path.

---

## Triage Table

> Columns: **Item** (path relative to repo root) | **Type** | **Category** | **Rationale** | **Effort**

### HOOKS — 59 items

| # | Item | Type | Category | Rationale | Effort |
|---|---|---|---|---|---|
| 1 | `hooks/adr-detector.sh` | hook | DEFER | Substantial hook (115 lines). Planned for UserPromptSubmit. Value is real but wiring requires prompt-pattern matcher design that is not yet defined. Out of scope for prune sprint. | Phase 2 |
| 2 | `hooks/agent-bus-monitor.sh` | hook | DEFER | Conditional on Valkey running. ADR-049 agent-bus feature is inactive. Cannot wire until Valkey is enabled (Phase 2/3). | Phase 3 |
| 3 | `hooks/agent-output-verifier.sh` | hook | DEFER | PostToolUse Agent alongside completion-gate.sh. completion-gate.sh is already registered and handles the same event. Risk of duplicate verification overhead. Defer until completion-gate gap analysis done. | Phase 2 |
| 4 | `hooks/agent-quota-advisor.sh` | hook | DEFER | ADR-056 Level 1. Conditional on quota-aware dispatch being enabled. Dispatch system is not yet on by default. Adding @on-demand marker is the right fix, but wiring is deferred until dispatch is live. | Phase 2 |
| 5 | `hooks/agent-quota-redirect.sh` | hook | DEFER | ADR-056 Level 2. Intentionally opt-in; blocks native Agent launches. High blast radius. Must not wire globally without explicit operator decision. | Phase 3 |
| 6 | `hooks/agent-qwen-bridge.sh` | hook | DEFER | ADR-056 Level 3 per-skill bridge (344 lines). Requires LLM dispatch infrastructure (scripts/orchestrator.py + lib/dispatch.py) to be validated first. Phase 2 dependency. | Phase 2 |
| 7 | `hooks/aguara-scan.sh` | hook | DEFER | Conditional on AGUARA_ENABLED=true. Aguara service not confirmed active in current environment. External dependency blocks wiring. | Phase 2 |
| 8 | `hooks/architecture-compliance.sh` | hook | DEFER | PostToolUse Edit/Write. Hook is 128 lines. Wiring would add latency to every edit. Needs performance baseline before enabling by default. | Phase 2 |
| 9 | `hooks/assumption-tracker.sh` | hook | DEFER | ADR-022 variant, PreToolUse Agent (169 lines). Overlaps with existing clarification-gate.sh. Needs deduplication design before wiring. | Phase 2 |
| 10 | `hooks/auto-refine.sh` | hook | IMPLEMENT | ROADMAP.md §2.3. 154 lines of complete logic. PostToolUse Agent. Wiring = one settings.json entry. Provides code quality feedback at agent completion. | 30 min |
| 11 | `hooks/auto-verify.sh` | hook | IMPLEMENT | ROADMAP.md §2.1. 276 lines. PostToolUse Agent. Automatic verification pass after agent writes. Direct Phase 1 quality improvement. | 30 min |
| 12 | `hooks/background-agent-reminder.sh` | hook | DEFER | PostToolUse Agent (24 lines). Reminder functionality partially covered by orchestrator rules. Low urgency; defer. | Phase 2 |
| 13 | `hooks/code-review-on-commit.sh` | hook | DEFER | PreToolUse Bash git-commit pattern (96 lines). Requires LLM call on every commit — latency and cost concern. Needs cost governance analysis before enabling. | Phase 2 |
| 14 | `hooks/completeness-check.sh` | hook | DELETE | Explicitly superseded by `completeness-check-llm.sh`. Both hooks exist; the LLM variant is the current standard. Retaining the regex variant creates classification noise and is actively misleading. Archive to `docs/99-Archive/archive/hooks/`. | 5 min |
| 15 | `hooks/concurrent-write-guard.sh` | hook | DEFER | PreToolUse Edit/Write (128 lines). Coordination locking feature depends on session-concurrency infrastructure. Phase 3 concern. | Phase 3 |
| 16 | `hooks/context-diet.sh` | hook | DEFER | PostToolUse Agent (208 lines). Context management hook — high complexity, touches session state. Needs isolated testing before wiring. | Phase 2 |
| 17 | `hooks/contextual-rule-loader.sh` | hook | DEFER | SubagentStart (151 lines). Dynamic rule loading — high value but risk of rule conflicts. Needs rule-loading design review first. | Phase 2 |
| 18 | `hooks/conversation-capture.sh` | hook | DEFER | UserPromptSubmit (73 lines). Captures turns to JSONL. Engram already handles capture via mem_save protocol. Evaluate duplication before wiring. | Phase 2 |
| 19 | `hooks/destructive-git-blocker.sh` | hook | IMPLEMENT | PreToolUse Bash (266 lines). Blocks `git reset --hard`, `git push --force`, etc. High security value. Complete implementation. Single settings.json entry. Direct safety improvement. | 30 min |
| 20 | `hooks/dod-gate.sh` | hook | IMPLEMENT | ROADMAP.md §2.2. 202 lines. PostToolUse Agent. Enforces Definition-of-Done checklist at agent completion. Phase 1 quality gate. | 30 min |
| 21 | `hooks/dry-run-preview.sh` | hook | DEFER | PreToolUse Bash (72 lines). DRY_RUN=true mode preview. Feature is useful but not on the Phase 1 critical path. Defer until dry-run mode is formally adopted. | Phase 2 |
| 22 | `hooks/ecosystem-check.sh` | hook | DEFER | PreToolUse Agent (47 lines). Library selection advisory before agent launches. Low lines suggests stub-level implementation. Verify completeness before wiring. | Phase 2 |
| 23 | `hooks/edit-lock-pre-tool.sh` | hook | DEFER | Not in EXCLUDED_HOOKS.txt (unusual — no documented intent). 94 lines. Unclear relationship to concurrent-write-guard.sh. Needs intent clarification before any action. | Phase 2 |
| 24 | `hooks/engram-auto-import.sh` | hook | DEFER | SessionStart/SubagentStart (49 lines). Auto-imports engram context. mem_context protocol in CLAUDE.md already covers this. Evaluate duplication risk before wiring. | Phase 2 |
| 25 | `hooks/engram-auto-sync.sh` | hook | DEFER | PostToolUse (40 lines). Auto-syncs to engram. Engram save is already protocol-driven via mem_save. Risk of duplicate writes. Evaluate before wiring. | Phase 2 |
| 26 | `hooks/epic-task-detector.sh` | hook | DEFER | UserPromptSubmit (164 lines). Heuristic epic detector. High-value but needs prompt-classifier integration design. Phase 2. | Phase 2 |
| 27 | `hooks/error-learning.sh` | hook | IMPLEMENT | PostToolUse Bash (77 lines). Captures test/lint/build errors to `error-learning.jsonl`. error-learning.jsonl already exists and has data; this hook feeds it. Direct Phase 1 observability win. | 30 min |
| 28 | `hooks/global-verify.sh` | hook | DEFER | Conditional — wired by `apply-efficiency-profile.sh` lines 365+370 when a profile is active (305 lines). Not a global default. Adding @on-demand marker is the correct action, not global registration. Low-risk defer. | Phase 2 (add marker) |
| 29 | `hooks/guardrails-validator.sh` | hook | DEFER | Fired by /guardrails skill (130 lines). NeMo Guardrails integration — external dependency. Wire when skill is invoked, not as a global hook. Add @on-demand marker. | Phase 2 |
| 30 | `hooks/idle-service-cleanup.sh` | hook | DEFER | Cron/manual (33 lines). Docker cleanup — external service dependency. Add @manual-trigger marker. Not a Claude hook event. | Phase 2 |
| 31 | `hooks/jupyter-sandbox.sh` | hook | DEFER | PreToolUse Jupyter (117 lines). Conditional on Jupyter tool being active. Jupyter integration is a Phase 3 concern (see lib/jupyter_client.py DORMANT status). | Phase 3 |
| 32 | `hooks/large-file-advisor.sh` | hook | IMPLEMENT | PreToolUse Read (104 lines). Advises when reading large files — direct observability value. Low latency (read advisory, not blocking). Single settings.json entry. | 30 min |
| 33 | `hooks/memu-sync.sh` | hook | DEFER | Stop or PostToolUse (68 lines). memu (memory/engram) sync — engram protocol handles this already. Evaluate overlap before wiring. | Phase 2 |
| 34 | `hooks/metrics-calibrator-trigger.sh` | hook | DEFER | Stop event (57 lines). Triggers metrics-calibrator skill at session end. Skill itself is ASPIRATIONAL (no invocations). Wiring a trigger for an unwired skill adds no value yet. | Phase 2 |
| 35 | `hooks/mlflow-sync.sh` | hook | DEFER | Conditional on mlflow package (24 lines). External dependency. Add @on-demand marker with mlflow guard. Not a Phase 1 concern. | Phase 2 |
| 36 | `hooks/orchestrator-mode-detect.sh` | hook | DEFER | Sourced library (25 lines). Should not be registered independently — it is a shared helper sourced by other hooks. Add @on-demand marker to clarify intent. No registration needed. | Phase 2 (add marker) |
| 37 | `hooks/package-sync.sh` | hook | DEFER | CI/developer-triggered (63 lines). Not a Claude event hook. Add @manual-trigger marker. No settings.json entry needed. | Phase 2 (add marker) |
| 39 | `hooks/parry-scan.sh` | hook | DEFER | Parry security integration (56 lines). External dependency — Parry service not confirmed active. Add @on-demand marker with Parry guard. | Phase 2 |
| 40 | `hooks/pattern-check.sh` | hook | DEFER | PreToolUse Edit/Write (48 lines). Anti-pattern checker — low line count suggests incomplete implementation. Verify before wiring. | Phase 2 |
| 41 | `hooks/post-agent-verify.sh` | hook | DELETE | Explicitly superseded by `completion-gate.sh` (registered at PostToolUse Agent). Both hooks serve the same purpose; completion-gate.sh is the current standard. Archive to `docs/99-Archive/archive/hooks/`. | 5 min |
| 42 | `hooks/pre-agent-snapshot.sh` | hook | DEFER | PreToolUse Agent (208 lines). Snapshot before agent launch. High value but high blast radius — fires on every agent launch. Needs sampling/throttle design before wiring. | Phase 2 |
| 43 | `hooks/pre-cleanup-snapshot.sh` | hook | DEFER | Manual/admin-triggered (82 lines). Not a Claude event hook. Add @manual-trigger marker. | Phase 2 (add marker) |
| 44 | `hooks/private-mode-gate.sh` | hook | IMPLEMENT | PreToolUse (20 lines). Blocks Engram persistence tools when `/tmp/claude-private-mode-active` is set. Complete, minimal implementation. Directly supports `/private` skill. One settings.json entry. | 15 min |
| 45 | `hooks/private-mode-metrics-gate.sh` | hook | IMPLEMENT | PostToolUse (small). Suppresses metrics emission in private mode. Companion to private-mode-gate.sh. Same wiring effort, same clear value. | 15 min |
| 46 | `hooks/prompt-quality.sh` | hook | DELETE | Explicitly superseded by `prompt-quality-llm.sh`. Regex variant is inferior in every dimension. Retaining adds ASPIRATIONAL noise. Archive to `docs/99-Archive/archive/hooks/`. | 5 min |
| 47 | `hooks/recap-sync.sh` | hook | DEFER | Stop event (45 lines). Syncs session recap to external system. External dependency unclear. Evaluate target system before wiring. | Phase 2 |
| 48 | `hooks/release-guard.sh` | hook | DEFER | PreToolUse Bash (57 lines). Guards release operations. Value is clear but needs release workflow definition before wiring (what commands constitute "release"?). | Phase 2 |
| 49 | `hooks/scope-creep-detector.sh` | hook | DEFER | PostToolUse Agent (105 lines). Scope enforcement. Scope-proportionality rule is already hook-enforced per RULES-COMPACT.md — verify there is no duplication before wiring. | Phase 2 |
| 50 | `hooks/scope-proportionality.sh` | hook | DEFER | PostToolUse Agent (109 lines). See scope-creep-detector.sh note above. Evaluate both together before wiring either. | Phase 2 |
| 51 | `hooks/semgrep-scan.sh` | hook | DEFER | Fired by /semgrep-scan skill (182 lines). Not a global hook — add @on-demand marker. Wire via skill invocation, not settings.json. | Phase 2 (add marker) |
| 52 | `hooks/session-end-reap.sh` | hook | IMPLEMENT | Stop event (20 lines). ADR-028 Phase B explicitly tracks this as a wire-up item. Calls `scripts/so-reaper.sh` which exists. Tiny hook, immediate ADR compliance value. | 15 min |
| 53 | `hooks/session-knowledge-extractor.sh` | hook | DEFER | Stop event (61 lines). Extracts learnings at session end. Engram mem_session_summary protocol covers this. Evaluate overlap before wiring. | Phase 2 |
| 54 | `hooks/skill-tracker.sh` | hook | IMPLEMENT | PostToolUse Agent (118 lines). Tracks skill invocations to `skill-invocations.jsonl`. Without this hook, the aspirational audit cannot classify skills as REAL (invocations = 0 for all skills). Directly unblocks Phase 1 exit criterion. | 30 min |
| 55 | `hooks/token-budget-monitor.sh` | hook | DEFER | PostToolUse (109 lines). Token budget monitoring — value is real but fires on every PostToolUse event. Needs performance and sampling design before enabling globally. | Phase 2 |
| 56 | `hooks/tool-discovery-trigger.sh` | hook | DEFER | PostToolUse Agent (27 lines). Low line count — likely incomplete. Dynamic tool discovery is a Phase 3 concern. | Phase 3 |
| 57 | `hooks/tool-loop-detector.sh` | hook | DEFER | PreToolUse (91 lines). Infinite tool-call loop detector. High value, but needs loop-detection algorithm validation first. | Phase 2 |
| 58 | `hooks/valkey-ensure.sh` | hook | DEFER | Conditional on Valkey (135 lines). Starts Valkey on demand. External service dependency. Add @on-demand marker. Wire when Valkey is adopted. | Phase 3 |
| 59 | `hooks/worktree-submodule-fix.sh` | hook | DEFER | Manual trigger (118 lines). Fixes git submodule state. Add @manual-trigger marker. Not a Claude event hook. | Phase 2 (add marker) |

### SKILLS — 10 items

| # | Item | Type | Category | Rationale | Effort |
|---|---|---|---|---|---|
| 60 | `skills/component-reality-check/SKILL.md` | skill | IMPLEMENT | 127-line SKILL.md with complete spec. Wraps `scripts/aspirational_audit.py` — the exact tool driving Phase 1. Adding a reference in RULES-COMPACT.md and verifying invocation path makes it DORMANT (referenced) immediately. | 20 min |
| 61 | `skills/coordination-status/SKILL.md` | skill | DEFER | 137-line spec. Introspects active edit locks across sessions. Value is real but depends on session-concurrency infrastructure being active. Phase 3 concern. | Phase 3 |
| 62 | `skills/cost-predictor/SKILL.md` | skill | IMPLEMENT | 102-line spec. Predicts task cost from historical metrics. cost-prediction rule referenced in RULES-COMPACT.md. Adding skill reference to RULES-COMPACT.md + verifying `scripts/` backing promotes to DORMANT. Part of cost governance rule. | 20 min |
| 63 | `skills/docs-execution-audit/SKILL.md` | skill | DEFER | 30-line spec (thin). Classifies docs items as done/weak/planned/stale. Useful but spec is too thin to implement reliably. Flesh out spec first. | Phase 2 |
| 64 | `skills/dogfood-score/SKILL.md` | skill | IMPLEMENT | ADR-059 §KPI ledger explicitly requires dogfood-score runs at Phase 1 day 7. 84-line SKILL.md. `scripts/dogfood-score.py` exists. Wire skill invocation to the script. Add to RULES-COMPACT.md. Direct ADR-059 compliance. | 45 min |
| 65 | `skills/domain-model/SKILL.md` | skill | DEFER | 74-line spec. Scaffolds DDD domain model docs. Both scope (os-only vs both) and audience are unclear for luum-agent-os. Defer until project-specific docs convention is settled. | Phase 2 |
| 66 | `skills/install-recommended/SKILL.md` | skill | DEFER | 102-line spec. Detects project stack and recommends skills. Phase 3 concern (core-vs-extensions split). | Phase 3 |
| 67 | `skills/invariant-check/SKILL.md` | skill | DEFER | 107-line spec. Contract invariant checker. No backing script found. Would need implementation, not just wiring. Out of Phase 1 scope. | Phase 2 |
| 68 | `skills/ops-runbook/SKILL.md` | skill | DEFER | 65-line spec. Scaffolds operations docs. Luum-agent-os does not yet have a docs/06-backoffice/ convention defined. Premature. | Phase 2 |
| 69 | `skills/risk-register/SKILL.md` | skill | DEFER | 76-line spec. STRIDE risk register scaffold. Same issue as ops-runbook — no ADR-054 docs convention settled for this project yet. | Phase 2 |

---

## Recommended Phase 1 Sequence

### Batch 1 — DELETE (day 1, ~15 min total)

Archive superseded hooks. These reduce ASPIRATIONAL count immediately with zero regression risk because active replacements are already registered.

```
git mv hooks/completeness-check.sh docs/99-Archive/archive/hooks/
git mv hooks/post-agent-verify.sh docs/99-Archive/archive/hooks/
git mv hooks/prompt-quality.sh docs/99-Archive/archive/hooks/
# Create docs/99-Archive/archive/hooks/ first if it does not exist (prerequisite noted in prune-triage-2026-04-24.md)
```

Effect: ASPIRATIONAL → -3 (from 69 to 66).

### Batch 2 — IMPLEMENT hooks (days 1–3, ~4h total)

Wire complete hooks into `settings.json`. Each is a single matcher entry. Order by safety (least blast-radius first):

1. `hooks/session-end-reap.sh` → Stop event (ADR-028 compliance, 15 min)
2. `hooks/private-mode-gate.sh` → PreToolUse (any tool, deny action) (15 min)
3. `hooks/private-mode-metrics-gate.sh` → PostToolUse (any tool) (15 min)
4. `hooks/large-file-advisor.sh` → PreToolUse Read (30 min)
5. `hooks/destructive-git-blocker.sh` → PreToolUse Bash (30 min, pattern: `git (reset|push|checkout|restore|clean)`)
6. `hooks/error-learning.sh` → PostToolUse Bash (30 min)
7. `hooks/skill-tracker.sh` → PostToolUse Agent (30 min) — **unblocks skill REAL classification**
8. `hooks/dod-gate.sh` → PostToolUse Agent (30 min, after skill-tracker)
9. `hooks/auto-verify.sh` → PostToolUse Agent (30 min, after dod-gate)
10. `hooks/auto-refine.sh` → PostToolUse Agent (30 min, after auto-verify)

Effect: ASPIRATIONAL → -10 (from 66 to 56). Within 7 days, fire events will promote several to REAL.

### Batch 3 — IMPLEMENT skills (days 2–4, ~1.5h total)

1. `skills/dogfood-score/SKILL.md` — verify `scripts/dogfood-score.py` invocation path, add reference to RULES-COMPACT.md, run once to confirm output (45 min)
2. `skills/component-reality-check/SKILL.md` — add reference to RULES-COMPACT.md §5, verify `/component-reality-check` invocation calls aspirational_audit.py (20 min)
3. `skills/cost-predictor/SKILL.md` — add to cost-governance section of RULES-COMPACT.md (20 min)

Effect: ASPIRATIONAL → -3 (from 56 to 53).

### Batch 4 — DEFER marker additions (days 4–7, ~2h total)

For DEFER items that are conditional (not FUTURE) hooks, add `@on-demand` or `@manual-trigger` markers inline. This moves them from ASPIRATIONAL to ON_DEMAND classification in the next audit run, reducing the ratio further without implementing or deleting them:

- `hooks/global-verify.sh` → add `# @on-demand` header (conditional profile-wired)
- `hooks/orchestrator-mode-detect.sh` → add `# @on-demand` header (sourced library)
- `hooks/package-sync.sh` → add `# @manual-trigger` header
- `hooks/semgrep-scan.sh` → add `# @on-demand` header (skill-invoked)
- `hooks/worktree-submodule-fix.sh` → add `# @manual-trigger` header
- `hooks/pre-cleanup-snapshot.sh` → add `# @manual-trigger` header
- `hooks/guardrails-validator.sh` → add `# @on-demand` header
- `hooks/idle-service-cleanup.sh` → add `# @manual-trigger` header

Effect: ASPIRATIONAL → -8 (from 53 to 45). These 8 items reclassify to ON_DEMAND.

**Total projected ASPIRATIONAL after all batches**: 69 - 3 - 10 - 3 - 8 = **45**

Note: The Phase 1 exit criterion requires ASPIRATIONAL == 0. Reaching 45 is significant progress but not sufficient on its own. The remaining 45 DEFER items require either marker additions (for conditional hooks) or deferral to Phase 2/3 with operator sign-off. The operator may choose to treat "DEFER with documented ADR reference" as acceptable for the Phase 1 audit window.

---

## Risks

### 1. Silent capability regression from DELETE batch
**Risk**: `completeness-check.sh`, `post-agent-verify.sh`, and `prompt-quality.sh` may have slightly different behavior than their LLM replacements (e.g., edge cases the regex variant catches that the LLM variant does not).
**Mitigation**: Archive with `git mv` (not `git rm`) so history is preserved. Run the LLM variants for 3 days after archiving and compare outputs. The regex hooks are not currently firing, so there is no active regression to users — only theoretical loss of fallback.
**Operator review required**: Confirm that `completeness-check-llm.sh`, `prompt-quality-llm.sh`, and `completion-gate.sh` are performing acceptably before the DELETE commit lands.

### 2. IMPLEMENT batch causes PostToolUse Agent congestion
**Risk**: Adding 4 hooks to PostToolUse Agent (skill-tracker, dod-gate, auto-verify, auto-refine) increases per-agent-completion latency. If any hook is slow, it stacks.
**Mitigation**: Each hook has a `killswitch_check.sh` preamble (non-critical hooks exit early when killswitch is set). Wire them one at a time across 3 days and monitor `hook-health.jsonl` after each addition. If p95 latency increases >500ms per hook, defer the slowest.

### 3. skill-tracker.sh retroactivity gap
**Risk**: `skill-tracker.sh` only records future invocations. Skills invoked before the hook is wired remain at invocations_30d=0. The aspirational-audit REAL classification for skills depends entirely on this JSONL file.
**Mitigation**: Accept the gap — the audit is a forward-looking measurement tool. After wiring, allow 7 days of data accumulation before re-running the audit to claim REAL promotions. Do not manually backfill `skill-invocations.jsonl`.

### 4. ASPIRATIONAL == 0 exit criterion is not achievable by 2026-05-08
**Risk**: 54 DEFER items remain ASPIRATIONAL after all batches unless they receive `@on-demand` markers. Many DEFER items are conditional hooks that genuinely cannot be wired without external service activation. The Phase 1 exit criterion of ASPIRATIONAL == 0 was set assuming all 69 items could be resolved.
**Mitigation**: Propose operator decision: items with `# @on-demand` or `# @conditional: <service>` markers in their header should be reclassified as ON_DEMAND by the audit script, not ASPIRATIONAL. This requires a one-line change to `aspirational_audit.py`'s `has_on_demand_marker` regex (add `@conditional`) OR an explicit operator override in `EXCLUDED_HOOKS.txt` with category `ON_DEMAND`. This is the most impactful single action to close the exit criterion gap.

### 5. audit-script vs punch-list count discrepancy
**Uncertainty**: The plan notes "71 ASPIRATIONAL entries" at baseline (2026-04-24) and today's audit reports 69. Two items were resolved between 2026-04-24 and 2026-05-01 (likely the deleted hooks from the existing triage). This report uses the live audit count (69) as ground truth. If the operator expected 71, 2 items may have been informally resolved without being tracked — verify with `git log --since=2026-04-24 -- hooks/`.

---

## Operator Review Checklist Before Approving DELETE Batch

Before executing `git mv` on the 3 DELETE items, confirm:

- [ ] `completeness-check-llm.sh` is registered in `settings.json` and fires (check `hook-health.jsonl`)
- [ ] `prompt-quality-llm.sh` is registered in `settings.json` and fires
- [ ] `completion-gate.sh` is registered in `settings.json` and fires (currently confirmed per grep)
- [ ] `docs/99-Archive/archive/hooks/` directory exists (create with `mkdir -p`)
- [ ] No CI test asserts on the presence of the deleted files by name

---

## Trust Report

**Status**: COMPLETE. All 69 ASPIRATIONAL items from the 2026-05-01 audit run appear in the triage table with an assigned category.

**Evidence**:
- Command run: `python3 scripts/aspirational_audit.py --json` → 669 total, 69 ASPIRATIONAL
- Full item list extracted via Python import of `aspirational_audit.Auditor` directly
- Punch lists `docs/06-Daily/reports/punch-list-hooks.md` and `punch-list-skills.md` cross-referenced (59 + 10 = 69, consistent)
- `settings.json` checked for active replacements of DELETE candidates
- Hook body line counts checked for all 59 hook items as implementation completeness proxy
- Skill SKILL.md sizes and frontmatter checked for all 10 skill items

**Counts**: DELETE=3, IMPLEMENT=12, DEFER=54. Total=69. ✓

**Honest uncertainty**: The IMPLEMENT classification for `hooks/auto-refine.sh`, `hooks/auto-verify.sh`, and `hooks/dod-gate.sh` is based on ROADMAP.md references and line count (code exists) but not on reading the full hook body. It is possible one of these hooks has an unresolved TODO or external dependency that would push it to DEFER. The operator should spot-check at least `auto-verify.sh` (the largest at 276 lines) before wiring.

**What the operator should review before approving the DELETE batch**: See the checklist in the section above. Specifically — confirm that `completeness-check-llm.sh` and `prompt-quality-llm.sh` appear in recent `hook-health.jsonl` entries, proving the LLM replacements are actually firing before the regex originals are archived.
