# Skills and Rules Canonicalization Risk Analysis

This document explains why moving skills and rules from a `.claude`-centered
model into a canonical `.cognitive-os` contract can break large parts of the
system if it is treated as a simple path migration.

The short version:

**this is not just a filesystem cleanup. It is a behavioral contract change.**

## Why This Change Is Dangerous

The repository already signals a desirable long-term direction:

- hooks are increasingly modeled as canonical behavior plus harness projection
- settings projection is becoming harness-aware
- `.cognitive-os/` already exists as a canonical runtime area

However, skills and rules still depend on `.claude/` in ways that are deeper
than simple file placement.

If we move them too early, we risk breaking:

- rule loading behavior
- skill discovery expectations
- installer/update flows
- diagnostics and CLI commands
- docs and onboarding guarantees
- a large body of behavior and integration tests

## The Hidden Contracts Behind `.claude/`

## Static Coupling Evidence

A static scan of Python, shell, Go, and Markdown sources shows broad coupling
to Claude-facing paths.

### Reference counts by surface

| Surface | Tests | Scripts/Hooks/Bin | Go | Docs | Other |
|--------|------:|------------------:|---:|-----:|------:|
| `.claude/skills` | 1 | 10 | 3 | 72 | 6 |
| `.claude/rules` | 13 | 12 | 5 | 106 | 6 |
| `.claude/settings.json` / `.claude/settings.local.json` | 25 | 30 | 7 | 134 | 5 |
| `.cognitive-os/skills` | 5 | 11 | 0 | 57 | 2 |
| `.cognitive-os/rules` | 3 | 3 | 0 | 22 | 3 |

This is not proof that every reference would break, but it is strong evidence
that the current contract is materially Claude-centered across runtime,
tooling, documentation, and validation.

### Test distribution with explicit `.claude/...` references

Tests that explicitly reference `.claude/skills`, `.claude/rules`, or
`.claude/settings*.json` appear across multiple suites:

- 9 unit files
- 9 behavior files
- 5 integration files
- 4 audit files
- 2 contract files
- 1 hooks test file
- 1 end-to-end test file

This confirms that a direct migration would not only touch implementation code.
It would also require coordinated redefinition of test expectations.

### 1. Claude's recursive rule loading is itself part of the design

Several docs and tests assume Claude Code loads all Markdown files under
`.claude/rules/` recursively. That is not just an implementation detail. It is
part of the current operational model and context-budget design.

This affects:

- `docs/04-Concepts/root/rules-loading-architecture.md`
- `docs/04-Concepts/architecture.md`
- `tests/behavior/test_claude_md_diet.py`
- `tests/unit/test_efficiency_stress.py`

If rules stop being materially present under `.claude/rules/`, then the current
loading model, token-budget model, and "RULES-COMPACT plus selected rules"
assumptions must all be revisited.

### 2. Skill exposure and skill truth are currently split

`scripts/cos-init.sh` already installs skills into both:

- `.cognitive-os/skills/cos/`
- `.claude/skills/`

That means the system already has a dual-path arrangement, but the current
behavior still treats the Claude-facing path as the harness-visible surface.

The important subtlety is:

- `.cognitive-os/skills/cos/` exists as kernel storage
- `.claude/skills/` remains the empirically verified discovery surface for the
  current Claude driver

So a migration that removes or demotes `.claude/skills/` without a replacement
driver contract will break skill discovery.

### 3. Rules are not mirrored the same way skills are

Rules are currently copied directly into `.claude/rules/cos/` by bootstrap
flows. Unlike hooks and templates, they are not yet centered on a canonical
`.cognitive-os/rules/...` runtime path.

That means rules are structurally more coupled to Claude-facing layout than
skills are.

### 4. Installer/export logic bakes in the current contract

`cmd/cos/internal/installer/export.go` still resolves:

- skills -> `.claude/skills/...`
- rules -> `.claude/rules/cos/...`

So package installation behavior, uninstall behavior, and lockfile expectations
currently embed the Claude-facing projection as the obvious destination for
these artifact types.

### 5. CLI and status tooling depend on `.claude/...`

`bin/cognitive-os.sh` and related tooling still inspect:

- `.claude/skills/`
- `.claude/rules/`
- `.claude/settings.json`

for status, management, and diagnostics.

So moving the canonical contract without updating tool semantics will make the
system appear broken even if the underlying artifacts still exist elsewhere.

### 6. Tests encode the old contract very broadly

The repo contains a large number of tests and assertions that explicitly check:

- `.claude/settings.json`
- `.claude/rules/cos/`
- `.claude/skills/`
- CLAUDE.md token budgets and rule-loading assumptions

This is good evidence of system coupling. It also means a migration will fail
widely unless the contract is intentionally redefined and test strategy is
updated in lockstep.

## What This Means Strategically

The desired destination is still valid:

- `.cognitive-os/` should become the clearer source of truth
- harnesses should consume projected views
- "portable" should mean canonical-first, not Claude-compatible-first

But the current system is not ready for a direct move of skills and rules out of
the `.claude` center without introducing new contracts first.

In other words:

**the portability thesis is right, but the migration shape matters more than the
destination.**

## What Must Exist Before a Safe Migration

### 1. A canonical discovery contract

For skills and rules, we first need to define what it means for the OS itself
to discover and reason about those artifacts independently of Claude.

That contract should answer:

- where the canonical files live
- how the OS enumerates them
- what counts as installed
- what projection metadata is attached

### 2. A projection contract per harness

Claude, Codex, and future harnesses need explicit projection rules for:

- skill exposure
- rule exposure
- instruction surfaces
- registration/discovery behavior

### 3. A truth hierarchy

The repo must clearly state:

- canonical truth
- harness projection
- compatibility shims

Without that hierarchy, path moves create semantic ambiguity rather than
portability.

### 4. Migration-safe tests

We need contract tests that verify:

- canonical artifacts exist without `.claude/`
- Claude projection is generated from canonical artifacts
- non-Claude harnesses do not depend on `.claude/`
- portable features fail only when a driver is missing, not when Claude paths
  are absent

## Recommended Migration Shape

Do not start by moving files.

Start with contract definition, then projection, then path movement.

### Phase 1: Define canonical contracts

- canonical rules path
- canonical skill discovery path
- projection metadata model

### Phase 2: Teach tooling about canonical-first semantics

- installer/export logic
- status/diagnostic tooling
- update flows
- validation and audit tooling

### Phase 3: Add dual-path compatibility

Make the system work from canonical state while still projecting into Claude.

### Phase 4: Only then consider demoting `.claude/...`

At that point `.claude/` becomes clearly a driver surface rather than the
implicit system center.

## Practical Conclusion

Moving skills and rules out of the `.claude` center is still the right
long-term direction.

But doing it now as a direct path migration would be high-risk and likely to
break behavior, tests, mental models, and product messaging all at once.

The safe move is:

- analyze the hidden contracts first
- define canonical discovery and projection explicitly
- migrate behaviorally before migrating physically

## References

- `docs/04-Concepts/architecture/skills-rules-portability-gap.md`
- `docs/04-Concepts/architecture/bootstrap-portability.md`
- `docs/04-Concepts/architecture/cross-harness-authoring.md`
- `cmd/cos/internal/installer/export.go`
- `scripts/cos-init.sh`
