# Automation: Doc Sync

> This functionality is implemented as the `/doc-sync` skill. Run `/doc-sync` to use it.
>
> For the full procedure, see `skills/doc-sync/SKILL.md`.

## Overview

Doc Sync detects stale documentation by watching source file edits (`.go`, `.ts`, `.java`) and mapping them to affected docs. When code changes, the `doc-sync-detector.sh` hook logs entries to `.cognitive-os/metrics/stale-docs.jsonl`; running `/doc-sync` updates the affected markdown files to reflect the current state of the code.
