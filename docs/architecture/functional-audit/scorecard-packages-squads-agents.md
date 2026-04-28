# Scorecard: Packages, Squads, Agents

**Audit date**: 2026-04-16
**Phase**: reconstruction (empirical, no fixing)
**Project root**: `<repo-root>`

## Executive Summary

| Category | Count | Integrated | Standalone | Orphan / Code-Dead |
|----------|-------|------------|------------|---------------------|
| Packages | 32 | 10 (symlink into `lib/`) | 21 (own files, docs present) | 1 (`mcp-server` — manifest only, no README) |
| Squads   | 5 YAML (4 team squads + 1 org) | 0 runtime-wired | 5 declarative-only (flat-symlinked to `.cognitive-os/squads/`) | 0 |
| Agents   | 3 MD files | 1 (`test-coverage-enforcer` has trigger frontmatter) | 2 (declarative-only MD guides) | 0 |

Symlinks in `lib/`: **42** (matches project-gotchas.md expectation `>40`). All resolve.

---

## 1. Packages Audit

32 directories under `packages/`. 31 have both `cos-package.yaml` and `README.md`. `mcp-server/` has `cos-package.yaml` only (no README, no SKILL.md, no skills/rules/hooks subdirs) — minimal stub.

### Classification

**Integrated (files symlinked into `lib/`)** — 10 packages:
Verified by inspecting `lib/` — 42 symlinks pointing into `../packages/<name>/lib/*.py`:

| Package | lib symlinks observed |
|---------|----------------------|
| agent-coordination | `agent_bus.py`, `agent_dashboard.py`, `file_lock_registry.py` |
| agent-lifecycle | `agent_permissions.py`, `batch_runner.py` |
| context-optimization | `capability_levels.py` |
| recall-search | `cognee_client.py` |
| scope-governance | `cost_predictor.py`, `estimation_calibrator.py` |
| verification-audit | `cross_verifier.py`, `error_classifier.py`, `error_matching.py` |
| sdd-compound | `domain_router.py` |
| usage-monitor | `claude_usage_reader.py` |
| paperclip-integration | (hook `paperclip-squad-sync.sh` referenced in runtime) |
| ecosystem-tools | `paperclip_client`, `jupyter_client`, etc. referenced via `lib/singularity.py`, `lib/model_router.py`, `lib/gateway_selector.py` — but note: `paperclip_client.py`, `jupyter_client.py`, `litellm_client.py`, `webhook_trigger.py` are in `_wiring-allowlist.txt` (intentionally not yet wired) |

**Standalone (files NOT symlinked into `lib/`, but own self-contained skills/rules/hooks + docs)** — 21 packages:
- adaptive-workflow, advisor-mcp, aguara-security, auto-repair-rollback, consequence-system, cos-index, document-sync, dry-run-simulation, e2b-sandbox, engram-sync, infra-lifecycle, mantis-security, prompt-quality-gate, privacy-mode, project-audit, project-discovery, quality-gates, sdd-compound (additional skills), session-parser, skill-governance, task-management, tero-testing

These carry their own `SKILL.md`, `rules/*.md`, `hooks/*.sh` files. Several have been symlinked into the project's top-level `skills/`, `rules/`, `hooks/` via `hooks/self-install.sh` (`SYNC_DIRS` config). The installer is the integration vector, not Python imports.

**Orphan / code-dead** — 1 package:
- **mcp-server/** — has only `cos-package.yaml` manifest. No README, no `SKILL.md`, no skills/rules/hooks subdirs. Minimal stub — likely a placeholder for a future MCP server package. Passes the "documentation present" test (manifest is documentation-adjacent) but is functionally empty.

### Findings

- **F1 (integration)**: Integration is dominated by symlinks, not Python imports. `lib/` contains 42 symlinks into `packages/*/lib/`. There is no Python package index (no `pyproject.toml` or `setup.py` entry per package; all packages lean on the symlink scheme).
- **F2 (allowlist ratchet)**: `lib/_wiring-allowlist.txt` documents 18 modules intentionally not-yet-wired (including `batch_runner`, `cognee_client`, `dynamic_tool_creator`, `file_lock_registry`, `webhook_trigger`). These count as integrated-but-dormant.
- **F3 (minimal stub)**: `packages/mcp-server/` is the only package without a README (only `cos-package.yaml` present). Verified 32 package dirs total — filesystem is fine; `mcp-server` appears to be a placeholder.
- **F4 (package registry)**: `packages/cos-index/` maintains an `index/packages.yaml` master registry. Used by `cos search`. All 32 packages (including `mcp-server`) have a `cos-package.yaml` manifest.

---

## 2. Squads Audit

5 YAML files under `squads/`:
- `organization.yaml` (kind: Organization — defines 6 named agents incl. engineering-manager-agent, backend-architect, test-coverage-enforcer, security-engineer, sre-agent, devops-agent)
- `infra-team.yaml` (kind: Squad)
- `mobile-team.yaml` (kind: Squad)
- `payments-team.yaml` (kind: Squad)
- `platform-team.yaml` (kind: Squad)

### Wiring Verification

- **Loader / parser in Python**: NONE. `grep "Squad|squad_loader|load.*squad"` across `lib/` found only `lib/repo_analyzer.py:444` (a string literal listing "Squad Protocol" as a rule name). No YAML parser, no Pydantic model, no runtime instantiation.
- **Hook references**: 2 hooks touch squads:
  1. `hooks/self-install.sh` line 39: `"squads|cos|flat|*.yaml"` — flat-symlinks `squads/*.yaml` into `.cognitive-os/squads/`.
  2. `hooks/inject-phase-context.sh` line 86: `SQUADS_DIR="$COGNITIVE_OS_DIR/squads"` — defines the path but no runtime parsing shown in the 20-line snippet.
  3. `hooks/cognitive-os-health.sh` line 70: counts `find "$AOS/squads" -name '*.yaml' | wc -l` for status display.
- **Skill/rule references**: `rules/squad-protocol.md` describes the squad semantics. `packages/agent-coordination/skills/squad-manager/SKILL.md` and `packages/paperclip-integration/hooks/paperclip-squad-sync.sh` reference squads by concept.
- **Referenced skill `testing-patterns`**: Each squad's `skills:` list contains `testing-patterns`. This skill is NOT present under `skills/` or `packages/*/skills/` (grep finds no directory named `testing-patterns`). Broken reference.

### Classification

| Squad | Classification | Reason |
|-------|----------------|--------|
| organization.yaml | orphan-yaml | No Organization kind parser anywhere. Uses `Organization` API version never resolved. |
| infra-team.yaml | orphan-yaml | Squad kind has no runtime loader; manager `engineering-manager-agent` only exists as a YAML string, not in `agents/*.md`. |
| mobile-team.yaml | orphan-yaml | Same — references `backend-architect` / `test-coverage-enforcer` by name; only `test-coverage-enforcer.md` physically exists. |
| payments-team.yaml | orphan-yaml | Same. |
| platform-team.yaml | orphan-yaml | Same. |

### Findings

- **F5 (no runtime)**: 5/5 squad YAMLs are ornamental. They are copied (symlinked) to `.cognitive-os/squads/` and counted in health reports, but no Python/Go code deserializes them. `repo_analyzer.py` only mentions the string "Squad Protocol" as a rule name label.
- **F6 (broken skill ref)**: Every squad references `skills: [testing-patterns]`. No `testing-patterns` skill exists in the tree. This is a known-broken reference across 5 YAMLs.
- **F7 (broken agentRef)**: Squads reference `backend-architect`, `security-engineer`, `sre-agent`, `devops-agent`, `engineering-manager-agent`. None exist as physical agent MD files under `agents/`. Only `test-coverage-enforcer` has a concrete MD file.
- **F8 (template comments)**: All 4 squad YAMLs (not organization.yaml) carry `repos: []  # Add your ... repos here` — they are **example templates meant to be customized per project**, not active runtime squads. This is consistent with the "plug-and-play" design per `docs/plug-and-play.md`.

---

## 3. Agents Audit

3 MD files under `agents/`:
- `service-health-checker.md` (frontmatter: `model: sonnet` only)
- `stack-validator.md` (frontmatter: `model: sonnet` only)
- `test-coverage-enforcer.md` (frontmatter: `name`, `description`, `triggers` — most structured)

### Wiring Verification

- **Loader / parser in Python**: NONE. `grep "agents/|AgentDef|agent_loader"` found only `lib/consequence_engine.py`.
- **Hook references**: `hooks/self-install.sh` line 41 `"agents|cos|flat|*.md"` — flat-symlinks `agents/*.md` into `.cognitive-os/agents/`.
- **Trigger file patterns**: `test-coverage-enforcer.md` declares `triggers: [file_pattern: "**/*.go", exclude: [...]]` but no hook scans for frontmatter triggers on file edits. Searched `hooks/` — no `trigger:` or frontmatter-parser found.
- **Squad references**: The 3 agent MD files are NOT referenced by any of the 5 squad YAMLs (squads reference `test-coverage-enforcer` which resolves by name to the MD file, but only as a string).

### Classification

| Agent | Classification | Reason |
|-------|----------------|--------|
| service-health-checker.md | declarative-only | Markdown guide with bash examples. No loader. Referenced by name only in docs (`docs/multi-model-factory.md`, `README.md`, `AGENTS.md`). |
| stack-validator.md | declarative-only | Same — markdown guide, no runtime dispatcher. |
| test-coverage-enforcer.md | declarative-only (with trigger metadata) | Has most structured frontmatter (name + triggers) but no code reads the triggers. Referenced by 3 squad YAMLs but purely as a name string. |

### Findings

- **F9 (no dispatcher)**: None of the 3 agents are runtime-wired. They are human-readable guides, symlinked into `.cognitive-os/agents/`, surfaced in health reports by count.
- **F10 (trigger frontmatter wasted)**: `test-coverage-enforcer.md` defines `triggers` with glob patterns — no hook parses this. The file-modified hook chain (`hooks/` contains file-mutation hooks) does not read agent frontmatter.
- **F11 (model field varies)**: `test-coverage-enforcer.md` has no `model:` in frontmatter; it relies on the squad YAML for model assignment (`claude-sonnet-4-6`). The other two agents hard-code `model: sonnet`. Inconsistent: mixes short aliases (sonnet) with full model IDs (claude-sonnet-4-6) across the agent+squad layer.
- **F12 (only 3 of 6 agents physical)**: The organization.yaml lists 6 named agents (engineering-manager-agent, backend-architect, test-coverage-enforcer, security-engineer, sre-agent, devops-agent). Only 1 (test-coverage-enforcer) has a physical MD file. 3 others (service-health-checker, stack-validator) exist as MD files but are NOT listed in organization.yaml.

---

## Scoring Summary

| Dimension | Packages | Squads | Agents |
|-----------|----------|--------|--------|
| Integrated / runtime-wired | 10/32 (31%) | 0/5 (0%) | 0/3 (0%) |
| Standalone (docs + self-contained) | 21/32 (66%) | 5/5 (template) | 3/3 (human-readable) |
| Orphan / code-dead | 1/32 (3%) | N/A (all are template-shape) | 0/3 |
| Broken cross-references | — | 5 (testing-patterns skill absent, 5 agentRefs absent) | — |

**Overall verdict**: Packages have partial runtime integration via symlinks (roughly a third). Squads and agents are **ornamental YAML/Markdown**: cataloged, counted in health reports, symlinked into place, but no runtime code deserializes them. The intent per `docs/plug-and-play.md` is that squads are user-customized templates, not pre-wired runtime entities. Documentation claim "5 squads, 3 agents wired" per self-hosting-check is **nominal** (file presence), not functional.
