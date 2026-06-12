---
name: dod-check
description: Run a deterministic Definition of Done check before claiming implementation, review, prompt-modernization, hook, skill, rule, release-prep, backend, frontend, UI component, or Storybook/documentation work is complete. Use when verifying finished work, selecting completion criteria, or mapping changed files to portable DoD profiles across any project stack.
metadata:
  command: /dod-check
  version: 1.2.0
  audience: project
  platforms:
  - claude-code
  - codex
  prerequisites: []
  inputs:
  - task_description (optional): What was done
  - complexity (optional): trivial | small | medium | large | critical. Auto-classified when omitted.
  outputs:
  - verdict: PASS | PARTIAL | FAIL
  - complexity: classified complexity level
  - dod_profiles: portable completion profiles inferred from changed files
  - stack_signals: repository stack/tooling signals detected from manifests/config
  - checks: deterministic hygiene and validation recommendations
  routing_intents:
  - check definition of done for a completed task
  - verify task completion criteria before declaring work finished
  - run a done check before claiming completion
  - assess whether backend frontend UI component or Storybook work is finished
  - report missing items against the definition of done
  triggers:
  - dod-check
  - /dod-check
  - $dod-check
  - Definition of Done Check
---
<!-- SCOPE: both -->
# Definition of Done Check

Use this skill before claiming work is complete. It combines a cheap deterministic
checker with portable DoD profiles for common engineering surfaces.

## Workflow

1. Run the deterministic checker from the repository root. In this SO repo, use:

```bash
python3 scripts/dod_check.py --format markdown
```

In an installed consumer project, use the projected skill-local checker:

```bash
python3 .cognitive-os/skills/cos/dod-check/scripts/check_dod.py --format markdown
```

2. Read `dod_profiles` and `stack_signals` in the output. `dod_profiles`
   classify the work surface; `stack_signals` report detected language,
   framework, package-manager, test-runner, and documentation tooling evidence.
3. For profile details, load
   `packages/quality-gates/skills/dod-check/references/dod-profiles.md` from the
   source repo or `references/dod-profiles.md` from an installed skill copy.
4. Convert each active profile into concrete acceptance criteria for the target
   repo. Do not assume a framework, package manager, test runner, UI library,
   database, or Storybook setup unless `stack_signals` or direct file evidence
   prove it.
5. Treat missing or weak `stack_signals` as uncertainty: base DoD still applies,
   but stack-specific validation needs project input or manifest discovery.
6. Treat `FAIL` items as blockers for completion claims.
7. Treat `PARTIAL` as unfinished work unless the skipped lane is explicitly out
   of scope.
8. Treat `WARN` items as explicit uncertainties in the Trust Report.
9. If the checker recommends a validation command, run the smallest command that
   covers the changed surface.
10. Report the checker verdict, active profiles, stack signals, validation
   command, and any skipped checks in the final answer.

## Portable DoD Profiles

The checker may infer these profiles from changed paths:

- `backend-api`: server handlers, APIs, auth, jobs, webhooks, persistence, migrations.
- `frontend-feature`: screens, routes, feature components, client hooks, forms, app-shell work.
- `ui-component`: reusable UI/design-system components, tokens, themes, shared visual APIs.
- `storybook-docs`: stories, MDX/component docs, visual examples, interaction examples.

Profiles are overlays. Apply every touched profile. Use the reference file for
detailed checks, then bind them to the repository's detected stack signals and
actual commands.

## Stack signal detection

The checker detects stack signals from repository evidence such as:

- JavaScript/TypeScript manifests and lockfiles: `package.json`, `pnpm-lock.yaml`,
  `package-lock.json`, `yarn.lock`, `bun.lock`, `tsconfig.json`.
- Web frameworks and tools declared in dependencies/config: React, Next.js, Vue,
  Svelte, Angular, Vite, Storybook, Vitest, Jest, Playwright, Cypress.
- Python manifests: `pyproject.toml`, `requirements.txt`, `uv.lock`, `setup.py`,
  with framework/test signals such as Django, FastAPI, Flask, pytest, Ruff, mypy.
- Other ecosystem manifests: `go.mod`, `Cargo.toml`, Maven/Gradle files,
  `.csproj`, `Gemfile`, `composer.json`, `mix.exs`, `deno.json`.
- Runtime/deploy evidence: Dockerfile and docker-compose files.

Signals are advisory evidence, not command permission. A signal can guide which
DoD checks matter, but validation commands still need configured scripts,
project-local docs, or direct user instruction.

## Output format

The checker reports one of three verdicts: `PASS`, `PARTIAL`, or `FAIL`. `PASS`
means deterministic checks found no blockers. `PARTIAL` means required evidence is
incomplete or a validation lane was intentionally skipped. `FAIL` means at least
one deterministic blocker is present.

## Phase enforcement

In `reconstruction` and `stabilization`, missing DoD evidence is usually a
`WARN` unless the task is security-, release-, or credential-sensitive. In
`production` and `maintenance`, missing required evidence is a `BLOCK` for
completion claims.

## Notes

- The checker does not run expensive test lanes by default.
- Use `--run-recommended` only when the recommended command is safe for the
  current machine and task scope.
- Security, credential, release, and destructive-git boundaries remain governed
  by deterministic hook and script checks rather than prose.
- Claude Code invokes this as `/dod-check`; Codex invokes the projected skill as
  `$dod-check`. Both use the same deterministic checker logic.
- Imported project-specific DoD prose should be adapted into portable profiles,
  not copied as hardcoded stack policy.

## Contextual Trigger

Keywords: done, completion, Definition of Done, DoD, verify finished work, Trust
Report, backend DoD, frontend DoD, component DoD, Storybook DoD, before final
answer.
