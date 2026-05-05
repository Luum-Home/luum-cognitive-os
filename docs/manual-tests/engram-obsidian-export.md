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
- No Stop hook or automatic background export is registered until this manual
  proof path is exercised successfully.
