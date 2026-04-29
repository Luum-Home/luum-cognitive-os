# Observability Backend Evaluation

> Date: 2026-04-24
> Purpose: decide whether MLflow can replace Langfuse in Cognitive OS, and keep the observability stack lightweight, portable, and real.

## Executive Decision

MLflow should replace Langfuse only for the default Cognitive OS outcome-observability path. It should not be documented or implemented as a full Langfuse replacement.

The durable product direction is a Cognitive OS observability contract with adapters:

- JSONL remains the always-on local audit log.
- MLflow is the default lightweight local metrics and run-summary exporter.
- OpenTelemetry GenAI semantics should become the portability layer for trace-shaped data.
- Langfuse, Opik, Phoenix, OpenLIT, Helicone, Portkey, Braintrust, Weave, and similar tools remain optional exporters or integration targets.

This preserves the product promise: governance, verification, and portability without forcing every project to run heavyweight observability infrastructure.

## Replacement Boundary

| Capability | Default replacement | Status | Notes |
|------------|---------------------|--------|-------|
| Completion trust score | MLflow | Covered | `MLflowBridge.log_agent_completion()` logs raw and normalized trust score. |
| Completion success/failure | MLflow | Covered | Logged as numeric metric and status param. |
| Skill/task identity | MLflow | Covered | Skill, task type, task ID, and model are logged as params. |
| Token and cost summaries | JSONL + MLflow | Covered | Existing JSONL-backed metrics can sync to MLflow. |
| No-Docker degraded mode | JSONL + MLflow no-op behavior | Covered | Missing MLflow must never block runtime completion. |
| Trace/span/generation UI | Optional exporter | Not covered by MLflow alone | Keep Langfuse/Phoenix/OpenLIT/Opik-style integrations behind adapters. |
| Hosted team dashboard | Optional exporter | Not covered by MLflow alone | Not part of the default wedge. |
| Gateway-level observability | Optional gateway adapter | Not covered by MLflow alone | Helicone/Portkey/LiteLLM-style surfaces must not make the runtime model-centric. |

## Product Rule

Do not choose an observability backend as the product center. Choose the Cognitive OS event contract first, then export to tools.

Required default events:

- `agent.completion`
- `quality.gate`
- `policy.decision`
- `capability.selection`
- `provider.invocation`
- `tool.use`
- `cost.summary`
- `session.summary`

Every event should be representable in append-only JSONL. Exporters may add richer semantics, but they must not become the only source of truth.

## Evaluation Matrix

| Tool | Role | Default position | Rationale |
|------|------|------------------|-----------|
| Cognitive OS JSONL metrics | Local source of truth | Core | Already portable, testable, low-friction, and independent of vendors. |
| MLflow | Lightweight local outcome metrics | Default exporter | Good for local runs, metrics, experiments, and summaries; not enough for full LLM trace UX. |
| OpenTelemetry GenAI | Vendor-neutral trace schema | Compatibility layer | Best long-term anti-lock-in layer for trace-shaped events. |
| Langfuse | LLM observability platform | Optional extension | Strong tracing/evals/prompt workflows, but too heavy for default local adoption. |
| Arize Phoenix | Open-source LLM observability/evals | Optional extension | Strong self-hosted candidate for traces and evals. |
| OpenLIT | OTel-native LLM observability | Optional extension | Good alignment with portability through OpenTelemetry. |
| Opik | LLM tracing/evaluation platform | Optional/cloud extension | Useful, but local stack is too heavy for default onboarding. |
| Helicone | Gateway observability | Optional gateway extension | Useful when gateway is the control point; must not become model-centric core. |
| Portkey | Gateway, guardrails, observability | Optional gateway extension | Strong gateway story; keep behind capability/gateway adapters. |
| LangSmith | LangChain ecosystem observability | Optional ecosystem adapter | Valuable for LangChain-heavy teams, not framework-agnostic enough for core. |
| Braintrust | Evals and observability | Optional evaluation extension | Strong eval workflows; default should remain backend-neutral. |
| W&B Weave | Tracing/evals for AI apps | Optional extension | Useful for teams already using W&B. |
| TruLens | Evaluation instrumentation | Optional eval extension | Better as an eval adapter than a default observability backend. |
| DeepEval | Evaluation framework | Optional eval extension | Useful for tests and quality gates, not runtime tracing source of truth. |
| Ragas | RAG evaluation | Optional eval extension | Domain-specific evaluation extension. |
| Lunary | LLM observability/platform | Optional extension | Useful hosted/self-hosted surface, not core. |
| Laminar | LLM observability/evals | Optional extension | Promising but should stay adapter-backed. |
| Agenta | Prompt/eval platform | Optional extension | Useful for prompt lifecycle workflows. |
| OpenLLMetry/Traceloop | OTel instrumentation | Compatibility/reference | Good implementation reference for OTel-first traces. |
| Langtrace | OTel-style LLM tracing | Optional/reference | Useful for OTel ecosystem comparison. |
| Grafana AI Observability | OTel/Grafana stack | Optional enterprise extension | Strong if team already runs Grafana. |
| SigNoz | OTel observability backend | Optional extension | Viable backend for OTel events. |
| Jaeger | Distributed tracing backend | Optional/reference | Lightweight trace backend but not LLM-native. |
| Athina | AI observability/evals | Optional extension | Useful vendor comparison. |
| Galileo | AI evaluation/observability | Optional extension | Strong platform, not default local path. |
| Humanloop | Prompt management/evals | Optional extension | Prompt lifecycle integration, not OS-level source of truth. |

## License And Dependency Doctrine

The default stack should prefer permissive, lightweight, local-first components. Tools with heavy service graphs, restrictive licenses, or cloud-first assumptions can still be valuable, but they must remain explicit extensions.

For this repository:

- Valkey remains the only Redis-compatible backend.
- ClickHouse-backed platforms should be optional because they are powerful but operationally heavy.
- Docker Compose services should not become default unless they prove a core product claim.
- Pip/local exporters are acceptable only when runtime degrades gracefully if they are absent.
- Gateway tools must be wrapped by capability profiles so Cognitive OS remains capability-centric, not model/vendor-centric.

## Implementation Consequences

1. Keep `langfuse.mode: disabled` in `cognitive-os.yaml` unless a team explicitly opts into it.
2. Keep `mlflow.mode: pip` as the lightweight default observability exporter.
3. Mirror completion outcomes from JSONL to MLflow through the Stop-time `mlflow-sync.sh` exporter by default; direct `record_completion` hot-path MLflow writes are opt-in with `COS_MLFLOW_HOTPATH_ENABLED=1` so optional observability cannot block agent completion recording.
4. Keep Langfuse tests only for Langfuse-specific optional-extension behavior.
5. Move product-claim tests from Langfuse to JSONL/MLflow when they assert outcome metrics rather than Langfuse UI semantics.
6. Add an explicit OpenTelemetry exporter only after the Cognitive OS event contract is stable enough to avoid duplicated trace logic.

## Research Sources

- [MLflow Tracing](https://mlflow.org/docs/latest/genai/tracing)
- [Langfuse Observability Overview](https://langfuse.com/docs/observability/overview)
- [Langfuse Documentation](https://langfuse.com/docs)
- [Arize Phoenix Documentation](https://arize.com/docs/phoenix/)
- [Arize Phoenix GitHub](https://github.com/arize-ai/phoenix)
- [OpenLIT Documentation](https://docs.openlit.io/)
- [OpenLIT](https://openlit.io/)
- [Comet Opik Documentation](https://www.comet.com/docs/opik)
- [Comet Opik Product](https://www.comet.com/site/products/opik/)
- [Helicone Open Source Reference](https://docs.helicone.ai/references/open-source)
- [Helicone AI Gateway](https://docs.helicone.ai/gateway)
- [LangSmith Observability](https://docs.langchain.com/langsmith/observability)
- [Braintrust AI Observability](https://www.braintrust.dev/blog/what-is-ai-observability)
- [Weights & Biases Weave](https://weave-docs.wandb.ai/)
- [TruLens](https://www.trulens.org/)
- [DeepEval](https://deepeval.com/)
- [Ragas Documentation](https://docs.ragas.io/)
- [Ragas Observability](https://docs.ragas.io/en/v0.3.5/howtos/observability/)
- [Portkey AI Gateway](https://portkey.ai/docs/product/ai-gateway)
- [Portkey Open Source](https://portkey.ai/docs/product/open-source)
- [Lunary Observability](https://docs.lunary.ai/docs/features/observability)
- [Lunary OpenTelemetry Integration](https://lunary.ai/docs/integrations/opentelemetry/overview)
- [Laminar Documentation](https://docs.laminar.sh/)
- [Laminar](https://laminar.sh/)
- [Agenta Documentation](https://docs.agenta.ai/)
- [Agenta OpenTelemetry Guide](https://agenta.ai/blog/the-ai-engineer-s-guide-to-llm-observability-with-opentelemetry)
- [OpenLLMetry Introduction](https://www.traceloop.com/docs/openllmetry/introduction)
- [Traceloop Integration](https://docs.traceloop.com/docs/openllmetry/integrations/traceloop)
- [Langtrace Introduction](https://www.langtrace.ai/blog/introducing-langtrace)
- [Langtrace Concepts](https://docs.langtrace.ai/concepts)
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OpenTelemetry](https://opentelemetry.io/)
- [Grafana AI Observability](https://grafana.com/docs/grafana-cloud/machine-learning/ai-observability/)
- [SigNoz AI Observability](https://signoz.io/observability-for-ai-native-companies/)
- [Jaeger](https://www.jaegertracing.io/)
- [Athina Documentation](https://docs.athina.ai/)
- [Galileo Documentation](https://docs.galileo.ai/)
- [Humanloop Prompt Management](https://humanloop.com/docs/prompt-management)

---

## Decision — 2026-04-24

**Outcome: Arize Phoenix is adopted as the new optional self-hosted observability
extension, replacing Langfuse.** Langfuse is deprecated with a phased removal
plan through 2026-06-30.

Recorded in: `docs/adrs/ADR-058-observability-migration-langfuse-to-phoenix.md`.

### Summary

- **Langfuse** — deprecated 2026-04-24. Containers stopped (the 6-service stack
  consumed ~1.34 GiB RAM and ~1380 % CPU aggregate idle). Volumes preserved
  until Phase 4 of the migration for rollback. Compose entries removed in
  Phase 3 (target 2026-06-15).
- **Arize Phoenix** — adopted as `mode: pip`. Launched on-demand via
  `skills/phoenix-trace-ui/` (Phase 1 pending). Wins on: Apache 2.0, no Docker,
  LLM-native OTel spans, ~150 MiB single-process footprint, active maintenance,
  ecosystem portability.
- **MLflow** — unchanged. Remains the default lightweight outcome exporter.
- **Opik / Helicone / OpenLIT / Laminar / Logfire / Weave / OpenLLMetry** —
  unchanged relative to the analysis above. None displaced as a result of
  this decision.
- **Self-improvement loop** — unchanged. `skills/analyze-improvements/`
  continues to read JSONL from `.cognitive-os/metrics/` as the authoritative
  feedback source. No trace-sink backend participates in PITER.

### Phased migration

1. **Phase 0 — 2026-04-24 (this doc pin):** containers stopped; catalog +
   config updated; ADR-058 recorded.
2. **Phase 1 — target 2026-05-15:** Phoenix package added to
   `pyproject.toml` observability extras, `skills/phoenix-trace-ui/` authored.
3. **Phase 2 — target 2026-05-30:** `lib/record_completion.py` trace sink
   migrated from Langfuse SDK to OTel exporter (Phoenix).
4. **Phase 3 — target 2026-06-15:** Langfuse removed from
   `docker-compose.cognitive-os.yml` and `hooks/*`.
5. **Phase 4 — target 2026-06-30:** Langfuse volumes deleted; ADR-058 closed
   as Implemented.

See ADR-058 for full rationale, alternatives analysis, consequences, and
rollback strategy.
