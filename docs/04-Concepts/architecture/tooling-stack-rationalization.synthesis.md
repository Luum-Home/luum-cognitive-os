---
type: concept-synthesis
source: docs/04-Concepts/architecture/tooling-stack-rationalization.md
provenance: "Keep Cognitive OS sophisticated inside but lightweight, portable, and honest outside — avoid becoming a bundle of heavyweight services by default."
---

## What it is

Decision framework classifying every external tool COS integrates into one of four positions, so power stays composable instead of bloating the default install.

## Key mechanics

**4 positions**: Core dependency (required, fast, local-first, default-CI-tested), Compatibility adapter (swappable behind a stable COS contract), Optional extension (opt-in, documented, tested in explicit lanes), Reference only (prior art, not a runtime expectation).

**Current tool classification** (mode / conclusion): LiteLLM (pip, optional gateway), Bifrost (disabled, reference), Langfuse (disabled, too many containers for first-run), MLflow (pip, lighter default observability candidate), Opik (cloud, optional/cloud extension), Valkey (on_demand, only Redis-compatible backend, file fallback matters), Cognee (pip, optional), MemU (pip, optional pending non-overlap proof vs Engram/Cognee), NeMo Guardrails (pip, optional in-process), AutoMaker (on_demand, optional UI reference), Jupyter (pip, optional), Webhook Trigger (profile-gated), COS Dashboard (profile-gated), Crawl4AI (cli, optional/task-triggered), DeepEval/RAGAS/Promptfoo (package/skill, explicit evaluation extensions).

**Opik finding**: local self-hosted stack needs MySQL+Redis+ClickHouse+ZooKeeper+MinIO+backend+frontend — too heavy for default adoption. Full trace ingestion tested only against official full stack or cloud/configured endpoint; reference backend health-checked via testcontainers only. Remains optional extension, not center of gravity.

**Lighter observability alternatives evaluated**: JSONL outcome metrics + local reports (zero deps, needs better viz), OpenTelemetry/OpenLIT (vendor-neutral, needs collector choice), MLflow local mode (lighter, not agent-native), Langfuse (heavy, disabled), Helicone/Portkey-style gateway observability (risks pulling architecture toward vendor-centric).

**Langfuse-to-MLflow replacement boundary** (what's covered): completion trust score, success/failure, skill/task identity, cost/token summaries, no-crash degraded mode — all covered via `MLflowBridge.log_agent_completion()` and related methods. NOT equivalent: Langfuse spans/generations UI, hosted collaboration dashboard, authenticated ingestion API.

**Product rule for new tools** (7 questions in PR): user-facing promise strengthened? core/compatibility/extension/reference-only? lighter alternative considered? runs without Docker in default path? smallest real test proving integration? vendor/API-change contingency? duplicate of existing component? For services specifically: no classification, no service — every new `docker-compose.cognitive-os.yml` service must be classified in Infrastructure Service Catalog and covered by `tests/integration/test_service_health.py`.

**Next inventory pass priorities**: Observability (Opik, Langfuse, MLflow, OpenLIT, Helicone, AgentOps) — High; Gateway/routing (LiteLLM, Portkey, Bifrost) — High; Memory (Engram, Cognee, MemU, file-backed) — High; Guardrails/security (NeMo, LLM Guard, Guardrails AI, Promptfoo, Aguara, Semgrep, Parry) — High; Evaluation (DeepEval, RAGAS, Promptfoo) — Medium; Compute/research (Jupyter, Crawl4AI, E2B) — Medium.

## Relations & where used

`docs/04-Concepts/architecture/infrastructure-service-catalog.md` (service-by-service contract), `observability-backend-evaluation-2026-04-24.md` (2026 research matrix), `tests/integration/test_service_health.py`, `cognitive-os.yaml` (mode declarations).

## Status / caveats

This is a living rationalization; the "Next Inventory Pass" table lists tools still awaiting the same rigor. Goal explicitly stated: not to remove powerful tools, but to keep power composable — default light, extension-rich, kernel never confused with optional infrastructure.
