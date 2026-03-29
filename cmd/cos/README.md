# cos -- Cognitive OS Package Manager

A package manager for AI agent components: skills, rules, hooks, agents, and templates. Built in Go with Cobra CLI.

## Overview

`cos` manages the lifecycle of reusable AI agent components. It handles installation from local paths or GitHub, dependency resolution using Minimum Version Selection (MVS), security auditing, quality scoring, versioning, and publishing.

Packages are installed into namespaced subdirectories (`cos/@org/pkg/`) to coexist safely with user-authored files.

## Installation

```bash
# Build from source
cd cmd/cos && go build -o cos .

# Install to GOPATH/bin
go install luum-agent-os/cmd/cos@latest

# With version embedded at build time
go build -ldflags "-X luum-agent-os/cmd/cos/internal/cli.Version=$(cat ../../VERSION)" -o cos .
```

## Quick Start

```bash
# Initialize a new package manifest
cos init

# Validate an existing cos-package.yaml
cos validate

# Install a package from GitHub
cos install github.com/luum/safety-mesh@v1.2.0

# List installed packages
cos list

# Search for packages
cos search "quality gates"

# Show package details
cos info @luum/safety-mesh

# Run security audit before installing
cos audit github.com/luum/untrusted-pkg
```

## Command Reference

### Package Management

| Command | Description |
|---------|-------------|
| `cos init` | Create a new `cos-package.yaml` interactively |
| `cos validate` | Validate `cos-package.yaml` in the current directory |
| `cos install <package>` | Install a cos package from local path, GitHub, or URL |
| `cos remove <package>` | Remove an installed cos package |
| `cos update [package]` | Update installed packages to latest versions |
| `cos list` | List installed cos packages |
| `cos search <query>` | Search for cos packages on GitHub |
| `cos info <package>` | Show detailed information about a cos package |
| `cos audit <package>` | Run security audit on a package without installing |
| `cos publish` | Validate and prepare package for publishing |

### Registry Management

| Command | Description |
|---------|-------------|
| `cos registry list` | Show configured package registries |
| `cos registry add <name>` | Add a new registry (requires `--type` flag) |
| `cos registry enable <name>` | Enable a disabled registry |
| `cos registry disable <name>` | Disable a registry |

```bash
# List all configured registries
cos registry list

# Add a GitHub org registry
cos registry add my-org --type github-org --org MyOrg

# Add a GitHub topic registry
cos registry add custom-topic --type github-topic --topic my-cos-packages

# Add a local directory registry
cos registry add local-pkgs --type directory --path ~/.cos-packages/

# Disable a registry
cos registry disable my-org

# Re-enable it
cos registry enable my-org
```

### Project Setup

| Command | Description |
|---------|-------------|
| `cos new <project-name>` | Create a new project with COS pre-configured (supports go, typescript, python, minimal templates) |
| `cos setup` | Interactive onboarding wizard for installing and configuring Cognitive OS |

### System Information

| Command | Description |
|---------|-------------|
| `cos version` | Show Cognitive OS and package versions |
| `cos status` | Show release status of all packages in `packages/` |
| `cos map [component]` | Show the system knowledge graph |
| `cos perf` | Show Cognitive OS performance dashboard |

### Release Management

| Command | Description |
|---------|-------------|
| `cos release [version]` | Create a new OS release (bump VERSION, update CHANGELOG, create git tag) |
| `cos release --patch` | Bump patch version |
| `cos release --minor` | Bump minor version |
| `cos release --major` | Bump major version |
| `cos release --check` | Validate release readiness without releasing |
| `cos release --dry-run` | Show what would happen without making changes |
| `cos release-all` | Release all packages with unreleased changes |
| `cos release-all --patch` | Bump patch version on changed packages |
| `cos release-all --include "pkg1,pkg2"` | Only release specific packages |
| `cos release-all --exclude "pkg1"` | Skip specific packages |
| `cos release-all --dry-run` | Preview changes without executing |

### Global Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--verbose` | `-v` | Enable verbose output |
| `--no-color` | | Disable colored output |
| `--version` | `-V` | Print cos version and exit |
| `--help` | `-h` | Print help and exit |

## Package Format

Every cos package has a `cos-package.yaml` manifest:

```yaml
name: "@myorg/my-skill"
version: "1.0.0"
description: "A reusable skill for code review"
type: skill                    # skill | rule | hook | agent | template | bundle
license: MIT
cos_version: ">=0.1.0"        # Minimum Cognitive OS version required

exports:
  skills:
    - src: skill.md
      dest: SKILL.md
  rules:
    - src: rules/quality.md
      dest: quality-gate.md

dependencies:
  "@luum/core-rules":
    version: ">=1.0.0,<2.0.0"
```

Package types: `skill`, `rule`, `hook`, `agent`, `template`, `bundle`.

## Versioning

### OS Versioning

The Cognitive OS itself is versioned in the `VERSION` file at the repo root. The `cos release` command bumps this version, updates the CHANGELOG, and creates a git tag.

### Package Versioning

Each package in `packages/` has its own independent semver version in its `cos-package.yaml`. Packages use scoped git tags (e.g., `@luum/quality-gates@1.2.0`) to track releases independently from the OS version.

The `cos_version` field in `cos-package.yaml` declares the minimum Cognitive OS version required by the package.

### Scoped Tags

Package releases use scoped git tags to avoid collisions:

```
@luum/quality-gates@1.0.0
@luum/trust-system@2.1.0
@luum/sdd-compound@1.0.0-beta.1
```

The `cos status` command shows the latest scoped tag and commits since that tag for each package.

## Release Workflow

### Single Package Release

```bash
# Check if a package is ready for release
cos release --check

# Create a patch release
cos release --patch

# Create a specific version
cos release 0.2.0
```

### Batch Package Release

```bash
# See which packages have unreleased changes
cos status --changed-only

# Release all changed packages with a patch bump
cos release-all --patch

# Preview what would happen
cos release-all --patch --dry-run

# Release only specific packages
cos release-all --patch --include "quality-gates,trust-system"
```

## CI/CD

### Building in CI

```bash
# Build with version from VERSION file
go build -ldflags "-X luum-agent-os/cmd/cos/internal/cli.Version=$(cat VERSION)" \
  -o cos ./cmd/cos/

# Run tests
cd cmd/cos && go test ./...
```

### Automated Releases

The `cos release` and `cos release-all` commands create git tags that can trigger CI pipelines. Set `GITHUB_TOKEN` for operations that interact with GitHub (search, publish).

```bash
export GITHUB_TOKEN="ghp_..."
cos search "quality"
cos publish --push
```

## Security

### Audit Before Install

The `cos audit` command runs a 5-gate security check on packages before installation:

1. **Manifest validation** -- `cos-package.yaml` is well-formed
2. **License check** -- License is compatible (blocks AGPL, SSPL, BSL)
3. **Injection scan** -- Skill content checked for prompt injection patterns
4. **Dependency audit** -- Transitive dependencies are scanned
5. **Integrity verification** -- SHA-256 hashes verified against `cos.lock`

```bash
# Audit a package before installing
cos audit github.com/untrusted/package

# Install with audit (default behavior)
cos install github.com/org/package
```

### Supply Chain Defense

- All installed packages are pinned to commit hashes in `cos.lock`
- Per-file integrity hashes prevent post-install tampering
- `cos update` verifies new commits are descendants of pinned commits (no force-push)

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `cos-package.yaml not found` | Run `cos init` to create one, or `cd` to the package directory |
| `resolution error` | Check `cos-package.yaml` for version constraint conflicts |
| `network error` | Verify internet connectivity and `GITHUB_TOKEN` for private repos |
| `integrity error` | Run `cos install --force` to re-resolve and regenerate `cos.lock` |
| `invalid version format` | Use semver format: `MAJOR.MINOR.PATCH` (e.g., `1.2.3`) |

### Verbose Output

Use `--verbose` (or `-v`) for detailed output on any command:

```bash
cos install @luum/safety-mesh --verbose
```

### Resetting State

```bash
# Remove lock file and re-resolve
cos install --force

# Remove all installed packages
cos remove @luum/safety-mesh
```
