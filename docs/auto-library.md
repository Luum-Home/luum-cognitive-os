# Auto Library Recommender

> This functionality is implemented as the `/recommend-library` skill. Run `/recommend-library` to use it.
>
> For the full procedure, see `skills/recommend-library/SKILL.md`.

## Overview

The Auto Library Recommender searches package registries (npm, PyPI, Go modules) and ranks results using license compliance checks, download thresholds, maintenance health, TypeScript support, and bundle size analysis. It enforces the project's library-selection policy and documents decisions to engram.
