---
evaluated_at: 2026-05-09 16:30 UTC
engram_id: pending
source_repo: https://github.com/langflow-ai/langflow
deepwiki_url: https://deepwiki.com/langflow-ai/langflow
analysis_depth: deep
classification: ASSESS
score: 7.4
adoption_kind: pattern-only, adapter-lab
license: MIT
---

# Deep Repo Scout — langflow-ai/langflow — 2026-05-09

## Stage 0 — Prior-work and corpus check

Langflow had not been evaluated as a tech-radar target in the durable radar corpus before this pass. The only prior repository hit was a broad security research mention listing Langflow among agent platforms; there was no `docs/03-PoCs/research/repo-scout/deep/*langflow*` artifact, no `external-tools-radar-*langflow*` addendum, no catalog entry in `docs/04-Concepts/patterns/ecosystem-tools.md`, and Engram search returned no previous `tech-radar/langflow` decision.

This report therefore adds Langflow as a new targeted Phase-4 radar item rather than refreshing an existing verdict.

## Stage 1 — Context-analysis primitive

| Dimension | Finding |
|---|---|
| Category | Visual AI workflow builder, agent/workflow runtime, FastAPI service, React flow UI, MCP-facing workflow deployment |
| COS relevance | High for visual flow-authoring UX, flow-to-API/MCP packaging, extension/bundle registry, and hosted workflow service boundaries |
| COS non-goal overlap | COS is a portable governance layer for coding agents; Langflow is an app/runtime for building and serving AI workflows |
| Decision pressure | Avoid importing an app/runtime into COS core; extract bounded patterns and compare future adapter-lab ideas |

## Stage 2 — Competitive-research primitive

Langflow sits in the same broad market as low-code AI app/workflow builders and agent platforms, not in the same narrow lane as COS hook/rule/skill governance. The useful comparison is against extraction targets already present in the radar:

| Comparison target | Langflow delta | COS action |
|---|---|---|
| Agno suite | Langflow is stronger on visual flow authoring and flow deployment; Agno is stronger as SDK/runtime vocabulary | Keep both as separate pattern sources |
| OpenSwarm | Langflow is a reusable workflow builder/runtime; OpenSwarm is a deliverable-specialist orchestration app | Extract routing/deliverable UX from OpenSwarm; extract visual flow and bundle UX from Langflow |
| Archon | Langflow has visual graph execution and app runtime; Archon focuses on coding-agent DAG mechanics | Do not replace COS TaskDAG with Langflow runtime |
| AgentGateway / MCP security tools | Langflow consumes and exposes MCP-facing workflows; gateway/security tools enforce network/policy boundaries | Treat Langflow as an adapter-lab candidate behind existing COS policy, not as a policy source |

## Stage 3 — License-first gate

| Gate | Result |
|---|---|
| Repository license | MIT |
| License guard | Safe: permissive, no restrictions |
| Archived | No |
| Activity gate | Pass: pushed on 2026-05-09 UTC |
| No-license gate | Not triggered |

Verdict: license allows code or pattern study, but adoption should remain pattern-only unless a future manifest row defines a bounded adapter with tests and rollback.

## Stage 4 — DeepWiki and metadata scout

DeepWiki was available and last indexed commit `bc927a` on 2026-05-08. It describes a Python/TypeScript system with three major layers: React 19 flow editor, FastAPI backend, and dynamic component registry / starter-project system. It also identifies MCP integration, workflow-to-API deployment, flow versioning, assistant features, and Python SDK surfaces.

GitHub metadata snapshot checked on 2026-05-09:

| Metric | Value |
|---|---:|
| Stars | 147,889 |
| Forks | 8,937 |
| Open issues / PRs | 924 |
| Default branch | `main` |
| Latest stable release | `v1.9.2`, published 2026-05-01 |
| Last push | 2026-05-09T12:35:14Z |
| Primary language | Python |
| Repo API size | 1,262,928 KB |

## Stage 5 — Repo-forensics primitive

A filtered shallow clone was inspected at commit `bc927abef25b`. The working tree contained 6,244 files and occupied about 308 MB locally.

| Area | Finding |
|---|---|
| Package topology | UV workspace with `langflow`, `langflow-base`, `lfx`, and `langflow-sdk` packages |
| Backend | FastAPI service under `src/backend/base/langflow`, service factories, SQLModel/Alembic database layer, auth service, flow execution APIs |
| Frontend | React 19 + TypeScript + Vite + `@xyflow/react`, Zustand stores, Jest/Playwright/Storybook tooling |
| Executor | `lfx` package provides component type system, graph processing, CLI, and `lfx-mcp` entry point |
| Tests | 1,378 test-related files under backend, frontend, SDK, and executor areas |
| CI/CD | Python, JS, TypeScript, smoke, integration, Docker, CodeQL, Mend, docs, release, and nightly workflows |
| Docker | Deployment compose includes backend/frontend/db/broker/result backend/celeryworker/prometheus/grafana support |
| Security posture | SECURITY.md, CodeQL, Mend, `.secrets.baseline`, explicit SSRF settings, auth tests, and public security advisories |

## Stage 6 — Reverse-engineer primitive

The reverse-engineering scan and manual source review found these integration surfaces:

| Surface | Evidence | Integration interpretation |
|---|---|---|
| CLI | `langflow = langflow.langflow_launcher:main`; `lfx = lfx.__main__:main`; `lfx-mcp = lfx.mcp.__main__:main` | Possible future operator-installed CLI adapter, not default bootstrap |
| API | FastAPI routers under `/api/v1`, `/agentic`, `/voice`, `/responses`, `/files`, `/variables`, `/mcp_projects` | Useful as examples for workflow deployment and MCP project lifecycle |
| Config | Large `LANGFLOW_*` env surface including auth, database, SSRF, CORS, telemetry, MCP composer, cache, superuser, and storage flags | Any adapter must project only explicit safe env vars, never import `.env` behavior wholesale |
| MCP | MCP server/client/composer code and docs; flows can become MCP tools | Relevant to COS MCP security, gateway, and fixture work |
| Dynamic code | Custom component validation and agentic assistant paths reach Python dynamic execution sinks | Strong reason to avoid default runtime adoption and require sandbox/policy wrappers |
| Auth | Cookie/bearer/API-key auth, superuser flows, websocket/SSE auth helpers | Useful as product reference, but not as COS auth substrate |

## Stage 7 — Threat-model primitive

| Threat | STRIDE | Severity | Why it matters for COS | Required mitigation before any adapter lab |
|---|---|---:|---|---|
| Generated/custom Python execution crosses trust boundary | Elevation of Privilege / Tampering | HIGH | Langflow intentionally supports user-defined code and has public advisories around dynamic execution paths | Adapter must run outside COS core with sandboxing, no shared credentials, and explicit opt-in |
| MCP tool exposure can widen tool-call blast radius | Spoofing / Information Disclosure / Elevation of Privilege | HIGH | Flow-as-tool is powerful but could bypass COS tool policies if mounted directly | Route through COS MCP scan/gateway policy and audit logs |
| Broad credential/env surface | Information Disclosure | HIGH | Many API-key and service credentials can be configured | Env allowlist, secret-ref indirection, no `.env` import, and redaction tests |
| File/storage readers and document processing | Information Disclosure / DoS | MEDIUM | File, S3, Google Drive, Docling/OCR paths can ingest large or sensitive content | Storage scope restrictions, size limits, provenance metadata, resource limits |
| Hosted/telemetry boundaries | Repudiation / Information Disclosure | MEDIUM | Telemetry and hosted/cloud paths may conflict with local-first project posture | Explicit telemetry-off and data-flow review |

## Stage 8 — Scoring and radar classification

| Criterion | Weight | Score | Rationale |
|---|---:|---:|---|
| Relevance | 30% | 8 | Strong reference for visual workflow authoring, flow packaging, MCP-facing deployments, extension bundles, and runtime UX |
| License | 25% | 10 | MIT, safe under current license policy |
| Activity | 20% | 10 | Pushed on evaluation day; active releases and high issue/PR velocity |
| Maturity | 15% | 8 | v1.9.2 stable release, large community, extensive tests/CI; public advisories show real security surface |
| Integration | 10% | 3 | App/runtime adoption would be heavy and risky; only bounded pattern extraction or adapter lab is appropriate |
| **Weighted total** | | **7.4/10** | **ASSESS / TRIAL-PATTERNS** |

### Adoption signals

| Signal | Value | Descriptor |
|---|---:|---|
| Issue velocity, 30 days | GitHub page capped at 100 recent issues/PRs | High issue activity |
| Release cadence | Latest stable `v1.9.2` on 2026-05-01; dev tags daily around 2026-05-06 to 2026-05-09 | Active release train |
| CI health | 6 success, 3 failure, 1 skipped in last 10 workflow runs | Mixed: core CI green, dependency-update workflows failing |

## What to extract

1. Visual graph-authoring UX for future COS flow explanations or policy-plan views.
2. Flow-to-API and flow-to-MCP packaging boundaries as adapter-lab references.
3. Bundle/extension registry mechanics, especially how starter projects and dynamic components are organized.
4. Settings surface taxonomy for separating safe runtime config from secrets, telemetry, and hosted boundaries.
5. Regression fixtures around MCP project lifecycle, auth, flow versioning, and custom code validation.

## What not to extract

- No default Langflow dependency in COS bootstrap, requirements, hooks, rules, or packaged runtime.
- No direct import of Langflow custom component execution into COS core.
- No shared `.env`, API keys, user database, telemetry settings, or local file storage between COS and a Langflow adapter lab.
- No bypass of COS MCP scan, gateway policy, credential policy, or audit logs.
- No claim that Langflow replaces COS skills, rules, hooks, Engram memory, SDD, or provider routing.

## Integration plan

| Phase | Action | Acceptance criteria |
|---|---|---|
| Radar only | Keep this report and addendum as durable evidence | Catalog entry links both artifacts |
| Pattern extraction | Write an architecture note only if a concrete COS visual-flow or MCP-fixture need appears | Patterns are described without runtime dependency |
| Adapter lab | Optional future local-only spike invoking Langflow as an external process | Manifest row, env allowlist, sandbox, MCP scan, audit log, rollback, and no default install |

## Raw metrics appendix

- Repo: `langflow-ai/langflow`
- Clone commit: `bc927abef25b`
- License: MIT
- Latest stable release: `v1.9.2` / 2026-05-01
- Last push: 2026-05-09T12:35:14Z
- Stars: 147,889
- Forks: 8,937
- Open issues/PRs: 924
- Source files under `src`: 4,647
- Test-related files under `src`: 1,378
- Config/build/deploy manifests found at depth <=3: 67
- Public security advisory observed: CVE-2026-33873 / GHSA-v8hw-mh8c-jxfc, authenticated code execution in Agentic Assistant validation

## Decision

Langflow is added to the radar as **ASSESS / TRIAL-PATTERNS** with adoption kind `pattern-only` and possible future `adapter-lab`. It is strategically valuable as a mature visual workflow and MCP-facing runtime reference, but direct runtime adoption is not justified for Cognitive OS core because it would import a large app surface, dynamic code execution, broad credentials, storage, telemetry, and hosted-control-plane concerns.
