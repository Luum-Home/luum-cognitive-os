# Cloud Worker Runtime Tooling Research — 2026-05

> Companion research for the headless/cloud deployment path. This document does
> not approve a production dependency; it narrows the technology search for the
> future `cos run-task`, `cos worker`, and queue-backed runtime surfaces.

## Related Plan

The execution plan is [`Headless and Clustered Runtime Plan`](../../.cognitive-os/plans/architecture/headless-clustered-runtime-plan.md).
This research is complementary: it evaluates event, queue, and durable workflow
options without making the local product heavy.

## Decision Frame

Cognitive OS should not add an orchestration platform before it has a stable
headless task contract:

```text
task payload -> isolated workspace -> optional provider/agent execution -> quality gates -> artifacts -> outcome
```

## Technology Map

| Tool | Category | Fit for COS | Main Use | Caution |
| --- | --- | --- | --- | --- |
| River | Go/Postgres job queue | High | simple `cos worker` / job queue | Postgres dependency; not a workflow engine |
| NATS + JetStream | lightweight broker / streams | High | VM/cloud workers, pub/sub, durable streams | adds broker operations; not workflow logic |
| DBOS Go | durable execution / workflows | High to very high | durable `cos run-task` / `cos repair` | verify maturity and lock-in |
| Restate | durable execution | High | durable handlers, workflows, promises | requires Restate runtime |
| Inngest Go | durable functions platform | Medium-high | event-driven durable functions | platform gravity |
| Hatchet | task/workflow orchestration | Medium-high | agent workflows and scheduling | larger platform than a queue library |
| Watermill | Go event abstraction | Medium | backend-agnostic pub/sub interface | may be broader than needed |
| Temporal | durable workflow platform | Medium now, high later | long-running repair/product workflows | operationally heavier |
| Dapr | distributed app runtime | Medium later | Kubernetes/microservice building blocks | sidecar/platform overhead |
| Vert.x | JVM reactive toolkit | Low for current repo | future JVM control plane only | adds JVM stack to a Bash/Python/Go core |
| luno/workflow | Go type-safe workflow library | Watch | event-driven typed workflows | young ecosystem |

## Recommendation

1. Keep Phase 1 no-broker: `cos run-task` must work on a laptop, CI runner, or
   single VM without external services.
2. Define a Phase 2 queue interface before choosing a backend.
3. Evaluate River and NATS JetStream for workers.
4. Evaluate DBOS Go and Restate for durable execution after the local contract is
   stable.
5. Keep Temporal, Dapr, Hatchet, Inngest, and Vert.x off the critical path until
   the worker/control-plane need is proven.
