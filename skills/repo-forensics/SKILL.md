<!-- SCOPE: both -->
---
name: repo-forensics
description: >
  Deep forensic analysis of git repositories. Clones, analyzes ALL code,
  dependencies, architecture patterns, tools, features, API endpoints,
  and produces exhaustive structured reports. Optionally compares with
  Cognitive OS capabilities.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-29
license: MIT
metadata:
  author: luum
audience: both
effort: opus
summary_line: Deep forensic analysis of git repositories.

---

## Purpose

Full forensic analysis of external (or internal) repositories. Goes far beyond
reading a README: clones the repo, scans every file, parses every dependency
manifest, detects architecture patterns, identifies integrated tools, extracts
API endpoints, and produces a structured report with optional COS comparison.

## Invocation

```
/repo-forensics <repo-url> [--compare] [--deps-only] [--features-only] [--depth quick|full]
```

| Flag | Effect |
|------|--------|
| (none) | Full forensic analysis |
| `--compare` | Include comparison with Cognitive OS |
| `--deps-only` | Only dependency analysis |
| `--features-only` | Only feature detection |
| `--depth quick` | Skip endpoint/architecture/tool detection |

## What to Do

### Step 1: Parse Arguments

Extract repo URL and flags from the invocation. Supported URL formats:

- `https://github.com/owner/repo`
- `https://github.com/owner/repo.git`
- `github.com/owner/repo`
- `owner/repo` (shorthand, assumes GitHub)
- Any git-cloneable URL

### Step 2: Clone Repository

Use `RepoAnalyzer` from `lib/repo_analyzer.py`:

```python
from lib.repo_analyzer import RepoAnalyzer

analyzer = RepoAnalyzer()
```

The analyzer clones with `--depth 1 --single-branch` for speed. Clone destination
is `/tmp/cos-repo-analysis/{repo-name}`.

### Step 3: Run Analysis Pipeline

For full analysis (default):

```python
analysis = analyzer.analyze(repo_url, depth="full")
```

For quick analysis (`--depth quick`):

```python
analysis = analyzer.analyze(repo_url, depth="quick")
```

For `--deps-only`: call `analyzer.detect_dependencies(repo_path)` directly after cloning.
For `--features-only`: call `analyzer.detect_features(repo_path)` directly after cloning.

### LICENSE-FIRST PROTOCOL (MANDATORY)

**Before ANY other analysis, check the license.** This determines what we can do:

| License | Code Adoption | Pattern Adoption | Action |
|---------|--------------|-----------------|--------|
| MIT / BSD / Apache-2.0 / ISC | ✅ YES | ✅ YES | Full adoption possible |
| LGPL / MPL | ⚠️ CAUTION | ✅ YES | Use as library only, don't modify |
| AGPL-3.0 / SSPL | ❌ BLOCKED | ✅ YES | Patterns only, clean-room reimplementation |
| Custom / NOASSERTION | ❌ BLOCKED | ⚠️ CAREFUL | Document patterns, verify with legal |
| No license | ❌ BLOCKED | ❌ BLOCKED | Cannot use anything |

**If license is AGPL/SSPL**: The report MUST clearly state "CODE ADOPTION BLOCKED" and list patterns that CAN be reimplemented independently (clean-room). IDEAS are free — code is not.

**If license is MIT/Apache**: The report should highlight specific code/components that can be directly adopted or adapted.

The full pipeline:
1. Clone repo (shallow)
2. **Detect license IMMEDIATELY** (step 2 is non-negotiable)
3. Count languages (line-by-line breakdown)
4. Parse ALL dependency files (package.json, go.mod, requirements.txt, Cargo.toml, build.gradle, pom.xml, Gemfile, mix.exs)
5. Detect features (README headings, CHANGELOG entries, directory structure, CLI commands)
6. Detect architecture patterns (monorepo, clean arch, MVC, hexagonal, plugin system, microservices, event-driven, serverless, CQRS)
7. Find integrated tools (Docker, CI/CD, linting, testing, security, monitoring)
8. Extract API endpoints (Express, Go, Flask/FastAPI, NestJS route patterns)
9. Detect Docker services from compose files
10. Detect security tools (Semgrep, Snyk, Trivy, CodeQL, Dependabot, etc.)
11. Check for plugin/extension system
12. Estimate test file coverage ratio

### Step 4: Compare with COS (if --compare)

```python
comparison = analyzer.compare_with_cos(analysis)
```

This produces:
- Features they have that COS does not
- Features COS has that they do not
- Tool overlap
- Architecture pattern comparison

### Step 5: Generate Report

```python
report = analyzer.format_report(analysis, comparison=comparison)
```

The report includes all sections: language breakdown, dependencies (grouped by
package manager), features, architecture patterns, tools, endpoints, CI/CD,
Docker services, security tools, plugin system, config files, and COS comparison.

### Step 6: Save to Engram

Save findings to persistent memory:

```
mem_save(
  title: "Repo Forensics: {repo-name}",
  topic_key: "docs/research/repo-forensics/{repo-name}",
  type: "discovery",
  scope: "project",
  project: "luum-cognitive-os",
  content: "{executive summary + key findings}"
)
```

### Step 7: Cleanup

```python
analyzer.cleanup()
```

Removes the cloned repo from `/tmp/cos-repo-analysis/`.

### Step 8: Return Result

Output the full report to the user and return the structured envelope:

```yaml
status: success
executive_summary: "{repo-name}: {language} project with {N} deps, {patterns}"
artifacts:
  - type: forensic-report
    location: "Engram: docs/research/repo-forensics/{repo-name}"
next_recommended:
  - "Review dependency licenses with /eval-repo if adoption is planned"
  - "Compare architecture patterns with current project"
risks:
  - "{any license concerns}"
  - "{any security tool gaps}"
```

## Rules

- ALWAYS clean up clones after analysis (call `analyzer.cleanup()`)
- NEVER commit cloned repo contents
- For repos larger than 500MB, warn the user before cloning
- If cloning fails, report the error and suggest checking the URL
- The analysis uses ONLY Python stdlib (no external dependencies)
- Dependency parsing is regex-based (no YAML/TOML/XML parsers required)
- Endpoint detection is heuristic — warn that it may miss framework-specific patterns
- Return a structured envelope with: `status`, `executive_summary`, `artifacts`, `next_recommended`, and `risks`
