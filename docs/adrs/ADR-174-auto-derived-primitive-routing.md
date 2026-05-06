---
adr: 174
title: Auto-Derived Primitive Routing for Skills (and Rules)
status: accepted
date: 2026-05-05
authors: [luum-agent-os]
supersedes: []
cross_references:
  - ADR-133  # auto-skill-generation — same "declare in artifact, derive at runtime" pattern
  - ADR-064  # canonical hook registry — analogous self-describing artifact pattern
  - hooks/skill-router-prompt-suggest.sh  # UserPromptSubmit hook that surfaces suggestions
  - dogfood-score  # skill_coverage: 24.07/100 — primary evidence for this ADR
---
# ADR-174 — Auto-Derived Primitive Routing for Skills

## Status

Accepted

## Context

### The Skill Routing Gap

As of 2026-05-05, `lib/skill_router.py` contains a hand-maintained
fallback routing table plus frontmatter-derived routing support. The local
post-mortem snapshot found 185 unique SKILL.md directories across `skills/`
and `.cognitive-os/skills/`; 82 were routeable as primary router targets,
one primary router entry (`sdd-new`) was an intentional meta-command without
a SKILL.md directory, and 103 skills remained unrouteable. The effective
global/full-surface routing coverage was therefore **44.3%**.

Evidence from `scripts/dogfood_score.py`:
```
skill_coverage: 24.07/100
```
This score is coherent with the gap: the scorer applies heavier penalties
for skills that exist but are unreachable by the orchestrator.

### Root Cause: Hand-Maintained Anti-Pattern

The routing table is a second artifact that must be kept in sync with
SKILL.md files. Every new skill requires a manual edit to `skill_router.py`.
In practice this discipline has not been maintained:

- The repo has multiple projection/adoption profiles (`lean/standard/strict`,
  `default/full`, and `core/team/maintainer/lab`) that were not represented
  in the router coverage metric.
- Existing tests mostly validated router → skill existence, not skill on disk
  → routeability.
- One router entry, `sdd-new`, is a valid meta-command rather than a concrete
  skill directory.

### Cascading Effect

The orchestrator (Claude Code) ignores skill suggestions because the router
does not know about most skills. The `hooks/skill-router-prompt-suggest.sh`
hook (added separately, see cross-references) surfaces suggestions via
`additionalContext` — but suggestions are only as good as the routing table.

### Prior Art in This Codebase

ADR-133 established auto-skill-generation: skills self-describe in SKILL.md
frontmatter and the generator derives everything from that declaration.
ADR-064 established a canonical hook registry following the same pattern.
This ADR extends that principle to routing patterns.

## Decision

### 1. Add `routing_patterns:` to the SKILL.md Frontmatter Schema

Skills declare their own routing patterns inline:

```yaml
routing_patterns:
  - pattern: "add (a )?new skill"      # regex, IGNORECASE
    confidence: 0.85
  - pattern: "agregar (una )?skill"
    confidence: 0.80
```

Rules:
- `pattern` is a Python regex string (compiled with `re.IGNORECASE`).
- `confidence` is a float in `[0.0, 1.0]`.
- At least one pattern is required if the field is present.
- Patterns may be English or Spanish.

### 2. Auto-Derive Routing from Frontmatter

New function `_load_routing_from_frontmatter(skills_root: Path)`:
- Scans `skills/`, `packages/*/skills/`, `.cognitive-os/skills/` for
  SKILL.md files.
- Parses YAML frontmatter (between `---` delimiters).
- If `routing_patterns:` is present, constructs a `_RoutingEntry` with the
  listed patterns and the skill's `name` field.

### 3. Backward-Compatible Merge Strategy

`_build_default_routing_table()` is refactored to:

1. Load frontmatter-derived entries via `_load_routing_from_frontmatter()`.
2. Merge with the existing hand-coded fallback entries for skills that have
   not yet migrated their patterns to frontmatter.
3. Deduplicate: if a skill appears in both sources, the frontmatter entry
   wins (frontmatter is the authoritative source).
4. Detect orphan hand-coded entries (skill_name has no SKILL.md on disk)
   and emit a warning to `sys.stderr` at instantiation time.

The hand-coded table remains as a migration scaffold; it will be removed
once 95%+ of skills have `routing_patterns:` in their frontmatter.

### 4. Invariant Tests as Enforcement

`tests/contracts/test_skill_router_coverage.py` enforces:

- primary router entries point to SKILL.md directories or explicit
  meta-command allowlist entries;
- skills on disk are either routeable or listed in the explicit unrouted
  backlog in `manifests/skill-routing-coverage.yaml`;
- routed skill count and coverage cannot regress below the current ratchet
  (`82` routed skills and `44.0%` coverage).

The current contract is global/full-surface. A follow-up should make the
metric profile-aware so that the router is measured against skills actually
projected by lean/standard/strict (or their canonical core/team/maintainer
equivalents), not every skill that exists on disk.

`tests/contracts/test_skill_router_invariant.py` complements the ratchet by
proving that the ADR-174 proof-of-concept skills are actually loaded from
`routing_patterns:` frontmatter.

## Acceptance Criteria

```
# 1. ADR document exists and is accepted
ls docs/adrs/ADR-174-auto-derived-primitive-routing.md

# 2. Implementation
python3 -c "from lib.skill_router import _load_routing_from_frontmatter; print('OK')"

# 3. Migration proof-of-concept (5 skills)
grep -l "routing_patterns:" skills/add-skill/SKILL.md \
  skills/audit-integrity/SKILL.md \
  skills/code-review/SKILL.md \
  skills/component-reality-check/SKILL.md \
  skills/cognitive-os-init/SKILL.md | wc -l  # expect 5

# 4. Coverage ratchet exists
ls tests/contracts/test_skill_router_coverage.py
ls tests/contracts/test_skill_router_invariant.py

# 5. Existing tests still pass
python3 -m pytest tests/unit/test_skill_router.py -q

# 6. Coverage contract passes
python3 -m pytest tests/contracts/test_skill_router_coverage.py \
  tests/contracts/test_skill_router_invariant.py -q

# 7. Advisory validator hook exists
ls hooks/skill-md-routing-validator.sh
```

## Border Cases

### Auto-Generated Skills

Skills under `.cognitive-os/skills/auto-generated/` are created at runtime
by agents and may not have human-curated `routing_patterns:`. The
frontmatter loader handles these silently — if `routing_patterns:` is
absent, no entry is generated, and the skill remains unrouted. A follow-up
can add an auto-generation template that includes a routing stub.

### Project-Only Skills

Skills with `SCOPE: project-only` or `audience: project` should not be
surfaced to every orchestrator by default. The first ratchet does not yet
filter by audience or projection profile; that is the profile-aware follow-up
captured by the post-mortem.

### Conflict Patterns

If two skills declare patterns that match the same phrase, the router
returns both sorted by confidence (same deduplication logic as today). No
conflict is an error — the orchestrator surfaces the top match.

### Malformed Frontmatter

If a SKILL.md has syntactically invalid YAML frontmatter, `_load_routing_from_frontmatter()`
logs a warning and skips that file. It never raises.

## Consequences

### Positive

- **Closed feedback loop**: adding a skill with `routing_patterns:` is
  sufficient to make it routable. No second-file edit.
- **Future skills auto-routed**: the 18 auto-generated skills can be
  templated to include routing stubs.
- **Orphan visibility**: the orphan warning at instantiation surfaces drift
  immediately without a dedicated audit script.
- **Testable invariant**: coverage ratchet prevents regression.

### Negative

- **Frontmatter discipline required**: skill authors must add
  `routing_patterns:`. The validator hook (Phase 5) provides a non-blocking
  reminder.
- **Migration cost**: ~95 skills need frontmatter migration. Estimated 2-4h
  with sonnet auto-extraction (batch task, not this ADR).
- **YAML parse overhead**: scanning 186+ SKILL.md files at `SkillRouter()`
  construction time adds ~50-150ms. Acceptable for CLI usage; cache if this
  becomes a bottleneck in tests.

## Alternatives rejected

### Keep Hand-Maintained Table

The status quo. Rejected because the gap is 108 skills and growing. The
maintenance burden scales O(N) with skill count; the auto-derive approach
scales O(1) per skill.

### Generate Routing from Description via LLM at Runtime

Run an LLM on each skill's `description` field to produce regex patterns
dynamically. Rejected because: (1) adds per-call LLM cost, (2) non-deterministic
output makes tests fragile, (3) patterns must be human-reviewed for false
positives before shipping.

### Central Registry File (e.g., routing.yaml)

A separate file listing all routing patterns. Rejected because it is still
a second artifact to maintain. The SKILL.md-inline approach follows the
principle established by ADR-133 and ADR-064: the artifact self-describes.

### Grep-Based Pattern Discovery

Scan SKILL.md description fields with heuristic regex at router init.
Rejected because description prose is not designed as regex-safe patterns;
false-positive rate would be unacceptably high without human curation.

- **Leave the decision implicit** — rejected because ADR slots must remain self-describing and audit-safe.
## Falsifiable Claim

> Within 90 days of this ADR being accepted, a scheduled audit will verify
> that `SkillRouter().routing_entry_count / count_of_SKILL_md_files >= 0.95`.
> If not, the migration plan must be accelerated or the threshold revised
> downward with explicit justification.

Measurement: `scripts/dogfood_score.py` dimension `skill_coverage`.

## Cross-References

- **Profile-aware routing note**: `docs/architecture/profile-aware-skill-routing.md` documents the profile-scoped router index, service cache invalidation, and lazy catalog contracts added after this ADR.

- **ADR-133**: Auto-skill-generation — same "declare in artifact, derive at
  runtime" pattern applied to skill creation.
- **ADR-064**: Canonical hook registry — hook self-description as the
  authoritative source of truth; this ADR applies the same principle to
  routing.
- **hooks/skill-router-prompt-suggest.sh**: UserPromptSubmit hook that
  surfaces router suggestions to the orchestrator; its effectiveness depends
  directly on routing coverage.
- **dogfood-score skill**: `skill_coverage` KPI is the primary health
  signal for this ADR.
- **tests/contracts/test_skill_router_coverage.py**: Global/full-surface
  coverage ratchet with orphan/meta-command enforcement.
- **tests/contracts/test_skill_router_invariant.py**: Frontmatter-loader
  proof for the ADR-174 migrated skills.
- **hooks/skill-md-routing-validator.sh**: Advisory SKILL.md write hook that
  warns when new skill content lacks `routing_patterns:`.
- **manifests/skill-routing-coverage.yaml**: Machine-readable baseline,
  meta-command exceptions, and unrouted skill backlog.
- **docs/reports/skill-router-primitive-routing-postmortem-2026-05-05.md**:
  Investigation that separates global router coverage from profile-specific
  primitive projection.

## Migration Plan

### Now (this ADR)

5 high-priority skills migrated as proof-of-concept:
`add-skill`, `audit-integrity`, `code-review`, `component-reality-check`,
`cognitive-os-init`.

### Batch Migration (~103 remaining skills)

Separate task with `model: sonnet`. For each unmigrated skill:
1. Read `name` + `description` from frontmatter.
2. Derive 2-3 regex patterns using the sonnet auto-extractor.
3. Submit PR with `routing_patterns:` additions.
4. Remove from `UNROUTED_SKILL_ALLOWLIST` in `test_skill_router_coverage.py`.

Estimated effort: 2-4h with sonnet auto-extraction.

### Auto-Generated Skills

Add a routing stub template to the auto-skill-generation scaffold so new
auto-generated skills ship with at least one pattern. Follow-up task.

### Rules Routing (ADR-174b)

The same `routing_patterns:` pattern can be applied to `rules/*.md` files
to enable rule-based auto-selection. That is a separate ADR (not this one).

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

