# Agentic Primitive Classification Protocol

## Purpose
Every new agentic primitive added to Cognitive OS must be classified as CORE or PACKAGE before being committed. This prevents the OS kernel from growing unbounded with optional functionality.

## Rule (Always Active for OS Development)

When a PR or agent task adds a new skill, hook, rule, or lib:
1. Run `/component-classifier` on the new agentic primitive
2. If CORE: place in the appropriate root directory (skills/, hooks/, rules/, lib/)
3. If PACKAGE: create or update a cos package in packages/{name}/
4. Document the classification in docs/06-Daily/root/component-audit.md

## Classification Criteria

| Signal | CORE | PACKAGE |
|---|---|---|
| OS boots without it? | No | Yes |
| External tool dependency? | No | Yes |
| Domain-specific? | No | Yes |
| Used by >50% of agentic primitives? | Yes | No |
| Can be installed/removed? | No | Yes |

## Versioning Rules

### CORE Agentic Primitives
- Versioned with the OS itself (v0.1.0, v0.2.0, etc.)
- Breaking changes require major version bump
- No independent versioning

### PACKAGE Agentic Primitives
- Each package has its own semver version in cos-package.yaml
- Follows semver 2.0: MAJOR.MINOR.PATCH
- MAJOR: breaking changes (incompatible API)
- MINOR: new features (backward compatible)
- PATCH: bug fixes
- Pre-release: 1.0.0-alpha, 1.0.0-beta.1
- Packages declare `cos_version` for minimum OS compatibility

## Package Versioning in cos-package.yaml

```yaml
name: "@luum/quality-gates"
version: "1.0.0"           # Package version (independent)
cos_version: ">=0.1.0"     # Minimum Cognitive OS version required
dependencies:
  "@luum/trust-system":
    version: ">=1.0.0,<2.0.0"  # Semver range constraint
```

## Upgrade Protocol

When upgrading a CORE component:
1. Bump OS version (MINOR for features, PATCH for fixes)
2. Update CHANGELOG.md
3. All packages continue to work (backward compatible)

When upgrading a PACKAGE:
1. Bump package version in cos-package.yaml
2. Update package CHANGELOG if exists
3. Test: `cos install ./packages/{name}` still works
4. Verify: no breaking changes for dependent packages
