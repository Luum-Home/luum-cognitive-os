# @luum/document-sync

Documentation synchronization — detects stale docs after code changes and syncs to repo on session stop

## Install

```bash
cos install @luum/document-sync
```

## Components

- `rules/doc-sync.md` (rule) -- Doc sync detection and session-end warning protocol
- `hooks/doc-sync-detector.sh` (hook) -- Detects when code changes affect documentation
- `hooks/sync-to-repo.sh` (hook) -- Syncs documentation changes to repo on session stop

## License

Apache-2.0
