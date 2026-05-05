# Engram Obsidian Export Manual Test

**Purpose**: prove the Phase 4 export path renders Engram observations into an
Obsidian-compatible Markdown graph without making Obsidian the source of truth.

## Preconditions

- Local Obsidian is installed and validated:

  ```bash
  bash scripts/install-obsidian-local.sh --status
  ```

- `engram serve` is running on the default local port, or the Engram HTTP API is
  otherwise reachable through the configured environment.
- You have an Obsidian vault path you are willing to use for a test export.
- The vault path is passed explicitly; there is no automatic vault discovery.

## Dry-run proof

```bash
bash scripts/export-engram-to-obsidian.sh \
  --vault /absolute/path/to/obsidian-vault \
  --project luum-agent-os \
  --limit 20 \
  --json
```

Expected:

- Command exits 0.
- JSON reports `"dry_run": true`.
- JSON reports `files_planned` greater than or equal to 0.
- No `Cognitive OS/Engram/` folder is created or changed in the vault.

## Write proof

```bash
bash scripts/export-engram-to-obsidian.sh \
  --vault /absolute/path/to/obsidian-vault \
  --project luum-agent-os \
  --limit 20 \
  --write \
  --json
```

Expected:

- Command exits 0.
- JSON reports `"dry_run": false`.
- Markdown files appear under `Cognitive OS/Engram/` inside the vault.
- Each exported file has YAML frontmatter with Engram identity fields such as
  `cos_observation_id`, `sync_id`, `topic_key`, `type`, and `project`.
- Observations with lifecycle trailers expose fields such as `confidence`,
  `last_reinforced`, `reinforcement_count`, and `decay_class` as frontmatter.
- The raw `<engram-lifecycle>` trailer is not present in the Markdown body.
- If exported observations have typed `memory_relations`, the source note has an
  `## Engram Relations` section with Obsidian wikilinks to target notes.

## Incremental proof

Run the same write command twice.

Expected:

- First run writes files.
- Second run reports `files_written: 0` for unchanged files because the manifest
  digest is unchanged.
- Passing `--force` rewrites planned files.

## Safety invariants

- This export never writes back to Engram.
- This export never reads or imports user edits from Obsidian.
- No default Stop hook registration is required. The optional Stop hook remains
  gated by an explicit `COS_OBSIDIAN_VAULT` environment variable.

## Actual proof run — 2026-05-05

Local vault used:

```text
$HOME/.cognitive-os/obsidian-vaults/luum-agent-os
```

Commands:

```bash
bash scripts/install-obsidian-local.sh --status
bash scripts/export-engram-to-obsidian.sh \
  --vault "$HOME/.cognitive-os/obsidian-vaults/luum-agent-os" \
  --project luum-agent-os \
  --limit 100 \
  --write \
  --json
```

Observed export summary:

```json
{
  "dry_run": false,
  "files_planned": 3,
  "files_written": 3,
  "relation_count": 0,
  "output_dir": "$HOME/.cognitive-os/obsidian-vaults/luum-agent-os/Cognitive OS/Engram"
}
```

Structural review:

- Exported notes were written under `Cognitive OS/Engram/`.
- Each sampled note had YAML frontmatter with `cos_observation_id`, `type`,
  `project`, `created_at`, `updated_at`, `lifecycle_stage`, and source metadata.
- The generated `_manifest.json` recorded file digests for incremental export.
- `relation_count: 0` was expected for the sampled observations; relation
  rendering remains covered by `tests/unit/test_engram_obsidian_exporter.py`.

## Optional Stop hook proof

`hooks/engram-obsidian-export-on-stop.sh` provides the opt-in automation path.
It is safe to register as a Stop hook because it exits 0 when
`COS_OBSIDIAN_VAULT` is unset and records non-blocking metrics when an export
fails.

Manual one-shot opt-in check:

```bash
COS_OBSIDIAN_VAULT="$HOME/.cognitive-os/obsidian-vaults/luum-agent-os" \
COS_OBSIDIAN_EXPORT_LIMIT=100 \
bash hooks/engram-obsidian-export-on-stop.sh
```

Observed on the same vault after the initial write: hook exited 0, appended an
`ok` event to `.cognitive-os/metrics/obsidian-export.jsonl`, and reported
`files_written: 0` because the manifest digests were unchanged.
