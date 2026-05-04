# Engram Command Contract

This document records the Engram CLI surface that Cognitive OS primitives may
use as of the locally verified binary:

```text
engram 1.15.4
```

The purpose is to keep scripts, hooks, tests, and docs aligned with the real
binary instead of old or aspirational command shapes.

## Supported command shapes used by COS

| Need | Supported shape | COS surface |
|---|---|---|
| Start local HTTP daemon | `engram serve [port]` | `hooks/engram-daemon-launcher.sh`, memory lifecycle checks |
| Start MCP stdio process | `engram mcp --tools=agent [--project=NAME]` | MCP setup/runtime docs |
| Search manually | `engram search <query> [--type TYPE] [--project PROJECT] [--scope SCOPE] [--limit N]` | operator procedures only |
| Search programmatically | Engram HTTP `GET /search` through `lib/engram_http_client.py` | `lib/engram_client.py`, memory providers, claim/lock wrappers |
| Save memory | `engram save <title> <content> [--type TYPE] [--project PROJECT] [--scope SCOPE] [--topic TOPIC_KEY]` | `lib/safe_engram.py`, `lib/engram_client.py`, MCP fallback, agent coordination |
| Local sync export/import/status | `engram sync [--import \| --status] [--all] [--project PROJECT]` | `scripts/engram-sync.sh` git-jsonl mode |
| Cloud sync | `engram sync --cloud --project PROJECT` | `scripts/engram-sync.sh --cloud` |
| Cloud config | `engram cloud config --server URL` | `scripts/cos-engram-cloud-enroll` |
| Cloud enroll | `engram cloud enroll PROJECT [--rotate]` | `scripts/cos-engram-cloud-enroll` |
| Cloud serve | `engram cloud serve` | `docker/cos-worker/docker-compose.yml`, `scripts/cos-engram-cloud-docker-smoke` |
| Cloud upgrade | `engram cloud upgrade` | `scripts/cos-engram-cloud-enroll --upgrade` |
| Diagnostics | `engram doctor [--json] [--project P] [--check CODE]` | operator/doctor docs |

## Unsupported or non-contract command shapes

Do not add these to product docs, scripts, hooks, or tests:

- `engram search --json ...`
- `engram save --json ...`
- `engram save --title ... --content ...`
- `engram save ... --topic-key ...`
- `engram search --query ...`
- `engram get --json ...`
- `engram delete ...`
- `engram cloud delete ...`

Current Engram v1.15.x treats several unsupported flags as positional text
instead of returning a hard error. That makes stale docs dangerous: a command can
appear to succeed while saving/searching the wrong value.

## Implementation rules

1. Human/operator procedures may use human-readable CLI output.
2. Programmatic reads must use `lib/engram_http_client.py` or an MCP tool that
   returns structured objects.
3. Programmatic saves may use the positional CLI, but wrappers must synthesize a
   conservative result dict and never rely on undocumented JSON output.
4. Cloud sync must always pass `--project`; COS wrappers must never call
   `engram sync --cloud --all`.
5. GDPR erasure docs must name the absence of documented delete commands instead
   of inventing one. Actual erasure uses the installed version's MCP/admin/API
   path or a documented maintenance-mode DB procedure.

## Verification

```bash
python3 scripts/cos-engram-command-audit.py --fail-on-findings
python3 -m pytest tests/unit/test_engram_client.py tests/unit/test_safe_engram.py tests/audit/test_engram_command_contract.py -q
```
