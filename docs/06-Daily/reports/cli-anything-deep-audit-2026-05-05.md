# CLI-Anything Deep Audit — Source-Level

**Date**: 2026-05-05
**Status**: research-only — no adoption decision yet.
**Trigger**: previous primitives audit identified HKUDS/CLI-Anything as the credible "primitive manager"; user requested deep source-level inspection before any adoption.

---

## TL;DR

- **Q1**: SKILL.md generation is deterministic, not LLM-based — a Python script parses Click decorators via regex from the harness source and renders a Jinja2 template; no LLM in the loop.
- **Q2**: The catalog is two flat JSON files (`registry.json` + `public_registry.json`) served as GitHub Pages from the HKUDS monorepo; no signing, no graph DB, per-CLI versioning via a `version` field, catalog-wide `updated` date.
- **Q3**: `cli-hub install <name>` fetches the merged registries (1-hour TTL cache), resolves `install_strategy` (pip/npm/uv/bundled), and runs the install command via subprocess — no signing, no sandbox, no semantic discovery.
- **Q4**: Contributor opens a PR to the HKUDS monorepo adding an entry to `registry.json`; merged to `main` → GitHub Pages updates immediately; no automated curation gate; single-org control; no self-hosted option in source.
- **Recommendation**: **pattern-only** — adopt the YAML-frontmatter + `## Command Groups` table convention for COS skill files; do not adopt the tooling or catalog infrastructure.

---

## Methodology

Read the following files via `gh api repos/HKUDS/CLI-Anything/contents/<path>` with base64 decode:

- `registry.json` and `public_registry.json` (catalog schema)
- `CONTRIBUTING.md` (publishing flow)
- `cli-anything-plugin/skill_generator.py` (generation code path, full source)
- `cli-anything-plugin/templates/SKILL.md.template` (Jinja2 template)
- `cli-anything-plugin/PUBLISHING.md` (distribution options)
- `cli-hub/cli_hub/cli.py` (discovery CLI entry point)
- `cli-hub/cli_hub/registry.py` (registry fetch + merge)
- `cli-hub/cli_hub/installer.py` (install dispatch)
- `skill_generation/tests/test_skill_path.py` (confirms layout contract)
- `cli-hub-meta-skill/SKILL.md` (agent-facing skill description)
- `skills/README.md` (canonical vs. compatibility SKILL.md layout)
- `skills/cli-anything-blender/SKILL.md` (representative published skill)

No repo clone. No WebFetch (source reading was sufficient).

---

## Architecture map

```
CONTRIBUTOR FLOW
================
Contributor writes <software>/agent-harness/
  └── cli_anything/<software>/<software>_cli.py   ← Click groups/commands
  └── cli_anything/<software>/README.md            ← intro text
  └── setup.py                                     ← version
  └── cli_anything/<software>/skills/SKILL.md      ← (compatibility copy)

scripts/skill_generator.py (cli-anything-plugin/skill_generator.py)
  extract_cli_metadata(harness_path)
    ├── parse README.md   → intro, system_package
    ├── parse setup.py    → version (regex)
    └── parse *_cli.py    → CommandGroup[] (regex on @xxx.group / @xxx.command)
  generate_skill_md(metadata)
    └── render templates/SKILL.md.template (Jinja2)
  → writes to:
    skills/cli-anything-<software>/SKILL.md        ← canonical repo-root copy
    <harness>/cli_anything/<software>/skills/SKILL.md ← pip-packaged runtime copy

Contributor adds entry to registry.json → opens PR → merged to main
GitHub Pages auto-publishes:
  hkuds.github.io/CLI-Anything/registry.json
  hkuds.github.io/CLI-Anything/public_registry.json


AGENT DISCOVERY FLOW
====================
Agent runs: cli-hub list / cli-hub search / cli-hub install

cli-hub/cli_hub/registry.py
  fetch_all_clis()
    ├── fetch_registry()        → GET hkuds.github.io/CLI-Anything/registry.json
    │     (cache: ~/.cli-hub/registry_cache.json, TTL 3600s)
    └── fetch_public_registry() → GET hkuds.github.io/CLI-Anything/public_registry.json
         (cache: ~/.cli-hub/public_registry_cache.json)
  merge both → tag each with _source: "harness" | "public"

cli-hub/cli_hub/cli.py
  cli-hub search <query>
    search_clis(query) → substring match on name/description/category/display_name

cli-hub install <name>
  installer.py::install_cli(name)
    ├── get_cli(name)            → registry lookup (case-insensitive)
    ├── _install_strategy(cli)   → pip | npm | uv | bundled | command
    └── subprocess.run(install_cmd)  ← shell=True when cmd contains | && ;
  tracks installs in ~/.cli-hub/installed.json

SKILL.md surface (separate from cli-hub):
  npx skills add HKUDS/CLI-Anything           ← external `skills` npm package
  reads skills/<skill-id>/SKILL.md from repo root
  ReplSkin (repl_skin.py) auto-detects skills/SKILL.md at runtime from __file__
```

---

## Q1 — How is `SKILL.md` generated?

**Deterministic static analysis — no LLM involved.**

Entry point: `cli-anything-plugin/skill_generator.py`, function `generate_skill_file(harness_path)`.

**Step 1 — `extract_cli_metadata(harness_path)`**

Reads three files from a harness directory:

1. `cli_anything/<software>/README.md` — extracts the first paragraph after the `# Title` heading as `skill_intro`; scans for `` `apt install <pkg>` `` / `` `brew install <pkg>` `` patterns via regex to populate `system_package`.

2. `setup.py` — extracts `version` with a regex that captures the value assigned to the `version` keyword.

3. `cli_anything/<software>/<software>_cli.py` — `extract_commands_from_cli()` runs two regex passes:
   - `@xxx.group(...)` followed by `def yyy(...):` and an optional docstring → produces `CommandGroup[]`
   - `@xxx.command(...)` followed by `def yyy(...):` and an optional docstring → populates commands into matching groups

   The regex uses `re.DOTALL` to handle multi-line decorators. No AST parsing; no subprocess invocation of `--help`.

**Step 2 — `generate_examples(software_name, command_groups)`**

Produces three boilerplate examples (new project, REPL, export-if-export-group-exists). These are generic templates, not introspected from actual CLI behavior.

**Step 3 — `generate_skill_md(metadata)`**

Renders `cli-anything-plugin/templates/SKILL.md.template` (Jinja2). If Jinja2 is unavailable, falls back to `generate_skill_md_simple()` which string-concatenates the same structure. The template is a fixed layout: YAML frontmatter → installation → usage → `## Command Groups` (table per group) → examples → state management → output formats → AI guidance.

**Step 4 — output**

Writes to:
- `skills/cli-anything-<software>/SKILL.md` — canonical repo-root copy (used by `npx skills`)
- `<harness>/cli_anything/<software>/skills/SKILL.md` — runtime copy shipped inside the pip package, auto-detected by `ReplSkin.__init__` via `Path(__file__).parent / "../skills/SKILL.md"` relative resolution

**Key finding**: The generator produces correct structural output only when the harness author writes proper Click docstrings. Undocumented commands produce rows like `| \`cmd-name\` | Execute cmd_name operation. |` (the fallback string). Quality of SKILL.md is proportional to harness code quality, not to any AI analysis.

---

## Q2 — Catalog format at clianything.cc

The catalog is **two flat JSON files** committed to the HKUDS/CLI-Anything monorepo and served via GitHub Pages at `hkuds.github.io/CLI-Anything/`.

### Harness registry (`registry.json`)

Schema (all fields required per CONTRIBUTING.md):

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | lowercase, unique identifier |
| `display_name` | string | human-readable |
| `version` | string | semver, per-CLI |
| `description` | string | one-line |
| `requires` | string\|null | runtime deps |
| `homepage` | string | upstream software URL |
| `source_url` | string\|null | null for in-repo harnesses |
| `install_cmd` | string | full `pip install ...` command |
| `entry_point` | string | CLI binary name |
| `skill_md` | string\|null | relative path under `skills/` for in-repo; full URL for standalone |
| `category` | string | one of existing enum values |
| `contributors` | array | `[{name, url}]` |

Outer envelope: `{meta: {repo, description, updated}, clis: [...]}`.

### Public registry (`public_registry.json`)

Same outer envelope. Extended per-CLI fields:

| Field | Notes |
|-------|-------|
| `package_manager` | "npm" \| "uv" \| "bundled" |
| `npm_package` | e.g. `"@larksuite/cli"` |
| `npx_cmd` | e.g. `"npx @larksuite/cli"` |
| `install_notes` | human note |
| `uninstall_cmd` | explicit uninstall |
| `update_cmd` | explicit update |

### Storage and versioning

- **Storage**: static JSON files in the git repository, served via GitHub Pages. No database, no graph, no S3 (despite the live catalog URL in the meta-skill pointing to a DigitalOcean Spaces CDN — that is a separately maintained aggregated SKILL.md, not the JSON catalog).
- **Versioning**: per-CLI `version` semver field updated manually in PRs; catalog-wide `updated` date in `meta` section. No per-skill version history; catalog state is the git history of `registry.json`.
- **Signing/verification**: none — no checksums, no GPG, no SLSA provenance.

---

## Q3 — Skill discovery flow

**There are two distinct discovery surfaces, often conflated.**

### Surface A: `cli-hub` (Python package manager)

`cli-hub` is a `pip install cli-anything-hub` package. Its CLI (`cli-hub/cli_hub/cli.py`) provides:

- `cli-hub list [--category] [--source]` — lists all available CLIs
- `cli-hub search <query>` — substring search across name/description/category/display_name
- `cli-hub install <name>` — installs by name
- `cli-hub info <name>` — shows detail

**Registry fetch** (`cli-hub/cli_hub/registry.py`):
1. GET `https://hkuds.github.io/CLI-Anything/registry.json`
2. GET `https://hkuds.github.io/CLI-Anything/public_registry.json`
3. Merge; tag each entry `_source: "harness" | "public"`
4. Cache both to `~/.cli-hub/*.json` with 1-hour TTL

**Discovery dimensions**: only substring text search. No semantic similarity, no toolchain detection, no project-requirements analysis.

**Install dispatch** (`cli-hub/cli_hub/installer.py`):
- Strategy resolution: `pip` (harness CLIs) → `subprocess([sys.executable, "-m", "pip", "install", ...])`
- `npm` → `subprocess([npm, "install", "-g", npm_package])`
- `uv` → `subprocess(install_cmd)`
- `command` / `bundled` → generic dispatch

**Trust contract**: none. The `install_cmd` from the registry is executed directly. The comment in `installer.py` notes: "Commands come from the trusted registry, not from user input" — trust is implicit, based on registry control by HKUDS. No package digest pinning, no sandbox, no capability restriction.

**Install tracking**: `~/.cli-hub/installed.json` — local JSON dict keyed by CLI name.

### Surface B: `npx skills` (npm package, external)

The `skills/README.md` shows the usage:
```bash
npx skills add HKUDS/CLI-Anything --list
npx skills add HKUDS/CLI-Anything --skill cli-anything-audacity -g -y
```

This uses a separate npm package `skills` (not hosted in this repo). It reads the `skills/` directory tree from the GitHub repo. At runtime, `ReplSkin` (in `cli-anything-plugin/repl_skin.py`) auto-detects `skills/SKILL.md` relative to its own `__file__` location — confirmed by `skill_generation/tests/test_skill_path.py`.

---

## Q4 — Publishing flow

### In-repo harness (Option A)

1. Contributor forks HKUDS/CLI-Anything and creates a branch.
2. Adds `<software>/agent-harness/` with Python package structure (Click CLI, tests, setup.py).
3. Runs `skill_generator.py` to produce `skills/cli-anything-<software>/SKILL.md`.
4. Adds entry to `registry.json` at repo root.
5. Opens PR against `main`. PR must: pass existing tests, include unit tests (`test_core.py`) and E2E tests (`test_full_e2e.py`), update README.
6. HKUDS maintainers review via standard GitHub PR. No automated curation gate described in source.
7. On merge to `main`, GitHub Pages serves the updated `registry.json` immediately.

**Version bumping**: contributor manually bumps `version` in `registry.json` entry when modifying a harness.

### Standalone repo (Option B)

Contributor hosts CLI in their own repo, publishes to PyPI or a git URL, and opens a **registry-only PR** to HKUDS/CLI-Anything adding a single `registry.json` entry with `source_url` pointing to their repo.

### Control and federation

- Single org: HKUDS controls the canonical `registry.json` and `public_registry.json`.
- No federated registry, no self-hosted option, no offline mirror described in any source file.
- The `public_registry.json` can list third-party CLIs (npm packages from e.g. `larksuite`, `WeComTeam`) but the registry file itself still lives in the HKUDS monorepo.

---

## Fit with Cognitive OS

| CLI-Anything concept | COS equivalent | Overlap / Conflict |
|---------------------|----------------|-------------------|
| `skills/<id>/SKILL.md` — YAML frontmatter + `## Command Groups` markdown | `skills/<name>/SKILL.md` — same layout, same YAML frontmatter convention | **Direct overlap**. COS already uses this exact format. |
| `registry.json` — flat JSON with name/version/description/install_cmd/skill_md/category | COS `skills/CATALOG.md` + `CATALOG-COMPACT.md` — markdown tables auto-generated by `scripts/generate_compact_catalog.py` | Conceptually similar; COS catalog is markdown not JSON; COS has no install_cmd field (skills are not pip packages). |
| `skill_generator.py` — deterministic regex-based generator from Click source | COS `skills/skill-creator/SKILL.md` skill — LLM-assisted skill authoring via the `skill-creator` skill | Different approach. COS uses LLM; CLI-Anything uses static analysis of Click decorators. |
| `cli-hub search <query>` — substring text search over registry | COS `skill_router.best_match(message)` — semantic routing (inferred from CLAUDE.md references) | CLI-Anything's search is weaker; COS routing is intent-based. No conflict, no reuse opportunity. |
| `npx skills add <repo>` — pull SKILL.md files from a GitHub tree | COS has no equivalent primitive for pulling external skills | **Gap in COS** — if COS wanted to consume external skill catalogs, this pattern is worth studying. |
| No signing, no sandbox on install | COS `agent-security` rule: TTL 120min, blocks `.env`/`*.key`/secrets; `supply-chain-defense`: digest pinning | **Conflict**. CLI-Anything's trust model (implicit registry trust, shell=True subprocess) is incompatible with COS security rules. |

---

## Adoption recommendation

**pattern-only**

CLI-Anything is a well-structured open-source project, not a general-purpose primitive substrate. Its value to COS is confined to two conventions already partially implemented in COS:

1. **SKILL.md format contract**: YAML frontmatter with `name` and `description` fields, followed by `## Command Groups` markdown tables. This is already COS's format. CLI-Anything validates the convention is useful to others and provides a concrete schema to reference when authoring COS skills for CLI-wrapping use cases. No code adoption needed.

2. **Registry JSON schema**: the `registry.json` field set (name/display_name/version/description/requires/homepage/install_cmd/entry_point/skill_md/category/contributors) is clean and worth referencing if COS ever needs to expose its skill catalog as a machine-readable JSON for external consumers. Currently COS uses markdown; the CLI-Anything schema would be a good starting point for a `skills/CATALOG.json` if that were ever needed.

**Why not adopt-as-substrate or fork-and-extend**: The tooling is tightly coupled to Python/Click harnesses. COS skills are not pip packages, have no `install_cmd`, and are author-written markdown files rather than generated artifacts. The discovery mechanism (substring search over flat JSON) is inferior to COS's intent-based routing. The trust contract (no signing, no sandbox, shell=True) conflicts with COS's supply-chain-defense and agent-security rules. Wrapping CLI-Anything as a COS substrate would require replacing its catalog, its install model, and its security model — at which point nothing meaningful remains.

**Concrete first step if the user wants to proceed with pattern adoption**: audit `skills/add-skill/SKILL.md` against the CLI-Anything SKILL.md template (`cli-anything-plugin/templates/SKILL.md.template`) and confirm COS's frontmatter fields are a superset. Add a note to `rules/` or CONTRIBUTING that the `## Command Groups` table format is the canonical CLI-wrapping pattern in COS.

**Falsifiable guard**: if COS adopts the convention, run `skill_generation/tests/test_skill_path.py`-equivalent assertions (frontmatter present, `## Command Groups` section present, at least one filled command row) as part of COS's audit tests for any CLI-wrapping skill.

---

## Open questions / blockers

1. **`npx skills` npm package not in this repo**: the `skills add HKUDS/CLI-Anything` surface depends on a separate npm package `skills` not hosted in HKUDS/CLI-Anything. Its source was not located within the tool budget. Whether it does any trust verification or sandboxing on download is unknown.

2. **DigitalOcean Spaces live catalog**: `cli-hub-meta-skill/SKILL.md` references `https://reeceyang.sgp1.cdn.digitaloceanspaces.com/SKILL.md` as a live auto-updated catalog. How this CDN file is generated, signed, or versioned was not investigated — it may be a separate aggregation pipeline not visible in the monorepo.

3. **Curation gate not codified**: CONTRIBUTING.md describes PR requirements (tests, README, registry entry) but does not describe any automated CI check that blocks merge if requirements are missing. Whether the HKUDS CI enforces these requirements was not verified.

4. **Self-hosted option**: PUBLISHING.md describes four distribution options for the Claude Code plugin, but none address self-hosting the CLI-Hub registry itself. An organization wanting a private catalog would need to host their own GitHub Pages equivalent and point `REGISTRY_URL` / `PUBLIC_REGISTRY_URL` constants in `registry.py` at it — this is structurally possible but not documented.

---

## Sources

- `https://github.com/HKUDS/CLI-Anything` — repo root (metadata, license)
- `https://github.com/HKUDS/CLI-Anything/blob/main/registry.json`
- `https://github.com/HKUDS/CLI-Anything/blob/main/public_registry.json`
- `https://github.com/HKUDS/CLI-Anything/blob/main/CONTRIBUTING.md`
- `https://github.com/HKUDS/CLI-Anything/blob/main/cli-anything-plugin/skill_generator.py`
- `https://github.com/HKUDS/CLI-Anything/blob/main/cli-anything-plugin/templates/SKILL.md.template`
- `https://github.com/HKUDS/CLI-Anything/blob/main/cli-anything-plugin/PUBLISHING.md`
- `https://github.com/HKUDS/CLI-Anything/blob/main/cli-hub/cli_hub/cli.py`
- `https://github.com/HKUDS/CLI-Anything/blob/main/cli-hub/cli_hub/registry.py`
- `https://github.com/HKUDS/CLI-Anything/blob/main/cli-hub/cli_hub/installer.py`
- `https://github.com/HKUDS/CLI-Anything/blob/main/skill_generation/tests/test_skill_path.py`
- `https://github.com/HKUDS/CLI-Anything/blob/main/cli-hub-meta-skill/SKILL.md`
- `https://github.com/HKUDS/CLI-Anything/blob/main/skills/README.md`
- `https://github.com/HKUDS/CLI-Anything/blob/main/skills/cli-anything-blender/SKILL.md`
