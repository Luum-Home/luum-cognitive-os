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
| `shell_ci_projection` | `manifests/shell-ci-projection.yaml` | Declares consumer shell/CI command and workflow projection surfaces. |
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

### Fail-new ratchet

Use `--fail-new` when ACC should reject newly introduced debt instead of only reporting aggregate score drift:

```bash
python3 scripts/acc_pipeline.py --project-dir . --brief --fail-new
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
```

`--fail-new` compares the current report with `--baseline` (default: `docs/acc/latest.json`) before writing the new report. It blocks new `missing`, `partial`, `stale`, `overexposed`, or `unverified` capabilities/findings. In strict mode, which is the default, it also blocks newly discovered capabilities that are aligned only by broad local-surface defaults such as `scripts/**`, `rules/*.md`, or `skills/**/SKILL.md`.

Use `--allow-new-local-defaults` only when an operator intentionally wants to tolerate a new local-only surface for one run. The durable fix is an exact row in `manifests/primitive-consumer-availability.yaml`, lifecycle metadata, or real projection proof.

The output includes a `new_debt` object in both the full and compact reports so hooks/CI can gate without loading the complete ACC JSON into agent context.

## Engram boundary

A Python script cannot call in-process MCP tools unless they are exposed to that process. Therefore `acc_pipeline.py` records:

- local append-only history always;
- `persistence.engram.status = unavailable` when no Engram bridge is configured;
- enough report content for the agent to call `mem_save`/`mem_session_summary` when those tools are surfaced.

The agent must not claim Engram persistence from the pipeline unless a real Engram write occurred.

## Consumer projection adapter

The consumer projection adapter creates temporary projects and runs the default and full installers for every harness marked `implemented` in `manifests/harness-projection.yaml`. It records projected paths under `.cognitive-os/hooks/cos/`, `.cognitive-os/skills/cos/`, and `.cognitive-os/rules/cos/`. Readiness rows whose source path matches those projected artifacts become `aligned` for the proved harnesses and profiles.

This is intentionally narrow. Claude Code and OpenAI Codex currently prove native/settings lifecycle projection. Cursor, OpenCode, VS Code Copilot, Qwen Code, and Kimi Code prove structural project-local instruction/config/context projection only. Shell/CI proves structural command/workflow projection only. Windsurf, Google Antigravity, MiniMax MaxClaw, and DeepSeek provider integrations remain planned until they have their own projection proof.

The profile manifest also declares SO-local profile drivers, such as `scripts/cos_init.py`, `scripts/cos-init.sh`, and install/profile doctors. Those scripts are not copied into consumer projects. Their proof is that they successfully generate the declared consumer projection surface.

## Consumer availability adapter

`manifests/primitive-consumer-availability.yaml` resolves lifecycle-declared consumer candidates that are not proven by file projection. It is intentionally explicit: a path must name its status and rationale. `maintainer-only` and `so-local-only` rows count as aligned because they are not consumer-project debt; `shell-ci-candidate` and `projectable-needs-driver` remain partial until a projection driver proves them.

The same manifest also carries local-surface defaults for broad families. These defaults mean unprojected scripts, hook support files, rules, repo skills, and Codex workspace skills are treated as local/repo-only unless a projection adapter proves otherwise.

## Shell/CI projection adapter

`scripts/project_shell_ci.py` reads `manifests/shell-ci-projection.yaml` and projects signed shell/CI commands into temp consumer projects. It writes canonical copies under `.cognitive-os/scripts/cos/`, creates consumer-facing driver symlinks under `scripts/`, and generates `.github/workflows/cognitive-os-shell-ci.yml`.

ACC runs this shell/CI projection inside the same temporary consumer projects used for Claude/Codex default/full proof. Rows listed as shell/CI commands become aligned only when their canonical projected file exists.

## Multi-IDE harness registry

`manifests/harness-projection.yaml` is the authoritative list of IDEs/harnesses considered by ACC. Claude Code and OpenAI Codex are `implemented` native/settings harnesses. Cursor, OpenCode, VS Code Copilot, Qwen Code, and Kimi Code are `implemented` structural instruction/config/context harnesses. Shell/CI is an `implemented` structural command/workflow harness. Windsurf, Google Antigravity, MiniMax MaxClaw, and DeepSeek provider integrations are declared as `planned`. Planned harnesses are roadmap scope only: they are reported as unverified and never inherit Claude/Codex projection proof.

Adding support for a new IDE means updating the manifest, implementing a projection driver or wrapper, adding a temp-project proof path, adding automated/manual tests, and only then changing its status to `implemented`. A planned row may document research sources or target files, but it must not be described as supported runtime behavior.

## Primitive duplication adapter

The `primitive_duplication` adapter is advisory during reconstruction. It complements readiness and projection checks by finding repeated implementation/configuration patterns that may be better represented as common agentic primitive infrastructure:

- Python repeats → `lib/`;
- Bash repeats → `hooks/_lib/` or `scripts/_lib/`;
- YAML/config repeats → `manifests/`;
- rule/skill overlap → merge, deprecate, or document boundaries.

The adapter must not auto-refactor. Duplicates can be intentional when isolation, portability, or harness-specific behavior is more important than abstraction.

## Proof-level boundary

See [Harness Proof Levels](harness-proof-levels.md). `implemented` does not mean universal runtime support. For structural harnesses it means project-local files/configs are generated from official docs and shape-tested; account-backed runtime smoke remains optional.
