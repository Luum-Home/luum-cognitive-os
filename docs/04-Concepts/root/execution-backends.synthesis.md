---
type: concept-synthesis
source: docs/04-Concepts/root/execution-backends.md
---

## What it is
Execution Backends is COS's driver-model abstraction for WHERE agent tasks run: COS acts as a control plane (decides what/how much/whether output is good enough) while pluggable backends (claude-code, cursor, kagent, agentfield, agent-sandbox) decide HOW to execute.

## Key mechanics
- Backend registry (`cognitive-os.yaml -> execution.backends`): claude-code (local process, 1-5 parallel, available now), cursor (cloud-agent VM, 10-100 parallel, needs Cursor API), kagent (K8s pod, 100-1000+, needs K8s), agentfield (microservice, unlimited), agent-sandbox (K8s Sandbox CRD, needs K8s 1.32+).
- Routing logic: five signals — task complexity (trivial/small/medium/large/critical), available backends, project phase, budget, special requirements (video proof, K8s isolation). Fallback is always `claude-code`.
- Routing table: TRIVIAL/SMALL(recon/stabilization) -> claude-code; SMALL(prod/maint) -> cursor or claude-code; MEDIUM -> cursor preferred; LARGE -> kagent or cursor; CRITICAL -> kagent+agent-sandbox; distributed -> agentfield.
- Backend interface contract: `dispatch(task, context, acceptance_criteria) -> task_id`, `status()`, `result()`, `cancel()`. COS sends task/context/acceptance_criteria/phase/budget_limit; expects back files_changed/test_results/trust_report/cost/pr_url/video_url.
- Migration path: Phase 1 claude-code only (now) -> Phase 2 +cursor (~2wk) -> Phase 3 +kagent (~4wk) -> Phase 4 +agentfield (~6wk).
- Open-source ecosystem, all Apache 2.0/license-policy compliant: kagent, AgentField, agent-sandbox, Firecracker, gVisor.
- Before implementing a new backend, run `lib/reinvention_guard.py` to check for existing capability coverage.

## Relations & where used
Linux-kernel analogy maps COS core to kernel, backends to drivers, `cognitive-os.yaml -> execution.backends` to `/dev/`. Integrates with SDD pipeline (apply phase benefits most from backend routing), `lib/singularity.py` MAPE-K controller (routes events like test_failure/new_feature/critical_bug to specific backends), `lib/agent_bus.py` (unified heartbeat across backends via Valkey), and `lib/cost_predictor.py` (backend-aware cost). Related rules: `resource-governance`, `definition-of-done`, `agent-security`, `closed-loop-prompts`.

## Status / caveats
Only `claude-code` is available now; cursor/kagent/agentfield/agent-sandbox are opt-in and require external infra (Cursor API, K8s cluster, AgentField setup, K8s 1.32+ respectively). Backends are stateless from COS's perspective — all persistent state lives in Engram and metrics.
