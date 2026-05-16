---
name: caveman-es
description: 'Deprecated locale-specific alias for the main caveman skill. Use /caveman for ultra-compressed English communication mode.'
audience: both
summary_line: Deprecated alias for the main caveman compression mode.
version: 1.0.1
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bcaveman[- ]?es\b
  confidence: 0.95
- pattern: /caveman-es\b
  confidence: 0.95
triggers:
- caveman-es
- /caveman-es
- Deprecated caveman alias
---
<!-- SCOPE: both -->
# Deprecated Caveman Alias

This file remains only as a compatibility alias for historical references to
`/caveman-es`. New usage should invoke `/caveman` instead.

## Behavior

Use the same behavior as `skills/caveman/SKILL.md`:

- Keep technical accuracy.
- Remove filler, hedging, and unnecessary prose.
- Preserve code blocks and quoted errors exactly.
- Use normal professional prose for security warnings, irreversible action
  confirmations, and multi-step instructions where compressed fragments could
  be misread.

## Migration

Prefer `/caveman lite|full|ultra` for all new invocations. This alias must not
add language-specific routing patterns or locale-specific behavior.
