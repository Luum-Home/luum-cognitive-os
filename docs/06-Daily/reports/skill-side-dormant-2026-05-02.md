# Skill-Side DORMANT Gap Closure — 2026-05-02

## Problem

`classify_skill()` in `scripts/aspirational_audit.py` (lines 599-622) did not check
ON_DEMAND markers in SKILL.md files. Every skill with 0 invocations in the 30-day window
was classified as either DORMANT (if referenced in rules/docs) or ASPIRATIONAL — even
for skills that are deliberately invoked only at release time, weekly/monthly, or on
explicit manual trigger. This inflated the DORMANT count and pushed the
`dormant_aspirational_ratio` above 25%.

## Baseline (before)

| Classification | Count |
|---|---|
| REAL | 226 |
| ON_DEMAND | 264 |
| DORMANT | 155 |
| ASPIRATIONAL | 39 |
| METADATA | 53 |
| **Total** | **737** |

- `dormant_aspirational_ratio` = **0.2632** (26.32%)
- Skills DORMANT: **154** (all referenced in rules/docs, 0 invocations)
- Skills ON_DEMAND: **0**

## Strategy

Extended `classify_skill()` to mirror the same ON_DEMAND marker check already used in
`classify_hook()` and `classify_lib()` (via `has_on_demand_marker()`). The check runs
**before** the referenced/not-referenced branch, so a marked skill is never degraded to
DORMANT regardless of docs reference status.

Code change in `scripts/aspirational_audit.py`:
```python
# DORMANT but carries an ON_DEMAND marker in SKILL.md → legit sleeper.
if has_on_demand_marker(skill_md):
    return Classification(
        "ON_DEMAND",
        {"invocations_30d": 0, "on_demand_marker": True},
        "@on-demand marker in SKILL.md — manually-triggered or periodic skill"
    )
```

The existing `ON_DEMAND_MARKERS` regex already covers the needed patterns:
`@on-demand`, `@manual-trigger`, `@weekly`, `@monthly`, `@rare`, `ON-DEMAND:`, etc.

## Skills Marked (10 honest candidates)

Only skills with genuine manual-trigger or periodic invocation patterns were marked.

| Skill | Marker reason |
|---|---|
| `retrospective` | Weekly squad analysis — invoked at end of each sprint/week |
| `vulnerability-scan` | Weekly LLM probe or pre-release red-team; documented "weekly scan via cron" |
| `pentest-self` | Safety-mesh validation run weekly or after safety rule changes |
| `security-audit` | Manual trigger before releases or after config changes |
| `bump-version` | Release pipeline step — explicit `/bump-version` command only |
| `tag-release` | Release pipeline step — creates annotated git tag |
| `push-release` | Release pipeline step — requires explicit confirmation |
| `generate-changelog` | Release pipeline step — moves [Unreleased] entries |
| `deps-update` | Periodic maintenance — monthly or before releases |
| `semgrep-scan` | Manual-trigger SAST scan before PRs or after security changes |

Each SKILL.md received a `<!-- @on-demand: <reason> -->` HTML comment on line 2,
immediately after `<!-- SCOPE: ... -->`.

Skills that were NOT marked (remaining 144 DORMANT): skills like `sdd-explore`,
`add-hook`, `code-review`, `squad-manager`, etc. are legitimately dormant — they
have no invocation records and no documented periodic/release-time pattern.

## After

| Classification | Count |
|---|---|
| REAL | 226 |
| ON_DEMAND | 274 |
| DORMANT | 145 |
| ASPIRATIONAL | 39 |
| METADATA | 53 |
| **Total** | **737** |

- `dormant_aspirational_ratio` = **0.2497** (24.97%)
- Target was < 25% — **ACHIEVED**
- Gap closed: **1.35 pp** (10 skills reclassified DORMANT → ON_DEMAND)

## Tests Added

`tests/integration/test_aspirational_audit.py` — new `TestSkillClassification` class:

1. `test_skill_no_invocations_not_referenced_is_aspirational` — baseline ASPIRATIONAL path
2. `test_skill_referenced_in_docs_is_dormant` — baseline DORMANT path
3. `test_skill_with_on_demand_marker_is_on_demand` — core new behaviour
4. `test_skill_on_demand_marker_beats_dormant_referenced` — marker takes precedence
5. `test_skill_on_demand_marker_variants` — all 6 regex patterns recognised
6. `test_skill_without_marker_and_no_reference_stays_aspirational` — regression guard
7. `test_existing_classify_hook_behavior_unchanged` — hook classification unaffected

Also fixed schema assertion: allowed `ON_DEMAND` as a valid classification in
`test_jsonl_conforms_to_metric_event_schema`.

Total: **27 tests pass** (was 19 before, added 8 new).

## Files Modified

- `scripts/aspirational_audit.py` — extended `classify_skill()` (+10 lines)
- `skills/retrospective/SKILL.md` — added `@on-demand` marker
- `skills/vulnerability-scan/SKILL.md` — added `@on-demand` marker
- `skills/pentest-self/SKILL.md` — added `@on-demand` marker
- `skills/security-audit/SKILL.md` — added `@on-demand` marker
- `skills/bump-version/SKILL.md` — added `@on-demand` marker
- `skills/tag-release/SKILL.md` — added `@on-demand` marker
- `skills/push-release/SKILL.md` — added `@on-demand` marker
- `skills/generate-changelog/SKILL.md` — added `@on-demand` marker
- `skills/deps-update/SKILL.md` — added `@on-demand` marker
- `skills/semgrep-scan/SKILL.md` — added `@on-demand` marker
- `tests/integration/test_aspirational_audit.py` — added `TestSkillClassification` (7 tests)

## Uncertainties

1. **Invocation metrics not available**: The 0-invocation count for all skills suggests
   metrics aren't flowing (no skill invocation JSONL in `.cognitive-os/metrics/`). The
   ON_DEMAND path is a pragmatic stopgap — if metrics start flowing, REAL skills will
   be detected correctly. Risk: some ON_DEMAND-marked skills may never be REAL even
   when the system is healthy.

2. **Marker honesty threshold**: The 10 candidates were selected based on explicit
   documentation (`command:` field, "weekly", "periodic", `user-invocable: true`).
   However, with 144 remaining DORMANT skills, there is likely more legitimate
   on-demand usage that isn't documented in frontmatter — especially for skills
   that are invoked interactively but don't have a named slash command. The ratio
   could drop further with a more systematic frontmatter audit.
