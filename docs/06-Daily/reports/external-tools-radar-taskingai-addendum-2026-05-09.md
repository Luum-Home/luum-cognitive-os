---
report_type: external-tools-radar-addendum
subject: TaskingAI/TaskingAI
generated_at: 2026-05-09
status: hold-pattern-only
source_artifacts:
  - .cognitive-os/reports/repo-scout/TaskingAI_TaskingAI.md
  - .cognitive-os/reports/repo-scout/TaskingAI_TaskingAI.analysis.json
  - .cognitive-os/reports/repo-scout/TaskingAI_TaskingAI.raw.json
  - docs/03-PoCs/research/repo-scout/deep/TaskingAI__TaskingAI-2026-05-09.md
related_docs:
  - docs/04-Concepts/patterns/ecosystem-tools.md
  - manifests/external-tools-adoption.yaml
---

# External Tools Radar TaskingAI Addendum — 2026-05-09

## Decision

Add [TaskingAI/TaskingAI](https://github.com/TaskingAI/TaskingAI) to the tech radar as **HOLD / pattern-only**.

TaskingAI is worth deeper analysis because it packages several AI-application primitives in one Apache-2.0 repository: provider routing, model catalogs, RAG/data collection flows, tool/plugin bundles, Python FastAPI services, a React console, and Docker Compose deployment. It is not a runtime adoption candidate today because the upstream repo is stale by the repo-scout gate: latest GitHub API `pushed_at` is **2024-12-02**, latest release is **v0.3.0 on 2024-06-03**, and recent concluded GitHub Actions runs are failing.

## Deep-analysis stages completed

| Stage | Result |
|---|---|
| Prior-memory check | Engram search found no prior TaskingAI radar evaluation for this project. |
| Current source check | GitHub page/API reviewed on 2026-05-09; GitHub reports Apache-2.0 license, ~5.4k stars, 358 forks, and 43 open issues. |
| License gate | PASS: Apache-2.0; `license_guard.check_and_enforce` returned safe. |
| Shallow clone forensics | PASS: local clone scanned; 1,648 files and 103,302 counted lines. |
| Architecture scan | Multi-service FastAPI/React stack: backend, inference, plugin, frontend, Nginx, Postgres/pgvector, Redis. |
| Test/build smoke | Python `compileall` passed for backend/inference/plugin app trees. Frontend build skipped because `npm` is unavailable in this runtime. |
| Security scan | Advisory concern: CI workflows contain hardcoded crypto-like env values; do not reuse. No first-party security scanner config found in shallow scan. |
| Radar merge | Added canonical HOLD entry to `docs/04-Concepts/patterns/ecosystem-tools.md`; manifest marks it pattern-only and disallowed as default dependency. |

## What COS should learn from it

1. **Provider resource catalogs** — TaskingAI keeps model/provider metadata in structured YAML resources. COS can study this shape for future provider-capability manifests while keeping ADR-049 direct SDK/provider adapters.
2. **Tool bundle surface** — `plugin/bundles/*` demonstrates a broad catalog of externally-backed tools with bundle-specific execution code and metadata. COS should compare this with skills, MCP tools, and the tool-discovery gate before implementing any catalog expansion.
3. **Service split** — `backend`, `inference`, and `plugin` are separately deployable services behind Docker Compose. Useful as a service-boundary reference, not as a dependency.
4. **BaaS mental model** — TaskingAI separates server-side AI logic from client applications through REST and SDKs. This may inform future COS remote/service runtime UX without changing COS's governance-first scope.

## Why HOLD, not TRIAL

- The activity gate is decisive: latest push is 2024-12-02, which is more than 12 months before 2026-05-09.
- Latest release is v0.3.0 from 2024-06-03; no current release train is visible.
- Recent concluded CI runs are failures in the GitHub API snapshot.
- Full-stack adoption would introduce a BaaS product and runtime infrastructure, which conflicts with COS's current external-tool doctrine: adopt commodity mechanisms behind adapters, but keep COS governance semantics first-party.

## Follow-up trigger

Revisit if upstream resumes releases/green CI or if COS opens a dedicated app-agent BaaS comparison lane. Until then, TaskingAI remains a pattern source only.
