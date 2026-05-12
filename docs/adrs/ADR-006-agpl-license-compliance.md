---
adr: 6
title: AGPL License Compliance -- Replace Redis and MinIO
status: accepted
implementation_status: partial
date: '2026-03-23'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit pending/deferred/planned scope
partial_remaining: License enforcement for additional blocked tools is tracked by ADR-267; this ADR remains partial only for the broader compliance-enforcement follow-up beyond the original Redis/MinIO/AutoCodeRover replacements.
remaining_in_scope: true
partial_remaining_basis: manual follow-up mapping after audit
follow_up_adr: ADR-267
---

# ADR-006: AGPL License Compliance -- Replace Redis and MinIO

**Date:** 2026-03-23
**Status:** Accepted
**Commits:** 1a7e421 (initial release included replacements)
**Engram IDs:** 1567, 1575

## Context

Cognitive OS was being prepared for SaaS distribution. A full license audit of the Docker infrastructure stack revealed three RED issues: Redis had changed to tri-license (AGPL/RSAL/SSPL) in 2025, MinIO was AGPL-3.0, and AutoCodeRover was GPL-3.0. AGPL and SSPL licenses can force source disclosure or block commercial SaaS use entirely. The remaining stack (Langfuse, LiteLLM, SeaweedFS, etc.) was MIT/Apache 2.0/BSD and fully SaaS-compatible.

## Decision

Replace all AGPL-licensed infrastructure components with permissively-licensed alternatives:

- **Redis 7 replaced with Valkey 8** (BSD-3, Linux Foundation fork). Valkey is a drop-in Redis replacement using the same protocol and CLI. Langfuse environment variables (REDIS_HOST, REDIS_PORT, REDIS_AUTH) retain their Redis names since Langfuse expects them, even though the backing service is Valkey.
- **MinIO replaced with SeaweedFS** (Apache 2.0). SeaweedFS provides an S3-compatible API. Its `server` command combines master, volume, filer, and S3 gateway in a single process. Runs on port 8333 with a credentials config file at `infra/seaweedfs/s3.json`.
- **AutoCodeRover (GPL-3.0) rejected** in favor of SWE-agent or Agentless (both MIT).
- **golangci-lint (GPL-3.0) kept** as a CI-only tool (not distributed with the product).

A blanket policy was established: block AGPL/SSPL/GPL dependencies for any component distributed with the OS. CI-only tools are exempt.

## Alternatives Considered

- **Keep Redis with commercial license**: Redis offers RSAL for commercial use, but it adds licensing complexity and cost. Valkey is functionally identical and free.
- **Use cloud S3 instead of SeaweedFS**: Cloud S3 removes the self-hosted requirement but adds external dependency and cost. SeaweedFS maintains the self-contained Docker stack.
- **Ignore AGPL for internal use**: AGPL obligations only trigger on network distribution, so internal-only use would be safe. However, the SaaS roadmap made this a ticking time bomb.

## Consequences

- All infrastructure components are now MIT, Apache 2.0, or BSD-3 licensed, safe for SaaS distribution.
- The AGPL blocking policy was later codified into the `cos` package manager's security audit pipeline, which automatically rejects packages with AGPL/SSPL/GPL licenses at install time.
- Five additional tools were later blocked during the tech radar evaluation (Mar 28) for AGPL violations: Firecrawl, and four others from the awesome-claude-code ecosystem scan.
- The policy created a clear precedent: every new dependency evaluation starts with a license check.
