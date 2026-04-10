# Plan System

> This functionality is implemented as the `/plan-feature` and `/plan-bug` skills. Run `/plan-feature` for new features or `/plan-bug` for bug fixes.
>
> For the full procedures, see `skills/plan-feature/SKILL.md` and `skills/plan-bug/SKILL.md`.

## Overview

The plan system provides structured planning, auto-evaluation, and archival for significant development tasks. Plans are scored on completeness, feasibility, risk assessment, architecture alignment, and test coverage (0–50 pts). Plans scoring below 25 are auto-improved before implementation begins. Plan files are stored in `.cognitive-os/plans/{type}/{date}-{slug}.md` and persist as historical records.
