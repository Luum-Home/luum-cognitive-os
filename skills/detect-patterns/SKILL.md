---
name: detect-patterns
description: 'Use when you need this Cognitive OS skill: Detect systemic problems
  in the Cognitive OS codebase: dead metadata, broken chains, phantom entries, and
  structural tests.; do not use when a narrower skill directly matches the task.'
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-04-15
license: MIT
metadata:
  author: luum
audience: os-dev
effort: haiku
summary_line: 'Detect systemic problems in the Cognitive OS codebase: dead metadata,
  broken…'
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bdetect[- ]?patterns?\b
  confidence: 0.95
- pattern: \bpattern\s+detection\b
  confidence: 0.8
triggers:
- detect-patterns
- /detect-patterns
- Run all detectors or a specific one
- 'Detect systemic problems in the Cognitive OS codebase: dead metadata, broken…'
---
<!-- SCOPE: both -->
## Purpose

Systematically finds code-level rot that accumulates over time. Detects four categories of systemic problems:

1. **Dead Metadata** — frontmatter fields in SKILL.md files that no code ever reads
2. **Broken Chains** — imports or references to files that don't exist (symlink-aware)
3. **Phantom Entries** — catalog/config entries pointing to non-existent components
4. **Structural Tests** — tests that only check file existence, never exercise behavior

## Invocation

```
/detect-patterns [--type dead-metadata|broken-chains|phantoms|structural-tests|all]
```

Default: `--type all`

## What to Do

### Step 1: Run the pattern detector

```python
from lib.pattern_detector import PatternDetector

detector = PatternDetector()

# Run all detectors or a specific one
if type_arg == "all":
    results = detector.run_all(project_dir)
else:
    results = detector.run_type(project_dir, type_arg)
```

### Step 2: Format and present results

```python
report = detector.format_report(results)
print(report)
```

### Step 3: Summarize actionable items

Group findings by severity and present:

- **CRITICAL** — broken chains that will cause runtime errors. Fix immediately.
- **WARNING** — dead metadata and phantom entries. Fix during next cleanup.
- **INFO** — structural tests. Improve when touching those test files.

### Step 4: Suggest next steps

- For broken chains: identify the source and target, suggest creating or fixing the reference
- For dead metadata: suggest removing unused frontmatter keys
- For phantoms: suggest creating the missing component or removing the catalog entry
- For structural tests: suggest adding behavioral assertions

## Rules

- ALWAYS resolve symlinks with `os.path.realpath()` before checking existence
- ALWAYS handle `try/except ImportError` gracefully when checking Python imports
- When checking config flags, grep for the YAML key in .py and .sh files
- Report evidence: show what was checked and what was found/not found
- Do NOT auto-fix — report only, let the human decide
