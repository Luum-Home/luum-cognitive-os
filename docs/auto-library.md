# Auto Library Recommender

## Overview

The Auto Library Recommender is a skill that searches package registries (npm, PyPI, Go modules) and ranks results using LLM analysis. It helps developers choose the right library for their needs while enforcing license compliance and quality standards.

## Usage

```
/recommend-library <natural language description>
```

### Examples

```
/recommend-library I need animations for React Native
/recommend-library date parsing and formatting for TypeScript
/recommend-library ORM for Go with PostgreSQL support
/recommend-library PDF generation in Python
/recommend-library state management for React Native with persistence
```

## Skill Location

```
.cognitive-os/skills/recommend-library/SKILL.md
```

## How It Works

### 1. Ecosystem Detection

The skill infers the target ecosystem from the description:
- Mentions of React Native, TypeScript, NestJS, Express -> npm registry
- Mentions of Python, Django, Flask -> PyPI
- Mentions of Go, Gin, GORM -> Go modules (pkg.go.dev)

### 2. Registry Search

Queries the appropriate registry API:
- **npm**: `https://registry.npmjs.org/-/v1/search?text=...`
- **PyPI**: `https://pypi.org/pypi/{name}/json`
- **Go**: `https://pkg.go.dev/search?q=...`

### 3. Filtering

Applies rules from `.cognitive-os/rules/library-selection.md`:
- License compatibility check (blocks AGPL, SSPL, unknown)
- Minimum adoption threshold (>1000 weekly downloads for npm)
- Maintenance health (prefer updated within 6 months)
- Deprecation check (reject deprecated packages)

### 4. LLM Ranking

Ranks surviving candidates by:
- Relevance to description (35%)
- Community adoption (25%)
- Bundle size (15%)
- Maintenance quality (15%)
- API quality and TypeScript support (10%)

### 5. Output

Returns top 3 recommendations with:
- Package name, version, and install command
- Weekly downloads and license
- Rationale for recommendation
- Any caveats or considerations
- Comparative guidance for choosing between the options

## Rules Reference

- `.cognitive-os/rules/library-selection.md` — Adoption policy, license checks, quality thresholds
- `.cognitive-os/rules/license-policy.md` — Detailed license compatibility matrix

## Integration with Project Stack

The skill is aware of the project technology stack and considers:
- Expo compatibility for React Native packages
- NestJS module ecosystem for backend packages
- Spring Boot starter compatibility for Java packages
- Gin/ginext compatibility for Go packages
- Existing project dependencies to avoid duplicates
