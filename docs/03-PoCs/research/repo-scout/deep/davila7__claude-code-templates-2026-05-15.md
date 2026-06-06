---
report_type: repo-scout-simple-research
date: 2026-05-15
repo: davila7/claude-code-templates
classification: ASSESS
adoption_kind: installer-ux-and-marketplace-patterns
license: MIT
clone_path: /tmp/claude-code-templates
commit: bbe998afa0759fc423ddf097e0ac13e09a3a8fa4
related_radar: docs/06-Daily/reports/external-tools-radar-claude-code-templates-addendum-2026-05-15.md
---

# Simple Research — davila7/claude-code-templates

## Question

When moving from agnostic Cognitive OS agentic primitives to concrete IDE/harness
installations, are we building the Claude projection correctly? The comparison
repo was cloned to inspect whether its packaging model should change the current
Cognitive OS direction.

## Source snapshot

| Field | Value |
|---|---|
| Repository | `davila7/claude-code-templates` |
| Local clone | `/tmp/claude-code-templates` |
| Commit inspected | `bbe998afa0759fc423ddf097e0ac13e09a3a8fa4` |
| Commit date | 2026-05-15 |
| License | MIT |
| Package | `claude-code-templates` v1.28.13 |

## Documents and implementation surfaces inspected

### Upstream docs

| Upstream path | Why it matters |
|---|---|
| `README.md` | Product positioning, quick install, component/template promise. |
| `cli-tool/README.md` | CLI surface: setup, analytics, health check, agents, skills. |
| `cli-tool/docs_to_claude/ARCHITECTURE.md` | Internal modular architecture of the CLI/dashboard system. |
| `cli-tool/docs_to_claude/CLAUDE_DATA_STRUCTURE.md` | Claude Code local data/session format reference for analytics tooling. |
| `cli-tool/docs_to_claude/HOOKS_GUIDE.md` | Claude hooks guide used by the package. |
| `cli-tool/docs_to_claude/COMMANDS_GUIDE.md` | Slash-command packaging pattern. |
| `cli-tool/docs_to_claude/SUBAGENTS_GUIDE.md` and `SUB_AGENTS.md` | Agent/subagent component model. |
| `cli-tool/docs_to_claude/STATUSLINE_GUIDE.md` | Claude statusline setting pattern. |
| `cli-tool/SKILLS_DASHBOARD.md` | Skills dashboard/reference surface. |

### Upstream code surfaces

| Upstream path | Why it matters |
|---|---|
| `cli-tool/bin/create-claude-config.js` | Main executable and option surface. |
| `cli-tool/src/index.js` | Orchestrates setup, individual component install, dashboards, health checks. |
| `cli-tool/src/templates.js` | Template selection and file projection model. |
| `cli-tool/src/file-operations.js` | GitHub raw download, retry/cache, backup, merge, post-install validation. |
| `cli-tool/src/agents.js` | Scans and installs Claude agents into `.claude/agents`. |
| `cli-tool/src/command-scanner.js` | Scans command Markdown and extracts display metadata. |
| `cli-tool/src/hook-scanner.js` | Extracts and filters Claude `settings.json` hooks. |
| `cli-tool/components/{agents,commands,hooks,mcps,settings,skills}` | Marketplace-style component inventory. |
| `cli-tool/templates/{common,javascript-typescript,python,ruby,...}` | Language/framework template files emitted into projects. |

### Cognitive OS docs and surfaces compared

| COS path | Why it matters |
|---|---|
| `scripts/cos_init.py` | Current author-once/project-many harness projector. |
| `install.sh` | Top-level install UX; currently narrower than `cos_init.py` for harness options. |
| `manifests/harness-projection.yaml` | Proof-level matrix for Claude, Codex, Cursor, opencode, structural harnesses, and planned harnesses. |
| `manifests/primitive-projection-profiles.yaml` | Primitive projection profile intent. |
| `manifests/harness-driver-capabilities.yaml` | Driver capability model. |
| `docs/04-Concepts/architecture/ide-agnostic-primitive-projection.md` | IDE-agnostic projection architecture. |
| `docs/04-Concepts/architecture/consumer-project-primitive-accessibility.md` | Consumer-project accessibility contract. |
| `docs/04-Concepts/architecture/portable-ai-consumer-package-spec.md` | Consumer `.ai` package surface. |
| `docs/06-Daily/reports/external-tools-radar-portable-primitives-addendum-2026-05-09.md` | Existing portable primitive radar baseline. |
| `tests/behavior/test_consumer_project_projection.py` | Structural projection proof across supported harnesses. |
| `tests/integration/test_installer.py` | Top-level installer smoke tests for Claude/Codex. |

## Findings

### 1. Upstream is Claude-native, not harness-agnostic

`claude-code-templates` is strongest as a Claude Code marketplace and setup CLI.
It installs directly into Claude surfaces such as `.claude/agents`,
`.claude/commands`, `.claude/settings.json`, `CLAUDE.md`, and `.mcp.json`.
That is useful for Claude DX, but it is not a canonical primitive registry with
loss-aware projection into multiple IDEs.

### 2. Cognitive OS has the stronger abstraction for the requested product

Cognitive OS keeps primitive truth under `.cognitive-os/` and projects to
harness-specific files. That is the right shape for agnostic primitives:

- Claude uses native settings and Claude-specific skill/rule projections.
- Codex uses `.codex/hooks.json` and avoids leaking `.claude/CLAUDE.md`.
- Structural IDEs receive instruction/rule/skill references with explicit proof
  boundaries.
- `manifests/harness-projection.yaml` records proof levels instead of claiming
  universal lifecycle parity.

### 3. Upstream has better component-marketplace UX

The upstream CLI supports individual install flags for agents, commands, MCPs,
settings, hooks, and skills. Cognitive OS should copy this product pattern, but
not its Claude-first storage model. The COS equivalent should be a canonical
primitive catalog plus harness-aware projection profiles.

### 4. Top-level COS install UX is the current mismatch

`cos_init.py` already supports many harnesses, but `install.sh` still exposes and
validates mostly `claude|codex`. That makes the product look less multi-IDE than
the internal projector already is.

### 5. Devin remains a signed gap

`manifests/harness-projection.yaml` marks Devin as planned, not implemented.
If the product claim is "each IDE", Devin needs a projection driver, proof
level, and consumer smoke before it is claimed.

## Verdict

**ASSESS / extract installer UX and marketplace patterns. Do not adopt runtime or
storage model.**

The Cognitive OS architecture is correct for agnostic primitive projection. The
next improvement is not to become Claude-native; it is to give the existing
harness projector a better public installer/catalog UX.

## Extractable patterns

| Pattern | Adopt? | COS destination |
|---|---:|---|
| Individual component installation flags | Yes, clean-room | Future `cos install primitive ... --harness ...` UX. |
| Backup/merge/conflict handling for generated files | Yes, clean-room | `install.sh` / `cos_init.py` projection writer. |
| GitHub/raw download retry/cache shape | Maybe | Only for optional remote catalogs, not default bootstrap. |
| Component dashboards/health checks | Maybe | Wrap existing COS audits in simpler operator commands. |
| Direct `.claude/*` as source of truth | No | Keep `.cognitive-os/*` canonical. |
| Marketplace bulk import of skills/agents | No by default | Gate through license, credentials, and primitive-authoring review. |

## Recommended next actions

1. Expand `install.sh --harness` to accept the same harness set as
   `scripts/cos_init.py`, or delegate validation to `cos_init.py`.
2. Add a canonical primitive catalog UX inspired by the upstream component flags.
3. Keep `.claude` as a projection target only.
4. Add/refresh consumer smokes for any new harness driver before public claims.
5. Implement Devin only after its project-local rule/MCP surfaces are signed.
