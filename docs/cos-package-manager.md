# cos -- Package Manager for AI Agent Components

> Design Document v1.0 -- 2026-03-27

## Table of Contents

1. [Vision](#1-vision)
2. [Architecture](#2-architecture)
3. [Implementation Phases](#3-implementation-phases)
4. [cos-package.yaml Specification](#4-cos-packageyaml-specification)
5. [cos.lock Specification](#5-coslock-specification)
6. [Registry Model](#6-registry-model)
7. [CLI Reference](#7-cli-reference)
8. [Integration with Cognitive OS](#8-integration-with-cognitive-os)
9. [Inspiration and References](#9-inspiration-and-references)
10. [Checklist for Contributors](#10-checklist-for-contributors)
11. [Known Issues and Limitations](#11-known-issues-and-limitations)

---

## 1. Vision

### Problem

AI coding agents (Claude Code, Cursor, Windsurf, Cline) use skills, rules, hooks, and templates to extend their capabilities. Today, sharing these components means copy-pasting files between repos. There is no versioning, no dependency resolution, no quality assurance, and no discovery mechanism.

### Solution

`cos` is a package manager purpose-built for AI agent components. It is to AI coding agents what npm is to JavaScript or cargo is to Rust: a tool for installing, publishing, versioning, and discovering reusable agent components.

### Core Principles

| Principle | What It Means |
|-----------|---------------|
| **IDE-agnostic** | Packages work for Claude Code today. The manifest format is extensible to Cursor, Windsurf, Cline, and future IDEs via the `platform.ide` field. |
| **Go-style naming** | Package identity uses domain-based paths (`github.com/luum/safety-mesh`) like Go modules. No central authority assigns names. |
| **Scoped aliases** | For ergonomics, `@luum/safety-mesh` resolves to `github.com/luum/safety-mesh` via a centralized index. Both forms are valid. |
| **Coexistence** | Installed packages live in namespaced subdirectories (`cos/@org/pkg/`) and never overwrite user-authored files. |
| **Minimum Version Selection** | Dependency resolution uses MVS (Go's algorithm) -- deterministic, fast, and avoids "dependency hell" by always choosing the minimum version that satisfies all constraints. |
| **Quality scoring** | Every package gets a pub.dev-style score (0-100) based on documentation, tests, license, and structure. Scores are visible during install and search. |
| **Lock files** | `cos.lock` pins exact versions and integrity hashes. Builds are reproducible. |

### Target Users

| User | Use Case |
|------|----------|
| Individual developer | Install community skills to extend their agent |
| Team | Share internal skills/rules across repos via private registry |
| Open-source author | Publish skills for the community |
| Enterprise | Enforce approved component sets via lock files and audit |

---

## 2. Architecture

### Directory Structure

```
cmd/cos/
  main.go                          # Entry point
  go.mod                           # Module: luum-agent-os/cmd/cos
  go.sum
  internal/
    cli/                           # Cobra command definitions
      root.go                      # cos --version, --help, global flags
      init.go                      # cos init
      install.go                   # cos install <pkg>
      uninstall.go                 # cos uninstall <pkg>
      list.go                      # cos list [--json]
      search.go                    # cos search <query>
      publish.go                   # cos publish
      score.go                     # cos score [path]
      tree.go                      # cos tree
      why.go                       # cos why <pkg>
      outdated.go                  # cos outdated
      audit.go                     # cos audit
      link.go                      # cos link <path>
      workspace.go                 # cos workspace <subcommand>
      validate.go                  # cos validate
      resolve.go                   # cos resolve [--dry-run]
      pack.go                      # cos pack
    manifest/                      # cos-package.yaml handling
      types.go                     # Package, Dependency, Feature, Export structs
      parse.go                     # YAML parsing with strict validation
      validate.go                  # Semantic validation rules
      defaults.go                  # Default values and normalization
    resolver/                      # Dependency resolution engine
      mvs.go                       # Minimum Version Selection algorithm
      features.go                  # Feature flag unification
      graph.go                     # Dependency graph construction
      conflict.go                  # Conflict detection and reporting
    registry/                      # Package source backends
      github.go                    # Git-based registry (clone + tag)
      index.go                     # Centralized index client
      cache.go                     # Local download cache (~/.cos/cache/)
      source.go                    # Source interface (registry abstraction)
    lockfile/                      # cos.lock management
      types.go                     # Lock file structs
      read.go                      # Parse existing lock
      write.go                     # Generate lock from resolved graph
      verify.go                    # Integrity verification (SHA-256)
      diff.go                      # Lock diff for debugging
    installer/                     # File installation to .claude/
      install.go                   # Copy files to target directories
      uninstall.go                 # Remove installed files
      coexist.go                   # Namespace management (cos/ subdirs)
      hooks.go                     # Post-install hook execution
      catalog.go                   # CATALOG.md and RULES-COMPACT.md updates
    scorer/                        # Package quality scoring
      score.go                     # Scoring engine
      rules.go                     # Individual scoring criteria
      report.go                    # Score report formatting
    ui/                            # TUI components (shared with cos-test)
      progress.go                  # Progress bars for install
      table.go                     # Table rendering for list/search
      styles.go                    # Lipgloss styles
    testutil/                      # Test helpers
      fixtures.go                  # Test fixture generation
      mockregistry.go              # Mock registry for tests
```

### Module Setup

The Go module follows the same pattern as `cmd/cos-test/`:

```go
// go.mod
module luum-agent-os/cmd/cos

go 1.22

require (
    github.com/spf13/cobra v1.8.1
    github.com/charmbracelet/lipgloss v1.0.0
    github.com/charmbracelet/bubbletea v1.2.4
    gopkg.in/yaml.v3 v3.0.1
)
```

### Data Flow

```
User runs: cos install github.com/luum/safety-mesh@v1.2.0
  |
  v
cli/install.go parses args, reads cos-package.yaml (project manifest)
  |
  v
registry/github.go clones the repo at tag v1.2.0 into ~/.cos/cache/
  |
  v
manifest/parse.go reads the package's cos-package.yaml
  |
  v
resolver/mvs.go builds dependency graph, resolves all transitive deps
  |
  v
resolver/features.go unifies feature flags across the graph
  |
  v
lockfile/write.go generates/updates cos.lock with pinned versions + hashes
  |
  v
installer/install.go copies exports to .claude/{rules,skills,hooks}/cos/@luum/safety-mesh/
  |
  v
installer/catalog.go updates CATALOG.md and RULES-COMPACT.md
  |
  v
installer/hooks.go runs postinstall scripts (if any)
  |
  v
Done. Package is available immediately.
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Separate Go module (`cmd/cos/`) | Same pattern as `cmd/cos-test/`. Independent binary, shared repo. |
| Cobra for CLI | Already used by `cos-test`. Consistent developer experience. |
| Lipgloss/Bubbletea for TUI | Already used by `cos-test`. Can share style definitions. |
| `gopkg.in/yaml.v3` for YAML | Standard Go YAML library. Strict mode catches typos. |
| MVS over SAT solver | Go proved MVS is simpler, faster, and more predictable than SAT-based resolution (npm/pip). No NP-hard problem to solve. |
| SHA-256 for integrity | Industry standard. Same as Go modules' `go.sum`. |
| Namespace via directories | `cos/@org/pkg/` subdirectories avoid collisions with user files. No symlinks, no magic. |

---

## 3. Implementation Phases

### Phase 1: Foundation (1 session)

**Goal**: Core types, parsing, validation, and the `cos init` command.

| Task | Description | Acceptance Criteria |
|------|-------------|---------------------|
| Go module setup | Create `cmd/cos/`, `go.mod`, `main.go` | `go build ./cmd/cos/` exits 0 |
| `manifest/types.go` | Define all structs: `Package`, `Dependency`, `Export`, `Feature`, `Script`, `Platform`, `Workspace`, `Publish` | Struct tags match YAML field names |
| `manifest/parse.go` | Parse `cos-package.yaml` with strict YAML (disallow unknown fields) | Parses all example manifests without error |
| `manifest/validate.go` | Validate: name format, semver version, license SPDX, export paths exist, no circular features | Returns structured errors with line context |
| `manifest/defaults.go` | Apply defaults: license from parent, version `0.1.0` | Defaults applied when fields omitted |
| `cli/root.go` | Root command with `--version`, `--verbose`, `--no-color` flags | `cos --version` prints version |
| `cli/init.go` | Interactive manifest generator (prompts for name, version, description, type) | Creates valid `cos-package.yaml` |
| `cli/validate.go` | `cos validate` reads and validates manifest | Exits 0 on valid, 1 on invalid with errors |
| Tests | Unit tests for parse, validate, defaults | `go test ./internal/manifest/...` passes |

### Phase 2: Local Operations (1 session)

**Goal**: Work with locally installed packages without needing a registry.

| Task | Description | Acceptance Criteria |
|------|-------------|---------------------|
| `cli/list.go` | Scan `.claude/*/cos/` for installed packages, display table | Lists name, version, type, install path |
| `scorer/rules.go` | Scoring criteria: has README (10), has tests (15), has license (10), has examples (10), manifest valid (15), exports valid (15), description present (5), version tagged (10), changelog exists (5), no lint errors (5) | Each criterion returns 0 or max points |
| `scorer/score.go` | Run all criteria, compute total, assign grade (A/B/C/D/F) | `cos score .` returns score and grade |
| `cli/score.go` | `cos score [path]` command | Runs scorer, prints report |
| `cli/link.go` | Symlink local package into `.claude/*/cos/` for development | `cos link ./my-skill` creates symlink |
| `cli/tree.go` | Display installed packages as a tree (with deps when lock exists) | ASCII tree output |
| Tests | Unit tests for scorer, list scanning | `go test ./internal/scorer/...` passes |

### Phase 3: Registry + Install (1-2 sessions)

**Goal**: Install packages from GitHub repositories.

| Task | Description | Acceptance Criteria |
|------|-------------|---------------------|
| `registry/source.go` | `Source` interface: `Fetch(name, version) -> PackageDir` | Interface defined with error types |
| `registry/github.go` | Git clone at tag, cache in `~/.cos/cache/github.com/org/pkg/v1.2.0/` | Clones, reads manifest, returns path |
| `registry/cache.go` | Check cache before clone, TTL-based expiry, `cos cache clean` | Cache hit avoids network |
| `registry/index.go` | Read centralized index YAML for `@scope/name` -> `github.com/org/repo` mapping | Resolves scoped names |
| `cli/install.go` | `cos install <pkg>[@version]` -- fetch, validate, resolve deps, install, update lock | Package appears in `cos list` after install |
| `cli/uninstall.go` | `cos uninstall <pkg>` -- remove files, update lock, update catalog | Package disappears from `cos list` |
| `installer/install.go` | Copy exports to `.claude/{type}/cos/{namespace}/` | Files exist at correct paths |
| `installer/coexist.go` | Never touch files outside `cos/` subdirectories | User files untouched after install |
| `installer/catalog.go` | Append skill entries to `CATALOG.md`, rule entries to `RULES-COMPACT.md` | Entries present after install, removed after uninstall |
| `lockfile/write.go` | Generate `cos.lock` with version + SHA-256 hash per package | Lock file valid YAML |
| `lockfile/read.go` | Parse existing lock file | Roundtrip: write then read produces identical data |
| `lockfile/verify.go` | Verify installed files match lock file hashes | Detects tampered files |
| Tests | Integration tests with mock git repos | `go test ./internal/registry/...` passes |

### Phase 4: Resolution (1 session)

**Goal**: Dependency resolution with MVS.

| Task | Description | Acceptance Criteria |
|------|-------------|---------------------|
| `resolver/graph.go` | Build dependency graph from manifest + transitive deps | Graph is a DAG (no cycles) |
| `resolver/mvs.go` | Minimum Version Selection: for each dep, pick the minimum version satisfying all constraints | Matches Go MVS behavior on test cases |
| `resolver/features.go` | Unify features: if A needs pkg[feat-x] and B needs pkg[feat-y], install pkg with both | Feature set is union of all requirements |
| `resolver/conflict.go` | Detect and report: incompatible version requirements, missing packages | Clear error messages with "required by" chain |
| `cli/resolve.go` | `cos resolve --dry-run` -- show what would be installed without doing it | Prints resolution plan |
| `cli/why.go` | `cos why <pkg>` -- explain why a package is in the dependency graph | Shows dependency chain |
| Tests | Resolution test cases: diamond deps, feature unification, conflicts | All test scenarios pass |

### Phase 5: Publishing (1 session)

**Goal**: Package creation and publishing workflow.

| Task | Description | Acceptance Criteria |
|------|-------------|---------------------|
| `cli/pack.go` | `cos pack` -- create `.cos-pkg.tar.gz` with manifest + exports | Tarball contains only declared files |
| `cli/publish.go` | `cos publish --dry-run` -- validate, score, show what would be published | Dry-run exits 0 on valid package |
| `cli/publish.go` | `cos publish` -- tag git repo + push (GitHub registry) | Git tag created |
| `cli/audit.go` | `cos audit` -- check license compatibility of all deps using license-policy rules | Reports BLOCKED/CAUTION/SAFE per dep |
| `scorer/report.go` | Format score report for publish (minimum score to publish: 40/100) | Blocks publish below threshold |
| Tests | Publish dry-run, audit with known licenses | Tests pass |

### Phase 6: Advanced (future sessions)

| Task | Description |
|------|-------------|
| `cli/workspace.go` | Monorepo support: `cos workspace init`, shared deps |
| `cli/search.go` | Full-text search against centralized index |
| `cli/outdated.go` | Compare installed versions against latest available |
| `self-update` | `cos self-update` downloads latest binary |
| TUI dashboard | Interactive mode: browse, install, score in Bubbletea TUI |

---

## 4. cos-package.yaml Specification

### Full Schema

```yaml
# === PACKAGE IDENTITY ===

# Package name. REQUIRED.
# Format: domain-based path (github.com/org/pkg) or scoped (@org/pkg).
# Must match regex: ^(@[a-z0-9-]+/)?[a-z0-9]([a-z0-9._-]*[a-z0-9])?$
# or ^[a-z0-9]+(\.[a-z0-9]+)+/[a-z0-9-]+/[a-z0-9-]+$
name: "github.com/luum/safety-mesh"

# Semantic version. REQUIRED.
# Must follow semver 2.0: MAJOR.MINOR.PATCH[-prerelease][+build]
version: "1.2.0"

# Human-readable description. REQUIRED.
# Must be 10-200 characters.
description: "Safety hooks and rules for AI agent guardrails"

# Package authors. REQUIRED (at least one).
# Each entry: "Name <email>" or "Name"
authors:
  - "Luum Team <team@luum.dev>"

# SPDX license identifier. REQUIRED.
# Must be a valid SPDX expression: MIT, Apache-2.0, BSD-3-Clause, etc.
# The license-policy rules from Cognitive OS apply during audit.
license: "MIT"

# Source repository URL. OPTIONAL but recommended for scoring.
repository: "https://github.com/luum/safety-mesh"

# Keywords for search indexing. OPTIONAL.
# Maximum 10 keywords, each 2-30 characters.
keywords:
  - "safety"
  - "guardrails"
  - "hooks"

# Minimum cos CLI version required. OPTIONAL.
# Uses semver range syntax.
cos_version: ">=0.1.0"


# === PROVIDES ===

# What type of components this package provides. REQUIRED.
# Valid values: skill, rule, hook, agent, template, bundle
# A bundle provides multiple types.
provides:
  - skill
  - rule
  - hook


# === EXPORTS ===

# Files to install, mapped to their destination type. REQUIRED.
# Each export declares:
#   - source: path relative to package root
#   - type: destination category (skill, rule, hook, template, agent)
#   - destination: optional override path (default: derived from type + package name)
#   - description: optional 1-line description for catalog entries
#   - triggers: optional list of contextual triggers (for skills/rules)
exports:
  - source: "skills/safety-review/SKILL.md"
    type: skill
    description: "Review code changes for safety concerns"
    triggers:
      - "security"
      - "safety review"

  - source: "rules/safety-gates.md"
    type: rule
    description: "Constitutional gates for safety-critical operations"

  - source: "hooks/safety-check.sh"
    type: hook
    hook_event: "PreToolUse"
    hook_matcher: "Agent"
    description: "Pre-flight safety check before agent execution"

  - source: "templates/safety-prompt.md"
    type: template
    description: "Safety-aware prompt template"


# === DEPENDENCIES ===

# Other cos packages this package depends on. OPTIONAL.
# Version ranges follow semver constraints:
#   ">=1.0.0"       - minimum version
#   ">=1.0.0,<2.0.0" - range (>=1.0.0 AND <2.0.0)
#   "^1.2.0"        - compatible (>=1.2.0, <2.0.0) -- caret
#   "~1.2.0"        - approximate (>=1.2.0, <1.3.0) -- tilde
#   "1.2.0"         - exact version (discouraged, prefer ranges)
dependencies:
  "github.com/luum/core-rules":
    version: ">=1.0.0,<2.0.0"
    # Optional: only install this dep when specific features are enabled
    features:
      - "strict-mode"

  "@community/prompt-library":
    version: "^2.0.0"


# === GROUPS ===

# Dependency groups for conditional installation. OPTIONAL.
# Groups are NOT installed by default. Use: cos install --group=dev
groups:
  dev:
    "github.com/luum/test-helpers":
      version: ">=0.5.0"
  test:
    "github.com/luum/mock-skills":
      version: "^1.0.0"
  # Custom groups are allowed (any string key).
  benchmarks:
    "github.com/luum/benchmark-suite":
      version: ">=0.1.0"


# === FEATURES ===

# Conditional exports. OPTIONAL.
# Features allow packages to optionally include components.
# Default features are enabled unless the consumer opts out.
# Non-default features must be explicitly requested.
features:
  strict-mode:
    default: false
    description: "Enable strict safety checks that block on warnings"
    exports:
      - source: "rules/strict-safety.md"
        type: rule
      - source: "hooks/strict-gate.sh"
        type: hook
        hook_event: "PostToolUse"
        hook_matcher: "Agent"

  telemetry:
    default: true
    description: "Include telemetry hooks for safety event tracking"
    exports:
      - source: "hooks/safety-telemetry.sh"
        type: hook
        hook_event: "PostToolUse"
        hook_matcher: "Agent"
    dependencies:
      "github.com/luum/metrics-core":
        version: ">=1.0.0"


# === SCRIPTS ===

# Lifecycle hooks. OPTIONAL.
# Scripts run at specific points during install/uninstall.
# Scripts execute in the package directory with bash.
# Exit code 0 = success, non-zero = fail (blocks the operation).
# Scripts have access to these environment variables:
#   COS_PACKAGE_NAME, COS_PACKAGE_VERSION, COS_INSTALL_DIR,
#   COS_PROJECT_DIR, COS_ACTION (install|uninstall|update)
scripts:
  # Runs after files are copied to .claude/
  postinstall: "scripts/postinstall.sh"
  # Runs before files are removed from .claude/
  preuninstall: "scripts/preuninstall.sh"
  # Runs during cos publish --dry-run validation
  validate: "scripts/validate.sh"
  # Runs during cos score
  test: "scripts/test.sh"


# === WORKSPACE ===

# Monorepo support. OPTIONAL.
# Only valid in the root cos-package.yaml of a workspace.
# Members are relative directory paths to sub-packages.
workspace:
  members:
    - "packages/core-rules"
    - "packages/safety-hooks"
    - "packages/prompt-templates"
  # Fields applied to all members unless overridden.
  shared:
    license: "MIT"
    authors:
      - "Luum Team <team@luum.dev>"
  # Dependencies shared across all workspace members.
  shared_dependencies:
    "github.com/luum/core-rules":
      version: ">=1.0.0"


# === PLATFORM ===

# Runtime requirements. OPTIONAL.
# cos validates these before install and warns on mismatch.
platform:
  # Operating systems. Values: linux, darwin, windows
  os:
    - linux
    - darwin
  # Required shell for hook execution. Values: bash, zsh, fish, sh
  shell: bash
  # External tools that must be available in PATH.
  tools:
    - name: "jq"
      version: ">=1.6"
    - name: "git"
      version: ">=2.30"
  # IDE compatibility. Values: claude-code, cursor, windsurf, cline
  ide:
    - claude-code


# === PUBLISH ===

# Publishing configuration. OPTIONAL.
publish:
  # Files to include in the published package (glob patterns).
  # If omitted, all files tracked by git are included.
  include:
    - "skills/**"
    - "rules/**"
    - "hooks/**"
    - "templates/**"
    - "scripts/**"
    - "cos-package.yaml"
    - "README.md"
    - "LICENSE"
    - "CHANGELOG.md"
  # Files to exclude (applied after include).
  exclude:
    - "**/*_test.go"
    - "**/testdata/**"
    - ".git/**"
    - "node_modules/**"
  # Target registry. Default: github (tag-based).
  registry: "github"
  # Minimum score required to publish. Default: 40.
  min_score: 40
```

### Validation Rules

| Field | Rule | Error Message |
|-------|------|---------------|
| `name` | Required. Must match name regex. | `name: required, must be lowercase alphanumeric with dots/hyphens` |
| `version` | Required. Must be valid semver. | `version: must follow semver 2.0 (e.g., 1.0.0)` |
| `description` | Required. 10-200 chars. | `description: required, must be 10-200 characters` |
| `authors` | Required. At least one entry. | `authors: at least one author required` |
| `license` | Required. Valid SPDX. | `license: must be a valid SPDX identifier` |
| `provides` | Required. At least one valid type. | `provides: at least one of skill/rule/hook/agent/template/bundle` |
| `exports` | Required. At least one entry. | `exports: at least one export required` |
| `exports[].source` | Must exist as a file relative to package root. | `exports[0].source: file "X" not found` |
| `exports[].type` | Must be: skill, rule, hook, template, agent. | `exports[0].type: must be skill/rule/hook/template/agent` |
| `exports[].hook_event` | Required when type is hook. Must be: PreToolUse, PostToolUse, SessionStart, Stop. | `exports[0].hook_event: required for hook exports` |
| `exports[].hook_matcher` | Required when type is hook. | `exports[0].hook_matcher: required for hook exports` |
| `dependencies` versions | Must be valid semver range. | `dependencies.X.version: invalid semver range` |
| `features` | Feature names must be kebab-case. No circular feature deps. | `features.X: circular dependency detected` |
| `keywords` | Max 10, each 2-30 chars. | `keywords: maximum 10, each 2-30 characters` |
| `workspace.members` | Each path must contain a `cos-package.yaml`. | `workspace.members[0]: no cos-package.yaml found at "X"` |
| `platform.tools[].version` | Valid semver range. | `platform.tools[0].version: invalid semver range` |
| `publish.min_score` | Integer 0-100. | `publish.min_score: must be 0-100` |

### Example Manifests

**Minimal (single skill)**:

```yaml
name: "@community/code-reviewer"
version: "1.0.0"
description: "Adversarial code review skill for pull requests"
authors:
  - "Jane Dev <jane@example.com>"
license: "MIT"
provides:
  - skill
exports:
  - source: "SKILL.md"
    type: skill
    description: "Review code with adversarial protocol"
```

**Bundle (multiple types)**:

```yaml
name: "github.com/luum/safety-mesh"
version: "1.2.0"
description: "Complete safety mesh: hooks, rules, and review skill"
authors:
  - "Luum Team <team@luum.dev>"
license: "Apache-2.0"
repository: "https://github.com/luum/safety-mesh"
provides:
  - skill
  - rule
  - hook
exports:
  - source: "skills/safety-review/SKILL.md"
    type: skill
    description: "Safety-focused code review"
  - source: "rules/safety-gates.md"
    type: rule
    description: "Constitutional safety gates"
  - source: "hooks/pre-safety-check.sh"
    type: hook
    hook_event: "PreToolUse"
    hook_matcher: "Agent"
    description: "Pre-execution safety validation"
dependencies:
  "github.com/luum/core-rules":
    version: "^1.0.0"
```

---

## 5. cos.lock Specification

### Purpose

The lock file pins exact versions, sources, and integrity hashes for every installed package (direct and transitive). It guarantees reproducible installations across machines and sessions.

### File Name

`cos.lock` -- placed in the project root alongside `cos-package.yaml`.

### Format

```yaml
# Auto-generated by cos. DO NOT EDIT.
# Run "cos install" to regenerate.

version: 1

# SHA-256 hash of the cos-package.yaml content that produced this lock.
# If the manifest changes, cos warns that the lock is stale.
content_hash: "sha256:a1b2c3d4e5f6..."

packages:
  "github.com/luum/core-rules":
    version: "1.3.0"
    source: "github.com/luum/core-rules"
    # Tag or commit used to fetch this version.
    ref: "v1.3.0"
    # SHA-256 hash of the package tarball content.
    integrity: "sha256:f7e8d9c0b1a2..."
    # Features enabled for this package in this resolution.
    features:
      - "telemetry"
    # Direct dependencies of this package (for tree display).
    dependencies: {}

  "github.com/luum/safety-mesh":
    version: "1.2.0"
    source: "github.com/luum/safety-mesh"
    ref: "v1.2.0"
    integrity: "sha256:1234567890ab..."
    features:
      - "telemetry"
    dependencies:
      "github.com/luum/core-rules":
        version: ">=1.0.0,<2.0.0"

  "github.com/luum/metrics-core":
    version: "1.0.0"
    source: "github.com/luum/metrics-core"
    ref: "v1.0.0"
    integrity: "sha256:abcdef123456..."
    features: []
    dependencies: {}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | int | Lock file format version. Always `1` for now. |
| `content_hash` | string | SHA-256 of the project's `cos-package.yaml`. Detects manifest drift. |
| `packages` | map | Map of package name -> locked entry. |
| `packages.*.version` | string | Exact resolved version (not a range). |
| `packages.*.source` | string | Registry source path. |
| `packages.*.ref` | string | Git tag or commit SHA used to fetch. |
| `packages.*.integrity` | string | `sha256:` prefixed hash of package content. |
| `packages.*.features` | list | Feature flags enabled for this resolution. |
| `packages.*.dependencies` | map | This package's declared dependencies (for `cos tree`). |

### Verification

`cos install` with an existing `cos.lock`:

1. Parse the lock file.
2. For each package, verify `integrity` matches the cached content.
3. If a hash mismatches: error with `"integrity check failed for X: expected sha256:..., got sha256:..."`.
4. If `content_hash` mismatches the current `cos-package.yaml`: warn `"cos.lock is stale. Run 'cos install' to update."`.

### Lock File Operations

| Scenario | Behavior |
|----------|----------|
| `cos install` (no lock) | Resolve from scratch, generate `cos.lock`. |
| `cos install` (with lock) | Use locked versions. Only re-resolve if manifest changed. |
| `cos install <pkg>` (add new) | Re-resolve full graph, update `cos.lock`. |
| `cos uninstall <pkg>` | Remove from lock, re-resolve remaining graph. |
| `cos install --force` | Ignore existing lock, re-resolve everything. |

---

## 6. Registry Model

### GitHub-Based Registry (Primary)

Packages are hosted in Git repositories. Versions are Git tags.

```
cos install github.com/luum/safety-mesh@v1.2.0
```

**Resolution flow**:

1. Parse package identifier: `github.com/{owner}/{repo}`
2. Check local cache: `~/.cos/cache/github.com/luum/safety-mesh/v1.2.0/`
3. If cached and not expired (TTL: 24 hours for release tags, 1 hour for branches): use cache.
4. If not cached: `git clone --depth 1 --branch v1.2.0 https://github.com/luum/safety-mesh.git` into cache.
5. Read `cos-package.yaml` from the cloned repo.
6. Validate the manifest.
7. Return the cached path.

**Version discovery** (for `cos outdated`, `cos install` without version):

1. `git ls-remote --tags https://github.com/luum/safety-mesh.git`
2. Filter tags matching `v*` semver pattern.
3. Sort by semver, return latest.

**Authentication**:

- Public repos: no auth needed.
- Private repos: uses `git` credential helpers already configured on the system (SSH keys, GH CLI auth, credential managers).
- cos does NOT manage credentials. It delegates to `git`.

### Centralized Index (Future)

A GitHub repository (`github.com/luum/cos-index`) containing a YAML index of known packages. This enables scoped names (`@org/pkg`) and search.

**Index format** (`index.yaml`):

```yaml
version: 1
packages:
  "@luum/safety-mesh":
    source: "github.com/luum/safety-mesh"
    description: "Safety hooks and rules for AI agent guardrails"
    license: "MIT"
    latest: "1.2.0"
    score: 85
    keywords:
      - "safety"
      - "guardrails"

  "@luum/core-rules":
    source: "github.com/luum/core-rules"
    description: "Foundational rules for Cognitive OS"
    license: "Apache-2.0"
    latest: "1.3.0"
    score: 92
    keywords:
      - "rules"
      - "foundation"

  "@community/code-reviewer":
    source: "github.com/janeDev/cos-code-reviewer"
    description: "Adversarial code review skill"
    license: "MIT"
    latest: "1.0.0"
    score: 71
    keywords:
      - "review"
      - "quality"
```

**Resolution of scoped names**:

```
@luum/safety-mesh  -->  index lookup  -->  github.com/luum/safety-mesh
```

**Index updates**:

- Publishing a package submits a PR to the index repo (automated by `cos publish`).
- The index repo has CI that validates the PR (checks manifest, runs score, verifies license).
- Merged PRs update the index.

**Search**:

```
cos search "safety"
```

Downloads the index (cached locally, refreshed every hour), filters by keyword/description match, displays results with scores.

### Caching Strategy

```
~/.cos/
  cache/
    github.com/
      luum/
        safety-mesh/
          v1.2.0/          # Cached clone at this tag
            cos-package.yaml
            skills/
            rules/
            hooks/
          v1.1.0/
      community/
        code-reviewer/
          v1.0.0/
    index/
      index.yaml           # Cached centralized index
      index.yaml.etag       # HTTP ETag for conditional fetch
  config.yaml              # Global cos configuration (optional)
```

**Cache policies**:

| Content | TTL | Rationale |
|---------|-----|-----------|
| Release tags (`v*`) | 24 hours | Immutable once published. |
| Branch refs (`main`, `latest`) | 1 hour | May change frequently. |
| Index file | 1 hour | Needs freshness for search. |
| Failed fetches | 5 minutes | Don't hammer on transient failures. |

**Cache commands**:

```bash
cos cache clean          # Remove all cached downloads
cos cache clean --older 7d  # Remove entries older than 7 days
cos cache list           # Show cache contents and sizes
```

### Checksum Verification

1. After downloading a package, compute SHA-256 of all files listed in `exports`.
2. Store the hash in `cos.lock` as `integrity: "sha256:..."`.
3. On subsequent installs from lock: re-compute hash and compare.
4. Mismatch = error. The package content changed for the same version tag. This is a supply chain attack indicator.

---

## 7. CLI Reference

### Global Flags

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--verbose` | `-v` | false | Enable verbose output |
| `--no-color` | | false | Disable colored output |
| `--version` | `-V` | | Print cos version and exit |
| `--help` | `-h` | | Print help and exit |

### cos init

Create a new `cos-package.yaml` interactively.

```
cos init [--name <name>] [--type <type>] [--non-interactive]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--name` | (prompted) | Package name |
| `--type` | (prompted) | Package type: skill, rule, hook, agent, template, bundle |
| `--non-interactive` | false | Use defaults without prompting |

**Exit codes**: 0 (success), 1 (error), 2 (file already exists).

**Example**:

```bash
$ cos init
Package name: @myteam/auth-hooks
Version [0.1.0]:
Description: Authentication hooks for session management
Type (skill/rule/hook/agent/template/bundle): hook
License [MIT]:
Author: Jane Dev <jane@example.com>

Created cos-package.yaml
```

### cos validate

Validate a `cos-package.yaml` file.

```
cos validate [path]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `path` | `.` | Directory containing `cos-package.yaml` |

**Exit codes**: 0 (valid), 1 (invalid -- errors printed to stderr).

**Example**:

```bash
$ cos validate
  cos-package.yaml is valid
  Name:    @myteam/auth-hooks
  Version: 0.1.0
  Type:    hook
  Exports: 2 files
```

### cos install

Install one or more packages.

```
cos install [<package>[@<version>]...]
cos install                         # Install from cos.lock or resolve cos-package.yaml
cos install <package>               # Add package (latest version)
cos install <package>@<version>     # Add package at specific version
cos install --group=dev             # Also install dev group dependencies
cos install --force                 # Re-resolve ignoring cos.lock
```

| Flag | Default | Description |
|------|---------|-------------|
| `--group` | (none) | Also install dependencies from this group |
| `--force` | false | Ignore existing lock file, re-resolve |
| `--dry-run` | false | Show what would be installed without doing it |

**Exit codes**: 0 (success), 1 (resolution error), 2 (network error), 3 (integrity error).

**Example**:

```bash
$ cos install github.com/luum/safety-mesh@v1.2.0
  Resolving dependencies...
  Fetching github.com/luum/safety-mesh@v1.2.0
  Fetching github.com/luum/core-rules@v1.3.0 (dependency)
  Installing:
    github.com/luum/safety-mesh@1.2.0
      -> .claude/skills/cos/@luum/safety-mesh/SKILL.md
      -> .claude/rules/cos/@luum/safety-mesh/safety-gates.md
      -> .claude/hooks/cos/@luum/safety-mesh/pre-safety-check.sh
    github.com/luum/core-rules@1.3.0
      -> .claude/rules/cos/@luum/core-rules/foundation.md
  Updated cos.lock
  Updated CATALOG.md (1 skill added)
  Updated RULES-COMPACT.md (2 rules added)
  Done. 2 packages installed.
```

### cos uninstall

Remove installed packages.

```
cos uninstall <package>...
```

**Exit codes**: 0 (success), 1 (package not installed).

**Example**:

```bash
$ cos uninstall github.com/luum/safety-mesh
  Removing github.com/luum/safety-mesh@1.2.0
    <- .claude/skills/cos/@luum/safety-mesh/
    <- .claude/rules/cos/@luum/safety-mesh/
    <- .claude/hooks/cos/@luum/safety-mesh/
  Checking orphaned dependencies...
    github.com/luum/core-rules@1.3.0 is no longer needed. Remove? [Y/n] y
    Removing github.com/luum/core-rules@1.3.0
  Updated cos.lock
  Updated CATALOG.md (1 skill removed)
  Updated RULES-COMPACT.md (2 rules removed)
  Done.
```

### cos list

List installed packages.

```
cos list [--json] [--format=<table|json|yaml>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--json` | false | Output as JSON |
| `--format` | table | Output format: table, json, yaml |

**Exit codes**: 0 (always).

**Example**:

```bash
$ cos list
  PACKAGE                            VERSION  TYPE    SCORE
  github.com/luum/safety-mesh        1.2.0    bundle  85/100
  github.com/luum/core-rules         1.3.0    rule    92/100
  @community/code-reviewer           1.0.0    skill   71/100
```

### cos search

Search for packages in the index.

```
cos search <query> [--limit=<n>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--limit` | 20 | Maximum results |

**Exit codes**: 0 (results found), 0 (no results -- empty output).

**Example**:

```bash
$ cos search "safety"
  PACKAGE                       VERSION  SCORE  DESCRIPTION
  @luum/safety-mesh             1.2.0    85     Safety hooks and rules for AI agent guardrails
  @community/safety-scanner     0.3.0    62     Security scanning skill for agent outputs
```

### cos score

Run quality scoring on a package.

```
cos score [path]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `path` | `.` | Directory containing `cos-package.yaml` |

**Exit codes**: 0 (score >= 40), 1 (score < 40).

**Scoring criteria**:

| Criterion | Max Points | Check |
|-----------|-----------|-------|
| Valid manifest | 15 | `cos-package.yaml` parses and validates |
| Has README | 10 | `README.md` exists and is >100 chars |
| Has LICENSE | 10 | `LICENSE` or `LICENSE.md` exists |
| Has tests | 15 | `scripts.test` defined and passes |
| Exports valid | 15 | All declared export files exist |
| Has description | 5 | Description field present and >10 chars |
| Version tagged | 10 | Current git tag matches `version` field |
| Has changelog | 5 | `CHANGELOG.md` exists |
| Has examples | 10 | `examples/` directory exists with files |
| No lint errors | 5 | `component-lint.sh` passes on exports |
| **Total** | **100** | |

**Grades**:

| Score | Grade |
|-------|-------|
| 90-100 | A |
| 75-89 | B |
| 60-74 | C |
| 40-59 | D |
| 0-39 | F |

**Example**:

```bash
$ cos score
  Package: @myteam/auth-hooks v0.1.0
  Score: 72/100 (C)

  [PASS]  Valid manifest          15/15
  [PASS]  Has README              10/10
  [PASS]  Has LICENSE             10/10
  [FAIL]  Has tests                0/15  (no scripts.test defined)
  [PASS]  Exports valid           15/15
  [PASS]  Has description          5/5
  [FAIL]  Version tagged           0/10  (no git tag v0.1.0 found)
  [FAIL]  Has changelog            0/5   (CHANGELOG.md not found)
  [PASS]  Has examples            10/10
  [PASS]  No lint errors           5/5
  [WARN]  Not publishable          2/2   (score >= 40 required)
```

### cos tree

Display installed packages as a dependency tree.

```
cos tree [--depth=<n>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--depth` | unlimited | Maximum tree depth |

**Exit codes**: 0 (always).

**Example**:

```bash
$ cos tree
  my-project@0.0.0
  +-- github.com/luum/safety-mesh@1.2.0
  |   +-- github.com/luum/core-rules@1.3.0
  |   +-- github.com/luum/metrics-core@1.0.0 (feature: telemetry)
  +-- @community/code-reviewer@1.0.0
```

### cos why

Explain why a package is installed.

```
cos why <package>
```

**Exit codes**: 0 (found), 1 (not installed).

**Example**:

```bash
$ cos why github.com/luum/metrics-core
  github.com/luum/metrics-core@1.0.0 is installed because:
    github.com/luum/safety-mesh@1.2.0
      -> feature "telemetry" requires github.com/luum/metrics-core@>=1.0.0
```

### cos outdated

Check for newer versions of installed packages.

```
cos outdated [--json]
```

**Exit codes**: 0 (all up to date), 1 (updates available).

**Example**:

```bash
$ cos outdated
  PACKAGE                       INSTALLED  LATEST  STATUS
  github.com/luum/safety-mesh   1.2.0      1.3.0   UPDATE AVAILABLE
  github.com/luum/core-rules    1.3.0      1.3.0   UP TO DATE
  @community/code-reviewer      1.0.0      1.1.0   UPDATE AVAILABLE
```

### cos audit

Audit installed packages for license and security issues.

```
cos audit [--fix]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--fix` | false | Attempt to fix issues (remove blocked packages) |

**Exit codes**: 0 (clean), 1 (issues found).

License checking follows `rules/license-policy.md`:

| License | Verdict | Action |
|---------|---------|--------|
| MIT, BSD, Apache-2.0, ISC | SAFE | None |
| LGPL, MPL-2.0 | CAUTION | Warning printed |
| AGPL, SSPL, BSL, ELv2 | BLOCKED | Error. Package must be removed. |
| Unknown | BLOCKED | Error. Cannot verify compliance. |

**Example**:

```bash
$ cos audit
  Auditing 3 packages...

  [SAFE]    github.com/luum/safety-mesh (MIT)
  [SAFE]    github.com/luum/core-rules (Apache-2.0)
  [CAUTION] @community/code-reviewer (LGPL-3.0)
            -> OK if used as dynamic library only (not modified)

  1 caution, 0 blocked. Audit passed.
```

### cos link / cos unlink

Symlink a local package for development.

```
cos link <path>
cos unlink <package>
```

**Exit codes**: 0 (success), 1 (error).

**Example**:

```bash
$ cos link ../my-local-skill
  Linked ../my-local-skill as @local/my-local-skill
  -> .claude/skills/cos/@local/my-local-skill -> /abs/path/to/my-local-skill/skills/

$ cos unlink @local/my-local-skill
  Unlinked @local/my-local-skill
```

### cos resolve

Resolve dependencies without installing.

```
cos resolve [--dry-run] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | true | Show resolution plan (default behavior) |
| `--json` | false | Output as JSON |

**Exit codes**: 0 (resolved), 1 (conflict).

### cos pack

Create a distributable package archive.

```
cos pack [--output=<path>]
```

**Exit codes**: 0 (success), 1 (error).

Creates a `.cos-pkg.tar.gz` containing only files matching `publish.include` patterns.

### cos publish

Publish a package.

```
cos publish [--dry-run] [--tag=<tag>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | false | Validate and score without publishing |
| `--tag` | `v{version}` | Git tag to create |

**Publish process**:

1. Run `cos validate` -- must pass.
2. Run `cos score` -- must be >= `publish.min_score` (default 40).
3. Run `cos audit` on own dependencies -- must have no BLOCKED licenses.
4. Run `scripts.validate` if defined -- must exit 0.
5. Create git tag `v{version}`.
6. Push tag to origin.
7. If centralized index: submit PR to index repo.

**Exit codes**: 0 (published), 1 (validation failed), 2 (score too low).

### cos workspace

Workspace (monorepo) management.

```
cos workspace init                  # Initialize workspace in current dir
cos workspace list                  # List workspace members
cos workspace run <cmd> [--member=<name>]  # Run a cos command in each member
```

---

## 8. Integration with Cognitive OS

### Coexistence with self-install.sh

The `self-install.sh` hook syncs `rules/*.md` to `.claude/rules/` via symlinks. cos-installed packages live in `.claude/rules/cos/` -- a subdirectory that `self-install.sh` does not touch.

**Directory layout after cos install**:

```
.claude/
  rules/
    phase-aware-agents.md        # Symlinked by self-install.sh
    error-learning.md            # Symlinked by self-install.sh
    cos/                         # cos-managed namespace
      @luum/
        safety-mesh/
          safety-gates.md        # Installed by cos
        core-rules/
          foundation.md          # Installed by cos
  skills/
    sdd-apply/SKILL.md           # User-managed
    cos/                         # cos-managed namespace
      @luum/
        safety-mesh/
          SKILL.md               # Installed by cos
  hooks/                         # Not in .claude (hooks go in .claude/ settings)
```

**Rule**: cos NEVER writes outside `cos/` subdirectories. User files and self-install symlinks are never touched.

### Integration with component-lint.sh

`cos score` uses the same linting logic as `hooks/component-lint.sh`. The scorer invokes the linting checks programmatically:

1. Skill files: validates SKILL.md has required sections (Purpose, Steps, etc.).
2. Rule files: validates Markdown structure.
3. Hook files: validates shebang, exit codes, permissions.
4. Template files: validates variable placeholders.

### CATALOG.md Auto-Update

When `cos install` adds a skill, it appends an entry to `CATALOG.md`:

```markdown
## cos-installed skills

| Skill | Package | Version | Description |
|-------|---------|---------|-------------|
| safety-review | @luum/safety-mesh | 1.2.0 | Review code changes for safety concerns |
```

When `cos uninstall` removes a skill, it removes the corresponding entry.

The section header `## cos-installed skills` marks the boundary. cos only modifies content within this section.

### RULES-COMPACT.md Auto-Update

Similarly, cos-installed rules get their own section:

```markdown
## cos-installed rules

- **Safety Gates** [`cos/@luum/safety-mesh/safety-gates`]: Constitutional gates for safety-critical operations.
- **Foundation** [`cos/@luum/core-rules/foundation`]: Foundational rules for agent behavior.
```

### .claude/settings.json Hook Registration

When a cos package exports hooks, `cos install` adds them to `.claude/settings.json` under the appropriate event:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Agent",
        "hooks": [
          "hooks/existing-hook.sh",
          ".claude/hooks/cos/@luum/safety-mesh/pre-safety-check.sh"
        ]
      }
    ]
  }
}
```

On `cos uninstall`, the hook entry is removed.

**Safety**: cos reads the existing `settings.json`, adds/removes only its own entries (identifiable by the `cos/` path prefix), and writes back. It never modifies non-cos hook entries.

### cognitive-os.yaml Integration

A new `packages` section in `cognitive-os.yaml` tracks cos state:

```yaml
packages:
  manifest: "cos-package.yaml"
  lockfile: "cos.lock"
  install_dir: ".claude"
  namespace: "cos"
  auto_update_catalog: true
  auto_update_rules_compact: true
  auto_register_hooks: true
```

---

## 9. Inspiration and References

| Source | What We Took | Specific Design Decision |
|--------|-------------|--------------------------|
| **npm** | Scoped packages, lock files, lifecycle scripts | `@org/name` scoping, `cos.lock` format, `scripts.postinstall` |
| **Go modules** | Minimum Version Selection, domain-based naming, checksum database | MVS algorithm for resolution, `github.com/org/pkg` naming, `integrity` hashes in lock |
| **Cargo** | Features system, workspaces, `Cargo.toml` clarity | `features` with default/non-default, `workspace.members`, manifest field structure |
| **pip** | Groups (extras_require), simple resolution | `groups` for dev/test/optional dependencies |
| **pub.dev** | Quality scoring, search index, package grades | Score 0-100, grade A-F, minimum score for publish, score displayed in search |
| **Homebrew** | Formula validation, tap model | Centralized index as a Git repo (like homebrew-core taps) |
| **Nix** | Reproducible builds, content-addressed storage | SHA-256 integrity verification, lock file determinism |

### Key Divergences from Existing Package Managers

| Decision | Unlike | Rationale |
|----------|--------|-----------|
| MVS instead of SAT solver | npm, pip, cargo | Simpler, deterministic, no NP-hard problem. Go proved this works at scale. |
| Git tags as versions | npm (centralized registry) | No infrastructure to maintain. Works with any git host. |
| YAML manifest | npm (JSON), cargo (TOML) | Consistency with Cognitive OS (`cognitive-os.yaml`). YAML is the lingua franca of this ecosystem. |
| `cos/` subdirectory isolation | npm (node_modules/) | Agent components coexist with user files in `.claude/`. Namespace isolation prevents collisions. |
| Score gating for publish | npm (no quality gate) | Prevents low-quality packages from entering the ecosystem. Learned from npm's spam problem. |
| No post-install arbitrary code | npm (allows any script) | Security. Post-install scripts are restricted to the package's own directory. They cannot modify files outside `cos/`. |

---

## 10. Checklist for Contributors

### Creating a cos Package

1. **Create the package directory** with your components:

   ```
   my-package/
     cos-package.yaml     # REQUIRED
     README.md            # Recommended (10 pts)
     LICENSE              # Recommended (10 pts)
     CHANGELOG.md         # Recommended (5 pts)
     skills/
       my-skill/SKILL.md
     rules/
       my-rule.md
     hooks/
       my-hook.sh
     examples/            # Recommended (10 pts)
       usage.md
   ```

2. **Write `cos-package.yaml`** with at minimum:

   ```yaml
   name: "@yourorg/my-package"
   version: "0.1.0"
   description: "A useful package for AI agents"
   authors:
     - "Your Name <you@example.com>"
   license: "MIT"
   provides:
     - skill
   exports:
     - source: "skills/my-skill/SKILL.md"
       type: skill
       description: "What this skill does"
   ```

3. **Validate**:

   ```bash
   cos validate
   ```

4. **Check your score**:

   ```bash
   cos score
   ```

5. **Fix any issues** until score >= 40 (grade D or better).

6. **Tag your version**:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

7. **Publish**:

   ```bash
   cos publish --dry-run   # Verify first
   cos publish             # Create tag + submit to index
   ```

### Package Quality Checklist

| Item | Points | How to Fix |
|------|--------|------------|
| Valid `cos-package.yaml` | 15 | Run `cos validate` and fix errors |
| `README.md` with >100 chars | 10 | Describe what the package does and how to use it |
| `LICENSE` file | 10 | Add a LICENSE file with your chosen SPDX license |
| Test script passes | 15 | Add `scripts.test` to manifest and implement tests |
| All export files exist | 15 | Ensure every `exports[].source` path exists |
| Description >10 chars | 5 | Write a meaningful description |
| Git tag matches version | 10 | Run `git tag v{version}` |
| `CHANGELOG.md` exists | 5 | Document changes per version |
| `examples/` directory | 10 | Add usage examples |
| No lint errors | 5 | Run `component-lint.sh` on your exports |

### Version Numbering

Follow semver 2.0:

| Change Type | Version Bump | Example |
|-------------|-------------|---------|
| Breaking change (removed export, renamed field) | MAJOR | 1.0.0 -> 2.0.0 |
| New feature (new export, new feature flag) | MINOR | 1.0.0 -> 1.1.0 |
| Bug fix (fixed hook, updated rule text) | PATCH | 1.0.0 -> 1.0.1 |
| Pre-release | Suffix | 1.0.0-alpha.1 |

---

## 11. Known Issues and Limitations

### What cos Does NOT Do

| Limitation | Reason | Workaround |
|------------|--------|------------|
| **No private registry server** | Phase 1 focuses on Git-based packages. A registry server adds infrastructure. | Use private Git repos with SSH auth. |
| **No automatic conflict resolution** | MVS picks minimum versions. If two packages require incompatible versions, cos reports the conflict but does not guess a resolution. | User must manually adjust version constraints. |
| **No binary distribution** | cos installs text files (Markdown, YAML, shell scripts). It does not compile or distribute binaries. | If a package needs compiled tools, declare them in `platform.tools`. |
| **No sandboxed script execution** | Post-install scripts run with the user's permissions. | Scripts are restricted by convention (only modify `cos/` subdirectories). Future: chroot/container sandbox. |
| **No automatic hook ordering** | When multiple packages install hooks for the same event, cos appends in install order. It does not resolve priority. | User can manually reorder hooks in `settings.json`. |
| **No rollback on failed install** | If installation fails midway (e.g., postinstall script fails), partial files may remain. | Run `cos uninstall` to clean up. Future: transactional installs. |
| **No cross-IDE package format** | Packages target Claude Code (`.claude/` directory structure). Cursor/Windsurf support requires adaptation layers. | Use `platform.ide` field to declare compatibility. Adapter skills can translate. |
| **No signed packages** | No cryptographic package signing (no GPG, Sigstore, etc.). | Integrity verification via SHA-256 hashes in `cos.lock`. Signing is a future enhancement. |
| **No dependency vendoring** | Unlike Go's `vendor/`, cos does not support vendoring dependencies into the project. | Lock file ensures reproducibility. Cache serves as local copy. |
| **No workspace dependency hoisting** | In workspaces, each member gets its own copy of shared dependencies. | Shared dependencies are declared once but installed per-member. Storage is cheap for text files. |

### Security Considerations

| Risk | Mitigation |
|------|------------|
| Malicious post-install scripts | Scripts run only from the package directory. `cos audit` checks licenses. Future: script sandboxing. |
| Tag rewriting (force-push a tag) | `cos.lock` integrity hashes detect content changes for the same version. cos warns: "integrity mismatch." |
| Typosquatting (`@luum/safty-mesh`) | Centralized index reviews PRs. Scoped names reduce collision space. Score visibility helps. |
| Dependency confusion | Domain-based naming (`github.com/org/pkg`) eliminates ambiguity. Scoped names (`@org/`) require index registration. |
| Supply chain attacks (compromised upstream) | Lock files pin exact versions. `cos audit` checks all transitive licenses. Manual `cos install --force` required to change locked versions. |

### Future Enhancements (Not In Scope)

| Enhancement | Target Phase |
|-------------|-------------|
| Dedicated registry server (REST API) | Phase 4+ |
| Package signing (Sigstore) | Phase 4+ |
| IDE adapters (Cursor, Windsurf) | Phase 4+ |
| Dependency vendoring | Phase 6+ |
| Automatic conflict resolution | Phase 6+ |
| Transactional installs (rollback on failure) | Phase 6+ |
| Web UI for package browsing | Phase 4+ (via web dashboard) |
| AI-powered package recommendations | Phase 5+ |

---

## 12. Universal Standard — The Babel of AI Agent Skills

### The Problem

Every AI coding tool invented its own format for rules, skills, and configuration:

| Format | Tools Using It | Type |
|--------|---------------|------|
| `CLAUDE.md` | Claude Code, Warp (compatible) | Instructions file |
| `GEMINI.md` | Gemini CLI | Instructions file |
| `AGENTS.md` | OpenAI Codex CLI | Instructions file |
| `.cursorrules` / `.cursor/rules/` | Cursor | Rules dir/file |
| `.windsurfrules` | Windsurf | Single file |
| `.clinerules` | Cline | Single file |
| `.rules` | Trae | Rules files |
| `.roo/rules-{mode}/` | Roo Code | Mode-scoped dirs |
| `.continue/rules/` | Continue.dev | Rules dir with globs |
| `.augment/rules/` | Augment Code | Rules dir |
| `WARP.md` | Warp | Instructions file |
| `.github/copilot-instructions.md` | GitHub Copilot | Instructions file |

No two tools use the same format. A skill written for Claude Code doesn't work in Cursor. A hook written for Gemini CLI doesn't work in Windsurf.

### The Solution: cos as Transpiler

Like Babel transpiles modern JavaScript to work in any browser, `cos` transpiles `cos-package.yaml` packages to work in any IDE:

```
cos-package.yaml (universal source)
    │
    └── cos install → ide-bridge generates:
          ├── .claude/rules/cos/     (Claude Code)
          ├── .claude/settings.json  (Claude Code hooks)
          ├── GEMINI.md              (Gemini CLI)
          ├── .cursor/rules/         (Cursor)
          ├── .windsurfrules         (Windsurf)
          ├── .clinerules            (Cline)
          ├── AGENTS.md              (Codex CLI)
          ├── .roo/rules-code/       (Roo Code)
          ├── .continue/rules/       (Continue.dev)
          └── .augment/rules/        (Augment Code)
```

### What Gets Transpiled

| cos-package.yaml section | Claude Code | Cursor | Windsurf | Gemini CLI |
|---|---|---|---|---|
| `exports.rules` | `.claude/rules/cos/` | `.cursor/rules/` | Appended to `.windsurfrules` | Referenced in `GEMINI.md` |
| `exports.hooks` | `settings.json` hooks | Not supported | Cascade Hooks (partial) | `settings.json` hooks |
| `exports.skills` | `.claude/commands/` | Not supported | Not supported | Not supported |
| `dependencies` | Resolved by cos | Resolved by cos | Resolved by cos | Resolved by cos |
| `features` | Conditional loading | Conditional loading | Not supported | Conditional loading |

### Compatibility Tiers

When `cos install` runs, it detects which IDE(s) are present and generates the appropriate format:

| Tier | What gets generated | IDEs |
|---|---|---|
| **Full** | Rules + hooks + skills + MCP | Claude Code, Gemini CLI |
| **Rules + MCP** | Rules only (no hooks) + MCP config | Cursor, Copilot CLI, Windsurf, Cline |
| **Rules only** | Rules converted to tool-specific format | Aider, Trae, Roo Code, Continue.dev, Augment |
| **None** | Warning: "this tool doesn't support external rules" | Devin, Replit, Bolt.new |

### The cos install Flow (Multi-IDE)

```bash
$ cos install @luum/safety-mesh

Detecting IDEs...
  ✓ Claude Code (.claude/ found)
  ✓ Cursor (.cursor/ found)
  ✗ Windsurf (not detected)

Installing @luum/safety-mesh v1.0.0...
  → .claude/rules/cos/safety-mesh/   (13 rules)
  → .claude/settings.json            (9 hooks registered)
  → .cursor/rules/cos-safety-mesh/   (13 rules, no hooks)

⚠ Note: Cursor does not support hooks. Safety mesh rules are
  advisory only in Cursor (no enforcement). For full enforcement,
  use Claude Code or Gemini CLI.

✓ Installed in 2 IDEs (full: 1, rules-only: 1)
```

### Why This Matters

1. **Write once, use everywhere** — skill authors write one `cos-package.yaml`, it works in 19+ tools
2. **No vendor lock-in** — switch from Claude Code to Gemini CLI without rewriting skills
3. **Community grows faster** — contributors don't need to support each IDE separately
4. **Quality is portable** — a well-tested skill works the same regardless of IDE
5. **Standards emerge from practice** — as cos gains adoption, the `cos-package.yaml` format becomes the de facto standard

### Relationship to MCP

MCP (Model Context Protocol) standardized TOOLS. `cos` standardizes SKILLS, RULES, and HOOKS. Together they cover the full customization surface:

```
MCP:  "What tools can the AI use?"      (universal, 97M downloads)
cos:  "How should the AI behave?"        (our contribution)
      "What quality gates apply?"
      "What skills does it have?"
      "What hooks enforce the rules?"
```

---

## Appendix A: MVS Algorithm Summary

Minimum Version Selection (MVS) was designed by Russ Cox for Go modules. It differs from traditional SAT-solver-based resolution (npm, pip, cargo) in a fundamental way: it always selects the **minimum** version that satisfies all constraints, rather than the latest.

### Why MVS

| Property | MVS | SAT-Based (npm/pip) |
|----------|-----|---------------------|
| Deterministic | Yes -- same inputs always produce same output | Depends on solver heuristics |
| Polynomial time | Yes -- O(V + E) graph traversal | NP-complete in general |
| Predictable | Minimum version means fewer surprises | Latest version may introduce breaking changes |
| Reproducible | Yes -- no solver state to influence results | Lock file needed to reproduce |
| Simple implementation | ~200 lines of Go | Thousands of lines for SAT solver |

### Algorithm

1. Build a requirement graph: each package lists its minimum version requirements.
2. For each package in the graph, collect all version constraints from all dependents.
3. For each package, select the maximum of all minimum requirements (the "minimum version that satisfies everyone").
4. This is a single-pass computation -- no backtracking, no conflict resolution loop.

### Example

```
Project requires:
  A >= 1.0.0
  B >= 1.0.0

A@1.0.0 requires:
  C >= 1.2.0

B@1.0.0 requires:
  C >= 1.5.0

Resolution:
  A@1.0.0  (minimum satisfying >= 1.0.0)
  B@1.0.0  (minimum satisfying >= 1.0.0)
  C@1.5.0  (minimum satisfying both >= 1.2.0 AND >= 1.5.0 = max(1.2.0, 1.5.0))
```

### Limitations of MVS

- Does not support `<` (upper bound) constraints natively. cos extends MVS with range support (`>=1.0.0,<2.0.0`).
- Does not automatically upgrade to latest. Users must run `cos outdated` and explicitly update.
- Assumes versions are immutable (a tag always points to the same content). Integrity hashes enforce this.

---

## Appendix B: Feature Unification Algorithm

When multiple dependents require the same package with different features, cos computes the **union** of all requested features.

### Algorithm

1. Collect all feature requests for each package across the dependency graph.
2. For each package, compute the union set of features.
3. Resolve any feature-specific dependencies for the unified set.
4. If a feature introduces a new dependency, add it to the graph and re-resolve.

### Example

```
Project requires:
  pkg[telemetry]

Dependency A requires:
  pkg[strict-mode]

Resolution:
  pkg with features: {telemetry, strict-mode}
  + telemetry's dependencies resolved
  + strict-mode's dependencies resolved
```

### Conflict Case

Features cannot conflict (they are purely additive -- each feature adds exports and/or dependencies). If two features export the same file path, cos reports an error:

```
Error: feature conflict in github.com/luum/safety-mesh
  Feature "telemetry" exports: hooks/tracker.sh
  Feature "strict-mode" exports: hooks/tracker.sh
  Both features export the same file. The package author must resolve this.
```

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **Package** | A versioned collection of AI agent components (skills, rules, hooks, etc.) with a `cos-package.yaml` manifest. |
| **Manifest** | The `cos-package.yaml` file that describes a package's identity, exports, dependencies, and configuration. |
| **Export** | A file declared in the manifest that gets installed into the consumer's `.claude/` directory. |
| **Feature** | A named set of optional exports and dependencies that consumers can enable or disable. |
| **Bundle** | A package that provides multiple component types (skill + rule + hook). |
| **Registry** | A source where packages can be fetched. GitHub (git-based) or centralized index. |
| **Index** | A YAML file mapping scoped package names to their git sources. Hosted in a GitHub repo. |
| **Lock file** | `cos.lock` -- pins exact versions and integrity hashes for reproducible installs. |
| **MVS** | Minimum Version Selection -- the dependency resolution algorithm. |
| **Integrity hash** | SHA-256 hash of package content, stored in `cos.lock` to detect tampering. |
| **Namespace** | The `cos/` subdirectory structure that isolates cos-managed files from user files. |
| **Score** | A 0-100 quality rating based on documentation, tests, license, and structure. |
| **Workspace** | A monorepo containing multiple related packages managed together. |
| **Coexistence** | The principle that cos-installed files never overwrite or conflict with user-authored files. |
