---
report_type: repo-scout-deep-analysis
repo: opensage-agent/opensage-adk
evaluated_at: 2026-05-09
classification: ASSESS
license: Apache-2.0
source_artifacts:
  - .cognitive-os/reports/repo-scout/opensage-agent_opensage-adk.md
  - .cognitive-os/reports/repo-scout/opensage-agent_opensage-adk.analysis.json
  - .cognitive-os/reports/repo-scout/opensage-agent_opensage-adk.raw.json
  - docs/06-Daily/reports/external-tools-radar-opensage-addendum-2026-05-09.md
---

# opensage-agent/opensage-adk Deep Analysis — 2026-05-09

## Executive classification

**ASSESS / trial-patterns.** OpenSage is one of the strongest current external references for COS's self-programming-agent lane: dynamic agent topology, dynamic tool/skill synthesis, sandboxed asynchronous tools, hierarchical graph memory, and benchmark loops. It is not a default runtime adoption candidate because it is young, unreleased, broad in dependencies, and intentionally gives agents tool-creation authority that COS must gate more strictly.

## Acceptance criteria

1. Prior radar/memory check confirms OpenSage had not already been evaluated in this project.
2. License gate runs before adoption scoring and blocks no permissive-license path.
3. Deep stages cover web/source context, GitHub API metadata, clone forensics, architecture, dependencies, CI/activity, smoke validation, security concerns, and radar merge.
4. Tech radar receives a canonical entry and manifest posture prevents default dependency adoption.

## Evidence sources

- GitHub repository: <https://github.com/opensage-agent/opensage-adk>
- Berkeley RDI OpenSage article: <https://rdi.berkeley.edu/blog/opensage/>
- Docs entry linked from README: <https://docs.opensage-agent.ai>
- DeepWiki page checked: <https://deepwiki.com/opensage-agent/opensage-adk>
- Local shallow clone at commit `481b4344f3d07de42082f367ecda4381f81c22c8`.
- GitHub API snapshot stored in `.cognitive-os/reports/repo-scout/opensage-agent_opensage-adk.raw.json`.
- Local analyzer snapshot stored in `.cognitive-os/reports/repo-scout/opensage-agent_opensage-adk.analysis.json`.

## Deep-analysis stages completed

| Stage / primitive | Result |
|---|---|
| Prior-memory check | Engram search found no prior OpenSage radar evaluation for this project. |
| Context analysis | Berkeley RDI positions OpenSage around self-generating topology, dynamic tools/skills, and hierarchical graph memory. |
| Competitive research | Compared against COS native primitives, EvoSkill's skill-improvement lane, Langflow's workflow runtime lane, and TaskingAI's BaaS lane; OpenSage is most relevant to self-programming + sandboxed tool execution. |
| Current source check | GitHub page/API reviewed on 2026-05-09; repository is Apache-2.0, 86 stars, 18 forks, 9 open issues/PRs, no tags/releases. |
| License gate | PASS: Apache-2.0; `license_guard.check_and_enforce` returned safe. |
| DeepWiki/repo-scout | Repo-scout artifact, raw API JSON, and analysis JSON were written under `.cognitive-os/reports/repo-scout/`. |
| Repo forensics | Shallow clone scanned: 395 tracked files and 81,121 counted lines at commit `481b4344...`. |
| Reverse engineering | Main surfaces mapped: agents, session managers, sandbox backends, memory, plugins, toolbox, bash tools, evaluation, CLI, and templates. |
| Build/test smoke | `python3 -m compileall -q src/opensage tests` passed. Full tests deferred because they require Docker/Neo4j/provider/sandbox dependencies. |
| Threat model | Dynamic tool generation, privileged Docker, remote/k8s sandboxing, provider secrets, and Neo4j memory retention are the primary hazards. |
| Radar update | Added ASSESS entry to `docs/04-Concepts/patterns/ecosystem-tools.md` and `packages/ecosystem-tools/rules/ecosystem-tools.md`; manifest marks pattern-only. |
| Docs-to-artifact | This deep report and the radar addendum were created as durable artifacts. |
| Impact analysis | Recommendation is pattern extraction only; any runnable adapter requires a manifest-backed lab and rollback path. |

## Repository facts

| Signal | Value |
|---|---|
| License | Apache-2.0 |
| Stars / forks | 86 / 18 at evaluation time |
| Open issues + PRs | 9 |
| Latest release | none found via GitHub API |
| Latest repo push | 2026-04-07 |
| Recent concluded CI | latest collected run succeeded on 2026-05-08 |
| Local scan size | 395 tracked files, 81,121 counted lines |
| Language mix | Python-dominant; Shell, Dockerfile, CodeQL, and Scala also present |
| Test-file signal | 88 files under tests or with test-like names |

## Architecture findings

OpenSage is a Google ADK-based research/runtime framework with these main surfaces:

- `src/opensage/agents/` — `OpenSageAgent`, MCP toolset wrapper, tool loader, and skill metadata loading.
- `src/opensage/session/` — dynamic agent manager, ensemble manager, sandbox manager, Neo4j client manager, message board, and session persistence.
- `src/opensage/sandbox/` — local, native Docker, remote Docker, Kubernetes, opensandbox, and agentdocker-lite backends.
- `src/opensage/memory/` and `src/opensage/patches/neo4j_logging.py` — graph memory/search and execution-history capture.
- `src/opensage/bash_tools/` and `src/opensage/toolbox/` — software-engineering/security tools including static analysis, retrieval, fuzzing, coverage, debugger, Neo4j, and general shell tools.
- `benchmarks/` and `rl/` — CyberGym, SWE-Bench Pro, SeCodePLT, and reinforcement-learning integration scripts.

## COS extraction candidates

1. **Dynamic subagent pool contract** — compare OpenSage's create/list/resume lifecycle with COS subagent governance and handoff audit trails.
2. **Tool-specific sandbox dependency model** — harvest metadata shapes for heterogeneous tool dependencies without bypassing COS license/credential gates.
3. **Asynchronous long-running tool execution** — useful for compile/static-analysis/fuzz lanes while the main agent continues planning.
4. **Graph memory topology** — study execution graph and unsummarized-output recovery patterns against Engram and COS memory lifecycle docs.
5. **Benchmark harness discipline** — use CyberGym/SWE-Bench Pro/SeCodePLT/DevOps-Gym coverage ideas to harden COS agentic-primitive evaluation.
6. **Claude Code hook bridge** — useful negative/compatibility fixture: it documents which hook events can and cannot be emulated through ADK callbacks.

## Security and operations notes

- License is permissive and safe for study.
- Workflows use GitHub secrets rather than hardcoded keys, but CI starts Docker with privileged DinD and passes provider credentials into integration tests.
- Runtime supports local, Docker, remote Docker, Kubernetes, opensandbox, and agentdocker-lite backends; this is powerful but expands execution blast radius.
- Dynamic tool and skill synthesis must be constrained by COS dynamic-tool, license, tool-discovery, and credential policies before any runnable experiment.
- Neo4j memory can retain prompts, tool outputs, and execution traces; future adapter labs need retention controls and redaction receipts.

## Final recommendation

Keep OpenSage in the tech radar as **ASSESS / trial-patterns**. It deserves a future adapter-lab spike only after COS defines fail-closed wrappers for dynamic tool creation, sandbox capabilities, memory retention, and benchmark-data provenance.
