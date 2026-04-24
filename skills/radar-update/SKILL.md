<!-- SCOPE: os-only -->
---
name: radar-update
command: /radar-update
description: >
  Tech radar curation pipeline. Evaluates one or more GitHub repos via /repo-scout,
  then merges the results into the canonical radar docs (ecosystem-tools.md,
  blocked-tools.md) while preserving all human-authored prose. Dry-run by default;
  --apply writes files. Delegates per-repo evaluation to /repo-scout unchanged.
version: 0.1.0
user-invocable: true
auto-generated: false
last-updated: 2026-04-24
license: MIT
audience: os-dev
metadata:
  author: luum
  adr: docs/adrs/ADR-065-radar-update-curation-pipeline.md
summary_line: >
  Merge /repo-scout evaluations into ecosystem-tools.md and blocked-tools.md
  while preserving human-authored prose. Dry-run by default, --apply writes.

---

<!-- SCOPE: os-only -->

# `/radar-update` — Tech Radar Curation Pipeline

> **ADR**: `docs/adrs/ADR-065-radar-update-curation-pipeline.md`
> **Delegates to**: `/repo-scout` (v2.0.1) — all per-repo evaluation is reused unchanged.
> **Target docs**: `docs/patterns/ecosystem-tools.md` (ADOPT/TRIAL/ASSESS/HOLD) and `docs/blocked-tools.md` (REJECT).

## Invocation

```
/radar-update <github-url>                      # single URL, dry-run
/radar-update --batch <file>                    # batch from file, dry-run
/radar-update <github-url> --apply              # single URL, write files
/radar-update --batch <file> --apply            # batch, write files
/radar-update <github-url> --force              # re-evaluate even if cached <30d
/radar-update --batch <file> --force --apply    # batch force-refresh + write
```

`<file>` formats (same as `/repo-scout --batch`):
- **Plain text**: one GitHub URL per line; `#` comments and blank lines skipped
- **CSV**: must have a `url` column; optional `priority` and `context` columns
- **JSON array**: `[{"url": "...", "priority": "high"}]`

`--force`: passes through to `/repo-scout`, bypassing the 30-day Engram cache.
`--apply`: writes changes to disk. Without `--apply`, the skill prints a unified diff and saves it to `.cognitive-os/reports/radar-update/<timestamp>.diff` — no files are modified.

---

## Auto-Owned vs Human-Owned Field Taxonomy

This is the merge contract. The merge engine rewrites **auto-owned** fields on every run; **human-owned** fields are preserved verbatim.

| Field | Owner | Rationale |
|-------|-------|-----------|
| `repo` (owner/name) | **auto** | Identity key — never edited |
| `stars` | **auto** | Snapshot value, refreshed every run |
| `last_commit` / `last_release` | **auto** | Activity signal — refreshed every run |
| `license` | **auto** | Pulled from GitHub API |
| `ci_health` (green/red/none) | **auto** | Pulled from latest workflow runs |
| `score` (numeric, weighted) | **auto** | Recomputed each run |
| `classification` (ADOPT/TRIAL/ASSESS/HOLD/REJECT) | **auto** | Recomputed each run |
| `one_liner` (≤120 char description) | **auto** | Generated from DeepWiki summary; deterministic |
| `last_evaluated` (ISO date) | **auto** | Stamped each run |
| `usage_examples` (code blocks, commands) | **human** | Written by adopters, not derivable |
| `adoption_notes` (how we actually use it) | **human** | Project-specific context |
| `gotchas` / `limitations` (free prose) | **human** | Field experience, not from upstream README |
| `linked_adrs` (e.g. ADR-048) | **human** | Curatorial decision |
| `replaces` / `superseded_by` (lifecycle prose) | **human** | Manual lifecycle marker |

Auto-owned fields are stored in a YAML frontmatter block (`---…---`) at the top of each entry heading. Human-owned fields are free-form markdown AFTER the closing `---`. The merge engine rewrites only the frontmatter block; everything after it (until the next `### ` heading) is left untouched.

---

## Classification → Target Document Routing

| Classification | Target document | Section |
|----------------|-----------------|---------|
| ADOPT | `docs/patterns/ecosystem-tools.md` | Existing top-level section or appended |
| TRIAL | `docs/patterns/ecosystem-tools.md` | `### (TRIAL)` subsection |
| ASSESS | `docs/patterns/ecosystem-tools.md` | `### (ASSESS)` subsection |
| HOLD | `docs/patterns/ecosystem-tools.md` | `### (HOLD)` subsection |
| REJECT | `docs/blocked-tools.md` | Grouped by license family (AGPL / GPL / SSPL / ELv2 / other) |

ASSESS and HOLD live as subsections so a reviewer can promote (move to ADOPT/TRIAL) or demote (move to REJECT) with a single section move.

---

## Process Steps

### Step 0: Parse Invocation Arguments

```bash
# Determine mode
if [ "$1" == "--batch" ]; then
    BATCH_FILE="$2"
    APPLY=$(echo "$@" | grep -q -- "--apply" && echo 1 || echo 0)
    FORCE=$(echo "$@" | grep -q -- "--force" && echo 1 || echo 0)
else
    SINGLE_URL="$1"
    APPLY=$(echo "$@" | grep -q -- "--apply" && echo 1 || echo 0)
    FORCE=$(echo "$@" | grep -q -- "--force" && echo 1 || echo 0)
fi
```

Validate that `SINGLE_URL` is a GitHub URL or that `BATCH_FILE` exists on disk.
On any validation error: print a clear error and stop — do NOT proceed with partial input.

### Step 1: Delegate Per-Repo Evaluation to `/repo-scout`

For each URL in the input:

```bash
# For a single URL
FORCE_FLAG=""
[ "$FORCE" = "1" ] && FORCE_FLAG="--force"
/repo-scout "$URL" $FORCE_FLAG
```

For batch mode, pass the file directly:

```bash
/repo-scout --batch "$BATCH_FILE" $FORCE_FLAG
```

`/repo-scout` writes one markdown artifact per repo to `.cognitive-os/reports/repo-scout/<owner>_<repo>.md` and persists classification + score to Engram under `tech-radar/{repo-name}`. The merge engine reads from these artifacts.

**Do NOT re-implement** DeepWiki fetch, scoring, or license detection. `/repo-scout` owns all of that.

### Step 2: Collect Evaluation Artifacts

```bash
# After /repo-scout completes, collect all artifacts for this batch
ARTIFACTS=()
for URL in "${URLS[@]}"; do
    OWNER=$(echo "$URL" | sed 's|.*github.com/||' | cut -d/ -f1)
    REPO=$(echo "$URL" | sed 's|.*github.com/||' | cut -d/ -f2 | sed 's|\.git$||')
    ARTIFACT=".cognitive-os/reports/repo-scout/${OWNER}_${REPO}.md"
    [ -f "$ARTIFACT" ] && ARTIFACTS+=("$ARTIFACT")
done
```

For each artifact, extract (using the Python merge engine):
- `repo: owner/name`
- `classification: ADOPT|TRIAL|ASSESS|HOLD|REJECT`
- `stars`, `license`, `ci_health`, `score`, `last_evaluated`, `one_liner`

### Step 3: Run the Merge Engine

```bash
# Dry-run (default)
python3 scripts/radar_merge.py \
    --artifacts "${ARTIFACTS[@]}" \
    --ecosystem-tools docs/patterns/ecosystem-tools.md \
    --blocked-tools docs/blocked-tools.md \
    --output-diff .cognitive-os/reports/radar-update/$(date +%Y%m%dT%H%M%S).diff

# Apply mode
python3 scripts/radar_merge.py \
    --artifacts "${ARTIFACTS[@]}" \
    --ecosystem-tools docs/patterns/ecosystem-tools.md \
    --blocked-tools docs/blocked-tools.md \
    --apply \
    --changelog CHANGELOG.md
```

The merge engine (see `scripts/radar_merge.py`) handles:
1. Parse each artifact for auto-owned fields
2. Locate existing entry by `repo:` frontmatter key (exact match first, fuzzy by heading name second)
3. For exact match: rewrite only the frontmatter block; preserve body
4. For fuzzy match: emit `WARN: fuzzy match found for {repo} — treating as new insert, please review`
5. For no match: insert new entry under the correct section, alphabetically by repo name
6. For classification shift (e.g. ADOPT → REJECT): move entry to the correct target doc, prepend `<!-- moved from {source-doc} on {date} by /radar-update -->`

### Step 4: Emit Dry-Run Output

If NOT `--apply`:

```
--- a/docs/patterns/ecosystem-tools.md
+++ b/docs/patterns/ecosystem-tools.md
@@ -42,0 +43,18 @@
+### some-tool — Short description (ADOPT)
+
+---
+repo: owner/some-tool
+stars: 4200
+license: MIT
+classification: ADOPT
+score: 84
+one_liner: "Does X well with Y approach"
+last_evaluated: 2026-04-24
+ci_health: green
+---
+
```

Print the unified diff to stdout. Save it to `.cognitive-os/reports/radar-update/<timestamp>.diff`. Summarize at the end:

```
--- radar-update dry-run summary ---
ecosystem-tools.md : 2 added, 1 updated, 0 moved
blocked-tools.md   : 1 added, 0 updated, 0 moved
Total repos        : 3 (0 errors, 0 fuzzy warnings)
Diff saved to      : .cognitive-os/reports/radar-update/20260424T143022.diff
Run with --apply to write changes.
```

### Step 5: Apply Mode — Write Files

If `--apply`:

1. Re-read target docs at write time; abort if frontmatter changed since dry-run (stale-write protection)
2. Write the merged content using atomic temp-file replace:

```bash
# Atomic write via temp file
python3 scripts/radar_merge.py --apply ... # writes to temp files, then os.replace()
```

3. Update CHANGELOG.md (see Step 6)
4. Print apply summary (same format as dry-run summary, minus "Run with --apply" line)

### Step 6: CHANGELOG Side-Effect (apply only)

On `--apply`, append one line per repo under `## [Unreleased]` → `### Documentation`.
Create the section if missing:

```markdown
## [Unreleased]

### Documentation
- radar: added owner/some-tool as ADOPT
- radar: updated owner/other-tool (TRIAL→ADOPT)
- radar: moved owner/bad-tool to blocked-tools (license: MIT→AGPL)
```

Rules:
- **NEW entry** → `- radar: added {owner}/{repo} as {classification}`
- **Updated classification** → `- radar: updated {owner}/{repo} ({prev}→{new})`
- **License-driven move** → `- radar: moved {owner}/{repo} to blocked-tools (license: {old}→{new})`
- **Fields refreshed only** → `- radar: refreshed {owner}/{repo} metrics`

One line per repo, no batching. The CHANGELOG is greppable by `owner/repo`.

---

## Merge Engine: Option A — `scripts/radar_merge.py`

**Choice: Option A (Python helper `scripts/radar_merge.py`)**

Rationale: the merge logic requires YAML frontmatter parsing, regex-based section location, alphabetical insertion, fuzzy name matching, unified diff generation, and atomic file writes. This exceeds 100 lines of clean logic. Inline bash with `awk`/`sed` would be brittle and harder to test in isolation. Python 3.12 handles all of this with stdlib only (`difflib`, `re`, `yaml` via `ruamel.yaml` or inline parser, `pathlib`, `tempfile`). The script lives in `scripts/` (no wiring-allowlist entry needed per project convention).

The merge engine is tested independently at `tests/unit/test_radar_merge.py`.

---

## Error Handling

| Condition | Behavior |
|-----------|----------|
| `/repo-scout` returns ERRORED for a URL | Log the error, skip that repo, continue with others |
| Target doc is missing | Abort with clear error — do NOT create it (it must exist already) |
| Frontmatter YAML parse error in target doc | Warn, treat entry as human-only (no frontmatter rewrite) |
| Classification shift ADOPT → REJECT | Move entry, preserve body, prepend moved-from comment |
| Fuzzy match only (no `repo:` frontmatter) | Warn, treat as new insert (operator reviews dry-run diff) |
| `--apply` + stale write (doc changed since dry-run) | Abort with: `ABORT: {doc} changed since dry-run. Re-run without --apply to regenerate diff.` |

---

## Dry-Run Report Directory

Reports are saved to `.cognitive-os/reports/radar-update/` as `<timestamp>.diff`.
The directory is created if it does not exist.
Old reports are NOT automatically deleted (they serve as an audit trail).

---

## Cache Behavior

`/repo-scout` caches results in Engram under `tech-radar/{repo-name}` with a 30-day TTL.
`/radar-update` inherits this cache: if a repo was evaluated within 30 days, `/repo-scout` returns the cached result without a fresh network call.
Use `--force` to bypass the cache and re-evaluate from scratch.

---

## Acceptance Criteria

- `skills/radar-update/SKILL.md` exists with `<!-- SCOPE: os-only -->` at line 1 and frontmatter `version: 0.1.0`, `audience: os-dev`
- Running dry-run prints unified diff to stdout without modifying any file
- `--apply` writes files and appends CHANGELOG entries
- Human-owned prose (usage examples, adoption notes, gotchas) is never overwritten
- Classification shift moves the entry between docs with body intact
- Tests pass: `uv run pytest tests/unit/test_radar_merge.py -q`
- Contract tests pass: `uv run pytest tests/audit/test_skills_contracts.py -q`

---

## Related

- `skills/repo-scout/SKILL.md` (v2.0.1) — per-repo evaluation, delegated unchanged
- `docs/adrs/ADR-065-radar-update-curation-pipeline.md` — full design spec
- `scripts/radar_merge.py` — merge engine implementation
- `tests/unit/test_radar_merge.py` — unit tests for merge engine
- `rules/license-policy.md` — license → REJECT mapping
- `docs/patterns/ecosystem-tools.md` — canonical ADOPT/TRIAL/ASSESS/HOLD doc
- `docs/blocked-tools.md` — canonical REJECT doc
