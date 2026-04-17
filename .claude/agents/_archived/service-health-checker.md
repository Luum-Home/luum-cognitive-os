---
model: sonnet
---

# Service Health Checker Agent

## Mission

Verify health status of all services in the local stack.
Report which are UP, which are DOWN, and suggest corrective actions.

## Verification Process

### 1. Docker Containers
Verify that infrastructure containers are running:
```bash
docker ps --format '{{.Names}} {{.Status}}'
```

Check `cognitive-os.yaml -> project.infrastructure` or `docker-compose.yml` for expected containers.

### 2. Application Services

For each service in the project, check health endpoints:

```bash
# Common health check patterns:
curl -s http://localhost:{port}/health
curl -s http://localhost:{port}/actuator/health
curl -s http://localhost:{port}/api/health
```

Read service ports from `cognitive-os.yaml -> project.infrastructure.services` or from `docker-compose.yml` port mappings.

### 3. Service Connectivity

Verify that the API gateway/BFF can reach backend services by checking its health endpoint and logs.

## Report Format

```
=== Project Stack Health Report ===

INFRASTRUCTURE:
  [{status}] {service_name} ............ port {port}
  ...

SERVICES:
  [{status}] {service_name} ............ port {port}
  ...

ACTIONS REQUIRED:
  1. {service}: {suggested action}
  ...
```

## Common Corrective Actions

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| Database not starting | Port occupied | `lsof -i :{port}` and kill process |
| Auth service 503 | Database not ready | Wait 30s, auth depends on database |
| Service timeout | Dependency not ready | Verify dependencies first |
| Gateway 401 | Auth not configured | Verify auth env vars |
| Database auth fail | Wrong credentials | Verify credentials in .env |
| Message broker refused | Not started | `docker-compose up -d {broker}` |
