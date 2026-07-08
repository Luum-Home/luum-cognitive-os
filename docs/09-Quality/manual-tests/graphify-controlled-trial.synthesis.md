---
type: quality-synthesis
source: docs/09-Quality/manual-tests/graphify-controlled-trial.md
provenance: "Manual test verifying Graphify can be used as an optional maintainer graph-indexing tool without scanning noisy directories, mutating assistant instructions, installing hooks, or being treated as verification evidence."
---

## What it is
A manual, bounded trial procedure for Graphify — an external code-graph-indexing tool — used strictly as an *optional maintainer aid* inside Cognitive OS. The test's real purpose is guarding against scope creep: no assistant-instruction mutation, no git hook installation, no implicit broad-directory scanning, and no treating graph output as verification evidence.

## Key mechanics
1. Dry-run preview: `scripts/cos-graphify-build lib --out /tmp/... --dry-run` — must print a `graphify extract` command with `.graphifyignore` patterns applied.
2. Bounded build: `scripts/cos-graphify-build lib --out /tmp/... --skip-benchmark`, confirming `graphify-out/graph.json` is written.
3. Bounded query: `graphify query "..." --graph ... --budget 1200` — returns graph context without requiring broad repository reads.
4. Hook-absence check: `git config --get core.hooksPath` and `grep -R "graphify-hook-start" .git/hooks` must show no installed Graphify hook.
5. Preload matrix: `scripts/cos-graphify-preload-matrix lib/harness_adapter/base.py --json --out ...`.
6. Telemetry join against an **explicit** Claude session JSONL path via `scripts/cos-graphify-run-telemetry --session ... --matrix-json ... --out ...`; latest-session auto-discovery only happens when `--latest-claude-session` is explicitly passed (with `--project-filter`/`--since-hours`) — implicit scanning of live session stores is disallowed for this test.
- Telemetry reports must label metrics `actual`, `estimated`, or `mixed` and must not claim causal token reduction from a single run.
- Failure handling: noisy roots (`reference/`, `dashboard/`, `.venv/`, `.git/`) appearing in the dry-run without exclusion means `.graphifyignore` needs fixing before extraction; Graphify itself should be installed as an operator tool (`uvx --from graphifyy graphify` or a temp venv), never vendored into the repo.

## Relations & where used
Falls under the `ecosystem-tools`/`library-selection`/`reinvention-prevention` contextual rules and the broader Tool Discovery gate pattern also seen in `cross-stack-license-audit-cli.md` (routing ad-hoc tooling back to governed primitives). `lib/harness_adapter/base.py` is used as the sample query target, tying it to the harness-adapter architecture (ADR-033).

## Status / caveats
Deliberately restrictive test — most of its assertions are "this must NOT happen" (no hook install, no instruction mutation, no implicit session scanning), reflecting a controlled-trial posture toward adopting a third-party tool rather than a feature-readiness proof. No dated run log embedded.
