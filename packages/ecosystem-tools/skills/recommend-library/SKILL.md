---
name: recommend-library
description: Search package registries and rank by relevance, adoption, maintenance,
  and license compliance
audience: project
summary_line: Search package registries and rank by relevance, adoption, maintenance,
  and…
version: 1.0.0
platforms:
- claude-code
prerequisites: []
routing_intents:
- recommend a library for this use case
- compare package options before adding a dependency
- find maintained libraries with safe licenses
- rank open source packages for this feature
- choose the best dependency for this problem
triggers:
- recommend-library
- /recommend-library
- 'Skill: recommend-library'
- Search package registries and rank by relevance, adoption, maintenance, and…
---
<!-- SCOPE: both -->
# Skill: recommend-library

> Auto Library Recommender — searches package registries and ranks results by relevance, adoption, maintenance, and license compliance.

## Invocation

```
/recommend-library <description>
```

Examples:
- `/recommend-library I need animations for React Native`
- `/recommend-library date parsing and formatting for TypeScript`
- `/recommend-library ORM for Go with PostgreSQL support`
- `/recommend-library PDF generation in Python`

## Supported Registries

| Ecosystem | Registry API | Search Endpoint |
|-----------|-------------|-----------------|
| npm (JS/TS) | `https://registry.npmjs.org/-/v1/search?text={query}&size=10` | Full-text search with scoring |
| PyPI (Python) | `https://pypi.org/pypi/{name}/json` | Per-package lookup (search via `https://pypi.org/search/?q={query}`) |
| Go modules | `https://pkg.go.dev/search?q={query}` | Web search (no JSON API) |

## Execution Steps

### Step 1: Detect Ecosystem

Determine the target ecosystem from the description:
- React Native, TypeScript, NestJS, Express -> **npm**
- Python, Django, Flask, FastAPI -> **PyPI**
- Go, Gin, GORM -> **Go modules**
- If ambiguous, ask the user or default to **npm** (primary stack)

### Step 2: Search Registry

For **npm**:
```bash
curl -s "https://registry.npmjs.org/-/v1/search?text=${QUERY}&size=10" | jq '.objects'
```

Each result contains:
- `package.name`, `package.version`, `package.description`
- `package.date` (last publish)
- `package.links.npm`, `package.links.repository`
- `score.detail.quality`, `score.detail.popularity`, `score.detail.maintenance`

For **PyPI** (individual package lookup after identifying candidates):
```bash
curl -s "https://pypi.org/pypi/${PACKAGE_NAME}/json" | jq '{name: .info.name, version: .info.version, summary: .info.summary, license: .info.license, downloads: .info.downloads}'
```

For **Go modules** (use WebSearch or WebFetch):
- Search `pkg.go.dev` for the query
- Extract module path, version, license, import count

### Step 3: Filter Candidates

Apply these filters (from `.cognitive-os/rules/library-selection.md`):

1. **License check** — Reject AGPL, SSPL, or unknown licenses. Flag GPL for review. Prefer MIT, Apache-2.0, BSD, ISC.
2. **Activity** — Prefer packages updated within the last 6 months. Warn if last publish > 12 months ago.
3. **Adoption** — Prefer packages with >1,000 weekly downloads (npm) or >100 stars (GitHub).
4. **Deprecation** — Reject deprecated packages entirely.

### Step 4: Rank with LLM Analysis

For each candidate that passes filters, evaluate:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Relevance | 35% | How well does it match the user's description? |
| Community adoption | 25% | Downloads, stars, dependents |
| Bundle size | 15% | Smaller is better (especially for React Native) |
| Maintenance | 15% | Recent commits, open issues ratio, response time |
| API quality | 10% | TypeScript types, documentation, examples |

### Step 5: Return Top 3

Format each recommendation:

```
## Recommendation #N: {package-name}

- **Version**: {version}
- **Weekly downloads**: {count}
- **License**: {license} {flag if concerning}
- **Last published**: {date}
- **Install**: `npm install {name}` / `pip install {name}` / `go get {module}`
- **Why recommended**: {1-2 sentence rationale based on ranking criteria}
- **Considerations**: {any caveats — bundle size, peer deps, breaking changes}
```

After listing all 3, add:

```
### Selection Guidance
{Brief comparison of the 3 options with a recommendation for the user's specific use case}
```

## Rules Reference

See `.cognitive-os/rules/library-selection.md` for the complete library adoption policy.

## Error Handling

- If registry API is unreachable, fall back to WebSearch for package information
- If fewer than 3 candidates pass filters, return what's available with a note
- If no candidates pass, explain why and suggest broadening the search or alternative approaches

## Integration with Project Stack

When recommending libraries, consider the existing project stack:
- **React Native 0.74 / Expo** — check Expo compatibility
- **NestJS 10** — prefer NestJS-native modules when available
- **Spring Boot 3.0.6 / Java 17** — check Java version compatibility
- **Express.js** — check middleware compatibility
- **Go** — check compatibility with the project's declared HTTP framework

Always check if a similar library is already in the project's dependencies before recommending a new one.
