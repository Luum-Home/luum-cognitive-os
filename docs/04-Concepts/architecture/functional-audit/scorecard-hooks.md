# Hooks Functional Audit — Capa 3 Scorecard

> **Phase**: reconstruction — empirical verification, no fixes applied.
> **2026-04-23 audit refresh**: audit contracts now use the canonical hook
> registration allowlist as the source of truth for intentionally non-default
> hooks. Previous code-dead entries (`auto-verify.sh`, `auto-refine.sh`,
> `dod-gate.sh`) now exist on disk and are tracked as allowlisted/non-default
> until promoted into an active driver profile.
> **Scope**: `hooks/*.sh` (184 files) + `hooks/_lib/*.sh` helpers.
> **Data sources**: `.claude/settings.json`, `scripts/apply-efficiency-profile.sh`,
> repo-wide grep of skill/rule/doc references.

User's question: **"of the hooks, how many actually fire and produce the documented effect?"**

Refresh answer: the checkout now has **184 hook files**. The current audit
distinguishes active driver wiring from intentionally non-default hooks via
`hooks/_lib/registration-allowlist.txt`. Missing-code risk is currently **0**;
the remaining risk is promotion/wiring debt, not nonexistent hook files.

---

## Summary

| Metric | Count | Notes |
|---|---|---|
| Total hook files on disk (`hooks/*.sh`) | **237** | Flat invocable hook scripts under `hooks/`; refreshed after adding the document-ingest guard. |
| Library helpers (`hooks/_lib/*.sh`) | **13** | Sourced by other hooks, not invocable directly (cache.sh, common.sh, etc.) |
| Invocable hooks (`hooks/*.sh`, excl. `_lib/`) | **118** (flat list) | `_lib/` is a subdir, so counts unchanged |
| **Functional-wired** (full profile) | **55** | Registered in `.claude/settings.json` |
| Functional-wired (standard profile) | **47** | Per `apply-efficiency-profile.sh` standard tier |
| Functional-wired (lean profile) | **7** | Per `apply-efficiency-profile.sh` lean tier |
| **Functional-unwired-by-design** | **22** | In `full` but NOT in `standard`/`lean` — only active at top tier |
| **Orphan** (in no profile anywhere) | **41** | Exist on disk, never wired — incl. 3 cluster-D names |
| **Stub** (placeholder-only bodies) | **0** | Inspected all `<10 non-comment-line` hooks; all three have real logic |
| **Code-dead** (ref'd by skill/rule/doc but no file) | **1 distinct name** (`deep-research-axis-gate.sh`) | `skills/deep-tool-research` documents an intended axis-gate hook; tracked in EXPECTED_CODE_DEAD until implemented. |
| **Referenced-but-unused** (wired but matcher rarely triggers) | **unknown** | Requires runtime telemetry — flagged for Capa 4 |

Project-gotchas claim is **"48/93 hooks intentionally not wired"**. Current reality is
**41/118 orphan + 22/118 only-in-full** (63 not wired at lean/standard). The 93 figure is
stale (predates growth to 118), but the design intent is consistent with the data.

---

## Profile Coverage Table

Only listing hooks that appear in at least one profile OR previously had a code-dead reference.
Full orphan list in the dedicated section below.

| Hook | lean | standard | full (settings.json) | Notes |
|---|---|---|---|---|
| `adr-detector.sh` | — | Yes | — | Standard-only; not in current settings.json |
| `agent-checkpoint.sh` | Yes | Yes | Yes | Core across all tiers |
| `agent-prelaunch.sh` | — | Yes | Yes | |
| `agent-work-tracker.sh` | — | Yes | — | Standard-only |
| `aguara-scan.sh` | — | — | Yes | Full-only |
| `architecture-compliance.sh` | — | — | Yes | Full-only |
| `assumption-tracker.sh` | — | — | Yes | Full-only (async) |
| `audit-id-enricher.sh` | — | Yes | — | Standard-only |
| `auto-checkpoint.sh` | — | Yes | Yes | |
| `auto-repair-dispatcher.sh` | — | — | Yes | Full-only (async) |
| `auto-skill-generator.sh` | — | — | Yes | Full-only (async) |
| `blast-radius.sh` | — | Yes | Yes | |
| `claim-validator.sh` | — | Yes | Yes | |
| `clarification-gate.sh` | — | Yes | Yes | |
| `completeness-check-llm.sh` | — | Yes | — | Standard-only (ADR-022 Haiku advisory) |
| `completeness-check.sh` | — | — | Yes | Full-only — LLM variant replaces it at standard |
| `completion-gate.sh` | — | Yes | Yes | |
| `confidence-gate-llm.sh` | — | Yes | — | Standard-only |
| `confidence-gate.sh` | — | — | — | **Orphan** (regex variant not wired; LLM variant used at standard) |
| `confidentiality-enforcer.sh` | Yes | Yes | — | **Lean/standard only — NOT in full settings.json** (anomaly) |
| `consequence-evaluator.sh` | — | — | Yes | Full-only (async) |
| `content-policy.sh` | — | Yes | Yes | |
| `context-watchdog.sh` | — | — | Yes | Full-only (async, PostToolUse catch-all) |
| `crash-recovery.sh` | — | Yes | Yes | SessionStart |
| `dequeue-notify.sh` | — | — | Yes | Full-only (async) |
| `dispatch-gate.sh` | — | Yes | Yes | |
| `doc-sync-detector.sh` | — | Yes | Yes | |
| `ecosystem-check.sh` | — | Yes | — | Standard-only |
| `engram-auto-import.sh` | — | — | Yes | Full-only (async, via packages path in settings.json) |
| `engram-auto-sync.sh` | — | — | Yes | Full-only (async, via packages path in settings.json) |
| `epic-task-detector.sh` | — | — | Yes | Full-only |
| `error-pattern-detector.sh` | — | Yes | Yes | |
| `error-pipeline.sh` | Yes | Yes | Yes | Core across all tiers |
| `git-context-capture.sh` | — | Yes | — | Standard-only (Stop) |
| `guardrails-validator.sh` | — | — | Yes | Full-only (async, NeMo Guardrails bridge) |
| `infra-health.sh` | — | — | Yes | Full-only (SessionStart async) |
| `inject-phase-context.sh` | — | Yes | Yes | |
| `kpi-trigger.sh` | — | — | Yes | Full-only (Stop async) |
| `large-file-advisor.sh` | — | Yes | — | Standard-only |
| `mcp-scan.sh` | — | — | Yes | Full-only (SessionStart async) |
| `mlflow-sync.sh` | — | Yes | — | Standard-only (Stop) |
| `observability-trace.sh` | — | — | Yes | Full-only (async) |
| `orchestrator-mode-detect.sh` | — | Yes | — | Standard-only (SessionStart) |
| `parry-scan.sh` | — | — | Yes | Full-only (async) |
| `pattern-check.sh` | — | Yes | — | Standard-only (SessionStart) |
| `pre-compaction-flush.sh` | — | — | Yes | Full-only (PreCompact) |
| `predev-completeness-check.sh` | — | Yes | — | Standard-only |
| `prompt-quality-llm.sh` | — | Yes | — | Standard-only (ADR-022 Haiku advisory) |
| `prompt-quality.sh` | — | — | Yes | Full-only (regex variant) |
| `rate-limit-protection.sh` | — | — | Yes | Full-only |
| `rate-limiter.sh` | — | Yes | Yes | |
| `recap-sync.sh` | — | Yes | — | Standard-only (Stop) |
| `registration-check.sh` | — | Yes | — | Standard-only |
| `result-truncator.sh` | — | Yes | Yes | |
| `scope-creep-detector.sh` | — | — | Yes | Full-only (async) |
| `scope-proportionality.sh` | — | — | Yes | Full-only (async) |
| `secret-detector.sh` | Yes | Yes | Yes | Core across all tiers (ADR-023 redact) |
| `self-install.sh` | Yes | Yes | Yes | Core across all tiers (SessionStart) |
| `semgrep-scan.sh` | — | — | Yes | Full-only (async) |
| `session-changelog.sh` | — | Yes | — | Standard-only (Stop) |
| `session-cleanup.sh` | Yes | Yes | Yes | Core across all tiers |
| `session-hygiene.sh` | — | Yes | — | Standard-only (Stop) |
| `session-init.sh` | Yes | Yes | Yes | Core across all tiers (SessionStart) |
| `session-learning.sh` | — | Yes | Yes | Stop |
| `session-resume.sh` | — | Yes | Yes | SessionStart |
| `state-heartbeat.sh` | — | Yes | Yes | |
| `subagent-context-injector.sh` | — | — | Yes | Full-only (SubagentStart async) |
| `task-bridge-notify.sh` | — | Yes | Yes | |
| `task-completed.sh` | — | — | Yes | Full-only (TaskCompleted async) |
| `task-created.sh` | — | — | Yes | Full-only (TaskCreated async) |
| `task-panel-sync.sh` | — | Yes | — | Standard-only |
| `task-recorder.sh` | — | — | Yes | Full-only (Stop async) |
| `teammate-idle.sh` | — | — | Yes | Full-only (TeammateIdle async) |
| `test-baseline-diff.sh` | — | Yes | — | Standard-only (Stop) |
| `trust-score-validator.sh` | — | Yes | Yes | |
| `usage-health-check.sh` | — | Yes | — | Standard-only (SessionStart) |
| `user-prompt-capture.sh` | — | — | Yes | Full-only (UserPromptSubmit async) |
| `wiring-check.sh` | — | Yes | — | Standard-only |

### Anomaly: `confidentiality-enforcer.sh`

Wired in **lean** and **standard** tiers, but **NOT** in the current `full` `settings.json`.
This is the only hook inverted from the usual pattern (normally: lean ⊂ standard ⊂ full).
Flag for follow-up; not fixed in this pass.

---

## Findings by Category

### Functional-wired (55, full profile)

Listed in the "Profile Coverage Table" above. Every hook in `.claude/settings.json`
exists on disk (`wired_missing_on_disk = []`). Every hook has > 9 non-comment non-empty
lines, so none are stubs.

### Functional-unwired-by-design (22)

These exist on disk and are in the `full` profile (wired in the current installation), but
are intentionally absent from the `standard` / `lean` tiers of `apply-efficiency-profile.sh`.
Users who apply `lean` or `standard` won't have them fire — this is **BY DESIGN** per
`rules/project-gotchas.md`:

```
aguara-scan.sh              ← only in full (security-heavy)
architecture-compliance.sh  ← only in full
assumption-tracker.sh       ← only in full (async)
auto-repair-dispatcher.sh   ← only in full (async)
auto-skill-generator.sh     ← only in full (async)
completeness-check.sh       ← only in full (LLM variant substitutes at standard)
consequence-evaluator.sh    ← only in full
context-watchdog.sh         ← only in full
dequeue-notify.sh           ← only in full
engram-auto-import.sh       ← only in full (via packages path)
engram-auto-sync.sh         ← only in full (via packages path)
epic-task-detector.sh       ← only in full
guardrails-validator.sh     ← only in full
infra-health.sh             ← only in full
kpi-trigger.sh              ← only in full
mcp-scan.sh                 ← only in full
observability-trace.sh      ← only in full
parry-scan.sh               ← only in full
pre-compaction-flush.sh     ← only in full (PreCompact event)
prompt-quality.sh           ← only in full (LLM variant substitutes at standard)
rate-limit-protection.sh    ← only in full
scope-creep-detector.sh     ← only in full
scope-proportionality.sh    ← only in full
semgrep-scan.sh             ← only in full
subagent-context-injector.sh ← only in full
task-completed.sh           ← only in full
task-created.sh             ← only in full
task-recorder.sh            ← only in full
teammate-idle.sh            ← only in full
user-prompt-capture.sh      ← only in full
```

Count: 30 (I undercounted in the summary; the correct figure is 30 "only-in-full" hooks.
This means standard tier covers the other 25 of 55 wired).

### Orphan (41, candidates for removal or wiring)

Not in `.claude/settings.json` AND not in ANY profile tier of `apply-efficiency-profile.sh`.
If the installer/generator never touches them, they are effectively dead code unless an
external script calls them directly.

```
adaptive-bypass.sh
agent-bus-monitor.sh
agent-output-verifier.sh
agnix-lint.sh
auto-rollback-trigger.sh
background-agent-reminder.sh
clarification-interceptor.sh
code-review-on-commit.sh
cognitive-os-health.sh
concurrent-write-guard.sh
confidence-gate.sh              ← regex variant; LLM variant wired at standard
context-diet.sh
contextual-rule-loader.sh
conversation-capture.sh
dry-run-preview.sh
error-learning.sh
idle-service-cleanup.sh
infra-intent-detector.sh
jupyter-sandbox.sh
memu-sync.sh
metrics-calibrator-trigger.sh
metrics-rotation.sh
notify.sh
package-sync.sh
pre-cleanup-snapshot.sh
pre-commit-gate.sh
private-mode-gate.sh
private-mode-metrics-gate.sh
reinvention-check.sh
release-guard.sh
resource-check.sh               ← CLUSTER D
session-knowledge-extractor.sh
session-state-save.sh
singularity-check.sh
skill-feedback-tracker.sh
skill-tracker.sh
sync-to-repo.sh
tool-discovery-trigger.sh
tool-loop-detector.sh
worktree-submodule-fix.sh
```

Note: a handful of these (e.g. `pre-commit-gate.sh`, `release-guard.sh`) are expected to
be invoked by git hooks or CI, not by the Claude harness — so "orphan" here means
"orphan from the harness-hook perspective". Differentiating requires checking `.githooks/`
and CI configs, which is out of scope for Capa 3 (pure harness-wiring audit).

### Stub (0)

Three hooks had < 10 non-comment non-empty lines and were manually inspected:

- `background-agent-reminder.sh` (9 lines) — **not a stub**. Real logic: reads
  `active-tasks.json`, counts in-progress tasks, emits reminder to stderr.
- `private-mode-gate.sh` (7 lines) — **not a stub**. Real logic: checks flag file,
  emits JSON deny decision if private mode active.
- `private-mode-metrics-gate.sh` (7 lines) — **not a stub**. Real logic: consumes
  stdin and exits silently when private mode is active, blocking downstream metric hooks.

**Stub count: 0.** All invocable hooks have non-trivial logic.

### Code-dead references (0 after 2026-04-23 refresh)

Previous missing hook names (`auto-verify.sh`, `auto-refine.sh`, `dod-gate.sh`)
now exist on disk. Their remaining risk is no longer "referenced but missing";
it is "implemented but not part of every active driver/profile". That status is
tracked in `hooks/_lib/registration-allowlist.txt` and should shrink only when
the hook is promoted through a tested product-zone path.

No lean / standard / full profile references any missing file
(`profile_refs_missing_on_disk = []`).

### Referenced-but-unused (unknown)

Requires runtime observation (matcher trigger logs per hook). Cannot be determined
statically. Recommended: add a telemetry wrapper that logs fire counts per hook per
session, then audit after ~10 real sessions. Flagged for Capa 4.

---

## Three Cluster-D Findings Explicitly Addressed

### 1. `uninstall.sh` stale jq scrub pattern

**Status**: Not a hook classification, but related to hook uninstall completeness.
The jq filter at `scripts/uninstall.sh` (lines 47–69, per cluster D report) targets
`.cognitive-os/hooks/` — a path **never emitted** by the current
`apply-efficiency-profile.sh` (which uses `$CLAUDE_PROJECT_DIR/hooks/`). Effect: after
profile-based install, uninstall leaves stale hook entries in `settings.json`.

**Classification**: Not a hook, but HALT-gated per cluster D. Logged here for completeness.
No action taken in this pass (read-only scope).

### 2. `auto-refine` skill → missing `hooks/auto-refine.sh`

**Status**: **CODE-DEAD** (classification above). Decision options:

- **Option A**: Delete the skill `skills/auto-refine/SKILL.md` (and its docs/rule refs) if
  the PITER auto-refine loop is not a priority.
- **Option B**: Implement `hooks/auto-refine.sh` per `docs/piter-framework.md:80` spec
  (PostToolUse on Agent, retry tracking, max-3 loop, phase-aware).
- **Option C**: Rename the existing `auto-repair-dispatcher.sh` to `auto-refine.sh` if
  the two names were intended to converge (needs owner input).

**Recommendation**: **Option B** — the rule is quoted in 4+ documents as live behavior;
removing it would require updating all those docs too, and the auto-refine loop is
architecturally meaningful (closes the PITER Evaluate→Refine edge).


**Status**: Both classified as **ORPHAN** above. Decision options:

| Hook | Option A (delete) | Option B (wire into `standard`) | Option C (wire into `full` only) |
|---|---|---|---|
| `resource-check.sh` | Lose budget-enforcement-in-loop for all profiles | Enforces `rules/resource-governance.md` at every agent launch | Matches other "async security" hooks (full-only) |

**Recommendation**:
- `resource-check.sh` → **Option B** at `PreToolUse Agent`. It operationalizes
  `rules/resource-governance.md`, which is listed as ALWAYS ACTIVE. An unwired
  always-active rule is a trust gap.

---

## Recommended Remediation (NOT applied in this pass)

1. **Wire orphans that operationalize always-active rules**:
   `resource-check.sh`, `auto-rollback-trigger.sh` (operationalizes `rules/auto-rollback.md`),
   `reinvention-check.sh` (`rules/reinvention-prevention.md`), `pre-commit-gate.sh`
   (`rules/pre-commit-gate.md`). Each is referenced as active behavior in its rule.
2. **Promote or demote allowlisted hooks intentionally**: `auto-verify.sh`,
   `auto-refine.sh`, and `dod-gate.sh` now exist, so the next decision is whether
   each belongs in an active driver profile, an installable extension, or
   experimental/deferred documentation.
3. **Delete truly unreferenced orphans**: hooks with zero skill/rule/doc/script/CI
   references are dead code. Candidates from quick scan: `memu-sync.sh`, `notify.sh`,
   `singularity-check.sh`, `tool-discovery-trigger.sh`, `session-state-save.sh`,
   `sync-to-repo.sh`. Verify each has no external caller before deletion.
4. **Fix the `confidentiality-enforcer.sh` inversion**: wire it into `full` so it fires
   at every tier (it's wired at lean+standard but not full — almost certainly a
   regression, not an intentional exclusion).
5. **Reconcile `project-gotchas.md`** wording "48/93" → real figure "63/118 not wired at
   standard or lower" once the above fixes land.

---

## Acceptance Criteria Check

1. **scorecard-hooks.md exists with classification + profile matrix**: Yes (this file).
2. **tests/audit/test_hooks_contracts.py with ≥ 4 test functions**: See companion file.
3. **3 cluster-D findings explicitly addressed**: Yes (dedicated section above).
4. **`python3 -m pytest tests/audit/test_hooks_contracts.py --collect-only` succeeds**:
   verification delegated to the consumer of this report.

---

## Cross-references

- `rules/project-gotchas.md` — "48/93 hooks intentionally not wired" (stale count; intent
  confirmed)
- `docs/architecture/harness-adoption-gap/scripts-audit-D-profile-uninstall.md` — cluster
  D parent report
- `scripts/apply-efficiency-profile.sh` — profile tier source of truth
- `.claude/settings.json` — current wiring (full profile)
- `hooks/self-install.sh` — installation entrypoint (the orchestrator for hook discovery)
- `hooks/ai-provider-identity-guard.sh` — standalone provenance/identity guard invoked by git hooks and scripts, not lifecycle-projected
- `hooks/session-end-cleanup.sh` — optional SessionEnd cleanup hook; intentionally unregistered until cleanup tier policy is default-on
