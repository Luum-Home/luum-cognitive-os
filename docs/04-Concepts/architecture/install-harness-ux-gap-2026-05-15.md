---
report_type: architecture-gap-review
date: 2026-05-15
status: active
related_files:
  - install.sh
  - scripts/cos_init.py
  - scripts/generate-project-settings.sh
  - scripts/_lib/settings-driver.sh
  - manifests/harness-projection.yaml
  - manifests/primitive-projection-profiles.yaml
  - manifests/harness-driver-capabilities.yaml
  - manifests/agentic-primitive-registry.lock.yaml
  - tests/integration/test_installer.py
  - tests/behavior/test_consumer_project_projection.py
related_research:
  - docs/06-Daily/reports/external-tools-radar-claude-code-templates-addendum-2026-05-15.md
  - docs/03-PoCs/research/repo-scout/deep/davila7__claude-code-templates-2026-05-15.md
---

# Install Harness UX Gap Review — 2026-05-15

## Question

Does the top-level installer communicate and expose the same multi-IDE ambition
that the underlying Cognitive OS projector already supports?

## Short answer

Partially. `scripts/cos_init.py` is the stronger contract today: it supports a
broad set of native and structural harness projections and records the selected
harness in `.cognitive-os/install-meta.json`. Before this review, `install.sh`
accepted and documented only `claude|codex`, so first-run UX under-claimed the
project's actual projection work.

This gap has two layers:

1. **Immediate mismatch** — `install.sh --harness` did not expose the harnesses
   already implemented in `scripts/cos_init.py`.
2. **Product capability gap** — COS still lacks a Claude-Code-Templates-style
   granular primitive catalog UX (`cos install primitive ...`, `cos install
   profile ...`, `cos project --harness ...`).

## Current state after the first correction

`install.sh` now accepts the same user-facing harness set that `cos_init.py`
projects today:

- `claude`
- `codex`
- `agents-md`
- `opencode`
- `vscode-copilot`
- `cursor`
- `qwen-code`
- `kimi-code`
- `gemini-cli`
- `warp`
- `amp-code`
- `jetbrains-junie`
- `qoder`
- `factory-droid`
- `cline`
- `continue-dev`
- `kilo-code`
- `zed-ai`
- `augment-code`
- `goose`
- `aider`
- `shell-ci`

The installer summary now handles structural harnesses generically: it reads the
actual `settings_driver` from `.cognitive-os/install-meta.json`, points skills to
the canonical `.cognitive-os/skills/cos/` surface, and warns the operator to check
`manifests/harness-projection.yaml` before claiming runtime enforcement.

A new integration smoke covers `install.sh --from <source> --force
--harness=cursor` and verifies `.cursor/rules/cognitive-os.mdc`, `.cursor/mcp.json`,
canonical skills, and absence of Claude-specific skill/instruction leakage.

The next recommended correction is also landed: `tests/integration/test_installer.py`
now compares `install.sh`'s `SUPPORTED_HARNESSES` with
`scripts/cos_init.py::SUPPORTED_HARNESSES`, so future drift fails in CI.

## Findings

### 1. `cos_init.py` is already the public projection contract in practice

`cos_init.py` owns:

- supported harness identifiers;
- settings/instruction output paths;
- native vs structural harness split;
- canonical copy into `.cognitive-os/{hooks,rules,skills,templates}/cos`;
- Claude-only driver projections into `.claude/skills` and `.claude/rules/cos`;
- install metadata, including `harness` and `settings_driver`.

The top-level installer should remain a source/bootstrap wrapper around that
contract, not a competing harness registry.

### 2. `install.sh` duplicates the harness list, but drift is now tested

The immediate fix uses a bash `SUPPORTED_HARNESSES` list matching `cos_init.py`.
That closes UX today. The drift risk is now covered by a permanent integration
test that parses both files and fails when the lists diverge. A future cleanup can
still replace the duplicate list with a shared generated registry.

### 3. Shell and Go helper support now preserve structural harness metadata

`scripts/_lib/settings-driver.sh` now accepts all currently implemented
`cos_init.py` harness IDs from `.cognitive-os/install-meta.json` and maps their
settings/instruction driver paths instead of falling back to `.claude/settings.json`.
The Go package installer helper `cmd/cos/internal/installer/settings_driver.go`
now performs the same metadata-first resolution and includes structural driver
paths.

This closes the immediate helper/update parity bug for structural harnesses;
further work should move both helper implementations to a shared generated
registry rather than maintaining parallel maps.

### 4. `generate-project-settings.sh` is intentionally native-lifecycle only

`generate-project-settings.sh` supports `claude|codex` because it emits native
hook settings. Structural harnesses are handled in `cos_init.py` by writing
instruction/rule/MCP-placeholder surfaces. This split is correct, but the docs
and helper errors should call it out as "native lifecycle settings" rather than
"the harness list".

### 5. Windsurf remains planned, not implemented

`manifests/harness-projection.yaml` marks Windsurf as planned. It is not in
`cos_init.py`'s supported harness list. That is the right honest posture until a
project-local Windsurf projection driver and proof exist.

## Claude Code Templates pattern extraction

`davila7/claude-code-templates` should influence COS UX, not source-of-truth
architecture.

| Upstream pattern | COS treatment |
|---|---|
| `--agent`, `--command`, `--hook`, `--skill`, `--mcp`, `--setting` individual installation flags | Reinterpret as `cos install primitive <family/name> --harness <id>` over COS canonical primitive registry. |
| Component inventory under `cli-tool/components/*` | Keep COS canonical inventory in manifests and primitive directories; do not move truth into `.claude/*`. |
| Backup/merge/conflict handling in `file-operations.js` | Adopt clean-room for projection writers. |
| Health/stats dashboards | Wrap existing COS audits and manifests behind simpler operator commands. |
| Direct `.claude/*` writes as the product model | Do not adopt; `.claude` is a driver target only. |

## Recommended roadmap

### Slice A — installer exposure parity (closed for first-run UX)

- [x] Allow `install.sh --harness=<implemented structural harness>`.
- [x] Update help text to show non-Claude/Codex harnesses.
- [x] Make summary generic for structural harnesses.
- [x] Add `install.sh --harness=cursor` smoke.
- [x] Add drift test: `install.sh` supported list equals `cos_init.py::SUPPORTED_HARNESSES`.
- [x] Update shell settings-driver helper to preserve structural harness metadata
      instead of defaulting unknown harnesses to Claude.
- [x] Update Go package-installer settings-driver helper to preserve structural
      harness metadata.

### Slice B — projection-driver truth source

- [ ] Introduce a machine-readable harness registry generated from or shared by
      `cos_init.py` and `manifests/harness-projection.yaml`.
- [ ] Make `install.sh --help` render the list from that registry.
- [ ] Make helper scripts resolve `settings_driver` from `.cognitive-os/install-meta.json`
      for every harness.
- [ ] Keep `generate-project-settings.sh` explicitly scoped to native lifecycle
      emitters (`claude|codex`) unless another harness gains native hooks.

### Slice C — granular primitive catalog UX (first CLI slice landed)

- [x] Define `cos install primitive <family/name> --harness <id>` as a
      source-of-truth-first projection plan over canonical skill/hook/rule
      surfaces.
- [x] Define `cos install profile <profile> --harness <id>` as a projection plan
      over registered `default|full` profiles, with explicit guidance when a
      named profile such as `sre` is not registered yet.
- [x] Define `cos project --harness <id>` as a project projection plan command.
- [x] Every primitive/profile/project plan says the target path and proof summary
      (`native-lifecycle`, `governed-wrapper-enforced`, or `structural-advisory`).
- [x] Promote the plan commands to first mutation commands with projection
      receipts, target backups, and opt-in runtime smoke. Profile registry
      signing remains a follow-up hardening item.
- [ ] Replace the hardcoded Go harness/proof maps with a generated registry from
      `manifests/harness-projection.yaml` and `manifests/primitive-projection-profiles.yaml`.

### Slice D — conflict-safe projection writes

- [x] Add first-slice backups for existing primitive targets and harness projection files.
- [ ] Preserve bounded COS blocks idempotently.
- [ ] Merge JSON settings where supported and refuse unsafe overwrites.
- [x] Emit a projection receipt under `.cognitive-os/receipts/`.

### Slice E — simple health/stats UX

- [ ] Add `cos doctor harness` or top-level installer post-check hints that wrap
      existing audits.
- [ ] Add `cos primitive stats --harness <id>` to report native/enforced/advisory
      primitive counts.
- [ ] Link counts back to `manifests/harness-projection.yaml` proof levels.

## Acceptance criteria for closing the gap

1. [x] `install.sh --help` and `cos_init.py --help` cannot disagree on supported
   first-run harnesses without a failing test.
2. [x] A fresh project can install at least one native harness (`claude`), one hook
   settings harness (`codex`), and one structural harness (`cursor`) through
   top-level `install.sh`.
3. [x] Shell and Go helper/update paths read structural harness install metadata
   instead of assuming Claude.
4. [x] A primitive/profile/project catalog command can plan one skill/profile
   projection with a harness-specific proof-level summary.
5. [x] Windsurf stays absent from supported first-run harnesses until projection
   files and tests exist, despite being in the planned manifest.
6. [x] Mutation/apply mode for granular primitive/profile commands writes
   backups and receipts, with deeper structured merge still tracked as follow-up.

## Bottom line

The architecture remains correct: `.cognitive-os/` is canonical, `.claude/` is a
projection target, and each harness carries an explicit proof boundary. The
install UX now has first-slice apply mode, but the product-quality close still
requires shared generated harness maps, deeper structured merge semantics, and
a simple doctor/stats wrapper over receipts.

## 2026-05-15 follow-up: apply-mode projection slice

The granular UX has moved beyond plan-only for the first safe slice:

- `cos install primitive <family/name> --harness <id>` now writes the selected
  primitive into `.cognitive-os/{skills,hooks,rules}/cos/`, backs up any existing
  target plus the harness projection file, and emits a JSON receipt under
  `.cognitive-os/receipts/`.
- `cos install profile default|full --harness <id>` and `cos project --harness
  <id> --profile default|full` now delegate to `scripts/cos_init.py`, back up the
  selected harness projection path first, and emit the same receipt shape.
- All three commands keep `--dry-run` for the previous plan output.
- `--runtime-smoke` is opt-in and runs real installed harness binaries only for
  mapped command-line harnesses (`cursor`, `qwen-code`, `gemini-cli`,
  `opencode`). Missing binaries are recorded as skipped rather than treated as a
  product proof.
- `windsurf` is explicitly recognized as planned-but-unsupported, so operators
  get an honest error instead of a generic unknown-harness message.

The canonical primitive catalog now has a generated lockfile at
`manifests/agentic-primitive-registry.lock.yaml`. The lockfile is the
canonical generated/locked primitive catalog; harness directories remain
projection targets, not source of truth.

Remaining hardening after this slice:

- move Go harness/proof maps to a generated registry shared with `cos_init.py`;
- merge JSON settings structurally instead of backing up then allowing the
  projector to rewrite them;
- add a human-facing `cos doctor harness` summary over projection receipts and
  harness proof levels.
