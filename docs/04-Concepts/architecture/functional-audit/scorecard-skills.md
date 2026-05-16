# Skills Functional Audit — Capa 3 Scorecard

> Generated 2026-04-16 by read-only audit under reconstruction phase.
> Methodology and script live in `tests/audit/test_skills_contracts.py`.

## Summary

- **Total skill directories**: 124 (under `skills/`, excluding catalog `.md` files)
- **Functional**: 113 (91.1%)
- **Stub**: 6 (4.8%)  — malformed frontmatter (YAML block placed after H1; invisible to strict parsers)
- **Code-dead**: 5 (4.0%) — SKILL.md references a path that does not exist on disk
- **Doc-drift**: 0 (0.0%) — no skills are both well-formed AND absent from the catalog

> REACHABLE != FUNCTIONAL. Of the 124 reachable skill directories, 11 (8.9%) are not
> functional today: 6 have broken frontmatter that harness parsers will silently drop,
> and 5 reference scripts/hooks/rules/SKILL.md files that do not exist on disk.

## Classification Heuristic

Each SKILL.md was evaluated against these rules in priority order:

1. **code-dead** — any of:
   - `SKILL.md` file is absent from the skill directory, OR
   - A referenced path (e.g. `hooks/foo.sh`, `rules/bar.md`, `lib/baz.py`) does not exist on disk.
     References inside fenced code blocks and quoted string literals are ignored (they are
     examples, not dependencies). Bare filenames in backticks (e.g. ``` `auto-refine.sh` ```)
     are also checked against `hooks/` / `scripts/` / `lib/` / `packages/` if they contain a
     hyphen (convention for project artifacts).
2. **stub** — frontmatter missing the top-level `name:` key (the skill is not discoverable
   by harness tooling), OR contains procedural-placeholder markers
   (`TODO: implement`, `not yet implemented`, `aspirational`, `coming soon`, `WIP` at line start).
3. **doc-drift** — well-formed + references resolve, but the skill name is absent from both
   `skills/CATALOG.md` and `skills/CATALOG-COMPACT.md`.
4. **functional** — fallthrough: frontmatter valid, references resolvable, appears in catalog.

### Known Limitations

- A handful of "code-dead" hits (`scaffold-project`, notably) reference output paths the
  skill is supposed to **generate**, not read. The classifier treats these as broken; this
  is called out in the findings below rather than papered over — the reader can decide.
- "Description missing" is annotated but does not by itself demote a skill to stub. Many
  skills (e.g. `simulation-arena`, `skill-creator`) have `triggers:` but no `description:`
  and appear in the catalog with an empty description column. This is a separate doc hygiene
  issue the catalog generator already exposes.

## Findings by category

### Functional (113)

add-hook, add-mcp, add-rule, add-skill, agent-dashboard, agent-kpis, analyze-improvements,
apply-improvements, audit-integrity, audit-website, automaker-bridge, batch-runner,
bump-version, catalog-full, caveman, caveman-compress, code-review,
cognee-integration, cognee-search, cognitive-os-benchmark, cognitive-os-init,
cognitive-os-test, compat-test, component-classifier, compose-prompt, confidence-check,
contract-drift, conversation-memory, deep-research, deepeval-integration, detect-patterns,
detect-stack, devbox-checkpoint, doc-sync, document-feature, dod-check, error-analyzer,
repo-scout, evaluate-plan, exhaustive-prompt, generate-changelog, generate-config,
gpu-sandbox, harness-audit, install-recommended, issue-pipeline, jupyter-execute,
memu-context, metrics-calibrator, model-optimizer, nemo-guardrails, opik-integration,
planning-poker, pr-review, private-mode, promptfoo-integration, push-release, queue-drain,
ragas-integration, readiness-check, recall-search, recommend-library, release-os,
repair-status, repo-forensics, research-protocol, resolve-blockers, resource-governor,
resume-tasks, retrospective, reverse-engineer, run-tests, sandbox-sample, scout,
sdd-compound, sdd-continue, sdd-explore, sdd-resume, secret-audit, security-audit,
self-improve, self-review, semgrep-scan, session-backlog, session-manager,
session-report-executive, session-wrapup, simulation-arena, singularity, skill-creator,
smoke-test, sprint, squad-manager, sre-agent, strands-evals-integration,
systematic-debugging, tag-release, test-driven-development, tool-discovery, trust-audit,
validate-config, validate-release, verification-before-completion, vulnerability-scan,
web-crawler, webhook-trigger

### Stub (6)

All six exhibit the same root cause: the YAML frontmatter block is placed **after** the
H1 heading and quote line instead of at the very top of the file. Strict frontmatter
parsers (including the one used by harness tooling and by this audit) require the
document to start with `---\n`. These skills are therefore invisible to tools that rely
on frontmatter for discovery.

- **agent-stress-test** — frontmatter block starts at line 5 (after `# /agent-stress-test` + blockquote); `name:` key not detected by strict parser.
- **auto-rollback** — same pattern; frontmatter at line 5 after H1.
- **capability-snapshot** — same pattern.
- **cognitive-os-status** — same pattern.
- **impact-analysis** — same pattern.
- **red-team** — same pattern.

> Fix for all six: move the frontmatter block to lines 1–N, then restore the `# /<name>`
> heading and blockquote below it. The CATALOG generator already lists these with
> "Description missing" style empty cells, which is the downstream symptom.

### Code-dead (5)

- **arena** — `run-arena.sh` (line 134) referenced in backticks; no such file exists under `hooks/`, `scripts/`, `lib/`, or `packages/`.
- **auto-generated** — skill directory is empty (no `SKILL.md` file). Previously a placeholder, now an orphan dir.
- **auto-refine** — `auto-refine.sh` (line 16) referenced as the trigger hook. The hook file exists ONLY under `hooks/_archived/auto-refine.sh.bak` — archived, not active. The entire PITER auto-refine loop described by this skill is unreachable.
- **coverage-enforcement** — `coverage-gate.sh` (line 142) referenced; no such file on disk.
- **scaffold-project** — references 4 paths: `rules/architecture.md` (line 49), `rules/constitutional-gates.md` (line 71), `rules/services-config.md` (line 83), `hooks/block-prod-urls.sh` (line 137). None exist. **Nuance**: for this skill the paths are OUTPUTS (files the skill is expected to generate in a target project's `.claude/`). The classifier still flags it because it cannot distinguish input-dep from output-artifact. The finding is retained so a reviewer can confirm that scaffold-project's template logic is intact even though its referenced template paths look stub-like.

### Doc-drift (0)

No skills are both well-formed and absent from the catalog. Every functional skill in
`skills/` appears in at least one of `CATALOG.md` or `CATALOG-COMPACT.md`.

## Sample verification (5 random functional, seed=42)

Random sample pulled with `random.seed(42); random.sample(functional, 5)`:

| Skill | SKILL.md size | Referenced artifact | On disk? |
|-------|---------------|---------------------|----------|
| sdd-compound | 53 lines, 1628 bytes | (no internal path refs — pure procedural doc) | N/A |
| caveman | 55 lines, 2657 bytes | (no internal path refs) | N/A |
| add-skill | 164 lines, 4563 bytes | `rules/RULES-COMPACT.md` | YES |
| simulation-arena | 114 lines, 3554 bytes | `lib/simulation_arena.py` | YES |
| document-feature | 278 lines, 9777 bytes | `rules/doc-sync.md` | YES |

All five samples have substantive content (>50 lines) and every referenced project path
resolves on disk. No stubs or placeholder content in the sample.

## Specific findings to flag

1. **`auto-refine` (code-dead, confirmed)** — Cluster D already flagged this. The hook
   `hooks/auto-refine.sh` is archived at `hooks/_archived/auto-refine.sh.bak`. The skill's
   entire activation mechanism ("when `auto-refine.sh` signals ORCHESTRATOR ACTION
   REQUIRED") is unreachable. This skill is documented heavily in
   `rules/closed-loop-prompts.md` and `rules/phase-aware-agents.md`, which both reference
   the missing hook. Removing or re-implementing the hook is a prerequisite for the PITER
   auto-refine loop to work at all.
2. **`auto-generated` (code-dead, trivial)** — empty directory under `skills/`. Either
   remove the directory or add a minimal `SKILL.md`. Today it contributes nothing and
   trips any discovery tool that iterates `skills/*/`.
3. **`coverage-enforcement` (code-dead)** — references `coverage-gate.sh` as the
   enforcement mechanism. No such script exists. The skill's Go-test-coverage flow has
   no shell actuator; the skill is procedural documentation only.
4. **`arena` (code-dead)** — references `run-arena.sh`. Not on disk. Related skills
   `simulation-arena` (functional, uses `lib/simulation_arena.py`) and
   `cognitive-os-benchmark` (functional) cover similar ground; arena may be a
   pre-refactor artifact that can be retired.
5. **Six-skill frontmatter bug cluster** (agent-stress-test, auto-rollback,
   capability-snapshot, cognitive-os-status, impact-analysis, red-team) — all share an
   inverted-header bug (H1 before YAML). Fix is mechanical and identical for all six. Any
   harness tool that walks `skills/*/SKILL.md` and parses frontmatter will miss them.
6. **`scaffold-project` (code-dead, but see nuance)** — flagged because it references 4
   paths that don't exist. On manual review, these are outputs the skill is designed to
   generate. Classification kept as code-dead so the output-vs-input distinction gets a
   human review pass before reclassifying.

## Methodology

Classifier source: inlined in `tests/audit/test_skills_contracts.py` (the pytest module
is also the authoritative audit tool). To reproduce:

```
python3 -m pytest tests/audit/test_skills_contracts.py -m audit --collect-only
python3 -m pytest tests/audit/test_skills_contracts.py -m audit -v
```

Under `-m audit`, every failing test names a specific skill — the failure IS the signal
for that skill's classification.

## Next actions (out of scope for this pass)

- Re-implement or remove `hooks/auto-refine.sh` (blocker for auto-refine, self-improve, and multiple rules).
- Mechanical fix pass on the six malformed-frontmatter skills.
- Decide whether `arena`, `coverage-enforcement`, `auto-generated` are retired or revived.
- Add a generator-verifier for `scaffold-project`: assert the skill can actually produce its documented output paths in a sandbox.
