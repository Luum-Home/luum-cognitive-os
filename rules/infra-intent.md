<!-- SCOPE: os-only -->
<!-- TIER: 2 -->
# Infrastructure Intent Detection Rules

## Purpose

The infra-intent-detector hook scans agent prompts for infrastructure keywords and suggests matching components from the project stack. It is advisory only — it never blocks execution.

## Keyword-to-Infrastructure Mapping

| Category | Keywords | Where to Find Stack Component |
|----------|----------|-------------------------------|
| **Database** | store, persist, save, database, collection, table, CRUD, query, migration, schema, entity, repository | `cognitive-os.yaml -> project.infrastructure.database` or `docker-compose.yml` |
| **Auth** | login, register, user accounts, authentication, password, JWT, session, oauth, token, authorize, sign-up, sign-in | `cognitive-os.yaml -> project.infrastructure.auth` |
| **Real-time** | real-time, websocket, live, sync, multiplayer, collaborative, socket.io, SSE | Check `docker-compose.yml` for WebSocket/SSE infrastructure |
| **Storage** | upload, file, image, S3, bucket, asset, blob, attachment, media | Check `docker-compose.yml` for S3-compatible storage (SeaweedFS/MinIO/GCS) |
| **Queue** | async, background, queue, event, message, kafka, rabbitmq, publish, subscribe, worker, consumer, producer | `cognitive-os.yaml -> project.infrastructure.messaging` |
| **Cache** | cache, valkey, redis, fast lookup, session store, TTL, rate limit | `cognitive-os.yaml -> project.infrastructure.cache` |
| **Search** | search, full-text, index, elasticsearch, algolia, filter, facet | Check `docker-compose.yml` for search engine |

## Behavioral Rules

1. **Advisory only** — The hook outputs suggestions to stderr and exits 0. It never blocks the agent.
2. **Config-driven** — Suggestions reference `cognitive-os.yaml` and `docker-compose.yml` for actual infrastructure, not hardcoded values.
3. **Mock-first** — Any new infrastructure integration should have a mock before real integration (if project uses this pattern).
4. **Logging** — All detections are logged to `.cognitive-os/metrics/infra-detections.jsonl` for trend analysis.
5. **No false positives on common words** — Keywords like "save" or "store" in non-infrastructure contexts may trigger. The agent should evaluate suggestions critically.

## Adding New Categories

To add a new infrastructure category:

1. Add the keyword pattern to `infra-intent-detector.sh` following the existing format
2. Add a suggestion string that references where to find the stack component in config
3. Update this rules file with the new mapping row
4. Update `.cognitive-os/docs/04-Concepts/root/infra-intent.md` with the new category

## Contextual Trigger

- When work relates to Infrastructure Intent Detection Rules.
