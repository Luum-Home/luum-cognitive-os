---
type: quality-synthesis
source: docs/09-Quality/manual-tests/engram-obsidian-export.md
provenance: "Manual test proving the Phase 4 export path renders Engram observations into an Obsidian-compatible Markdown graph without making Obsidian the source of truth."
---

## What it is
A manual test (including one embedded dated proof run) for the Engram-to-Obsidian export path: a one-way, read-only-from-Engram export that renders Engram observations as Obsidian Markdown notes with YAML frontmatter and wikilink relations, explicitly keeping Engram as the sole source of truth.

## Key mechanics
- **Dry-run**: `bash scripts/export-engram-to-obsidian.sh --vault <path> --project luum-agent-os --limit 20 --json` → exits 0, JSON `"dry_run": true`, `files_planned >= 0`, no `Cognitive OS/Engram/` folder created.
- **Write**: same command with `--write` → exits 0, `"dry_run": false`, Markdown files land under `Cognitive OS/Engram/` with frontmatter (`cos_observation_id`, `sync_id`, `topic_key`, `type`, `project`, plus lifecycle fields `confidence`, `last_reinforced`, `reinforcement_count`, `decay_class` for observations that have them). The raw `<engram-lifecycle>` trailer is stripped from the body. Typed `memory_relations` render as an `## Engram Relations` section with Obsidian wikilinks.
- **Incremental**: re-running the write command reports `files_written: 0` when manifest digests are unchanged (digest-based skip); `--force` overrides.
- **Safety invariants**: export never writes back to Engram, never reads/imports Obsidian user edits; no default Stop hook — the optional `hooks/engram-obsidian-export-on-stop.sh` only activates when `COS_OBSIDIAN_VAULT` is explicitly set, and it exits 0 (non-blocking) when unset or on export failure.
- **Dated proof run (2026-05-05)**: against `$HOME/.cognitive-os/obsidian-vaults/luum-agent-os`, observed `files_planned: 3`, `files_written: 3`, `relation_count: 0`; sampled notes had the expected frontmatter fields plus `created_at`/`updated_at`/`lifecycle_stage`; `_manifest.json` recorded digests. A follow-up Stop-hook check on the same vault exited 0 and reported `files_written: 0` (unchanged digests), appending an `ok` event to `.cognitive-os/metrics/obsidian-export.jsonl`.

## Relations & where used
Preconditioned on `scripts/install-obsidian-local.sh --status` and a running `engram serve` / reachable Engram HTTP API. Part of the same Engram operability suite as `engram-cloud-docker-sync.md`, though export (Obsidian) and cloud sync (Postgres) are independent, non-overlapping paths.

## Status / caveats
This source mixes a general procedure with one embedded dated point-in-time proof run (2026-05-05) — flagged per instructions since it documents actual observed output (e.g., `relation_count: 0`) rather than only expected behavior; treat the dated section as a historical snapshot, not a standing guarantee.
