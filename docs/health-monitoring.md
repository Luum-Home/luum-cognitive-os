# Health Monitoring

> This functionality is implemented as the `/cognitive-os-status` skill. Run `/cognitive-os-status` to use it.
>
> For the full procedure, see `skills/cognitive-os-status/SKILL.md`.

## Overview

Health monitoring checks the operational state of Cognitive OS: hook registration, Docker service availability, session metrics, and recent error counts. Running `/cognitive-os-status` produces a structured health report with green/yellow/red indicators for each layer, helping diagnose issues before they affect agent quality.
