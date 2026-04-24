# How to Use Cognitive OS — Building With the OS

**Status:** Living document (updated 2026-04-16 after 98% stabilization)

This document explains how to leverage the OS's own tooling to build both itself (self-construction) and other projects (normal usage). Updated after the stabilization session to reflect new guardrails and capabilities.

## Philosophy

The OS has 5 self-awareness mechanisms. When you work with it, **let them do their job**. Don't bypass the pre-commit hooks, don't skip the ADR prompts, don't disable the pattern detector. Each one was built to prevent a specific wound (see `docs/architecture/LESSONS-LEARNED.md`).

## Self-Construction (Building the OS itself)

### Every session

1. **Start:** Open Claude Code in `/Users/marialuzmontiel/projects/luum/luum-agent-os`. Read the 4 living documents to recover context:
   ```
   Read docs/architecture/stabilization-roadmap.md
   Read docs/architecture/FROZEN-BACKLOG.md
   Read docs/architecture/LESSONS-LEARNED.md
   Read memory files in ~/.claude/projects/.../memory/
   ```

2. **Work:** Use the OS's own skills whenever possible:
   - `/audit-integrity` — before classifying any file as missing
   - `/detect-patterns` — before adding a new field/flag (checks if it'd be aspirational)
   - `/eval-repo <url>` — before evaluating new dependencies
   - `/reverse-engineer <path>` — before guessing how an external tool works

3. **Commit:**
   - Pre-commit hooks run automatically. They enforce:
     - Gate 1: no project-specific terms leaking into OS code
     - Gate 2: Python syntax + lint
     - Gate 3a: new hooks must be registered in both profile scripts
     - Gate 3e: imports must resolve
     - Gate 3f: new tests must be behavioral (not structural-only)
   - `adr-detector.sh` runs async on `git commit`. It analyzes the diff and, if the change is architectural (dependency, config, hooks, license, large deletion, integration, structure, breaking), generates an ADR draft in `docs/architecture/adrs/`.

4. **End:** `engram-auto-sync.sh` runs on Stop event. It exports project-scoped observations to `.engram/exports/` and commits them. Next time you clone on another device, `engram-auto-import.sh` reconstructs local engram.

### Red flags (stop signs)

Before merging any significant change, check `docs/architecture/LESSONS-LEARNED.md` for the 10 red flags. Any active flag → STOP and investigate.

### When you need to add something new

**Adding a hook:**
1. Write it in `hooks/yourhook.sh`
2. Register it in both `scripts/apply-efficiency-profile.sh` AND `scripts/set-security-profile.sh`
3. Pre-commit will reject if you forget either one
4. Add behavioral test (not structural) in `tests/unit/test_yourhook_perf.py` or `tests/hooks/`
5. CI gate requires mutation score ≥ 40%

**Adding a skill:**
1. Write `skills/yourskill/SKILL.md` with proper frontmatter
2. Include `audience: os-dev|project|both|human`
3. Add `paths:` if stack-specific (e.g., `["*.go"]` for Go skills)
4. Add `disable-model-invocation: true` if user-only
5. Add `effort: opus|sonnet|haiku` if model-specific
6. Add entry to `skills/CATALOG.md`
7. Run `scripts/generate-compact-catalog.py` to regenerate `CATALOG-COMPACT.md`

**Adding a config flag:**
1. **DO NOT** add a flag without the code that reads it. `detect_dead_metadata` will flag it.
2. Add the flag to `cognitive-os.yaml` AND the reader code in the same PR.

**Adding a validator (cos-dispatch):**
1. Implement in `internal/validator/impl/yourvalidator.go`
2. Register in `internal/validator/impl/factory.go`
3. Write test in `internal/validator/impl/yourvalidator_test.go`
4. Verify: `go vet ./... && go test ./internal/validator/...`

### When you need to change architecture

1. The change triggers `adr-detector.sh` — a draft ADR appears in `docs/architecture/adrs/`
2. Review the draft, flesh it out, change status from Draft to Accepted
3. Link related ADRs (supersedes, related to)
4. Include in the commit message: "Includes ADR-NNN"

## Using COS in Other Projects

COS is installable in any project via `cos init`:

```bash
cd your-project/
cos init --profile standard  # or --minimal or --full
```

This copies:
- `hooks/` — selected by profile (lean/standard/paranoid)
- `.claude/rules/cos/` — namespaced rules (won't overwrite your project rules)
- `skills/` — filtered by `audience: project|both|human` (os-dev skills stay home)
- `cognitive-os.yaml` — config template

Some skills are intentionally internal to the Cognitive OS repository. For
example, `test-contract-repair` is tagged `SCOPE: os-only` and
`audience: os-dev` because it governs how maintainers repair this OS's own test
suite with persistent run artifacts. It can appear in this repository's
self-hosted harness projection, but it is not part of the default project
adopter surface.

What stays in your project vs COS:
- Your project's CLAUDE.md — untouched
- Your project's `.claude/rules/*.md` — untouched
- COS rules in `.claude/rules/cos/` — namespaced
- Your `.claude/settings.json` — merged (your hooks + COS hooks)

### Cross-device memory in other projects

Install the sync hooks similarly:
```bash
cp $COS_HOME/scripts/engram-sync.sh your-project/scripts/
cp $COS_HOME/packages/engram-sync/hooks/*.sh your-project/hooks/
```

Register in your project's settings.json. Your project-scoped engram observations sync via git like this repo does.

## Measuring Health

Run these periodically:

```bash
# Health check
./scripts/doctor.sh

# Detect drift (aspirational metadata, broken chains, etc.)
source .venv/bin/activate
python -c "from lib.pattern_detector import PatternDetector; \
  p = PatternDetector(); \
  patterns = p.run_all('.'); \
  [print(f'{x.severity}: {x.description}') for x in patterns]"

# Mutation score of a specific lib
cosmic-ray init .cosmic-ray.toml /tmp/mut.db
cosmic-ray --config .cosmic-ray.toml exec /tmp/mut.db
cr-report /tmp/mut.db
```

## When Things Go Wrong

**Tests start failing:**
1. Check if it's a `session-init.sh` timeout (known issue — fix by extracting to `_lib/`)
2. Check if it's a structural test (delete it — it shouldn't exist anymore)
3. Check mutation score on affected file (should be ≥40%)

**Hooks getting slow:**
1. Run the 3 perf tests: `pytest tests/unit/test_*_perf.py`
2. If a hook regressed, look for: subprocess in while loop, multiple Python cold starts, EXIT trap not guarded
3. Consolidate Python calls into single script in `hooks/_lib/`

**Agent makes repeated errors:**
1. Check `templates/agent-mandatory-rules.md` — is the rule there?
2. If not, add it — it gets injected into every sub-agent via `subagent-context-injector.sh`

**Disk fills up:**
1. Clean `~/.claude/projects/` of stale project dirs
2. Clean `mutants/` (gitignored)
3. Clean `/private/tmp/claude-501/` (task outputs)

## Key Files Reference

- `scripts/setup.sh` — one-command environment setup
- `scripts/doctor.sh` — 12 health checks
- `scripts/engram-sync.sh` — cross-device memory
- `scripts/check-test-quality.py` — AST-based test classifier
- `scripts/generate-compact-catalog.py` — skill catalog regen
- `hooks/_lib/file_checker.sh` — symlink-aware file checks
- `hooks/_lib/dispatch_gate_check.py` — consolidated dispatch logic
- `hooks/_lib/session_init_helper.py` — consolidated session init
- `hooks/_lib/singularity-suggestion.sh` — extracted for testability
- `hooks/_lib/task_panel_adapter.py` — ADR-021 first impl
- `hooks/_lib/recap_adapter.py` — /recap integration
- `templates/agent-mandatory-rules.md` — injected into every sub-agent

## For Next Sessions

See:
- `docs/architecture/stabilization-roadmap.md` — current status
- `docs/architecture/FROZEN-BACKLOG.md` — what to unfreeze
- `docs/architecture/LESSONS-LEARNED.md` — what NOT to repeat
- `docs/architecture/POST-MORTEM-2026-04.md` — history
