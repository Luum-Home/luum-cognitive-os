---
report_type: external-tools-radar-addendum
subject: opensage-agent/opensage-adk
generated_at: 2026-05-09
status: assess-trial-patterns
source_artifacts:
  - .cognitive-os/reports/repo-scout/opensage-agent_opensage-adk.md
  - .cognitive-os/reports/repo-scout/opensage-agent_opensage-adk.analysis.json
  - .cognitive-os/reports/repo-scout/opensage-agent_opensage-adk.raw.json
  - docs/03-PoCs/research/repo-scout/deep/opensage-agent__opensage-adk-2026-05-09.md
related_docs:
  - docs/04-Concepts/patterns/ecosystem-tools.md
  - manifests/external-tools-adoption.yaml
---

# External Tools Radar OpenSage Addendum — 2026-05-09

## Decision

Add [opensage-agent/opensage-adk](https://github.com/opensage-agent/opensage-adk) and the [Berkeley RDI OpenSage context](https://rdi.berkeley.edu/blog/opensage/) to the tech radar as **ASSESS / trial-patterns**.

OpenSage is worth deep analysis because it is explicitly built around agentic primitives that overlap with COS: self-generating agent topology, dynamic tool/skill synthesis, hierarchical graph memory, sandboxed asynchronous execution, software-engineering/security toolkits, and benchmark loops. It is not a default runtime adoption candidate today because it is a young unreleased research ADK with broad Docker/Neo4j/Google-ADK dependencies and autonomous tool creation semantics that COS must wrap with stricter governance.

## Deep-analysis stages completed

| Stage | Result |
|---|---|
| Prior-memory check | Engram search found no prior OpenSage radar evaluation for this project. |
| Current source check | GitHub page/API reviewed on 2026-05-09; GitHub reports Apache-2.0 license, 86 stars, 18 forks, 9 open issues/PRs, and no releases/tags. |
| License gate | PASS: Apache-2.0; `license_guard.check_and_enforce` returned safe. |
| Shallow clone forensics | PASS: local clone scanned; 395 tracked files and 81,121 counted lines at commit `481b4344...`. |
| Architecture scan | Google ADK-based framework with dynamic agents, ensembles, sandbox backends, Neo4j memory, plugins, toolboxes, CLI/web UI, benchmark harnesses, and RL scripts. |
| Test/build smoke | Python `compileall` passed for `src/opensage` and `tests`; full tests deferred because they require Docker/Neo4j/provider/sandbox dependencies. |
| Security scan | Advisory concerns: privileged Docker CI, remote/k8s sandbox backends, provider-key integration tests, graph-memory retention, dynamic tool/skill creation. |
| Radar merge | Added canonical ASSESS entry to `docs/04-Concepts/patterns/ecosystem-tools.md`; manifest marks it pattern-only and disallowed as default dependency. |

## What COS should learn from it

1. **Dynamic agent topology** — OpenSage's session-scoped dynamic agent manager and ensemble manager are useful comparison points for COS subagent lifecycle and handoff audit trails.
2. **Tool synthesis under sandboxing** — tool-specific containers, dependency metadata, and async execution are valuable patterns, but COS must keep license/credential/tool-discovery gates first-party.
3. **Hierarchical graph memory** — execution graph, memory agent, and unsummarized-output recovery patterns should be compared with Engram and `docs/04-Concepts/architecture/memory-lifecycle.md`.
4. **Security/SWE benchmarks** — CyberGym, SWE-Bench Pro, SeCodePLT, DevOps-Gym, CodeQL, Joern, fuzzing, coverage, GDB/PDB, and retrieval toolkits can inform COS primitive benchmarks.
5. **Hook compatibility boundaries** — the Claude Code hook loader is a useful fixture because it documents ADK callback events that cannot fully simulate Claude Code/Codex governance hooks.

## Why ASSESS, not ADOPT

- No release tags or stable API contract were visible as of 2026-05-09.
- Direct dependency adoption would import a broad ADK/sandbox/memory stack instead of a narrow commodity library.
- Dynamic tool and skill generation can conflict with COS's no-incomplete-code, license, credential, dynamic-tool, and tool-discovery policies unless wrapped.
- Running the full system requires Docker/Neo4j/provider and benchmark infrastructure, which is too heavy for default COS runtime.

## Follow-up trigger

Open an adapter-lab spike only if COS starts a dedicated self-programming-agent or sandboxed-long-running-tool lane. Required preconditions: `manifests/self-programming-agent-patterns.yaml` passes `scripts/cos-self-programming-pattern-audit`, ADR-256 phase 1/2 primitive contract and intervention-ledger slices exist, and the lab has a disposable fixture repo, generated-file allowlist, provider-key isolation, sandbox capability policy, memory-retention policy, and rollback receipts.
