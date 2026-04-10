# Definition of Done (DoD) System

> This functionality is implemented as the `/dod-check` skill. Run `/dod-check` to use it.
>
> For the full procedure, see `skills/dod-check/SKILL.md`.

## Overview

The DoD system ensures task completion quality scales with task complexity. Every task is classified into one of five complexity levels (trivial, small, medium, large, critical), each with progressively stricter completion criteria. Agents must classify complexity before starting and cannot mark work as done until all criteria for that level pass. The authoritative criteria table lives in `rules/definition-of-done.md`.
