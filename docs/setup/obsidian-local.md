# Local Obsidian Installation

**Purpose**: install and validate a local Obsidian desktop app for the optional
Engram → Obsidian graph export workflow.

Obsidian is not the Cognitive OS memory source of truth. Engram remains the
canonical memory backend; Obsidian is a human-readable Markdown graph and audit
surface.

## Sources verified

- Official Obsidian download page: https://obsidian.md/download
- Homebrew cask page: https://formulae.brew.sh/cask/obsidian

As of 2026-05-05, the Homebrew cask installs Obsidian with:

```bash
brew install --cask obsidian
```

The Homebrew cask page lists Obsidian as a local-folder Markdown knowledge base,
current cask version `1.12.7`, and macOS requirement `>= 12`.

## Managed install script

Use the repository wrapper instead of remembering the cask details:

```bash
bash scripts/install-obsidian-local.sh
```

What the script does:

1. Verifies the host is macOS.
2. Verifies Homebrew is installed.
3. Installs the `obsidian` Homebrew cask if Obsidian is absent.
4. Leaves an existing unmanaged `/Applications/Obsidian.app` untouched unless
   `--force` is passed.
5. Reports app version, cask state, and CLI shim path.

## Status check

```bash
bash scripts/install-obsidian-local.sh --status
```

Expected output shape:

```text
[obsidian-local] app=present path=/Applications/Obsidian.app version=1.12.7
[obsidian-local] homebrew-cask=installed
[obsidian-local] cli=/opt/homebrew/bin/obsidian
```

## Replacing an unmanaged app

If Obsidian was installed manually from the website before this script existed,
Homebrew may not own the app. To replace the existing app with the Homebrew cask:

```bash
bash scripts/install-obsidian-local.sh --force
```

This passes `--force` to Homebrew Cask and may overwrite
`/Applications/Obsidian.app`.

## Open after install

```bash
bash scripts/install-obsidian-local.sh --open
```

## Use with Engram export

After Obsidian is installed and you have created or selected a vault, run the
Engram export dry-run first:

```bash
bash scripts/export-engram-to-obsidian.sh \
  --vault /absolute/path/to/obsidian-vault \
  --project luum-agent-os \
  --limit 100 \
  --json
```

Write only after inspecting the dry-run output:

```bash
bash scripts/export-engram-to-obsidian.sh \
  --vault /absolute/path/to/obsidian-vault \
  --project luum-agent-os \
  --limit 100 \
  --write
```

Local proof vault used for the 2026-05-05 manual run:

```text
$HOME/.cognitive-os/obsidian-vaults/luum-agent-os
```

Optional automation exists as an explicit Stop-hook helper:

```bash
COS_OBSIDIAN_VAULT=/absolute/path/to/obsidian-vault \
bash hooks/engram-obsidian-export-on-stop.sh
```

Register that hook only when the operator wants session-end export on that
device. With `COS_OBSIDIAN_VAULT` unset, the hook exits 0 without exporting.

## Safety invariants

- Installing Obsidian does not enable automatic Engram export.
- The export script is still dry-run by default.
- Stop-hook export is opt-in through `COS_OBSIDIAN_VAULT`.
- Vault paths are explicit and operator-owned.
