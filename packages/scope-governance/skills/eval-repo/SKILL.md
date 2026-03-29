---
name: eval-repo
description: >
  Evaluate external git repositories for potential inclusion in the tech radar.
  Three-level assessment: DeepWiki summary, shallow clone analysis, deep evaluation.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-26
license: MIT
metadata:
  author: luum
audience: project
---

## Purpose

Structured evaluation of external repositories for tech radar classification. Provides a repeatable, scored assessment instead of ad-hoc review.

## Invocation

`/eval-repo <github-url> [--level=shallow|deep] [--no-cleanup]`

## What to Do

### Step 1: Parse Repository URL

Extract `owner` and `repo` from the GitHub URL.

Supported formats:
- `https://github.com/owner/repo`
- `https://github.com/owner/repo.git`
- `github.com/owner/repo`
- `owner/repo` (shorthand)

Strip `.git` suffix, protocol prefix, and `github.com/` prefix. Reject non-GitHub URLs.

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

### Step 5: Scoring

Apply weighted scoring (each criterion 0-10):

| Criterion | Weight | Scoring Guide |
|-----------|--------|---------------|
| **Relevance** | 30% | How well does it fit our stack, solve our problems, align with our architecture? |
| **License** | 25% | MIT/Apache=10, BSD=8, MPL=7, LGPL=6, GPL=5, Unknown=2, AGPL/SSPL=0 |
| **Activity** | 20% | Commits <1mo=10, <3mo=8, <6mo=6, <12mo=3, >12mo=0 |
| **Maturity** | 15% | v1.0+=8, semver=7, pre-release=5, no versioning=3; production users boost score |
| **Integration** | 10% | Clean API=10, good types=8, docs+examples=7, minimal config=6, complex setup=3 |

**Total** = weighted sum (0.0 - 10.0)

### Step 6: Classification

| Score | Ring | Meaning |
|-------|------|---------|
| 8.0 - 10.0 | **ADOPT** | Proven, recommend for production use |
| 6.0 - 7.9 | **TRIAL** | Promising, test in non-critical path first |
| 4.0 - 5.9 | **ASSESS** | Interesting, needs deeper evaluation |
| 2.0 - 3.9 | **HOLD** | Not recommended now, revisit later |
| 0.0 - 1.9 | **REJECT** | Fundamentally misaligned |

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

### Step 10: Return Report

```markdown
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
```

## License Auto-Enforcement

After scoring, the evaluation MUST run license enforcement via `lib/license_guard.py`:

1. Call `check_and_enforce(repo_name, detected_license)` with the detected SPDX license ID
2. If the result is `blocked`: auto-add to `.cognitive-os/content-policy.yaml` and classify as **REJECT**
3. If the result is `caution`: include a warning in the evaluation report under Risks
4. If the result is `safe`: no additional action
5. If the result is `unknown`: flag for manual review in the report

This enforces the license policy (`rules/license-policy.md`) automatically during repository evaluation, preventing blocked-license tools from entering the tech radar without explicit override.

## Rules

- ALWAYS clean up clones unless `--no-cleanup` is specified
- NEVER commit contents of `reference/` (already in .gitignore)
- Auto-reject gates are NON-NEGOTIABLE — AGPL/SSPL/BUSL always rejected
- DeepWiki is the first pass — only clone repos that pass Level 0
- Scoring is a starting point — the user makes the final classification call
- If the repo is already in Engram (`tech-radar/{repo-name}`), load the previous evaluation and note changes
- Return a structured envelope with: `status`, `executive_summary`, `artifacts`, `next_recommended`, and `risks`
