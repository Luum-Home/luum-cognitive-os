---
type: concept-synthesis
source: docs/04-Concepts/architecture/observability-backend-evaluation-2026-04-24.md
provenance: "Decide whether MLflow can replace Langfuse in Cognitive OS while keeping the observability stack lightweight, portable, and real."
---

## What it is
Executive decision (2026-04-24): MLflow replaces Langfuse only for the default outcome-observability path, not as a full Langfuse replacement. Durable direction: JSONL as always-on local audit log, MLflow as default lightweight exporter, OpenTelemetry GenAI semantics as the trace portability layer, with Langfuse/Opik/Phoenix/OpenLIT/Helicone/Portkey/Braintrust/Weave etc. as optional exporters.

## Key mechanics
- Product rule: choose the Cognitive OS event contract first, then export to tools. Required default events: `agent.completion`, `quality.gate`, `policy.decision`, `capability.selection`, `provider.invocation`, `tool.use`, `cost.summary`, `session.summary` — all representable as append-only JSONL.
- Replacement boundary: MLflow covers completion trust score (`MLflowBridge.log_agent_completion()`), success/failure, skill/task identity, token/cost summaries (JSONL+MLflow), no-Docker degraded mode. NOT covered by MLflow alone: trace/span/generation UI, hosted team dashboard, gateway-level observability — these stay optional adapters.
- Evaluation matrix reviewed ~25 tools (Langfuse, Phoenix, OpenLIT, Opik, Helicone, Portkey, LangSmith, Braintrust, Weave, TruLens, DeepEval, Ragas, Lunary, Laminar, Agenta, OpenLLMetry/Traceloop, Langtrace, Grafana AI Observability, SigNoz, Jaeger, Athina, Galileo, Humanloop) and classified each as Core/Default exporter/Compatibility layer/Optional extension.
- Decision (2026-04-24, ADR-058): Langfuse deprecated — 6-service stack consumed ~1.34 GiB RAM / ~1380% CPU aggregate idle, volumes preserved for rollback until Phase 4. Arize Phoenix adopted as `mode: pip`, on-demand via `skills/phoenix-trace-ui/`; ELv2 server / Apache-2.0 OTel bridge; ~150 MiB single-process footprint. MLflow unchanged (default exporter). Opik/Helicone/OpenLIT/Laminar/Logfire/Weave/OpenLLMetry unchanged. Self-improvement loop (`skills/analyze-improvements/`) unchanged — reads JSONL from `.cognitive-os/metrics/` as authoritative feedback source; no trace-sink backend participates in PITER.
- Phased migration: Phase 0 (2026-04-24) containers stopped + catalog updated; Phase 1 (2026-05-15) Phoenix dependency lane + `skills/phoenix-trace-ui/`; Phase 2 (2026-05-30) `lib/record_completion.py` trace sink migrated to OTel/Phoenix; Phase 3 (2026-06-15) Langfuse removed from Compose/hooks; Phase 4 (2026-06-30) Langfuse volumes deleted, ADR-058 closed.
- Implementation consequences: `langfuse.mode: disabled`; `mlflow.mode: pip`; outcomes mirrored JSONL->MLflow via Stop-time `mlflow-sync.sh` by default, direct hot-path MLflow writes opt-in via `COS_MLFLOW_HOTPATH_ENABLED=1` so optional observability never blocks completion recording.

## Relations & where used
ADR-058 (Langfuse->Phoenix migration ADR), `docs/04-Concepts/architecture/infrastructure-service-catalog.md` (service catalog decision entries).

## Status / caveats
Explicit OpenTelemetry exporter deferred until the COS event contract is stable enough to avoid duplicated trace logic.
