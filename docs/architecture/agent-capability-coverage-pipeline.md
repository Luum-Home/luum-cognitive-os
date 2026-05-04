# Agent Capability Coverage Pipeline

> Runtime architecture for turning existing COS primitive audits into one ACC report.

## Purpose

The ACC pipeline automates the manual primitive-readiness loop. It does not discover every possible endpoint, event, job, or integration in arbitrary applications yet. Its first scope is the Cognitive OS itself: scripts, hooks, skills, rules, docs claims, primitive coverage, and downstream consumer accessibility.

## Entrypoint

```bash
python3 scripts/acc_pipeline.py --project-dir . --refresh
```

Outputs:

- `docs/acc/latest-compact.md` — context-diet entrypoint for agents and humans.
- `docs/acc/latest.json` — machine-readable ACC report and drift baseline. Do not load this whole file into agent context unless debugging the pipeline.
- `docs/acc/latest.md` — human review summary.
- `.cognitive-os/metrics/acc-pipeline-history.jsonl` — append-only local history.

## Adapter flow

```text
existing tools / ledgers
  -> adapter status records
  -> capability rows
  -> mapping status classifier
  -> ACC score + findings
  -> docs/acc/latest.json + latest.md
  -> local JSONL history
  -> Engram handoff when mem tools are surfaced to the agent
```

## Context diet

ACC/readiness reports are intentionally machine-readable and can be large. Agent sessions must treat them as queryable artifacts, not startup context. The default human/agent entrypoint is:

```bash
python3 scripts/acc_pipeline.py --project-dir . --brief
cat docs/acc/latest-compact.md
```

Do not `cat` these files into an agent conversation unless the task is debugging report generation itself:

- `docs/acc/latest.json`
- `docs/reports/primitive-readiness-ledger-*.json`

Subagents should receive selected rows or findings only. Use Python/JQ snippets to extract those rows instead of passing complete ledgers.

## Current adapters

| Adapter | Source | Role |
|---|---|---|
| `cos_coverage` | `scripts/cos_coverage.py --json --refresh` | Existing ACC counts and trend. |
| `script_readiness` | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | Script primitive representation and consumer accessibility. |
| `family_readiness:{hooks,skills,rules}` | `docs/reports/primitive-readiness-ledger-*-latest.json` | Hook/skill/rule representation and consumer accessibility. |
| `docs_execution` | `scripts/docs_execution_audit.py` output when available | Stale/docs-reality signal. |
| `primitive_coverage` | `scripts/primitive_coverage.py` output when available | Coverage/actionable-gap signal. |
| `primitive_gap_snapshot` | `scripts/primitive_gap_snapshot.py` output when available | Family risk signal. |
| `primitive_duplication` | `scripts/primitive_duplication_audit.py` output when available | Refactor/extraction signal for repeated Bash, Python, YAML/config, and primitive behavior. |
| `harness_projection` | `manifests/harness-projection.yaml` | Registry of implemented/planned/unsupported IDE and harness projection surfaces. |
| `projection_profiles` | `manifests/primitive-projection-profiles.yaml` | Declares `default`, `full`, `shared`, `profile-driver`, and maintainer-only projection classes. |
| `consumer_availability` | `manifests/primitive-consumer-availability.yaml` | Explicitly classifies lifecycle consumer candidates as shell/CI candidates, projectable-needs-driver, maintainer-only, or so-local-only. |
| `consumer_projection` | Temporary projects generated for harnesses with `status: implemented` | Proof that hooks, skills, and rules are actually projected into consumer projects for default and full profiles. |

## Scope boundary

This first implementation answers: “how well are COS agentic primitives represented and projected?” It does not yet provide application-specific static adapters for TypeScript routes, Go services, Python APIs, Terraform resources, MCP tools, or workflow engines. Those adapters should emit the same capability row shape and feed the same classifier later.

## Gate policy

Gate severity follows `cognitive-os.yaml → project.phase`:

| Phase | Default behavior |
|---|---|
| `reconstruction` | Warn on partial/unverified debt; block only stale/overexposed/critical missing when explicit fail flags request it. |
| `stabilization` | Warn on partial; block stale/overexposed and critical missing. |
| `production` | Block stale, overexposed, critical missing, or `acc_effective` below threshold. |
| `maintenance` | Same as production, with tighter tolerance for new missing mappings. |

## Engram boundary

A Python script cannot call in-process MCP tools unless they are exposed to that process. Therefore `acc_pipeline.py` records:

- local append-only history always;
- `persistence.engram.status = unavailable` when no Engram bridge is configured;
- enough report content for the agent to call `mem_save`/`mem_session_summary` when those tools are surfaced.

The agent must not claim Engram persistence from the pipeline unless a real Engram write occurred.

## Consumer projection adapter

The consumer projection adapter creates temporary projects and runs the default and full installers for Claude Code and OpenAI Codex. It records projected paths under `.cognitive-os/hooks/cos/`, `.cognitive-os/skills/cos/`, and `.cognitive-os/rules/cos/`. Readiness rows whose source path matches those projected artifacts become `aligned` for the proved harnesses and profiles.

This is intentionally narrow. It does not sign native support for Cursor, Windsurf, VS Code Copilot, Google Antigravity, OpenCode, or shell/CI until those harnesses have their own projection proof.

The profile manifest also declares SO-local profile drivers, such as `scripts/cos_init.py`, `scripts/cos-init.sh`, and install/profile doctors. Those scripts are not copied into consumer projects. Their proof is that they successfully generate the declared consumer projection surface.

## Consumer availability adapter

`manifests/primitive-consumer-availability.yaml` resolves lifecycle-declared consumer candidates that are not proven by file projection. It is intentionally explicit: a path must name its status and rationale. `maintainer-only` and `so-local-only` rows count as aligned because they are not consumer-project debt; `shell-ci-candidate` and `projectable-needs-driver` remain partial until a projection driver proves them.

## Multi-IDE harness registry

`manifests/harness-projection.yaml` is the authoritative list of IDEs/harnesses considered by ACC. Claude Code and OpenAI Codex are currently `implemented`; Cursor, Windsurf, VS Code Copilot, OpenCode, Google Antigravity, Qwen Code, Kimi Code, MiniMax MaxClaw, DeepSeek provider integrations, and Shell/CI are declared as `planned`. Planned harnesses are reported as unverified and never inherit Claude/Codex projection proof.

Adding support for a new IDE means updating the manifest, implementing a projection driver or wrapper, and adding a temp-project proof path before changing its status to `implemented`.

## Primitive duplication adapter

The `primitive_duplication` adapter is advisory during reconstruction. It complements readiness and projection checks by finding repeated implementation/configuration patterns that may be better represented as common agentic primitive infrastructure:

- Python repeats → `lib/`;
- Bash repeats → `hooks/_lib/` or `scripts/_lib/`;
- YAML/config repeats → `manifests/`;
- rule/skill overlap → merge, deprecate, or document boundaries.

The adapter must not auto-refactor. Duplicates can be intentional when isolation, portability, or harness-specific behavior is more important than abstraction.
