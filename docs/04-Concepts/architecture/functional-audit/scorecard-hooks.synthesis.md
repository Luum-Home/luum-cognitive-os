---
type: concept-synthesis
source: docs/04-Concepts/architecture/functional-audit/scorecard-hooks.md
provenance: "User's question: of the hooks, how many actually fire and produce the documented effect?"
---

## What it is

Capa-3 static audit scorecard classifying every hook file in `hooks/*.sh` by whether it is actually wired into an active profile — not merely present on disk.

## Key mechanics

- Scope/counts: 257 hook files on disk, 13 `_lib/` helpers (not invocable directly), 118 invocable flat hooks. Of those: 55 functional-wired in the `full` profile (47 in `standard`, 7 in `lean`); 22 functional-unwired-by-design (`full`-only, e.g. `aguara-scan.sh`, `semgrep-scan.sh`, `mcp-scan.sh`, `kpi-trigger.sh`); 41 orphan (wired in no profile at all, e.g. `adaptive-bypass.sh`, `pre-commit-gate.sh`, `resource-check.sh`, `reinvention-check.sh`); 0 stubs (all `<10`-line hooks manually inspected have real logic); code-dead reduced to 0 after `auto-verify.sh`/`auto-refine.sh`/`dod-gate.sh` were built (see `ux2-hook-hygiene.md`).
- Anomaly: `confidentiality-enforcer.sh` was wired in `lean`+`standard` but **not** `full` — inverting the expected `lean ⊂ standard ⊂ full` coverage pattern.
- Data sources: `.claude/settings.json`, `scripts/apply-efficiency-profile.sh`, `hooks/_lib/registration-allowlist.txt`, repo-wide grep of skill/rule/doc references.
- `rules/project-gotchas.md`'s "48/93 hooks intentionally not wired" claim is stale (predates growth to 118 hooks); real figure is 41 orphan + 22 full-only = 63/118 not wired at standard-or-lower.
- Recommended remediation (not applied in this pass): wire `resource-check.sh` into `standard` (it operationalizes the always-active `rules/resource-governance.md`), wire `auto-rollback-trigger.sh` and `reinvention-check.sh`, fix the confidentiality-enforcer inversion, delete truly-unreferenced orphans (`memu-sync.sh`, `notify.sh`, `singularity-check.sh`, `tool-discovery-trigger.sh`, `session-state-save.sh`, `sync-to-repo.sh`) after confirming no external caller.

## Relations & where used

`rules/project-gotchas.md`, `scripts/apply-efficiency-profile.sh`, `.claude/settings.json`, `hooks/self-install.sh`, `hooks/ai-provider-identity-guard.sh`, `hooks/session-end-cleanup.sh`; feeds `tests/audit/test_hooks_contracts.py`; sibling scorecards `scorecard-rules.md`, `scorecard-skills.md`.

## Status / caveats

Read-only audit (reconstruction phase), no fixes applied here. "Referenced-but-unused" (wired but matcher rarely triggers) is unknown — requires runtime telemetry, explicitly flagged for Capa 4 (see `sprint-5-observability.md`).
