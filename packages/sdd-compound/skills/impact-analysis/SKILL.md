<!-- SCOPE: both -->
---
name: impact-analysis
description: "Analyze change impact: imports, tests, configs, services, and SDD artifacts affected"
triggers: ["/impact-analysis"]
audience: project
summary_line: "\"Analyze change impact: imports, tests, configs, services, and SDD artifacts…"

version: "1.0.0"
platforms: ["claude-code"]
prerequisites: []
---

# /impact-analysis

> Analyze the blast radius of a set of changed files before making changes.


## Instructions

Run a comprehensive impact analysis before or after making changes to understand the blast radius.

### Step 1: Identify Changed Files

Determine which files to analyze. Sources (in priority order):

1. **User-specified files**: If the user provides a file list, use those
2. **Git diff**: `git diff --name-only HEAD` for unstaged changes
3. **Git staged**: `git diff --name-only --cached` for staged changes
4. **SDD context**: If running within an SDD phase, use the files from the tasks artifact

### Step 2: Run Impact Analysis

Use the `lib/impact_analysis.py` module:

```python
from lib.impact_analysis import analyze_impact, format_impact_report

report = analyze_impact(changed_files, project_dir)
print(format_impact_report(report))
```

Or run via command line:
```bash
python -c "
import sys
sys.path.insert(0, 'lib')
from impact_analysis import analyze_impact, format_impact_report
report = analyze_impact(sys.argv[1:], '.')
print(format_impact_report(report))
" file1.go file2.ts
```

### Step 3: Interpret Results

| Risk Level | Action |
|-----------|--------|
| LOW | Proceed normally |
| MEDIUM | Review affected tests, run them explicitly |
| HIGH | Consider breaking the change into smaller PRs |
| CRITICAL | HALT — require human review before proceeding |

### Step 4: Output Report

Present the formatted impact report to the user. Include:
- Risk level with justification
- List of affected files (importers, tests, configs)
- Docker services that may need rebuilding
- SDD artifacts that may need updating
- Recommended actions based on risk level

## SDD Integration

When used before `sdd-apply`:
1. Run impact analysis on the files listed in the tasks artifact
2. If risk is HIGH or CRITICAL, include the impact report in the apply prompt
3. The apply agent should address high-risk areas first

When used after `sdd-apply`:
1. Run impact analysis on the actual changed files
2. Include the report in the verify phase context
3. Verify that all affected tests were run

## Acceptance Criteria

1. All changed files are analyzed: `len(report.changed_files) == len(input_files)`
2. Risk level is assigned: `report.risk_level is not None`
3. At least one analysis dimension has results (importers, tests, configs, services, or SDD artifacts)
4. Report is formatted and readable
