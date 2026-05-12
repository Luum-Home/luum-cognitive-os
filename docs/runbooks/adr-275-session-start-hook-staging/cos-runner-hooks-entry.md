# cos-runner `.cognitive-os/cos-runner-hooks.json` — SessionStart entry to add

Locate `events.SessionStart` (array) and APPEND:

```json
{
  "name": "adr-275-session-start-projector",
  "command": ["python3", "scripts/cos-session-start-projector"],
  "non_blocking": true,
  "timeout_seconds": 5
}
```

cos-runner enforces a 5s timeout by default; the projector finishes in
<100ms with cache hit, <500ms on cache miss.

If the file does not yet exist, create it with the standard cos-runner
schema (see ADR-008 for the canonical shape).
