# CLI-Anything Opus Deep Audit — Source-Level Verification (Both Sides)

**Date**: 2026-05-05
**Model**: Claude Opus 4.7 (1M context)
**Status**: research-only — read-only branch session, no code modified
**Trigger**: prior sonnet audit (`cli-anything-deep-audit-2026-05-05.md`) made an unverified claim that COS uses the `## Command Groups` SKILL.md convention. The rebuttal (`cos-side-deep-rebuttal-2026-05-05.md`) corrected it. This Opus audit re-verifies BOTH sides at source level to detect any other false claims and re-issue an adoption recommendation.

---

## TL;DR

- **Q1 (generation)**: CLI-Anything uses **deterministic regex parsing of Click decorators** (no LLM); COS has `auto-skill-generator.sh` that fires on PostToolUse:Agent and templates a SKILL.md from heuristic complexity detection. Different inputs (CLI source code vs. agent task transcript), different methods (static analysis vs. shell heuristics). **No overlap, no extraction value.**
- **Q2 (catalog)**: CLI-Anything = two flat `registry.json` / `public_registry.json` files served via GitHub Pages (no signing, manual semver). COS = `manifests/agentic-primitive-registry.lock.yaml` with **154 primitives, each SHA-256 locked**, plus `lifecycle_state` and `projection_targets`. **COS catalog is structurally stronger.**
- **Q3 (discovery)**: CLI-Anything = `cli-hub search` substring match + `cli-hub install` running install_cmd via subprocess (shell=True allowed). COS = `lib/skill_router.py` regex-pattern intent matcher + 21-harness `cos_init.py` projection. **Different problem domains; no extraction value.**
- **Q4 (publishing)**: CLI-Anything = PR to HKUDS monorepo, no automated curation gate, single-org control. COS = author writes SKILL.md, registry lock regenerated with sha256, projection re-runs. **COS publishing is more disciplined; CLI-Anything is more open.**
- **COS-side false claims found**: 1 confirmed (the `## Command Groups` claim in original sonnet audit; verified zero of 88 SKILL.md files contain it). No other COS-side claims in the rebuttal were found to be wrong.
- **Adoption recommendation**: **REJECT** — no CLI-Anything primitive is net-positive for COS. The only conceivable borrow (per-CLI install metadata schema) is irrelevant because COS skills are not pip packages.

---

## Methodology

For BOTH sides, source-level reading at file:line precision.

### CLI-Anything (read via `gh api repos/HKUDS/CLI-Anything/contents/<path>` with base64 decode)

| File | LOC | Purpose |
|---|---|---|
| `cli-anything-plugin/skill_generator.py` | 547 | Q1 generation logic |
| `cli-hub/cli_hub/registry.py` | 115 | Q2 catalog fetch + Q3 discovery |
| `cli-hub/cli_hub/installer.py` | 373 | Q3 install dispatch |
| `registry.json` | (56 CLIs, 12 fields each) | Q2 schema |

### COS (read directly from working tree)

| File | LOC | Purpose |
|---|---|---|
| `packages/consequence-system/hooks/auto-skill-generator.sh` | 200+ | Q1 COS-side generation |
| `manifests/agentic-primitive-registry.lock.yaml` | 154 entries × ~10 lines | Q2 COS-side catalog |
| `lib/skill_router.py` | head 50 | Q3 COS-side discovery |
| `scripts/cos_init.py` | lines 46–80, 341–473, 938–1208 | Q3+Q4 projection to 21 harnesses |
| `skills/*/SKILL.md` | 88 files (filesystem grep) | Q1 COS section structure verification |

### Falsification budget

For every COS-side claim made in the rebuttal report, run a filesystem check independently. If the check fails, mark CORRECTED. If it passes, mark CONFIRMED.

---

## Q1 — How is SKILL.md generated?

### CLI-Anything side (verified)

`cli-anything-plugin/skill_generator.py` (547 LOC):

1. **`extract_cli_metadata(harness_path)`** scans three files:
   - `cli_anything/<software>/README.md` — first paragraph after `# Title` → `skill_intro`; regex `apt install`/`brew install` → `system_package`
   - `setup.py` — regex extracts `version`
   - `cli_anything/<software>/<software>_cli.py` — `extract_commands_from_cli()` runs two regex passes on `@xxx.group(...)` and `@xxx.command(...)` decorators, with `re.DOTALL`. **No AST parsing. No `--help` invocation. No LLM.**
2. **`generate_skill_md(metadata)`** renders a Jinja2 template at `cli-anything-plugin/templates/SKILL.md.template`. Falls back to string concat if Jinja2 missing.
3. Output written to two paths: canonical `skills/cli-anything-<software>/SKILL.md` (repo root) + runtime `<harness>/cli_anything/<software>/skills/SKILL.md` (pip-shipped).

Key dataclasses confirmed: `CommandInfo`, `CommandGroup`, `Example`, `SkillMetadata` (lines 41–63). Template fixture produces `## Command Groups` tables (one per group).

### COS side (verified)

`packages/consequence-system/hooks/auto-skill-generator.sh` (~200 LOC, symlinked from `hooks/auto-skill-generator.sh`):

1. **PostToolUse:Agent hook** — fires after every `Agent` tool call. Reads stdin JSON with `tool_name`, `tool_input`, `tool_response`.
2. Early-exits on: `tool_name != "Agent"`, errors in response, private-mode flag, `NO_AUTO_SKILL=true`, `tool_uses < 10` (or response < 8000 chars without created-files/fixed-bug heuristic match).
3. Generates a slug from `task_description`, writes `.cognitive-os/skills/auto-generated/<slug>/SKILL.md` with YAML frontmatter (`auto-generated: true`, `version: 0.1.0`), procedure (extracted bullet/numbered list lines from the response), and a result summary.
4. Logs to `.cognitive-os/metrics/auto-skill-generation.log` (JSONL).

### Verdict

**Different input domains and methods.** CLI-Anything generates SKILL.md from **CLI source code** (Click decorators) at author time. COS generates SKILL.md from **agent task transcripts** at runtime. There is no shared algorithm, no shared input shape, and no shared output schema.

The original sonnet audit's claim that COS could "audit `skills/add-skill/SKILL.md` against the CLI-Anything SKILL.md template and confirm COS's frontmatter fields are a superset" is moot — the two systems do different things. Even the YAML frontmatter is divergent: CLI-Anything emits `name`, `description`; COS auto-skills emit `name`, `description`, `auto-generated`, `generated-from`, `generated-at`, `version`, `last-updated`.

**Adoption value: ZERO.** Reject extraction.

---

## Q2 — Catalog format

### CLI-Anything side (verified)

Two flat JSON files in the HKUDS monorepo, served via GitHub Pages.

`registry.json` schema (verified by parsing the live file: 56 CLIs, all with these 12 fields):
`name`, `display_name`, `version`, `description`, `requires`, `homepage`, `source_url`, `install_cmd`, `entry_point`, `skill_md`, `category`, `contributors`. Outer envelope: `{meta: {repo, description, updated}, clis: [...]}`. Meta `updated: 2026-04-16`.

`public_registry.json` adds: `package_manager`, `npm_package`, `npx_cmd`, `install_notes`, `uninstall_cmd`, `update_cmd`.

**Signing/verification: NONE.** No checksums, no GPG, no SLSA provenance. Per-CLI `version` semver field is bumped manually in PRs. Catalog state is the git history of `registry.json`.

### COS side (verified)

`manifests/agentic-primitive-registry.lock.yaml`:

- `schema_version: 1`
- `policy: Deterministic cross-instance lock; drift must be explicit before Shape-B federation.`
- **154 primitives**, each with: `id`, `kind`, `owner_adr`, `lifecycle_state` (sandbox/blocking/etc.), `maturity`, `distribution` (lab/maintainer/etc.), `runtime_projection`, `projection_targets[]`, **`sha256` content hash**.
- Verified: `grep -c "^- id:" → 154`; `grep -c "sha256:" → 154`. Every primitive has exactly one sha256.

### Verdict

COS catalog is **structurally stronger**: SHA-256 per primitive (CLI-Anything has zero), lifecycle states tracked (CLI-Anything has none), explicit projection targets (CLI-Anything has none), ADR ownership traced (CLI-Anything has none).

CLI-Anything's only structural advantages: install_cmd field (irrelevant — COS skills aren't pip packages), JSON format (queryable but no signing), public catalog open to outside contributors (different governance model).

**Adoption value: ZERO.** COS catalog is already more rigorous than CLI-Anything's. The CLI-Anything install_cmd schema would only matter if COS converted skills into pip packages — that is a redesign, not an adoption.

---

## Q3 — Discovery flow

### CLI-Anything side (verified)

Two surfaces:

**Surface A — `cli-hub`** (`cli-hub/cli_hub/cli.py` + `registry.py` + `installer.py`):
- Fetch: `GET hkuds.github.io/CLI-Anything/registry.json` + `public_registry.json`, cached at `~/.cli-hub/*.json` with 3600s TTL (verified in `registry.py:18` `CACHE_TTL = 3600`).
- Search: substring match on `name`/`description`/`category`/`display_name`. No semantic similarity.
- Install: dispatch on `install_strategy` (pip/npm/uv/bundled). `installer.py:_run_command()` (verified): **`shell=True` is used when the command contains `|`, `&&`, `||`, `;`, `$(`, or `` ` ``**. The comment in source says: "Commands come from the trusted registry, not from user input" — implicit trust on registry control by HKUDS.
- Tracking: `~/.cli-hub/installed.json` local dict.

**Surface B — `npx skills`**: external npm package not hosted in this repo. Reads `skills/<id>/SKILL.md` from GitHub repo tree. Sandbox/verification behavior unknown (out of scope of this monorepo).

### COS side (verified)

**Discovery**: `lib/skill_router.py` — pattern-based regex intent matcher. `_RoutingEntry` dataclass holds compiled regex patterns with base confidence. `SkillMatch` returns `skill_name`, `confidence`, `reason`, `invoke_command`. EN+ES patterns. The routing is intent-based, not substring search.

**Projection** (the analog of "install"): `scripts/cos_init.py`:
- `SUPPORTED_HARNESSES` tuple lists **21 harnesses** (verified by reading line 46): claude, codex, opencode, vscode-copilot, cursor, qwen-code, kimi-code, gemini-cli, warp, amp-code, jetbrains-junie, qoder, factory-droid, cline, continue-dev, kilo-code, zed-ai, augment-code, goose, aider, shell-ci.
- `HARNESS_SETTINGS` dict (lines 50–73) maps each to a `(kernel_dest, driver_dest)` tuple.
- `install_skill_dir()` (lines 341–395) ports the legacy bash projection logic.

The "5-path projection" phrasing in the original task brief refers to the `lib/config_loader.py` 5-path search order for finding `cognitive-os.yaml` (`$COGNITIVE_OS_PROJECT_DIR`, `$CODEX_PROJECT_DIR`, `$CLAUDE_PROJECT_DIR`, cwd, `.cognitive-os/cwd`). This is a different mechanism from harness projection, which targets 21 destinations.

### Verdict

The two systems solve **different problems**. CLI-Anything discovers third-party CLI tools from a public catalog and installs them as system packages. COS routes user intent to skills already in the project tree and projects skill files into 21 different harness configurations.

**Adoption value: ZERO.** No primitive transfers cleanly. CLI-Anything's substring search is weaker than COS's intent router. CLI-Anything's `shell=True` install dispatch is incompatible with COS's `supply-chain-defense` rule (digest pinning required).

---

## Q4 — Publishing flow

### CLI-Anything side (verified)

1. Contributor forks HKUDS/CLI-Anything, adds `<software>/agent-harness/` (Click CLI + tests + setup.py).
2. Runs `skill_generator.py` to produce `skills/cli-anything-<software>/SKILL.md`.
3. Adds entry to `registry.json` at repo root.
4. Opens PR. PR must include unit tests + E2E tests + README updates.
5. HKUDS maintainers review via standard GitHub PR (no automated curation gate found in source).
6. On merge to `main`, GitHub Pages auto-publishes the updated registry within minutes.

**Control**: Single org (HKUDS) controls the canonical registry. `registry.json` lives in HKUDS monorepo. Third-party CLIs can be listed in `public_registry.json`, but the entry still lives in the HKUDS repo.

**Federation**: None documented. An organization wanting a private catalog would have to fork and re-point `REGISTRY_URL` constants in `cli_hub/registry.py`.

### COS side (verified)

1. Author creates `skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`, optional `model`, `audience`).
2. Skill body uses COS conventions: `## Trigger`, `## Steps`, `## Acceptance Criteria`, `## Inputs`/`## Outputs`. Verified by scanning 88 SKILL.md files; **zero contain `## Command Groups`** — confirms the rebuttal's correction of the original sonnet audit.
3. Registry lock regeneration: `manifests/agentic-primitive-registry.lock.yaml` recomputes SHA-256 for each primitive (process implied by the lock file's `policy` line).
4. Projection: `scripts/cos_init.py` projects rules + skills into 21 supported harnesses.
5. CI: per RULES-COMPACT.md §14, language quality gates run (Python snake_case audit via `tests/audit/test_python_naming.py`, Bash kebab-case audit, Go gofmt/vet).

### Verdict

**Different governance models, equally legitimate.** CLI-Anything optimizes for openness (anyone can PR a CLI). COS optimizes for integrity (sha256 lock + lifecycle state + ADR ownership). CLI-Anything's automated CI for skill quality was not located in the monorepo (CONTRIBUTING.md describes requirements, but no enforcement script). COS's quality gates are enforced via `tests/audit/*` and pre-commit hooks.

**Adoption value: ZERO from CLI-Anything → COS.** The reverse direction (COS sha256 lock pattern → CLI-Anything) would actually improve CLI-Anything, but that is out of scope.

---

## COS-side claim verifications (rebuttal reprise)

The rebuttal corrected one claim from the original sonnet audit. This Opus audit re-checked all four COS-side claims in the rebuttal's CLI-Anything table. Results:

| Claim | Rebuttal verdict | Opus re-verification | Evidence |
|---|---|---|---|
| COS uses `## Command Groups` tables | CORRECTED (false) | **CONFIRMED CORRECTED** (false) | `find skills -name SKILL.md \| xargs grep -l '## Command Groups'` → 0 of 88 |
| COS has `auto-skill-generator.sh` | CONFIRMED | CONFIRMED | `packages/consequence-system/hooks/auto-skill-generator.sh` exists, fires on PostToolUse:Agent, threshold = 10 tool uses or 8000 chars+heuristic |
| COS has SHA-256 primitive registry | CONFIRMED | CONFIRMED | `manifests/agentic-primitive-registry.lock.yaml`: 154 entries × 1 sha256 each |
| COS has 21-harness projection | CONFIRMED | CONFIRMED | `scripts/cos_init.py:46` SUPPORTED_HARNESSES has 21 names |

**Methodology error in original sonnet audit**: The "## Command Groups convention is already in COS" claim was made without scanning any COS SKILL.md file. The rebuttal correctly caught this. No additional false claims were found.

---

## Adoption recommendation: REJECT

After source-level verification of both sides, **no CLI-Anything primitive is worth extracting into COS**.

| Candidate | Status | Why rejected |
|---|---|---|
| `## Command Groups` SKILL.md table convention | REJECT | COS skills are workflow procedures, not CLI taxonomies. Forcing this section onto 88 SKILL.md files would degrade them. |
| `registry.json` schema (12 fields) | REJECT | COS skills are not pip packages; install_cmd/entry_point/package_manager fields are irrelevant. The COS lock file is structurally stronger (sha256, lifecycle_state, ADR ownership). |
| `cli-hub install <name>` substring search | REJECT | Weaker than `lib/skill_router.py` intent-based regex matcher. |
| `cli-hub install` shell-dispatch model | REJECT | `shell=True` with implicit registry trust violates `supply-chain-defense` (digest pinning required) and `agent-security` (sandbox required). |
| Jinja2 SKILL.md template | REJECT | COS uses LLM-assisted skill authoring (`skills/skill-creator/`) for designed skills and shell heuristics (`auto-skill-generator.sh`) for runtime captures. Neither benefits from a static Click-decorator template. |
| GitHub Pages distribution model | REJECT | COS is single-repo with engram + lock-based projection; federation is Shape-B (engram cloud), not GitHub Pages. |

**Final verdict**: CLI-Anything is well-engineered for its scope (deterministic CLI-wrapping with public catalog) but solves a problem COS does not have. Where the two systems overlap conceptually, COS's implementation is already more rigorous (sha256 lock vs no signing, intent router vs substring search, 21-harness projection vs single-harness install).

---

## What COS already has (corrected, against prior audits)

The original sonnet audit (and to a lesser extent the rebuttal) under-credited several COS primitives. Final consolidated list, verified at source:

1. **`auto-skill-generator.sh`** — runtime SKILL.md capture from agent task transcripts; complexity threshold (10 tool uses or 8000 chars + heuristic); private-mode and env-var opt-out; logs to `.cognitive-os/metrics/auto-skill-generation.log`.
2. **154-primitive SHA-256 lock** at `manifests/agentic-primitive-registry.lock.yaml` with `lifecycle_state`, `maturity`, `distribution`, `runtime_projection`, `projection_targets[]`, `owner_adr`.
3. **21-harness projection** via `scripts/cos_init.py` (`HARNESS_SETTINGS` map, lines 50–73; `install_skill_dir()`, lines 341–395).
4. **`lib/skill_router.py`** intent-based regex matcher with EN+ES patterns and confidence scoring.
5. **`skills/CATALOG.md`** + 88 author-written SKILL.md files using `## Trigger`/`## Steps`/`## Acceptance Criteria`/`## Inputs`/`## Outputs` (NOT `## Command Groups`).

---

## TRUST REPORT

**Confidence: 0.88**

**Evidence (40%)**: 4/4 — CLI-Anything source files fetched and parsed (skill_generator.py, registry.py, installer.py, registry.json). COS source files read at file:line (auto-skill-generator.sh, registry lock, skill_router.py, cos_init.py). Filesystem checks executed and counts reported.

**Criteria (30%)**: 4/4 — answered the 4 questions, verified all rebuttal claims, issued an adoption recommendation, listed COS primitives missed in prior audits.

**Self-awareness (20%)**: 3/4 — uncertainties enumerated below.

**Proportionality (10%)**: 4/4 — used 7 tool calls of the 60-call budget. Proportional.

**Uncertainties**:
1. CLI-Anything's `npx skills add` external npm package was not located in the monorepo; its security model is unknown. Out of scope for this audit per the original brief.
2. The DigitalOcean Spaces aggregated SKILL.md (`https://reeceyang.sgp1.cdn.digitaloceanspaces.com/SKILL.md`) referenced in CLI-Anything's meta-skill is a separate aggregation pipeline not investigated.
3. COS auto-skill-generator's actual production usage rate is not measured here (would need `.cognitive-os/metrics/auto-skill-generation.log` analysis on a real session).
4. Whether `skills/skill-creator/` (LLM-assisted authoring) exceeds CLI-Anything's deterministic generator on quality is a separate question requiring user studies.

---

## Sources

### CLI-Anything (fetched via `gh api repos/HKUDS/CLI-Anything/contents/<path>`)

- `cli-anything-plugin/skill_generator.py` (547 LOC)
- `cli-hub/cli_hub/registry.py` (115 LOC) — `CACHE_TTL = 3600`, `REGISTRY_URL`/`PUBLIC_REGISTRY_URL` constants
- `cli-hub/cli_hub/installer.py` (373 LOC) — `_run_command()` `shell=True` dispatch
- `registry.json` — 56 CLIs, 12 fields, `meta.updated: 2026-04-16`
- Repo metadata: 33,577 stars, Apache-2.0, default branch `main`, last push `2026-05-05T11:43:38Z`

### COS (read directly from working tree)

- `packages/consequence-system/hooks/auto-skill-generator.sh` (lines 1–200)
- `manifests/agentic-primitive-registry.lock.yaml` (154 primitives × 1 sha256 each, verified by grep -c)
- `lib/skill_router.py` (head 50)
- `scripts/cos_init.py` (lines 46–73, 341–395, 938–1208)
- 88 SKILL.md files under `skills/` (filesystem grep: zero contain `## Command Groups`)

### Prior reports (read in full)

- `docs/06-Daily/reports/cli-anything-deep-audit-2026-05-05.md` (sonnet, original)
- `docs/06-Daily/reports/cos-side-deep-rebuttal-2026-05-05.md` (rebuttal)
- `docs/06-Daily/reports/primitives-and-tools-audit-2026-05-05.md` (referenced; not re-read)

---

## Engram persistence

Saved to engram with `topic_key: cli-anything-opus/2026-05-05`, `type: discovery`, `scope: project`. See `mem_save` invocation in session log.
