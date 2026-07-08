---
type: concept-synthesis
source: docs/04-Concepts/architecture/cos-dispatch/adr-detection.md
provenance: "The project accumulated 252 commits in 18 days with zero Architecture Decision Records (Docker-to-pip migration, hook architecture v2, AGPL license adoption, dependency replacements existed only in commit messages and engram); manual ADR authoring has near-zero adoption."
---

## What it is
`ADRDetector` is a cos-dispatch PostToolUse transformer that watches `git commit` events, scores the diff against a weighted signal table, and auto-generates a draft ADR when the total weight crosses a threshold.

## Key mechanics
- Signal weights (`internal/pattern/adr_detector.go`): new dependency 0.30, dependency replaced 0.50, config schema change 0.35, hook change 0.25, file structure change 0.20, pattern change 0.40, license impact 0.60, breaking change 0.55, significant deletion 0.35, new integration 0.45. Default threshold 0.70; each signal type capped at 1.0 to prevent volume-based noise.
- Detection checkers: checkDependencyFiles (go.mod, pyproject.toml, requirements.txt, package.json, lockfiles, Cargo.toml, Gemfile), checkConfigFiles (cognitive-os.yaml, cos-dispatch.toml, .claude/settings.json - structural changes only), checkHookChanges (settings.json hooks array; weight halved for enable/disable toggles), checkDirectoryStructure, checkLicenseFiles, checkDeletionScale (>10 files deleted or net >500 lines removed), checkIntegrationPatterns, checkBreakingChanges.
- `ADRGenerator` (`internal/pattern/adr_generator.go`) auto-numbers the next ADR by scanning `docs/02-Decisions/adrs`, builds title/context/decision/consequences, optionally enriches Context via Engram search (by commit message, signal keywords, recent 24h decisions), writes `ADR-{num}-{slug}.md` from a Go template, status always "Draft".
- Registered as PostToolUse transformer, priority 30, predicate `EventIs(PostToolUse) AND ToolTypeIs(Bash) AND CommandContains("git commit")`.
- Config (`cos-dispatch.toml` `[adr]`): enabled, output_dir=docs/02-Decisions/adrs, threshold=0.70, engram_enrich=true, max_per_session=5 (rate limit), auto_commit=false; `[adr.ignore]` paths (tests/**, docs/**/*.md, *.lock, go.sum) and commit_patterns (chore/docs/style/test prefixes) are skipped.
- Persists to `patterns.db` table `adr_detections` (session_id, commit_hash, total_weight, threshold, triggered, signals_json, adr_path, engram_refs).
- Worked example: commit `b79e850` (Docker-to-pip Phase 1) scores 1.30 (dep_replaced 0.50 + config_schema 0.35 + new_integration 0.45), generating an ADR-006 draft. Other commits that would trigger: `329deb2` hook architecture v2 (1.00), `57ed5cf` contamination removal (0.75), `d302843` MLflow bridge (0.75), `f92f03c` agent progress monitoring (0.75), `c5e3d70` host resource monitor (0.85). Test-only, value-tuning, and doc-only commits correctly stay below threshold.
- CLI: `cos-dispatch adr list`, `adr history --since 7d`, `adr analyze <hash>`, `adr promote ADR-006`, `adr calibrate`.

## Relations & where used
Runs inside the cos-dispatch Transformer pipeline (see cos-dispatch/README.md, interfaces.md). Writes to `docs/02-Decisions/adrs`. Optional Engram integration for context enrichment.

## Status / caveats
Design doc (Go code shown is illustrative, not confirmed shipped in this batch). Rate-limited to max_per_session=5 so large refactor sessions don't overwhelm the developer with drafts; below-threshold commits still logged to `patterns.db` for later `adr history` review.
