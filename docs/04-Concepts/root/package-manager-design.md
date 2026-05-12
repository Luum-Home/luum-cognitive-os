# Package Manager Design — Why Brew, Not npm

## The Problem

114+ tools in the Claude Code ecosystem (awesome-claude-code), 38 internal dependencies, growing daily. Manual integration (copy files, edit config, write tests) takes hours per tool. Need automated install/remove/search/audit.

## Package Manager Comparison

### npm / pnpm / yarn

| Aspect | npm | cos |
|---|---|---|
| Package count | 2M+ | <1000 (niche ecosystem) |
| Package content | JavaScript code + binaries | Text files (markdown, bash, yaml) |
| Build step | Yes (transpile, bundle, link) | No (copy files) |
| Tree shaking | Critical (node_modules bloat) | Unnecessary (packages are tiny) |
| Registry | centralized (registry.npmjs.org) | GitHub repos |
| Lockfile | package-lock.json (complex) | cos-lock.yaml (simple) |
| Dependency resolution | Complex (semver ranges, peer deps, hoisting) | Flat (first-wins) |

**Verdict**: Massively over-engineered for our use case. We'd spend months building infrastructure we don't need.

### Cargo (Rust)

| Aspect | Cargo | cos |
|---|---|---|
| Primary purpose | Build system + package manager | Package manager only |
| Features system | Conditional compilation | Conditional exports (simpler) |
| Registry | crates.io (centralized, curated) | GitHub (decentralized) |
| Build step | Compile Rust code | Copy text files |
| Lockfile | Cargo.lock (build reproducibility) | cos-lock.yaml (install reproducibility) |

**Verdict**: Elegant but tied to compilation. Our packages don't compile — they're markdown, bash, and yaml.

### Go Modules

| Aspect | Go Modules | cos |
|---|---|---|
| Resolution algorithm | MVS (Minimum Version Selection) | Flat (first-wins) |
| Proxy | proxy.golang.org (centralized cache) | None needed |
| Checksum DB | sum.golang.org (security) | SHA256 in lockfile |
| Module format | Go source code in repos | cos-package.yaml in repos |

**Verdict**: MVS is mathematically elegant but needs a proxy server. We use GitHub directly.

### Homebrew (Our Model)

| Aspect | Brew | cos |
|---|---|---|
| Package format | Formula (Ruby DSL) | cos-package.yaml (YAML manifest) |
| Registry | GitHub repos ("taps") | GitHub repos (topic: cos-package) |
| Install mechanism | Download + copy + link | git clone + audit + copy |
| Dependency resolution | Simple (flat) | Simple (flat, first-wins) |
| Discovery | `brew search` (GitHub API) | `cos search` (GitHub API) |
| Build step | Optional (bottles = pre-built) | None (text files) |
| Security | Formula audit | 6-gate security pipeline |

**Verdict**: Closest match. GitHub as registry, simple install, minimal infrastructure. We add security auditing that Brew lacks.

## Key Design Decisions

### 1. GitHub IS the Registry
No custom registry server. A cos package is a GitHub repo with `cos-package.yaml`. Discovery via GitHub search API (topic: `cos-package`). This means zero infrastructure to maintain.

### 2. Security Audit > Speed
Unlike npm (install first, audit later), cos audits BEFORE installing. 6 mandatory gates:
1. License check — block AGPL/SSPL/GPL
2. Secret scan — no hardcoded credentials
3. Injection scan — no prompt injection in skills
4. Dependency audit — check transitive deps
5. Sandbox test — run in worktree isolation
6. Signature verify — trusted publishers (future)

### 3. Text Files, Not Binaries
Packages contain markdown skills, bash hooks, yaml rules. No compilation, no linking, no binary distribution. Install = copy files to the right directories.

### 4. Flat Dependencies
No complex dependency resolution. If package A needs B, install B first. If B is already installed at a compatible version, skip. If version conflict, warn. This covers 99% of cases for a small ecosystem.

### 5. Lockfile for Reproducibility
`cos-lock.yaml` tracks every installed package, its version, source commit, installed files, and audit results. Enables `cos install` to reproduce the exact same setup on another machine.

## Architecture

```
cos install @luum/safety-mesh
    |
    +- Resolve: @luum/safety-mesh -> github.com/luum/safety-mesh
    |
    +- Fetch: git clone --depth 1 -> /tmp/cos-xxx/
    |
    +- Parse: cos-package.yaml -> Manifest struct
    |
    +- Audit (6 gates):
    |   . License: Apache-2.0 (SAFE)
    |   . Secrets: 0 found
    |   . Injection: 0 patterns
    |   . Dependencies: all resolved
    |   . Sandbox: tests pass
    |   . Signature: skipped (not implemented)
    |
    +- Install exports:
    |   skill -> .claude/skills/safety-mesh/SKILL.md
    |   hook  -> .cognitive-os/hooks/cos/safety-mesh/pre-check.sh
    |   rule  -> .claude/rules/cos/safety-mesh/governance.md
    |
    +- Register hooks in .claude/settings.json
    |
    +- Update cos-lock.yaml
    |
    +- Run scripts.postinstall (if defined)
```

## CLI Commands

| Command | What | Priority |
|---|---|---|
| `cos install <pkg>` | Install from GitHub/local/URL | P0 |
| `cos remove <pkg>` | Uninstall + cleanup | P0 |
| `cos list` | Show installed packages | P0 |
| `cos audit <pkg>` | Security audit without installing | P1 |
| `cos search <query>` | Find packages on GitHub | P1 |
| `cos update [pkg]` | Update to latest version | P2 |
| `cos publish` | Tag + validate for publishing | P2 |
| `cos init` | Create cos-package.yaml (already exists) | Done |
| `cos validate` | Validate manifest (already exists) | Done |
