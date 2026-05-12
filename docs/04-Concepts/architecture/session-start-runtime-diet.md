# SessionStart Runtime Diet

The SessionStart diet has two different numbers that must not be conflated:

1. **Active maintainer projection** — the committed `.claude/settings.json` used by
   this self-hosting repository. It may keep the full maintainer SessionStart
   surface for solo-swarm operation.
2. **Generated adoption profile projection** — the hook set that would be emitted
   for `core`, `team`, or `maintainer` by the canonical settings driver.

`core` diet means the generated consumer projection is small. It does **not**
mean this maintainer checkout must run with the consumer projection at all times.

## Commands

```bash
scripts/cos-session-start-budget --profile current --json
scripts/cos-session-start-budget --profile core --json
```

Important fields:

- `session_start_hook_count` — count for the requested profile/projection.
- `projection_source` — `active_settings` for `current`, `generated_profile` for
  generated profiles such as `core`.
- `active_session_start_hook_count` — count in the currently committed active
  `.claude/settings.json`.
- `active_projection_matches_profile` — whether active settings exactly match the
  requested generated profile.

If `--profile core` reports `session_start_hook_count: 3` while
`active_session_start_hook_count: 20`, the diet is working for the consumer
projection and the local checkout is still in maintainer mode. That is expected
for this repository unless the operator explicitly applies the core projection:

```bash
bash scripts/apply-efficiency-profile.sh core --harness=claude-code
```

Do not use the active maintainer count as proof that core adoption is heavy. Use
`projection_source` to tell which surface is being measured.
