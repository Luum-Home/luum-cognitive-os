# Library Selection Rules

## License-First Protocol

**ALWAYS check license BEFORE any other evaluation.** This applies to libraries, frameworks, tools, and external repos.

- **MIT/Apache/BSD** → Can adopt code AND patterns
- **AGPL/SSPL** → BLOCKED for code. CAN adopt architectural patterns via clean-room reimplementation. IDEAS are free, code is not.
- **Custom/Unknown** → BLOCKED for code. Verify with legal before adopting patterns.

When a repo is license-blocked, the evaluation must still document valuable PATTERNS that can be independently reimplemented.

## Mandatory Checks

Before adopting any new library, the following checks are required:

### 1. License Compatibility

| License | Status | Action |
|---------|--------|--------|
| MIT, Apache-2.0, BSD-2, BSD-3, ISC | Approved | Use freely |
| MPL-2.0 | Conditional | OK if not modifying library source |
| LGPL-2.1, LGPL-3.0 | Conditional | OK for dynamic linking; review if bundling |
| GPL-2.0, GPL-3.0 | Restricted | Requires explicit approval — viral copyleft |
| AGPL-3.0 | Blocked | Never use — network copyleft applies to SaaS |
| SSPL | Blocked | Never use — MongoDB-style server-side copyleft |
| Unlicensed / Unknown | Blocked | Never use — no legal clarity |

Reference: `.cognitive-os/rules/license-policy.md` for the complete policy.

### 2. Minimum Adoption Threshold

- **npm**: Prefer packages with >1,000 weekly downloads
- **PyPI**: Prefer packages with >500 monthly downloads
- **Go**: Prefer packages with >50 GitHub stars or listed on pkg.go.dev with importers
- Below threshold: acceptable only if no alternatives exist and the package is well-maintained

### 3. Maintenance Health

- **Last publish**: Prefer packages updated within the last 6 months
- **Warning**: Flag packages with last publish >12 months ago
- **Reject**: Packages explicitly marked as deprecated
- **Check**: Open issues count vs. closed ratio (healthy: >50% closed)
- **Check**: Whether the maintainer responds to issues/PRs

### 4. Bundle Size (Frontend/Mobile)

For React Native and frontend packages:
- Prefer smaller bundles (check via `bundlephobia.com` for npm)
- Avoid packages that pull large transitive dependencies
- Tree-shaking support is a strong positive signal

### 5. TypeScript Support

For TypeScript projects (BFF, onboarding, monolith, mobile):
- Prefer packages with built-in TypeScript types (`types` field in package.json)
- Acceptable: `@types/{package}` available on DefinitelyTyped
- Avoid: packages with no TypeScript support in a TypeScript codebase

### 6. Existing Dependencies

Before recommending a new library:
- Check if the project already has a dependency that covers the use case
- Check if a framework-native solution exists (NestJS modules, Spring Boot starters, Expo SDK)
- Prefer extending existing dependencies over adding new ones

## Decision Record

When a library is selected, save the decision to engram:
- **What**: Library name, version, and purpose
- **Why**: What alternatives were considered and why this was chosen
- **Where**: Which service(s) will use it
- **Learned**: Any gotchas, peer dependency issues, or configuration needed
