---
adr: 65
title: Tech Radar Curation Pipeline (`/radar-update`)
status: proposed
implementation_status: planned
date: '2026-04-24'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit proposed status without accepted status
---

<!-- SCOPE: os-only -->
<!-- audience: os-dev -->

# ADR-065 — Tech Radar Curation Pipeline (`/radar-update`)

## Status

**Proposed** — 2026-04-24. Builds on `/repo-scout` (formerly `/eval-repo`,
v2.0.1) and reuses the same per-repo evaluation pipeline. Closes the manual
curation gap between per-repo evaluation artifacts and the canonical radar
documents (`docs/04-Concepts/patterns/ecosystem-tools.md`, `docs/05-Methodology/root/blocked-tools.md`).

## Context

The Cognitive OS publishes a curated tech radar across two hand-edited
documents:

- `docs/04-Concepts/patterns/ecosystem-tools.md` (367 lines) — ADOPT / TRIAL / ASSESS
  entries with usage examples and adoption notes.
- `docs/05-Methodology/root/blocked-tools.md` (132 lines) — REJECT entries (AGPL/SSPL/BUSL
  license-blocked tools) per `rules/license-policy.md`.

Per-repo evaluation already exists. `skills/repo-scout/SKILL.md` (v2.0.1)
runs a 10-step pipeline — DeepWiki summary, license gate, weighted scoring,
classification (ADOPT/TRIAL/ASSESS/HOLD/REJECT), per-repo markdown artifact
at `.cognitive-os/reports/repo-scout/<owner>_<repo>.md`, batch-mode input
(plain list, CSV, JSON), and Engram persistence under `tech-radar/{repo-name}`.

What is **missing** is the merge step: taking the N artifacts produced by a
batch run and folding them into the two canonical radar documents without
clobbering the human-written prose around them. Today an operator runs
`/repo-scout --batch urls.txt`, then opens both markdown files in an editor
and copy-pastes 5–20 entries by hand, reformatting each one to match the
surrounding style.

The operator stated the pain plainly:

> Operator request: allow a batch of URLs to update the radar without overwriting
> manually curated notes for each repository.

Manual curation does not scale past roughly **20 tools/month**. It is also
the single most common source of radar drift (a repo gets re-evaluated, the
score moves, but nobody updates the doc because the diff is annoying). ADR-048
(docker freshness) is structurally similar — automated evaluation already
runs, the hand-off to the canonical doc is the bottleneck.

### What is already in place

| Building block | Status | Used by `/radar-update` |
|---|---|---|
| Per-repo eval pipeline | `skills/repo-scout/` v2.0.1 | Delegated unchanged |
| Batch input parsing (txt/csv/json) | `/repo-scout --batch` | Reused unchanged |
| Per-repo Engram cache `tech-radar/{repo}` | Live | Read-through cache |
| License gate (AGPL/SSPL/BUSL → REJECT) | `rules/license-policy.md` | Drives target-doc routing |
| Per-repo markdown artifact | `.cognitive-os/reports/repo-scout/` | Source of merge content |

### Why now

ADR-064 just made the OS harness-agnostic. The radar is the SO's public face
(README links to `ecosystem-tools.md`); keeping it fresh is part of the
marketing surface. Closing the curation gap turns "we evaluated 30 repos this
sprint" into a 1-command radar refresh.

## Decision

Create a new SO-only skill `/radar-update <url-or-file> [--apply]` that
orchestrates per-repo evaluation **plus** canonical-doc merge. Seven design
points:

### 1. Input parity with `/repo-scout --batch`

`/radar-update` accepts the same four input shapes: single URL, plain text
list, CSV, JSON. No new parser — we shell out to the existing batch front-end
and consume its output.

### 2. Per-repo eval is delegated, not reimplemented

For each URL the skill calls `/repo-scout` (sub-agent or direct skill
invocation depending on harness). It does **not** re-implement DeepWiki
fetch, scoring, or license detection. Cache hits in Engram
(`tech-radar/{repo-name}`) are reused; only stale or missing entries trigger
a fresh eval.

### 3. Classification → target-doc routing

| Classification | Target document | Section |
|---|---|---|
| ADOPT | `docs/04-Concepts/patterns/ecosystem-tools.md` | `## Adopted` (or existing top-level section) |
| TRIAL | `docs/04-Concepts/patterns/ecosystem-tools.md` | `## Trial` |
| ASSESS | `docs/04-Concepts/patterns/ecosystem-tools.md` | `### (ASSESS)` subsection — promotion candidates |
| HOLD | `docs/04-Concepts/patterns/ecosystem-tools.md` | `### (HOLD)` subsection alongside ASSESS |
| REJECT | `docs/05-Methodology/root/blocked-tools.md` | grouped by license family (AGPL / SSPL / BUSL / other) |

ASSESS and HOLD live in subsections of the same file so a reviewer can
promote (move to ADOPT/TRIAL) or demote (move to REJECT) with a single
section move.

### 4. Auto-owned vs human-owned field taxonomy

This is the most important contract. The merge engine MUST know which fields
it can rewrite freely and which it must preserve verbatim.

| Field | Owner | Rationale |
|---|---|---|
| `repo` (owner/name) | auto | Identity key — never edited |
| `stars` | auto | Snapshot value, refreshed every run |
| `last_commit` / `last_release` | auto | Activity signal — refreshed every run |
| `license` | auto | Pulled from GitHub API |
| `ci_health` (green/red/none) | auto | Pulled from latest workflow runs |
| `score` (numeric, weighted) | auto | Recomputed each run |
| `classification` (ADOPT/TRIAL/ASSESS/HOLD/REJECT) | auto | Recomputed each run |
| `one_liner` (≤120 char description) | auto | Generated from DeepWiki summary; deterministic |
| `last_evaluated` (ISO date) | auto | Stamped each run |
| `usage_examples` (code blocks, commands) | **human** | Written by adopters, not derivable |
| `adoption_notes` (how we actually use it) | **human** | Project-specific context |
| `gotchas` / `limitations` (free prose) | **human** | Field experience, not from upstream README |
| `linked_adrs` (e.g. ADR-048) | **human** | Curatorial decision |
| `replaces` / `superseded_by` (lifecycle prose) | **human** | Manual lifecycle marker |

Auto-owned fields are stored as a YAML frontmatter block at the top of each
entry (machine-parseable). Human-owned fields are free-form markdown after
the frontmatter. The merge engine rewrites only the frontmatter; everything
between `---` markers and the next `### ` heading is left untouched.

### 5. Merge algorithm (top-down with fuzzy match)

```
for each evaluated repo R in batch:
    parse target doc (ecosystem-tools.md or blocked-tools.md per classification)
    scan headings ### for entries with frontmatter `repo: <owner>/<name>`
    if exact match found:
        rewrite frontmatter (auto-owned fields only)
        leave human-owned body untouched
        emit diff line "updated {repo} ({prev_class} → {new_class})" if class changed
    else if fuzzy match (case-insensitive name, with/without owner prefix):
        emit warning, treat as new insert (human reviews dry-run)
    else:
        insert new entry under correct section, alphabetically
        emit diff line "added {repo} as {classification}"
```

Conflict on classification shift (e.g. ADOPT entry now scores REJECT due to
license relicense): the entry is **moved** to `blocked-tools.md`, the
human-owned body travels with it, a comment `<!-- moved from ecosystem-tools.md
on YYYY-MM-DD by /radar-update -->` is prepended.

### 6. Dry-run by default, `--apply` writes

Default mode: emit a **unified diff** (chosen over side-by-side because git
tooling and PR review surfaces already render unified diffs natively;
side-by-side would require a custom renderer). The diff is printed to stdout
and saved to `.cognitive-os/reports/radar-update/<timestamp>.diff` for
audit.

`--apply` writes the changes, **without** committing. Commit is a separate
explicit step (operator runs `git add -p` to review hunks before committing,
matching how the rest of SO docs are edited).

### 7. CHANGELOG side-effect

On `--apply`, append to `CHANGELOG.md` under `## [Unreleased]` →
`### Documentation`:

- New entry: `- radar: added {owner/repo} as {classification}`
- Updated classification: `- radar: updated {owner/repo} ({prev}→{new})`
- License-driven move: `- radar: moved {owner/repo} to blocked-tools (license: {old}→{new})`

If `## [Unreleased]` or the `### Documentation` subsection is missing they
are created. One line per repo, no batching ("3 repos updated"), so the
changelog is greppable.

## What we replicate / what we don't

**Replicate (via delegation)**: the entire `/repo-scout` per-repo pipeline.
Including its Engram cache, license gate, and scoring weights. `/radar-update`
adds zero new evaluation logic.

**Do not replicate**:

- ThoughtWorks-style D3 radar visualization (quadrants, rings, blips). Operator
  did not ask for it; the canonical surface is markdown for git/PR review.
- Auto-commit / auto-push. `--apply` writes files; humans commit.
- Cross-radar federation (consuming external radars like CNCF). Out of scope.
- Per-repo deep-dive ADR generation. That remains a manual `/repo-forensics`
  follow-up for repos worth a dedicated ADR.

## Implementation phases

Honest cost estimates — these are 1-session items only if Phase 1 finds no
parser surprises in the existing radar docs.

### Phase 1 — Skill + merge engine + dry-run (1.5 sessions)

- `skills/radar-update/SKILL.md` with input parsing (delegating to `/repo-scout`).
- `lib/radar_merger.py` — frontmatter parser, section locator, fuzzy matcher,
  unified-diff emitter.
- Dry-run output to stdout + `.cognitive-os/reports/radar-update/`.

Risk: existing radar entries may not have YAML frontmatter today. Phase 1
includes a one-time migration pass to add frontmatter to existing entries
(human-owned bodies untouched). This is its own PR.

### Phase 2 — `--apply` + CHANGELOG side-effect (0.5 session)

- File-write path with atomic temp-file replace.
- CHANGELOG append logic with section bootstrap.
- No git operations — leaves staging to the human.

### Phase 3 — Test coverage (1 session)

Minimum tests:

- Dedup correctness: same URL twice in a batch produces one entry.
- Human-owned field preservation: golden-file test where body has code blocks,
  custom prose, ADR links — all survive a re-run.
- Classification routing: 5-URL fixture (1 AGPL, 2 MIT-ADOPT, 2 ASSESS) maps
  to (1 in blocked-tools, 3 in ecosystem-tools) with stable diffs.
- Classification shift: ADOPT → REJECT migration moves the entry between docs
  and preserves human-owned prose.
- Fuzzy-match warning fires when frontmatter says `repo: foo/bar` but a
  heading says `### bar` (no owner prefix).

Total: roughly **3 sessions** for a usable v1, not counting the migration PR
for existing entries.

## Consequences

### Positive

- Curation scales: 20 URLs → 1 dry-run → 1 review → 1 apply.
- Single source of truth: the radar docs stay canonical, no parallel database.
- Human annotations preserved by contract (auto vs human field split).
- Drift detection: re-running on existing entries surfaces stale licenses,
  archived repos, score drops — visible in the dry-run diff.
- CHANGELOG entries make radar movement auditable per release.

### Negative

- Diff-merge conflicts if a human edits an entry while a batch is mid-flight.
  Mitigation: `--apply` re-reads the doc at write time and aborts if the
  parsed frontmatter changed since the dry-run was emitted.
- Radar doc format becomes load-bearing. Any future reformat (e.g. moving
  from `### heading` to a table) must be backward-compat or ship with a
  migration script in the same PR.
- Frontmatter clutter: existing readable entries get a YAML block prepended.
  Cosmetic; reviewable in the migration PR.

### Neutral

- No runtime impact (docs only).
- No new external dependencies; merger is pure Python + existing skill
  infrastructure.

## Alternatives rejected

1. **Status quo: `/repo-scout --batch` + manual copy-paste.** Exactly today's
   pain. Operator explicitly asked us to fix this; rejecting the status quo
   *is* the ADR.

2. **Maintain the radar in a database (SQLite, JSON file, etc).** Loses git
   history, breaks PR-based review, diverges from how every other SO doc is
   maintained, and breaks the README links that point at the markdown. The
   radar is *prose with structure*, not a record set.

3. **Auto-commit on `--apply` without dry-run default.** Too destructive for
   a doc that is part of the public marketing surface. Even a 1-character
   accidental rewrite would land in main without review.

4. **Generate the radar entirely from `/repo-scout` artifacts on every run
   (no human-owned fields).** Would scale infinitely but destroys the
   adoption notes and usage examples that make the radar *useful* vs a
   GitHub-stars dashboard. The whole point of curation is human judgment.

5. **Use a third-party tool (Backstage TechRadar, ThoughtWorks Build Your
   Own).** Heavyweight (Node frontend, JSON spec format), introduces a build
   step for what is currently a markdown file, and replaces git-native review
   with a JSON-edit workflow. Rejected on simplicity grounds.

## Verification

The skill is verified working when:

- Feeding a 5-URL batch with 1 AGPL repo, 2 MIT-ADOPT repos, 2 ASSESS repos
  produces exactly **3 inserts** in `ecosystem-tools.md` (2 ADOPT + 2 ASSESS
  → wait, that's 4) — corrected: **2 ADOPT + 2 ASSESS = 4 inserts** in
  `ecosystem-tools.md`, **1 insert** in `blocked-tools.md`, **0 changes** in
  any other file.
- `--apply` output is byte-identical to the dry-run diff applied to the
  source files.
- Re-running the same batch immediately is a **no-op diff** (auto-owned
  fields unchanged because Engram cache returns identical scores within the
  TTL window).
- Editing a `usage_examples` block and re-running does **not** revert the
  edit — frontmatter refreshes, body stays.
- Switching one repo's license upstream from MIT to AGPL between runs
  produces a single move-diff: entry leaves `ecosystem-tools.md`, appears in
  `blocked-tools.md`, with the human-owned body intact and a `<!-- moved
  from ... -->` marker prepended.
- CHANGELOG `[Unreleased] → Documentation` gains exactly one line per repo
  added/updated.

Phase 3 tests encode each of these as a golden-file assertion.

## Related

- `skills/repo-scout/SKILL.md` (v2.0.1) — per-repo eval, delegated unchanged
- `rules/license-policy.md` — license → REJECT mapping
- `docs/04-Concepts/patterns/ecosystem-tools.md` — canonical ADOPT/TRIAL/ASSESS doc
- `docs/05-Methodology/root/blocked-tools.md` — canonical REJECT doc
- ADR-048 — docker container freshness (structurally similar curation gap)
- ADR-062 — multi-provider agent loop (orthogonal, not used by this skill)
- ADR-063 — agent tool replication strategy (orthogonal)
- ADR-064 — harness-agnostic OS. **`/radar-update` is SO-only**, so
  cross-harness portability is explicitly out of scope; the skill assumes
  Claude Code or the SO's bare runner.

## Open questions

1. **Conflict resolution when human curation disagrees with auto
   classification.** A human may have written "ADOPT — production-proven
   since 2025-09" in the body, while `/repo-scout` now scores TRIAL because
   stars dropped. Do we (a) honor the auto classification and let the human
   prose look stale, (b) honor the human classification and emit a warning
   in the diff, or (c) introduce a `classification_override: ADOPT` field
   in the frontmatter (human-owned, suppresses auto-rewrite of that one
   field)? Leaning toward (c) but deferring to first real conflict.

2. **Periodic `--refresh` mode.** Should `/radar-update --refresh` re-evaluate
   every existing entry on a cadence (weekly cron?) to catch drift —
   relicenses, archived repos, score changes? Pro: catches silent radar
   rot. Con: floods CHANGELOG with mechanical updates and may exhaust the
   eval budget for repos that haven't meaningfully changed. Decision deferred
   until we have ~60 entries (currently ~26 from ADR-048 sweep).

3. **Multi-repo entries.** Some radar entries cover a *family* (e.g.
   "OpenTelemetry — collector + sdk + contrib"). The frontmatter assumes one
   `repo: owner/name`. Do we support `repos: [...]` arrays, or force one
   entry per repo with a curated `family: opentelemetry` tag? Probably the
   latter, but flagging now.
