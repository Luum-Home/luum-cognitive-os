# Safe Auto-Repair Actions (No Approval Needed)

These actions are reversible, do not touch data or code, and can be applied automatically
by the SRE agent without human approval.

## Container Restart

- **Trigger**: Container exited, OOM killed, or health check failing
- **Action**: `docker restart {container}`
- **Max retries**: 3 per run (then escalate to Level 3)
- **Cooldown**: Wait 15 seconds between retries
- **Verification**: Check `docker ps` and `docker logs {container} --since 30s` after restart

## Dependency Restart (Cascade)

- **Trigger**: Service logs show "Connection refused" or "ECONNREFUSED" to a dependency
- **Action**:
  1. Identify the dependency from the error (host:port mapping)
  2. Check if the dependency container is running: `docker ps --filter name={dep}`
  3. If not running: `docker restart {dependency_container}`
  4. Wait 15 seconds for dependency to stabilize
  5. Restart the original service: `docker restart {service_container}`
- **Dependency discovery**: Use `docker-compose.yml` `depends_on` or `cognitive-os.yaml project.infrastructure` to identify dependencies. Do NOT hardcode port-to-service mappings.

## Cache Service Connection Lost

- **Trigger**: Cache connection error, "ECONNREFUSED" on cache port, "connection lost"
- **Action**: Restart the cache container (Redis, Valkey, Memcached, etc.)
- **Post-action**: Restart affected services that depend on cache

## Database Connection Pool Exhausted

- **Trigger**: "connection pool exhausted", "MongoNetworkError", "too many connections"
- **Action**: Restart the affected service (NOT the database itself)
- **Rationale**: The connection pool is in the application, restarting the app resets it
- **If recurring (3+ times)**: Flag for code review -- likely a connection leak

## Database Connection Error

- **Trigger**: Database connection errors, "Too many connections", "Connection lost"
- **Action**: Restart the affected service
- **If database itself is down**: Restart the database container, wait for it to be healthy, then restart dependent services

## Auth Provider Token Issues

- **Trigger**: "401 Unauthorized" from auth provider, "Token is not active"
- **Action**: Restart the calling service (forces new token acquisition)
- **If auth provider itself is down**: Restart auth provider container, wait for health, then restart dependent services

## Message Broker Connection Lost

- **Trigger**: "connection error", "Channel closed", "Connection refused" to message broker
- **Action**: Restart the message broker container, wait 15s, then restart affected services
- **Warning**: Messages in-flight may be lost if not using persistent queues

## Disk Space Warning

- **Trigger**: "no space left on device", "ENOSPC"
- **Action**:
  1. `docker system prune -f` (remove stopped containers, unused images, build cache)
  2. Check space: `df -h /var/lib/docker`
  3. If still low: `docker volume prune -f` (remove unused volumes -- CAUTION with data volumes)
- **Never prune**: Named volumes with "data" or "db" in the name

## Health Check Failure

- **Trigger**: Container status shows "(unhealthy)" in `docker ps`
- **Action**:
  1. Check logs for the cause: `docker logs {container} --since 5m 2>&1 | tail -20`
  2. Restart the container: `docker restart {container}`
  3. Wait 30 seconds, check health again
- **If still unhealthy after restart**: Escalate to Level 3

## Node.js Unhandled Rejection

- **Trigger**: "UnhandledPromiseRejectionWarning", "Unhandled rejection"
- **Action**: Restart the Node.js service
- **If recurring**: Flag for code review -- missing error handling

## Java OutOfMemoryError

- **Trigger**: "java.lang.OutOfMemoryError", "GC overhead limit exceeded"
- **Action**: Restart the Java service
- **If recurring**: Flag for heap size review (JVM_OPTS)

## Go Panic

- **Trigger**: `panic:` followed by goroutine stack trace
- **Action**: Restart the Go service
- **Always**: Save the panic stack trace to Engram for code review

---

# Unsafe Actions (REQUIRE APPROVAL)

These actions modify data, code, or infrastructure and MUST have human approval.

## Code Changes

- Any modification to source code files
- Adding/removing dependencies
- Updating package versions
- Modifying build configurations

## Database Operations

- Running SQL queries
- Running database commands
- Database migrations
- Data fixes or corrections
- Cache invalidation beyond simple restart

## Configuration Changes

- Modifying .env files
- Changing docker-compose.yml
- Updating environment variables
- Modifying proxy/gateway configs
- Changing auth provider settings

## Infrastructure Changes

- Modifying docker-compose.yml
- Adding/removing containers
- Changing network settings
- Modifying volume mounts
- Port mapping changes

## Message Queue Operations

- Purging queues
- Modifying queue bindings
- Changing exchange configurations
- Manual message publishing

## Security Operations

- Anything involving API keys or secrets
- Certificate changes
- Firewall/network policy changes
- User/role modifications in auth provider
