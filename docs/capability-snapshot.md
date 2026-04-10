# Capability Snapshot

> This functionality is implemented as the `/capability-snapshot` skill. Run `/capability-snapshot` to use it.
>
> For the full procedure, see `skills/capability-snapshot/SKILL.md`.

## Overview

Capability Snapshot saves a checkpoint of all hooks, rules, skills, squads, and agents before structural changes, then diffs the before/after states to detect unintended feature loss. Use it before any cleanup or refactor of `.cognitive-os/` to ensure no capabilities are accidentally removed.
