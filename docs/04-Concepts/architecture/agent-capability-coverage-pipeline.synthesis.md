---
type: concept-synthesis
source: docs/04-Concepts/architecture/agent-capability-coverage-pipeline.md
---

## What it is
Runtime pipeline (ACC) that aggregates existing Cognitive OS primitive audits (hooks/skills/rules/scripts/docs/consumer accessibility) into one scored report; scope is the Cognitive OS repo itself, not arbitrary applications.

## Key mechanics
- Entrypoint: `python3 scripts/acc_pipeline.py --project-dir . --refresh`. Outputs: `docs/07-Capabilities/acc/latest-compact.md` (context-diet entrypoint), `docs/07-Capabilities/acc/latest.json` (machine-readable, do not load whole file into agent context), `docs/07-Capabilities/acc/latest.md` (human summary), `.cognitive-os/metrics/acc-pipeline-history.jsonl` (append-only history).
- Adapter flow: existing tool/ledger outputs -> adapter status records -> capability rows -> mapping status classifier -> ACC score + findings -> latest.json/latest.md -> local JSONL history -> Engram handoff when mem tools are surfaced.
- Context diet: use `python3 scripts/acc_pipeline.py --project-dir . --brief` + `cat docs/07-Capabilities/acc/latest-compact.md`; never `cat` `latest.json` or `docs/06-Daily/reports/primitive-readiness-ledger-*.json` into a conversation unless debugging the pipeline itself; sub-agents get selected rows/findings, not full ledgers.
- Adapters table: `cos_coverage` (`scripts/cos_coverage.py --json --refresh`), `script_readiness`/`family_readiness:{hooks,skills,rules}` (readiness ledger JSONs), `docs_execution` (`scripts/docs_execution_audit.py`), `primitive_coverage` (`scripts/primitive_coverage.py`), `primitive_gap_snapshot` (`scripts/primitive_gap_snapshot.py`), `primitive_duplication` (`scripts/primitive_duplication_audit.py`), `harness_projection` (`manifests/harness-projection.yaml`), `projection_profiles` (`manifests/primitive-projection-profiles.yaml`), `consumer_availability` (`manifests/primitive-consumer-availability.yaml`), `shell_ci_projection` (`manifests/shell-ci-projection.yaml`), `consumer_projection` (temp projects proving actual hook/skill/rule projection).
- Gate policy by `cognitive-os.yaml -> project.phase`: reconstruction (warn on partial/unverified, block only stale/overexposed/critical-missing if explicit fail flags); stabilization (warn on partial, block stale/overexposed/critical-missing); production (block stale/overexposed/critical-missing/low `acc_effective`); maintenance (same as production, tighter tolerance for new missing mappings).
- Fail-new ratchet: `--fail-new` (compares against `--baseline`, default `latest.json`) blocks new missing/partial/stale/overexposed/unverified capabilities; strict mode (default) also blocks new capabilities aligned only via broad local-surface defaults (`scripts/**`, `rules/*.md`, `skills/**/SKILL.md`); `--allow-new-local-defaults` tolerates one run intentionally. Report includes a `new_debt` object for CI gating without loading full JSON.
- Engram boundary: pipeline records local history always; sets `persistence.engram.status = unavailable` with no bridge; the agent (not the script) must call `mem_save`/`mem_session_summary` — script cannot claim Engram persistence itself.
- Consumer projection adapter: creates temp projects, runs default/full installers for every `implemented` harness in `manifests/harness-projection.yaml`; records projected paths under `.cognitive-os/{hooks,skills,rules}/cos/`. Claude Code and OpenAI Codex prove native/settings lifecycle projection; Cursor/VS Code Copilot/Qwen Code/Kimi Code prove structural instruction/config/context only; OpenCode proves structural `opencode.json` only (plugin/permission runtime surfaces reserved for a future adapter); Shell/CI proves structural command/workflow only; Devin/Google Antigravity/MiniMax MaxClaw/DeepSeek remain planned.
- Consumer availability adapter: `manifests/primitive-consumer-availability.yaml` resolves candidates not proven by file projection; `maintainer-only`/`so-local-only` count as aligned, `shell-ci-candidate`/`projectable-needs-driver` remain partial until proven.
- Shell/CI adapter: `scripts/project_shell_ci.py` projects signed commands into `.cognitive-os/scripts/cos/`, symlinks under `scripts/`, generates `.github/workflows/cognitive-os-shell-ci.yml`.
- Primitive duplication adapter: advisory during reconstruction; flags Python/Bash/YAML repeats that may belong in `lib/`, `hooks/_lib/`/`scripts/_lib/`, or `manifests/`; never auto-refactors.

## Relations & where used
References `docs/04-Concepts/architecture/harness-proof-levels.md` for the proof-level boundary (implemented does not mean universal runtime support — structural harnesses only prove project-local files/configs generated + shape-tested).

## Status / caveats
First implementation only answers "how well are COS primitives represented and projected"; no application-specific adapters yet for TypeScript routes, Go services, Python APIs, Terraform, MCP tools, or workflow engines (future work should emit the same capability-row shape).
