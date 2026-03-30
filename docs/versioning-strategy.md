# Versioning & Release Strategy

## Overview

Cognitive OS uses a dual-versioning model:
- **OS Core** has a single version (e.g., `v0.2.0`) -- the kernel
- **Packages** have independent versions (e.g., `@luum/quality-gates@1.2.0`) -- the add-ons

## OS Core Versioning

### Semver Rules
- **MAJOR** (1.0.0 -> 2.0.0): Breaking changes to core APIs (hooks interface, manifest format, CLI commands)
- **MINOR** (0.1.0 -> 0.2.0): New features, new core hooks/rules, backward compatible
- **PATCH** (0.1.0 -> 0.1.1): Bug fixes, documentation, performance improvements

### Version File
The OS version lives in `VERSION` at the repo root:
```
0.2.0
```

### Release Process
```bash
# 1. Update VERSION file
echo "0.2.0" > VERSION

# 2. Update CHANGELOG.md -- move [Unreleased] to [0.2.0] with date
# 3. Commit
git add VERSION CHANGELOG.md
git commit -m "release: v0.2.0"

# 4. Tag
git tag v0.2.0

# 5. Push
git push && git push --tags

# 6. GitHub Release (automated via scripts/create-release.sh)
```

### Recommended: `cos release`

The `cos release` command automates the entire release process:

```bash
cos release 0.3.0          # Create release v0.3.0
cos release --minor         # Bump minor version
cos release --patch         # Bump patch version
cos release --dry-run       # Preview without executing
cos release --check         # Validate readiness only
```

What `cos release` does automatically:
1. Updates `VERSION` file
2. Moves `[Unreleased]` to `[x.y.z]` in `CHANGELOG.md`
3. Updates version in `docs/INDEX.md`
4. Creates git commit + tag
5. **Auto-updates all registered projects** (via `scripts/auto-update-projects.sh`)

### Auto-Update of Registered Projects

When you run `cos release`, all projects registered in `~/.cognitive-os/installations.json` are automatically updated to the new version. This means:

- `/n1u/` or any other project using COS gets the latest rules, hooks, and skills
- Profile filtering is applied (standard = 14 core rules)
- No manual intervention needed

**How projects get registered:**
```bash
# During initial install:
cos setup                    # Interactive — registers automatically
cos setup --preset team      # Non-interactive — registers automatically

# Or manually:
bash scripts/cos-registry.sh register /path/to/project standard 0.3.0 my-project /path/to/cos
```

**When auto-update triggers:**

| Action | Updates projects? | Mechanism |
|--------|------------------|-----------|
| `cos release` | ✅ Yes | Runs auto-update-projects.sh after release |
| `git pull` on COS repo | ✅ Yes | post-merge git hook |
| `git push` on COS repo | ❌ No | No post-push hook in Git |
| Manual | ✅ Yes | `bash scripts/auto-update-projects.sh` |

### Legacy: `scripts/create-release.sh`
Still available for interactive release prompts, but `cos release` is preferred.

## Package Versioning

### Independent Semver
Each package has its own version in `cos-package.yaml`:
```yaml
name: "@luum/quality-gates"
version: "1.2.0"
cos_version: ">=0.2.0"  # Minimum OS version required
```

### Package Release Process
```bash
# 1. Update version in cos-package.yaml
# 2. Update package CHANGELOG if exists
# 3. Commit
git add packages/quality-gates/cos-package.yaml
git commit -m "release(@luum/quality-gates): v1.2.0"

# 4. Tag (scoped)
git tag @luum/quality-gates@1.2.0

# 5. Or use cos CLI
cos publish  # validates + suggests tag
```

### Compatibility Constraints
Packages declare minimum OS version:
```yaml
cos_version: ">=0.2.0"       # Works with 0.2.0 and above
cos_version: ">=0.2.0,<1.0.0" # Works with 0.2.x only
```

Package dependencies use semver ranges:
```yaml
dependencies:
  "@luum/trust-system":
    version: "^1.0.0"       # >=1.0.0, <2.0.0
```

## Version Matrix

| Component | Current | Next | Format |
|---|---|---|---|
| OS Core | 0.1.0 | 0.2.0 | `VERSION` file + `git tag v0.2.0` |
| @luum/quality-gates | 1.0.0 | - | `cos-package.yaml` + `git tag @luum/quality-gates@1.0.0` |
| @luum/ecosystem-tools | 1.0.0 | - | `cos-package.yaml` + scoped git tag |
| ... (23 packages) | 1.0.0 | - | Each versioned independently |

## Changelog Strategy

### OS Core: `CHANGELOG.md` (root)
Follows [Keep a Changelog](https://keepachangelog.com/) format:
```markdown
## [Unreleased]
### Added
- ...

## [0.2.0] - 2026-03-28
### Added
- cos package manager (9 commands, 210+ tests)
- 23 packages restructured
...
```

### Packages: `packages/{name}/CHANGELOG.md` (optional)
Only for packages with significant independent history. Most packages start at 1.0.0 and increment with the OS.

## Release Types

| Type | When | Version Bump | Tag |
|---|---|---|---|
| **OS Release** | Major feature complete | MINOR or MAJOR | `v0.2.0` |
| **OS Patch** | Bug fix or security | PATCH | `v0.2.1` |
| **Package Release** | Package-specific change | Per package semver | `@luum/pkg@1.1.0` |
| **Pre-release** | Testing before release | Pre-release suffix | `v0.2.0-beta.1` |

## Git Tag Convention

```
v{major}.{minor}.{patch}           # OS core
v{major}.{minor}.{patch}-{pre}     # OS pre-release
@luum/{name}@{major}.{minor}.{patch}  # Package
```

Examples:
```
v0.1.0                             # First release
v0.2.0                             # Second release (current)
v0.2.0-beta.1                      # Pre-release
@luum/quality-gates@1.0.0          # Package release
@luum/ecosystem-tools@1.1.0        # Package minor update
```

## Automated Release Notes

`scripts/create-release.sh` generates release notes from:
1. Git log since last tag
2. CHANGELOG.md entries
3. Package version bumps
4. Test suite results
5. Breaking change warnings

## Who Bumps What

| Scenario | Who | What to bump |
|---|---|---|
| New core hook/rule added | OS maintainer | OS MINOR |
| Core hook API changed | OS maintainer | OS MAJOR |
| Bug fix in core lib | OS maintainer | OS PATCH |
| New skill added to package | Package maintainer | Package MINOR |
| Skill fix in package | Package maintainer | Package PATCH |
| Package restructure | OS maintainer | OS MINOR + affected packages |

## Lockfile Pinning

When a user installs packages, `cos-lock.yaml` pins:
- Package version (exact)
- Git commit hash (immutable)
- Per-file integrity hashes (tamper detection)
- OS version at install time

This ensures reproducible installs across machines and time.

## Future: Registry Versioning

When a public registry exists:
- Published packages get immutable version entries
- Yanked versions are marked but not deleted
- Version metadata includes: audit results, test status, OS compatibility
