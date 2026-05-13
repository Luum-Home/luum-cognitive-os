<!-- SCOPE: both -->
---
name: repo-scout
description: 'Scout external git repositories for potential inclusion in the tech radar. Three-level assessment: DeepWiki
  summary, shallow clone analysis, deep evaluation. Supports bulk mode (--batch <file>) for evaluating multiple repos in one
  pass.

  '
version: 2.0.1
user-invocable: true
auto-generated: false
last-updated: 2026-04-24
license: MIT
metadata:
  author: luum
audience: both
summary_line: Scout external git repositories for tech radar classification (bulk mode, markdown artifacts, adoption signals).
routing_patterns:
- pattern: https?://github\.com/[\w.\-]+/[\w.\-]+
  confidence: 0.75
- pattern: \brepo[- ]?scout\b
  confidence: 0.95
- pattern: \btech\s*radar\b
  confidence: 0.8
- pattern: \b(evalua[rt]\w*|evaluate)\s+(this|the|ese?|este?)?\s*repo
  confidence: 0.85
platforms:
- claude-code
prerequisites: []
routing_intents:
- intent: repository_scouting_evaluation
  description: User asks to evaluate, scout, or assess an external git repository for tech radar, adoption, or tool comparison.
  confidence: 0.86
---

## Purpose

Structured evaluation of external repositories for tech radar classification. Provides a repeatable, scored assessment instead of ad-hoc review. Supports single-repo and bulk-batch invocations, writes markdown artifacts per repo, and captures adoption signals (issue velocity, release cadence, CI health).

## Invocation

```
/repo-scout <github-url> [--level=shallow|deep] [--no-cleanup]
/repo-scout --batch <file> [--force] [--level=shallow|deep] [--no-cleanup]
```

`<file>` accepted formats:
- **Plain text**: one GitHub URL per line; blank lines and `#` comments are skipped
- **CSV**: must have a `url` column; optional `priority` and `context` columns pass through to the per-repo report
- **JSON array**: `[{"url": "...", "priority": "high", "context": "..."}]`

`--force`: re-evaluate repos already in Engram within the last 30 days (skip the cache check).

## What to Do

### Step 0: Mode Dispatch

If `--batch <file>` is present:
1. Parse the file according to its extension/content (plain → URL-per-line; `.csv` → parse header; `.json` → parse array)
2. Collect all `{url, priority?, context?}` entries
3. Run **Steps 1–9** for each URL **serially** (not in parallel — gh api + WebFetch have rate limits)
4. On any per-repo error: set `classification = ERRORED`, record the error message, and **continue** to the next URL
5. After all repos are processed: write the consolidated batch report (see **Step 10b**)
6. Return the batch summary as the final output

If no `--batch`, run Steps 1–9 for the single URL and go to Step 10a.

### Step 1: Parse Repository URL

Extract `owner` and `repo` from the GitHub URL.

Supported formats:
- `https://github.com/owner/repo`
- `https://github.com/owner/repo.git`
- `github.com/owner/repo`
- `owner/repo` (shorthand)

Strip `.git` suffix, protocol prefix, and `github.com/` prefix. Reject non-GitHub URLs.

**Batch cache check** (skip if `--force`):

```
result = mem_search(query: "tech-radar/{repo-name}")
if result found and observation timestamp < 30 days ago:
    reuse cached classification + score, skip Steps 2–9 for this URL
    note "skipped (cached {date})" in the batch summary
```

### Step 2: DeepWiki Fetch (Level 0 — always)

Use WebFetch to query `https://deepwiki.com/{owner}/{repo}`:

```
Extract:
├── Architecture overview
├── Primary language and framework
├── Key dependencies (and their licenses)
├── API surface / exported interface
├── Design patterns used
├── Test strategy
└── Known limitations or trade-offs
```

**Fallback**: If DeepWiki is unavailable or returns empty:
```bash
gh api repos/{owner}/{repo} --jq '{
  name, description, language, license: .license.spdx_id,
  stars: .stargazers_count, forks: .forks_count,
  archived: .archived, pushed_at, created_at,
  open_issues: .open_issues_count
}'
```

### Step 3: Auto-Reject Gates

Immediately classify and STOP if any gate fails:

| Gate | Condition | Classification |
|------|-----------|---------------|
| License | AGPL-3.0, SSPL, BUSL | **REJECT** |
| Archived | `archived: true` | **REJECT** |
| Inactive | Last commit > 12 months ago | **HOLD** |
| No license | License field empty/null | **ASSESS** (flag for manual review) |

If REJECT or HOLD, skip to Step 8 (Persist) with the gate as rationale.

### Step 4: Shallow Clone (Level 1 — default)

```bash
git clone --depth 1 --single-branch {url} reference/{repo-name}
```

Analyze the cloned repository:

```
Code Quality:
├── Directory structure (flat vs organized, separation of concerns)
├── Code style consistency (linting config present?)
├── Error handling patterns
└── Type safety (TypeScript strict? Go error handling?)

API Surface:
├── Exported functions/types/interfaces
├── Entry points (main, index, exports)
├── Configuration options
└── Extension points (plugins, hooks, middleware)

Testing:
├── Test file presence and organization
├── Test runner config
├── Coverage config (if any)
├── Test patterns (unit, integration, e2e)

Dependencies:
├── Direct dependency count
├── Known vulnerable deps (check lock file dates)
├── Dependency freshness
└── Vendored vs fetched

Documentation:
├── README completeness (install, usage, API, examples)
├── API documentation (generated or manual)
├── Changelog / release notes
└── Contributing guide
```

### Step 5: Scoring + Adoption Signals

#### Core weighted scoring (each criterion 0–10)

| Criterion | Weight | Scoring Guide |
|-----------|--------|---------------|
| **Relevance** | 30% | How well does it fit our stack, solve our problems, align with our architecture? |
| **License** | 25% | MIT/Apache=10, BSD=8, MPL=7, LGPL=6, GPL=5, Unknown=2, AGPL/SSPL=0 |
| **Activity** | 20% | Commits <1mo=10, <3mo=8, <6mo=6, <12mo=3, >12mo=0 |
| **Maturity** | 15% | v1.0+=8, semver=7, pre-release=5, no versioning=3; production users boost score |
| **Integration** | 10% | Clean API=10, good types=8, docs+examples=7, minimal config=6, complex setup=3 |

**Total** = weighted sum (0.0 – 10.0)

#### Adoption Signals (soft — not folded into the numeric score)

These three signals are QUALITATIVE descriptors only. They do not alter the numeric score. Rationale: the existing weights already balance activity and maturity; forcing issue/CI data into the score would create unstable math (some repos have no Actions, or are single-maintainer with intentionally low issue count). Use them as tiebreakers and as extra context in the Risks section.

**1. Issue velocity** — issues opened or closed in the last 30 days:

```bash
gh api "repos/{owner}/{repo}/issues?state=all&since=$(date -v-30d +%Y-%m-%d)&per_page=100" \
  --jq 'length'
```

Descriptor map: ≥20 = "high issue activity", 5–19 = "moderate issue activity", 1–4 = "low issue activity", 0 = "dormant issues".

**2. Release cadence** — median days between the last 5 tags:

```bash
gh api "repos/{owner}/{repo}/tags?per_page=5" --jq '[.[].commit.sha]'
# for each sha: gh api repos/{owner}/{repo}/commits/{sha} --jq '.commit.committer.date'
# compute median interval in days
```

Descriptor map: median ≤7d = "weekly releases", ≤30d = "monthly releases", ≤90d = "quarterly releases", >90d = "infrequent releases", no tags = "no releases found".

**3. CI health** — last 10 workflow run success rate:

```bash
gh api "repos/{owner}/{repo}/actions/runs?per_page=10" \
  --jq '[.workflow_runs[].conclusion] | map(select(. != null)) | {total: length, passing: map(select(. == "success")) | length}'
```

Skip if repo has no Actions workflows. Descriptor map: 90–100% = "CI green", 70–89% = "CI flaky", <70% = "CI red", no runs = "no CI found".

### Step 6: Classification

| Score | Ring | Meaning |
|-------|------|---------|
| 8.0 – 10.0 | **ADOPT** | Proven, recommend for production use |
| 6.0 – 7.9 | **TRIAL** | Promising, test in non-critical path first |
| 4.0 – 5.9 | **ASSESS** | Interesting, needs deeper evaluation |
| 2.0 – 3.9 | **HOLD** | Not recommended now, revisit later |
| 0.0 – 1.9 | **REJECT** | Fundamentally misaligned |

### Step 7: Deep Evaluation (Level 2 — ADOPT candidates or `--level=deep`)

Only if classification is ADOPT, or user specified `--level=deep`:

```bash
# Full clone (replace shallow)
rm -rf reference/{repo-name}
git clone {url} reference/{repo-name}
cd reference/{repo-name}
```

Run:
```
├── Full test suite execution
├── Security audit:
│   ├── npm audit / pip audit / govulncheck (language-dependent)
│   └── Check for hardcoded secrets or credentials
├── Build verification:
│   └── Does it build cleanly from fresh clone?
├── Integration prototype:
│   └── How would we integrate this? Estimate effort.
└── Performance notes (if applicable)
```

### Step 8: Cleanup

```bash
rm -rf reference/{repo-name}
```

Unless `--no-cleanup` was specified. Always verify cleanup succeeded:
```bash
[ ! -d "reference/{repo-name}" ] && echo "Cleanup OK" || echo "WARNING: cleanup failed"
```

### Step 9: Persist

Save evaluation to Engram:

```
mem_save(
  title: "Evaluated {repo-name}: {CLASSIFICATION}",
  topic_key: "tech-radar/{repo-name}",
  type: "decision",
  project: "{project}",
  content: "{full evaluation report}"
)
```

Record the returned observation ID for use in Step 10a.

Also create the markdown artifact directory and write the per-repo report:

```bash
mkdir -p .cognitive-os/reports/repo-scout
```

Write `.cognitive-os/reports/repo-scout/{owner}_{repo}.md` using the template in Step 10a.

### Step 10a: Per-Repo Markdown Artifact + Return Report

Write the following to `.cognitive-os/reports/repo-scout/{owner}_{repo}.md`
(underscore separator keeps the directory flat):

```markdown
---
evaluated_at: {YYYY-MM-DD HH:MM UTC}
engram_id: {observation-id returned by mem_save, or "n/a"}
deepwiki_url: https://deepwiki.com/{owner}/{repo}
---

## Repository Evaluation: {owner}/{repo}

### Classification: {ADOPT|TRIAL|ASSESS|HOLD|REJECT}
**Score**: {N}/10
**Evaluation Level**: {0: DeepWiki only | 1: Shallow clone | 2: Deep evaluation}

### Summary
{2-3 sentence overview of what this repo does and why it got this classification}

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | {N}/10 | {brief} |
| License | 25% | {N}/10 | {license name} |
| Activity | 20% | {N}/10 | {last commit date, frequency} |
| Maturity | 15% | {N}/10 | {version, stability indicators} |
| Integration | 10% | {N}/10 | {API quality, docs, types} |
| **Weighted Total** | | **{N}/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | {count} issues | {descriptor} |
| Release cadence | median {N}d between last 5 tags | {descriptor} |
| CI health | {pass}/{total} last runs | {descriptor} |

### Key Findings
- **Strengths**: {what it does well}
- **Weaknesses**: {concerns or limitations}
- **Architecture**: {patterns, design approach}

### Integration Plan (TRIAL+ only)
- **What to use**: {specific modules/APIs}
- **How to integrate**: {approach — library, CLI, MCP, fork, reference}
- **Effort estimate**: {small/medium/large}
- **Dependencies it brings**: {list}

### Risks
{Known issues, caveats, vendor lock-in, maintenance burden}

### Alternatives
{If known, mention alternative repos and brief comparison}

### Raw Metrics Appendix
<details>
<summary>gh api JSON (truncated to ~500 lines)</summary>

{raw gh api output, truncated}

</details>
```

Return the same content as the step output in the session.

### Step 10b: Consolidated Batch Report

After all repos are processed in batch mode, write:

```
.cognitive-os/reports/repo-scout/batch-{timestamp}.md
```

where `{timestamp}` = `$(date +%Y%m%d-%H%M%S)`.

Contents:

```markdown
# Repo Scout Batch Report — {YYYY-MM-DD HH:MM UTC}

## Summary Table
| Repo | Classification | Score | Rationale | Notes |
|------|---------------|-------|-----------|-------|
| {owner/repo} | {ring} | {N}/10 | {1-line} | {cached / errored / priority} |
...

## Details
See individual reports in `.cognitive-os/reports/repo-scout/`.

## Skipped (cached)
{list of repos skipped due to 30-day cache, with cached date}

## Errored
{list of repos that failed with error message}
```

Return the summary table as the final output in the session.

## License Auto-Enforcement

After scoring, the evaluation MUST run license enforcement via `lib/license_guard.py`:

1. Call `check_and_enforce(repo_name, detected_license)` with the detected SPDX license ID
2. If the result is `blocked`: auto-add to `.cognitive-os/content-policy.yaml` and classify as **REJECT**
3. If the result is `caution`: include a warning in the evaluation report under Risks
4. If the result is `safe`: no additional action
5. If the result is `unknown`: flag for manual review in the report

## Rules

- ALWAYS clean up clones unless `--no-cleanup` is specified
- NEVER commit contents of `reference/` (already in .gitignore)
- Auto-reject gates are NON-NEGOTIABLE — AGPL/SSPL/BUSL always rejected
- DeepWiki is the first pass — only clone repos that pass Level 0
- Scoring is a starting point — the user makes the final classification call
- If the repo is already in Engram (`tech-radar/{repo-name}`), load the previous evaluation and note changes
- Adoption signals are SOFT: they inform the narrative but do not alter the numeric score
- In batch mode: process serially, never in parallel; one error must not halt the entire batch
- The `.cognitive-os/reports/repo-scout/` directory must be created with `mkdir -p` before writing
- Return a structured envelope with: `status`, `executive_summary`, `artifacts`, `next_recommended`, and `risks`
