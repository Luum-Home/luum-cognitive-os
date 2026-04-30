# ADR-027a — Addendum: Reconciliation with main baseline

**Status**: Addendum to ADR-027
**Date**: 2026-04-18
**Supersedes**: ADR-027 §Baseline (context overhead table), §KPIs row "CLAUDE.md tokens loaded on session start"
**Amends**: ADR-027 §D2 (task list), §D3 (KPI row for registered hook entries), §Phase 1 (risks & mitigations)

---

## Why this addendum exists

ADR-027 was written on 2026-04-17 without verifying the actual state of `main` — specifically,
without checking whether prior token-optimization work had already landed. Reconciliation against
20 pre-existing plan documents and the 14-item `.cognitive-os/work-queue.json` revealed that the
ADR-027 baseline measurement of 24,124 bytes / ~6,031 tokens for `~/.claude/CLAUDE.md` is stale:
commit `1ee19a4` ("Phase 2 EXCLUDED_RULES") already landed an `EXCLUDED_RULES` array in
`hooks/self-install.sh` that excludes 100 of 101 rules from context load. This addendum corrects
the baseline, adjusts D2 scope to avoid re-doing already-completed work, adds a mandatory
prerequisite for Phase 1, clarifies the hook-count KPI contradiction with `hook-architecture-v2.md`,
and formalises the JSONL rotation threshold amendment that ADR-028 already claimed informally.

---

## 1. Baseline correction

The ADR-027 context-overhead table reported:

| Source | Claimed in ADR-027 | Actual on main |
|---|---|---|
| `~/.claude/CLAUDE.md` size | 24,124 bytes | ~11,125 bytes |
| `~/.claude/CLAUDE.md` estimated tokens | ~6,031 | ~1,904 |
| Rules excluded from context load | 0 (not mentioned) | 100 of 101 |
| Mechanism | — | `EXCLUDED_RULES` array in `hooks/self-install.sh` |
| Landed via commit | — | `1ee19a4` ("Phase 2 EXCLUDED_RULES") |

The EXCLUDED_RULES mechanism operates as follows: `hooks/self-install.sh` maintains an
`EXCLUDED_RULES` array; any rule file listed there is not injected into sub-agent context on
`PreToolUse Agent` events. With 100 of 101 rules excluded, the effective per-session rule-injection
overhead is already drastically reduced — the 80 % token saving that ADR-027 D2 intended to achieve
via `compact-claude-md.py` has already been achieved by a different mechanism.

The remaining ~1,904 tokens in `~/.claude/CLAUDE.md` are **not rule files**. They are inline prose
decisions: git commit rules, orchestrator delegation protocol, engram memory protocol, SDD workflow,
and agent model routing. These cannot be moved to rule files and excluded — they are mandatory
on every session.

---

## 2. D2 scope changes

The following changes to ADR-027 Phase 2 surface are in effect as of this addendum:

### REMOVE from D2

- **`scripts/compact-claude-md.py` migration script** — redundant. The EXCLUDED_RULES mechanism
  already achieves the context reduction that `compact-claude-md.py` was intended to automate.
  Implementing this script would duplicate existing infrastructure and risk colliding with or
  regressing the current `self-install.sh` caching logic.

- **KPI target "CLAUDE.md ≤ 400 tokens"** — mathematically infeasible without deleting the global
  inline prose sections (git rules, orchestrator protocol, engram protocol, SDD workflow, model
  routing). Those sections are not rule files; they are session-mandatory decisions that cannot be
  externalized via ref-key loading. The KPI row in ADR-027 §KPIs must be updated to reflect the
  corrected baseline (1,904 tokens, down from the stale 6,031) and a realistic target.

### KEEP from D2

- **`lib/ref_key_loader.py` (on-demand rule loading by ref-key)** — still valuable. The
  EXCLUDED_RULES mechanism excludes rules wholesale; the ref-key loader enables *contextual
  on-demand inclusion* when a specific rule is needed mid-session. These are complementary, not
  redundant.

### NEW target for D2

Replace the infeasible "≤ 400 tokens" KPI with a concrete but achievable target:

> **Target**: `~/.claude/CLAUDE.md` ≤ 1,200 tokens (down from current ~1,904) by consolidating
> duplicate SDD/engram prose sections. Specifically: the SDD workflow block and the engram protocol
> block each contain redundant sub-bullets that re-state content already covered in the dedicated
> rule files (`rules/...`). Deduplication is safe because sub-agents load those rule files
> independently. The inline prose in `~/.claude/CLAUDE.md` need only retain the orchestrator-facing
> summary (decision + hook, not the full specification).

Measurement after consolidation: `wc -c ~/.claude/CLAUDE.md | awk '{print int($1/4)}'` (bytes/4
approximation). Target: result ≤ 1,200.

---

## 3. Phase 1 prerequisite (ws9-test-errors)

ADR-027 Phase 1 §Risks states: "Resolver maps wrong → agent skips a failing test. Fallback to the
full suite when resolver returns < 1 test file."

This fallback is triggered by the current state of the test suite: `ws9-test-errors` in
`.cognitive-os/work-queue.json` documents 292 `pytest` collection errors caused by import failures.
With 292 collection errors active, `lib/targeted_test_resolver.py` will almost always produce
< 1 resolvable test file for changed paths that touch broken import chains — causing the fallback
to the full suite to fire on every agent invocation. This defeats the entire purpose of Phase 1.

**Mandatory prerequisite:** `ws9-test-errors` MUST be resolved and the pytest collection error
count reduced to 0 before Phase 1 executes. This item should be marked with
`"blocks": "ADR-027/Phase-1"` in `.cognitive-os/work-queue.json`.

The orchestrator must not launch the Phase 1 agent until:

```
python3 -m pytest tests/unit/ --collect-only -q 2>&1 | grep "error" | wc -l
```

returns `0`.

---

## 4. C1 — Hook count reconciliation (conflict with hook-architecture-v2)

`.cognitive-os/plans/features/hook-architecture-v2.md` Phase 2 defines canonical hook counts for each
efficiency profile:

| Profile | hook-arch-v2 target |
|---|---|
| minimal | 17 registered hooks |
| standard | 34 registered hooks |
| paranoid | 88 registered hooks |

ADR-027 D3 KPI table targets **≤ 18 registered hook entries** total, measured as:

```
jq '[.hooks[][].hooks | length] | add' .claude/settings.json
```

These are **not the same metric** and the apparent contradiction is resolvable with the following
clarification:

- ADR-027 D3's **≤ 18** applies specifically to `PreToolUse Agent` + `PostToolUse Agent` matchers
  — the subset that fires on every agent launch. This is where the merge work in D2/D3 reduces
  redundant per-launch overhead. D3 merges 4 PreToolUse Agent entries into 1 and 3 PostToolUse
  Agent entries into 1, reducing this subset from 7 entries to 2.
- The **total** `settings.json` entry count (across all matchers: SessionStart, UserPromptSubmit,
  Bash, Write/Edit, Stop, PreCompact, Notification) is governed by the active efficiency profile
  and is orthogonal to the D3 target.
- `.cognitive-os/plans/features/hook-architecture-v2.md`'s `standard=34` measures total entries across all matchers, which is
  consistent with the efficiency profile system, not with D3's subset target.

**ADR-027 D3 KPI row correction:** The KPI row "Registered hook entries | 27 | ≤ 18" is replaced
with:

> Registered hook entries (Agent-matcher subset) | 7 (4 PreToolUse Agent + 3 PostToolUse Agent) |
> **≤ 2** (1 merged PreToolUse Agent + 1 merged PostToolUse Agent) | Total settings.json entry
> count governed by efficiency profile per `.cognitive-os/plans/features/hook-architecture-v2.md` canonical counts.

This removes the contradiction: ADR-027 D3 owns the Agent-matcher subset; `.cognitive-os/plans/features/hook-architecture-v2.md`
owns the total profile counts. Both can be satisfied simultaneously.

---

## 5. Rotation threshold (already amended inline)

ADR-027 D3 line 215 originally read `>2 MiB` as the JSONL rotation trigger. The version of
ADR-027 on `main` as of 2026-04-17 reads `>1 MiB, per ADR-028 D1.A` — this inline amendment was
applied during the ADR-028 authoring session.

This addendum formalises the precedence rule:

> **ADR-028 D1.A takes precedence over ADR-027 D3 on all JSONL size thresholds.** Both ADRs
> designate `hooks/rotate-metrics.sh` as the implementation target; ADR-028 D1.A's 1 MiB threshold
> is the binding value. Any future amendment to the threshold is owned by ADR-028 D1.A; ADR-027
> D3 text is informational only on this point.

---

## 6. References

- Engram: `gaps/adr-027-028-reconciliation-analysis` (full reconciliation table, all contradictions
  and gaps; observation #11552)
- Engram: `gaps/adr-027-stale-baseline` (discovery of baseline mismatch; same observation)
- Commit `1ee19a4` — "Phase 2 EXCLUDED_RULES" — the commit that landed the mechanism making
  ADR-027's 6,031-token CLAUDE.md baseline stale
- Work-queue: `.cognitive-os/work-queue.json` — `ws9-test-errors` item (prerequisite for Phase 1)
- `.cognitive-os/plans/features/hook-architecture-v2.md` — canonical hook count targets per profile
- ADR-028 D1.A — authoritative source for JSONL rotation thresholds

---

## Action items (for orchestrator before ADR-027 execution)

- [x] Update ADR-027 D3 KPI row per §4: replace "≤ 18 total" with "Agent-matcher subset ≤ 2" — RESOLVED 2026-04-21 (commit `<pending-commit>`)
- [x] Remove D2 task bullet for `scripts/compact-claude-md.py` per §2 — RESOLVED 2026-04-21 (commit `<pending-commit>`)
- [x] Replace D2 KPI target "CLAUDE.md ≤ 400 tokens" with "≤ 1,200 tokens" per §2 — RESOLVED 2026-04-21 (commit `<pending-commit>`)
- [x] Add ws9 dependency to ADR-027 Phase 1 §Risks per §3: "ws9-test-errors must be resolved first" — RESOLVED 2026-04-21 (commit `<pending-commit>`)
- [x] Update `.cognitive-os/work-queue.json`: mark `ws9-test-errors` as `"blocks": "ADR-027/Phase-1"` — ws9 already resolved per queue.json:122

---

## Resolution Log — 2026-04-21

All four pending action items from the "Action items (for orchestrator before ADR-027 execution)" list have been executed against `docs/adrs/ADR-027.md`. Resolution details:

| # | Item | Target in ADR-027 | Action taken |
|---|------|-------------------|--------------|
| 1 | KPI "Registered hook entries ≤ 18" contradicted hook-architecture-v2 | KPI row (formerly line 265) in §KPIs | Row rewritten to "Registered hook entries (Agent-matcher subset) — baseline 7 (4 PreToolUse Agent + 3 PostToolUse Agent), target ≤ 2". Measurement `jq` query scoped to the Agent matcher subset. Explicit note added that total entry count is governed by the efficiency profile and is orthogonal. Cross-reference to ADR-027a §4 included. |
| 2 | D2 bullet referencing `scripts/compact-claude-md.py` (redundant with EXCLUDED_RULES) | Phase 2 §Surface (formerly line 339); Phase 2 §Tasks item 2 | Surface bullet struck through with explicit removal rationale citing commit `1ee19a4`. Task 2 rewritten from "Draft compact CLAUDE.md via `scripts/compact-claude-md.py`; manual review" to "Manually deduplicate SDD/engram prose blocks in `~/.claude/CLAUDE.md` to reach ≤ 1,200 tokens". |
| 3 | KPI "CLAUDE.md ≤ 400 tokens" (infeasible — remaining tokens are session-mandatory inline prose) | KPI row (formerly line 259) in §KPIs | Baseline corrected from ~6,031 to ~1,904 (stale baseline discovered per ADR-027a §1). Target changed from ≤ 400 to ≤ 1,200. Measurement note updated from "after compact migration" to "after SDD/engram prose deduplication". |
| 4 | Phase 1 depended on ws9-test-errors but the dependency was not documented in-situ | Phase 1 §Risks & mitigations (circa line 309) | New **Prerequisite** sub-section inserted above Risks, including the orchestrator gating command (`pytest --collect-only ... \| grep error \| wc -l == 0`) and noting that ws9 has since been resolved per `work-queue.json:122`. |

**Scope not touched (intentional):**

- `.cognitive-os/work-queue.json` — item 5 says "ws9 already resolved per queue.json:122" so no edit needed.
- `rules/so-slo.md` — no new SLO row required. The four resolved items are ADR-level doc corrections / task-list corrections; none of them introduces a new measurable SLO beyond what ADR-027 §KPIs already defines.
- Existing code/hooks — none of the four items required a code change. The `EXCLUDED_RULES` mechanism they defer to already exists (commit `1ee19a4`).

**Smoke test:**

`python3 -m pytest tests/unit/test_cos_config_audit.py -q` — no edits touched `cognitive-os.yaml` or the config schema, so the audit suite should be unaffected. Test result captured in the resolution session log.
