---
name: eval-repo
description: 'Use when you need this Cognitive OS skill: DEPRECATED — renamed to /repo-scout
  (2026-04-24). This stub preserves backward compatibility for any documentation or
  workflows referencing /eval-repo. New work should use /repo-scout.; do not use when
  a narrower skill directly matches the task.'
version: 2.0.1
audience: both
last-updated: 2026-04-24
summary_line: DEPRECATED alias for /repo-scout
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \beval[- ]?repo\b
  confidence: 0.95
- pattern: \bevaluate\s+repo\b
  confidence: 0.85
triggers:
- eval-repo
- /eval-repo
- /eval-repo (DEPRECATED)
- DEPRECATED alias for /repo-scout
---
<!-- SCOPE: both -->
# /eval-repo (DEPRECATED)

This skill was renamed to `/repo-scout` on 2026-04-24. See `skills/repo-scout/SKILL.md`.

Run `/repo-scout <github-url>` instead. All functionality is preserved.
