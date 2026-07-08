---
type: methodology-synthesis
source: docs/05-Methodology/setup/obsidian-local.md
provenance: "Install/validation guide for a local Obsidian desktop app used only for the optional Engram-to-Obsidian graph export workflow, making explicit that Obsidian is a human-readable audit surface, not the memory source of truth."
---

## What it is

Setup guide for installing Obsidian on macOS via a managed wrapper script, and for wiring it to the optional Engram → Obsidian Markdown graph export. Engram remains the canonical memory backend; Obsidian is explicitly a secondary, human-readable surface.

## Key mechanics

- Sources verified as of 2026-05-05: official Obsidian download page and the Homebrew cask page, which lists cask version `1.12.7` and a macOS ≥ 12 requirement. Raw install is `brew install --cask obsidian`.
- Managed install: `bash scripts/install-obsidian-local.sh` verifies the host is macOS, verifies Homebrew is present, installs the cask if absent, leaves an existing unmanaged `/Applications/Obsidian.app` untouched unless `--force` is passed, and reports app version/cask state/CLI shim path.
- Status check: `--status` flag prints app presence/path/version, cask state, and CLI path in a fixed `[obsidian-local] key=value` format.
- `--force` replaces an unmanaged, manually-installed Obsidian app with the Homebrew-owned cask (may overwrite `/Applications/Obsidian.app`); `--open` launches the app after install.
- Engram export workflow: after selecting/creating a vault, run `scripts/export-engram-to-obsidian.sh --vault ... --project luum-agent-os --limit 100 --json` as a dry run first, then re-run with `--write` only after inspecting dry-run output. A proof vault path used for the 2026-05-05 manual run is documented as `$HOME/.cognitive-os/obsidian-vaults/luum-agent-os`.
- Optional automation: `hooks/engram-obsidian-export-on-stop.sh`, gated by `COS_OBSIDIAN_VAULT` — if unset, the hook exits 0 without exporting; it should only be registered on a device where the operator explicitly wants session-end export.

## Relations & where used

Audited as a "current repo surface" by the sibling `cross-device-dependencies.md` (ADR-168), which classifies it as "explicitly not cross-platform yet" (macOS-only helper). Feeds the Engram → Obsidian export pipeline (`scripts/export-engram-to-obsidian.sh`, `hooks/engram-obsidian-export-on-stop.sh`).

## Status / caveats

Dated point-in-time facts: the cask version (`1.12.7`) and macOS-requirement claim are "as of 2026-05-05" and will drift as Obsidian releases new versions; the proof-vault path is tied to one specific manual run on that date. The doc itself is honest about being macOS-only (no Linux/Windows install path is offered here), consistent with the cross-device-dependencies audit's classification.
