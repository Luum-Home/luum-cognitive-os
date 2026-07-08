---
type: reference-synthesis
source: docs/08-References/business/open-source-design.md
provenance: "Designs how to extract a universal, domain-agnostic Agent Operating System core out of a real-world fintech platform's `.claude/` directory, separating core/plugin/project-specific files and defining the FSL-1.1-MIT licensing posture."
---

## What it is

A framework design document proposing a `core/` + `plugins/` + `generators/`
repository structure for a source-available Cognitive OS, including a
complete file-by-file audit of an existing project's `.claude/` directory
(rules, hooks, skills, agents, commands) classified as CORE, PLUGIN, PROJECT-
SPECIFIC, GENERATED, or RUNTIME, plus the `cognitive-os init` command flow,
plugin system design, parameterization requirements, and the FSL-1.1-MIT
licensing decision.

## Key mechanics

- **Five design principles**: core is domain-agnostic (no company/fintech/
  stack references in `core/`), plugins are optional layers, project config
  is generated not copied, parameterize don't hardcode
  (`$CLAUDE_PROJECT_DIR`, `$COGNITIVE_OS_CONFIG`), progressive adoption
  (each subsystem works independently, e.g. installing only `core/memory`).
- **Repository structure**: `core/` (memory, workflow/sdd, workflow/openspec,
  fault-tolerance, model-evaluation, discipline, skill-system, safety,
  agents, orchestrator) + `plugins/` (fintech, ecommerce, saas, mobile, each
  with `plugin.yaml`) + `generators/` (init.sh, detect-stack.sh, generate-*.sh
  + templates) + top-level `install.sh`/`uninstall.sh`/`LICENSE`.
- **File audit tables** (§3) classify every rule/hook/skill/agent/command
  file from an existing `.claude/` directory: e.g. `rules/fault-tolerance.md`
  → CORE (no parameterization needed), `rules/constitutional-gates.md` →
  PLUGIN (fintech), `rules/architecture.md` → stays PROJECT-SPECIFIC.
- **`cognitive-os init` flow** (§4): 7-step interactive flow — detect stack,
  select domain plugin, install core primitives, install plugin, generate
  project-specific hooks, generate health-check skill from
  `docker-compose.yml`, generate `CLAUDE.md`/`settings.json`. Config is
  written to `.claude/cognitive-os.yaml`.
- **Plugin system** (§5): `plugin.yaml` manifest schema, flat dependency
  model (plugins depend only on core, never on other plugins — avoids
  diamond-dependency problems), lifecycle CLI (`add`/`remove`/`list`/
  `update`/`create`), two-source registry (built-in + community Git repos).
- **Core vs Plugin vs Project-specific boundary rationale** (§7): core =
  works on any project, no business-rule references, removing it breaks the
  runtime, solves a universal AI-session problem. Plugin = domain-specific
  business rules/personas, removable without breaking core. Project-specific
  = references specific services/ports/credentials for this one project.
- **Three numbered ADRs proposed inline** (§10): ADR-001 Flat Plugin Model
  (no plugin-to-plugin deps), ADR-002 File Copy Over Symlinks (copy during
  install, track source version for updates), ADR-003 YAML Configuration
  Over Environment Variables (single `cognitive-os.yaml` source of truth). All
  three carry **Status: Proposed** in the document.
- **Later addendum**: documents the actual 2026-05-07 orchestration substrate
  landing (ADR-220/221/222/223/226/227/228/230, table of 14 ADRs with pillar/
  code-surface mapping) as "load-bearing for the OSS surface," explicitly
  listing honest pendings (T6 single-platform perf, T7 partial chaos
  coverage, T8 event-bus-only cross-harness, T9/T10 pending).
- **Licensing decision**: FSL-1.1-MIT (Functional Source License with MIT
  Future) — source-available with a temporary Sell limitation preventing
  hyperscaler-hosted resale, auto-converts to MIT after the Change Date.
  Explicitly notes ADR-004 is a tombstone/reserved slot, not the canonical
  license ADR.

## Relations & where used

- The historical naming note at the top of the document itself flags
  terminology drift: "open source" language throughout the body predates the
  current FSL-1.1-MIT public posture and should be read as "source-available
  before MIT conversion."
- The §10 orchestration-substrate addendum duplicates and cross-references
  the same ADR-220–236 material documented in `master-plan-checklist.md` §9
  and `master-plan-execution-requirements.md`'s post-2026-05-07 sequence
  update.
- The core/plugin/project-specific classification directly informed the
  `docs/product-zones.md` / `manifests/product-zones.yaml` taxonomy referenced
  throughout `feature-reality-audit.md` and `master-plan-checklist.md`.

## Status / caveats

- **Internal inconsistency, not fixed here**: ADR-001/002/003 in §10 are
  design proposals with explicit `Status: Proposed`, meaning as written in
  this document they were never marked Accepted — yet the document treats
  their decisions (flat plugin model, copy-not-symlink, YAML config) as
  settled design throughout the earlier sections (§2, §5, §7) without
  qualification. Readers should not assume Proposed-status decisions are
  binding without checking the canonical ADR store.
- Document mixes two very different time horizons in one file: an early
  "extract an OSS framework from a monorepo" plan (§1–9, using illustrative
  bash/YAML examples that were not necessarily ever executed as literally
  shown) and a later, evidence-backed orchestration-substrate status report
  (§10 addendum). Treat §1–9 as design intent/historical snapshot and the
  §10 addendum as the more current, verifiable status.
- The document itself flags its own naming drift (see provenance) — this is
  documented self-awareness, not an unflagged inconsistency.
