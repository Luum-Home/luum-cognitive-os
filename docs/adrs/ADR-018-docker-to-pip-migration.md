# ADR-018: Docker-to-pip Migration -- Service Infrastructure Change

**Date:** 2026-04-11 to 2026-04-13
**Status:** Accepted
**Commits:** b79e850, 767b772
**Engram IDs:** 4819, 4820, 4826

## Context

The Docker infrastructure was consuming 100GB+ disk cache and 4-6GB RAM on a 16GB MacBook. Measured footprint: 4.75GB images + 2.95GB volumes = ~7.7GB total. The docker-compose.cognitive-os.yml defined 21 services, but analysis showed 18 of them could be replaced with pip-installed libraries or cloud APIs. Many containers were literally just pip wrappers -- memu, cognee, and litellm were already in requirements.txt. Opik was already configured to use its cloud API with the container serving no purpose.

## Decision

Migrate Docker services to pip-installed libraries in two phases:

**Phase 1 -- Quick Wins (7 services)**:
- Langfuse (6 containers: web, worker, clickhouse, postgres, redis, minio) replaced by MLflow (`pip install mlflow`). Savings: ~2.2GB RAM.
- nemo-guardrails, memu, jupyter, opik-backend: added to requirements.txt with MIGRATED FROM DOCKER comments.
- LiteLLM: already in requirements.txt, container marked as pip-migratable.
- Docker Compose services annotated with MIGRATED TO PIP comments but NOT deleted (kept for CI reference).

**Phase 2 -- Refactor (3 services)**:
- Bifrost: removed (LiteLLM covers its functionality for the current scale).
- Cognee: migrated to pip.
- LiteLLM container: disabled in favor of library mode.

**Phase 3 -- Keep (3 services)**:
- Paperclip + PostgreSQL: genuine web application, no pip equivalent.
- Valkey: file-based fallback already exists in agent_bus.py, but kept for production deployments.

**Key discovery**: `memu-ai` does not exist on PyPI; the correct package is `memu` (v2.1.4).

## Alternatives Considered

- **Keep Docker for everything**: Consistent deployment model. Rejected because the resource consumption was unsustainable on a 16GB development machine.
- **Use Docker Desktop resource limits**: Cap container memory. Rejected because 21 services competing for limited memory leads to OOM kills and instability.
- **Move to Kubernetes/Podman**: Better orchestration but does not solve the fundamental problem of running unnecessary containers. The services themselves were redundant.
- **Cloud-hosted alternatives for everything**: Remove self-hosted entirely. Rejected because it defeats the self-contained architecture goal and adds external dependencies.

## Consequences

- ~5GB RAM and ~7.7GB disk freed from Docker overhead.
- `cognitive-os.yaml` service modes updated: services marked as `pip`, `cloud`, or `disabled` instead of `always`/`optional`.
- The infra-health rule was updated with a "Pip-Installed Services" section.
- 20 behavior tests validate the migration state.
- The migration established a preference: pip-first for development, Docker for production deployment. Smart infrastructure (`lib/smart_infra.py`) manages the distinction.
