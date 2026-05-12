---
adr: 67
title: Defense-in-Depth for SKILL.md Frontmatter Quality
status: proposed
implementation_status: planned
date: '2026-04-24'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-067 — Defense-in-Depth for SKILL.md Frontmatter Quality

## Status

Proposed — 2026-04-24. Implementation tracked separately as Phase 1 of this ADR.

This ADR is **design-only**. No source code, hook, or test is created here. It
ratifies a 3-layer policy that subsequent commits will implement.

## Context

Today (2026-04-24) the operator opened `skills/CATALOG.md` and noticed **18
skills** rendered as `No description` in the auto-generated bullet list.
Investigation surfaced two concurrent failure modes:

1. **Parser bug in `lib/session_hygiene.py`**. The function `_fm()` uses the
   regex `r"^---\s*\n(.*?)\n---"` with only `re.DOTALL` (no `re.MULTILINE`),
   which requires the `---` fence at the absolute start of the file. But every
   `SKILL.md` in this repo begins with a SCOPE comment:

   ```
   <!-- SCOPE: both -->
   ---
   name: ...
   ```

   The parser never matches → returns `None` → falls through to
   `or "No description"`. A separate agent (`ab0a05ec`) is fixing this in
   parallel.

2. **Empty `description: >` blocks in 7 skills**. The frontmatter declares the
   YAML key but supplies an empty multi-line value. Affected skills:
   - `caveman-compress`
   - `pattern-audit`
   - `project-scaffold`
   - `rules-export`
   - `doc-review-personas`
   - `so-vs-vanilla`
   - `radar-update` ← **shipped this session, 2026-04-24**

   That last item is the alarm bell. A skill created in the current session
   landed in tree without a description and **no automated check fired**.

Operator quotes (verbatim):
- *"esto no tiene un test para evitarlo, probarlo?"*
- *"esto no tiene hooks u otro componente para asegurarnos de que no pase?"*
- *"si, y que sea adr"*

### Gap analysis (state today)

| Defense layer | State today | Why it didn't catch the 7 skills |
|---|---|---|
| `tests/audit/test_skills_contracts.py` | Exists. Validates only that `name:` is present. | No `description:` content check. |
| Pre-commit hook (`pre-commit-gate.sh`) | Exists. | Does not parse SKILL.md frontmatter. |
| PostToolUse hook on Write/Edit of SKILL.md | **Does not exist.** | No immediate-feedback gate during agent sessions. |
| Canonical SKILL.md template | **Does not exist.** | Each agent invents the format → empty `description: >` boilerplate ships. |
| Skill-creator (`/add-skill`, `/skill-creator`) frontmatter enforcement | Skills exist; do not enforce description quality. | Generated frontmatter contains placeholder, agent never fills it. |

Two of three meaningful gates (template, hook) are missing. The third (audit)
is too narrow. That is why the 7 skills slipped through. The root problem is
**not the parser bug or the empty descriptions individually** — it is the
**total absence of defense layers** that would have prevented either symptom
from reaching the catalog.

This ADR specifies the layers. Implementation is Phase 1.

## Decision — Three orthogonal layers

The policy is defense-in-depth: three independent gates fire at three
different times, with three different cost profiles, against three different
failure modes. **All three are required.** Removing any layer leaves a real
gap that today's incident demonstrated.

| Layer | When it fires | Cost | What it catches | Failure mode if missing |
|---|---|---|---|---|
| **A) Canonical template + skill-creator enforcement** | When an agent creates a new skill | ~15 min one-time | Empty placeholders shipping as final values; missing fields | Agent emits `description: >` boilerplate, never fills it (today's bug source) |
| **B) PostToolUse hook on `Write\|Edit` matching `skills/*/SKILL.md`** | Immediately after the agent writes the file | ~15 min one-time + small per-invocation cost | Frontmatter violations during the agent session — agent gets warned BEFORE the work is "done" | Agent finishes session with broken skill, lands in next commit |
| **C) Audit test `test_skill_descriptions_nonempty`** | CI / local `pytest tests/audit/` | ~5 min one-time | Anything that escaped (A) and (B); regressions; ratchet | Drift sneaks past the hook (e.g., direct file write outside Edit/Write tools) |

### Why each layer is non-negotiable

- **A alone**: a template only helps if agents actually use it. New agent
  authors will deviate. Hook + audit must catch deviations.
- **B alone**: hooks fire on Edit/Write tool calls. They do **not** fire when
  files are written by other paths (e.g., Bash `cat > skills/foo/SKILL.md`,
  git merges, scripts that run outside the tool harness). Audit is the safety
  net.
- **C alone**: ratchet works, but feedback arrives at CI time — long after
  the agent claimed "done." Layer B closes the in-session feedback loop.
- **A + C without B**: agent finishes a session, ships a broken skill,
  operator notices in catalog hours later (today's exact scenario, modulo the
  parser bug compounding it).
- **B + C without A**: every new skill round-trips through hook warnings.
  Toil. Templates are cheap; absence is expensive.

## Decision — What each layer enforces

The v1 contract for SKILL.md frontmatter:

| Field | Rule | Layer A enforces | Layer B enforces | Layer C enforces |
|---|---|---|---|---|
| `name:` | non-empty string | yes (placeholder) | yes (regex) | yes (already exists) |
| `description:` | non-empty, not bare `>` or `\|`, length ≥ 30 chars | yes (`<REQUIRED>` placeholder) | yes (warn) | yes (assert) |
| `audience:` | one of `{os, os-dev, os-only, project, both, adopters, human}` | yes (template hint) | yes (warn) | yes (assert) |
| `version:` | semver-ish (`X.Y.Z` or `X.Y`) | yes (default `0.1.0`) | yes (regex) | yes (regex assert) |
| `last-updated:` | `YYYY-MM-DD` format | yes (filled at creation) | yes (regex) | yes (regex assert) |
| `<!-- SCOPE: ... -->` HTML comment (line 1) | one of `{os-only, project, both}` | yes (template) | yes (warn) | yes (assert) |

**This list is the single source of truth.** When the contract evolves, this
ADR's table is updated first, and the template, hook, and audit test are
updated to match. No layer adds fields not in this list without amending the
ADR.

## Decision — Failure semantics

| Layer | On violation | Default behavior |
|---|---|---|
| **A** Template | N/A (proactive) | `/add-skill` and `/skill-creator` MUST consume `templates/skill-template.md`. If they don't, that's a separate bug to file. |
| **B** PostToolUse hook | stderr: `WARNING: SKILL.md frontmatter incomplete: <issue list>` | Exit `0` (advisory). Strict mode (`exit 2`, block) is opt-in via `COS_STRICT_SKILL_VALIDATION=1`. |
| **C** Audit test | pytest assertion fails with the offending file path and reason | CI red. Local `pytest tests/audit/` red. |

Why advisory by default for Layer B: hook chain timing budgets are tight
(see ADR-066 §Context and the perf RCA at engram topic
`perf/hook-chain-rca-2026-04-24` — Stop event hit 18s). Adding another
**blocking** hook risks regressions in latency. Audit (Layer C) is the hard
gate. Hook is the fast warner.

If empirically the warning is ignored and the audit keeps catching the same
class of error, flip the default. Tracked as an open question.

## Decision — Generalization to other artifacts

The 3-layer pattern (**template + hook + audit**) is reusable. Phase 2
candidates, **out of scope for this ADR's Phase 1**:

| Artifact | Template would specify | Hook would check | Audit would assert |
|---|---|---|---|
| `rules/*.md` | `# Title`, `## Purpose`, `## Rule`, `## Contextual Trigger` sections | Required sections present on Write/Edit | All present in CI |
| `hooks/*.sh` | Header comment with description, scope, exit codes, dependencies | Header present + executable bit set | Bash `set -euo pipefail`; no `cd` without restoring |
| `docs/adrs/ADR-*.md` | `## Status`, `## Context`, `## Decision`, `## Consequences`, `## Alternatives rejected` | Required sections on Write/Edit | All present in CI; numbering monotonic |

Phase 2 sequencing is opportunistic: when an analog incident occurs (e.g., an
ADR ships missing `## Alternatives rejected`), elevate that artifact to the
3-layer treatment.

## Decision — What we replicate, what we don't

**Replicate** (template + hook + audit) where the artifact is:
- High-value (drives catalog UX, governance, contract surface)
- High-velocity (touched in many sessions per week)
- Drift-prone (placeholders, missing fields, format variance)

→ skills ✅ (this ADR), hooks (Phase 2), rules (Phase 2), ADRs (Phase 2).

**Do NOT replicate** to:
- Every YAML file in the repo (paranoia → toil).
- Code files (Python/bash) — those have lint, typecheck, and unit tests.
- Generated artifacts (CATALOG.md, registry files) — they're outputs, not
  authored content; their producers are the gate.

The principle: **apply the 3-layer pattern only where drift has cost and
authoring is human/agent-driven.**

## Consequences

### Positive

- Drift like today's becomes structurally impossible. Three independent gates
  must all fail for a skill to ship without description.
- Newcomers (human or agent) get a working starting point: copy the template,
  fill placeholders, hook warns if you forget.
- In-session feedback (Layer B) means agents fix issues before claiming done,
  not after operator notices.
- Audit test (Layer C) is a permanent ratchet. If a regression slips, CI
  catches it.
- Pattern is reusable for hooks, rules, ADRs. Phase 2 is straightforward.

### Negative

- Layer B adds latency per Edit/Write of `skills/*/SKILL.md`. Estimated
  budget: <100ms (Python frontmatter parse + 6 regex checks). Hooks fire
  0–2 times per session typically. Negligible against the 18s baseline.
- Hook can be **bypassed** by writes that go around the Edit/Write tools
  (raw Bash redirection, scripts run outside the harness, git merges,
  symlink shenanigans). This is acknowledged limitation. Layer C exists
  precisely because of this.
- Strict mode (`COS_STRICT_SKILL_VALIDATION=1`) could regress sessions if
  enabled prematurely. Default is advisory.

### Neutral

- Existing skills already passing the contract are unaffected.
- The 7 currently-broken skills will be fixed by the in-flight agent
  (`ab0a05ec`) before Layer C lands; otherwise CI would go red on first run.
  Sequencing matters: parser fix + 7 description backfills → then Layer C
  audit test → then Layer A template → then Layer B hook.

## Alternatives rejected

1. **"Just fix the parser, leave 7 broken descriptions for later."**
   Rejected. Addresses one symptom (parser), not the source (no gate against
   empty descriptions). The 7 would come back. Operator's directive
   ("esto no tiene un test para evitarlo") explicitly rejects this option.

2. **"Audit test alone (no hook, no template)."**
   Rejected. Ratchet works, but feedback arrives at CI time. Agents finish
   broken work and the operator notices in the catalog. Closes the loop too
   late. Hook adds the in-session feedback that actually changes agent
   behavior.

3. **"Hook alone (no audit, no template)."**
   Rejected. Hook can be bypassed via direct file writes outside the
   Edit/Write tool surface. Without Layer C, drift returns silently. Without
   Layer A, every new skill round-trips through hook warnings (toil).

4. **"Make `description` optional and just live with `No description`."**
   Rejected. Capitulation. Description is the catalog's primary UX —
   `skills/CATALOG.md` is how agents discover capabilities. Empty
   descriptions degrade discovery. The fix is to require descriptions, not
   to weaken the contract.

5. **"Use a real YAML schema validator (jsonschema, Pydantic)."**
   Rejected (for now). Overkill for ~140 files with 6 fields. Adds a Python
   dependency and a schema file to maintain. Plain regex in the hook +
   pytest assertions in the audit suffice. If the field count grows past
   ~15 or cross-field constraints emerge, revisit.

6. **"Push the gate up to git pre-commit only."**
   Rejected. `pre-commit-gate.sh` is one-and-only-one shot at commit time,
   serial with other checks. Layer B (PostToolUse hook) gives in-session
   feedback during agent work. Both layers are useful at different
   timescales; pre-commit alone is too late.

## Verification

How Phase 1 will be measured (run after implementation):

```bash
# Layer C: audit test exists and passes
pytest tests/audit/test_skill_descriptions_nonempty.py -v

# Layer A: template exists with required placeholders
test -f templates/skill-template.md
grep -c "<REQUIRED" templates/skill-template.md  # >= 6

# Layer B: hook registered and fires on SKILL.md writes
grep -l "skills/.*SKILL.md" .claude/settings.json
# Stress test: write a broken SKILL.md, confirm warning emitted
echo "<!-- SCOPE: both -->\n---\nname: test\ndescription: >\n---" > /tmp/broken-skill.md
# (manual: copy to skills/_test/SKILL.md via Edit tool, observe warning, revert)

# Field-level: zero empty multi-line description blocks
test "$(grep -c 'description: >' skills/*/SKILL.md | grep -v ':0' | wc -l)" -eq 0

# Catalog: zero "No description" entries (depends on parser fix landing first)
grep -c "No description" skills/CATALOG.md  # = 0
```

## Phase 2 — Extension to rules/, hooks/, ADRs/

Phase 2 extends the defense-in-depth pattern (template + hook + audit) from
`skills/*/SKILL.md` to:

| Artifact | Template | Hook | Audit test |
|---|---|---|---|
| `rules/*.md` | `templates/rule-template.md` | `hooks/rule-frontmatter-validator.sh` | `tests/audit/test_rules_enforcement.py` (extended) |
| `hooks/*.sh` | `templates/hook-template.sh` | `hooks/hook-header-validator.sh` | `tests/audit/test_hooks_contracts.py` (extended) |
| `docs/adrs/ADR-*.md` | `templates/adr-template.md` | `hooks/adr-section-validator.sh` | `tests/audit/test_adr_contracts.py` (new) |

Operator decisions ratified for Phase 2:
- Hooks default to WARN; opt-in BLOCK via `COS_STRICT_RULE_VALIDATION=1` /
  `COS_STRICT_HOOK_VALIDATION=1` / `COS_STRICT_ADR_VALIDATION=1`.
- ADR `## Alternatives rejected` backfill: cutoff at ADR-067. Pre-067 ADRs
  grandfathered.
- Hook PURPOSE/EVENT backfill: existing 154 hooks grandfathered. Required
  for new hooks only.
- ADR enforcement cutoff: ADR-067+. Pre-067 ADRs grandfathered.

For the full research, operator triage decisions, and open questions resolved in
Phase 2, see `docs/reports/adr-067-phase-2-2026-04-24.md`.

## Related

- `lib/session_hygiene.py` — parser whose bug surfaced today (in-flight fix
  by agent `ab0a05ec`)
- `tests/audit/test_skills_contracts.py` — existing contract test that does
  not yet check `description:` content
- `skills/add-skill/SKILL.md`, `skills/skill-creator/SKILL.md` — generators
  that must adopt the canonical template (Layer A)
- ADR-066 — polyglot policy. This ADR follows the same "rule + audit test"
  pattern ratified there for Python naming.
- ADR-064 — harness-agnostic Cognitive OS. Frontmatter contract applies
  uniformly across harnesses.
- `rules/agent-quality.md` — broader principle: agents must produce
  production-ready output. Empty `description: >` is a "stub implementation"
  in a different file format.
- `rules/acceptance-criteria.md` — every Phase 1 task should have measurable
  AC drawn from this ADR's §Verification.
- engram topic `perf/hook-chain-rca-2026-04-24` — context for the latency
  budget that pushes Layer B to advisory by default.

## Open questions

1. **BLOCK or WARN by default for Layer B?**
   Today's choice: WARN (exit 0). Strict mode is opt-in via
   `COS_STRICT_SKILL_VALIDATION=1`. Revisit after one month of metrics: if
   Layer C catches >0 violations that Layer B already warned about, flip
   to BLOCK by default.

2. **Phase 2 sequencing — hooks, rules, or ADRs first?**
   No analog incident has occurred yet for those artifact types. Wait for
   one (or for an explicit operator directive). Don't preemptively apply
   the pattern.

3. **How is the template kept in sync with the validators when fields
   evolve?**
   Single source of truth: this ADR's §Decision — What each layer enforces
   table. Any field addition requires (a) updating that table, (b) updating
   `templates/skill-template.md`, (c) updating the hook regex list,
   (d) updating the audit test. A meta-test could assert these four are in
   sync, but that's Phase 2 metalevel work.

4. **Does Layer B need a metrics file?**
   Probably yes — `metrics/skill-frontmatter-warnings.jsonl` — to track
   warning frequency and inform the BLOCK-vs-WARN decision (Q1). Phase 1
   includes basic metrics; full dashboard is later.

5. **What about `audience: os-dev` — is that real or a typo for `os-only`?**
   Inspect the skill catalog before finalizing the audience enum. If
   `os-dev` is unused, drop it from the v1 contract and let Layer C catch
   any straggler.
