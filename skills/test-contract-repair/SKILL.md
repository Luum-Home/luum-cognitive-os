<!-- SCOPE: os-only -->
---
name: test-contract-repair
description: Repair failing or misleading tests without greenwashing. Classify the contract, confirm history, fix runtime when needed, and strengthen structural checks into behavioral proof.
invoke: /test-contract-repair
version: 1.0.0
audience: os-dev
platforms: ["claude-code"]
prerequisites: []
---

# Test Contract Repair

Use this skill when Cognitive OS tests fail, skip suspiciously, or appear to
protect stale or structural-only behavior.

## Goal

Keep the suite honest.

Do not make tests pass by weakening them. Decide whether the runtime is broken,
the fixture is stale, the lane is optional, or the test is a false-positive
proxy for a product claim.

## Inputs

- failing test names or a failing test family;
- the relevant runtime files;
- the closest ADR, architecture doc, or repair-ledger evidence;
- the smallest trustworthy validation lane.

## Scope

This is an OS-maintainer skill, not a project-adopter skill.

- `<!-- SCOPE: os-only -->` keeps it internal to Cognitive OS development.
- `audience: os-dev` keeps it out of normal project installations.
- Self-hosted harness projections inside this repository may expose it under
  `.claude/skills/` or another active driver because the OS is developing
  itself. That does not make it a project-facing contract.

When repairing Cognitive OS tests, always run pytest through the persistent
summary wrapper so partial, interrupted, and full runs leave analyzable local
evidence:

```bash
bash scripts/pytest-with-summary.sh -- <pytest args>
```

The wrapper automatically writes `inventory.md` and `inventory.json` via
`scripts/test_run_inventory.py`. Use those files as the first triage surface
before rerunning a broad suite. They list failures, errors, skips, xfails,
slow tests, and heuristic tags such as `optional-lane`, `drift`,
`aspirational`, `timeout`, and `false-positive-risk`.

For projects that install Cognitive OS, use the project's own test command or a
project-facing test skill. Do not impose this OS-internal runner unless the
project explicitly opts into Cognitive OS development tooling.

## Classification

Classify each touched test before editing it:

- `active-contract`: the test protects current product behavior. Prefer fixing
  runtime, fixtures, or generated artifacts.
- `stale-contract`: the test protects behavior replaced by an ADR, commit, or
  current architecture decision. Update the test only after finding evidence.
- `optional-lane`: the test needs external infra, credentials, or platform
  capabilities not present in the default lane. Document the lane and command.
- `false-positive-risk`: the test can pass while proving only shape, headings,
  existence, or stale counts. Strengthen it into a behavioral contract.

If the failing test touches infrastructure, classify the dependency one step
further before deciding the repair:

- `core-default`: required for the default product path;
- `optional-integration`: supported but opt-in;
- `legacy-reference`: kept for migration, demos, or isolated validation only.

## Workflow

1. Reproduce the failure in the smallest targeted lane with
   `scripts/pytest-with-summary.sh`.
2. Read the enforcing runtime files, not only the test.
3. Check repository history, ADRs, and architecture docs before changing a
   failing expectation.
4. Decide whether the fix belongs in runtime, fixtures, generators, or the test.
5. If the test supports a product claim, add an observable effect:
   - install into a temp project;
   - project canonical state into a driver;
   - execute a hook or script;
   - read/write canonical metrics or state;
   - prove a real safety guard blocks or preserves something.
6. For infrastructure tests, do not silently promote optional/reference stacks
   into the default lane:
   - use lightweight contract tests for compose/runtime classification;
   - use `testcontainers` when you need isolated proof that a stack really boots;
   - keep localhost probes opt-in unless the service is truly core-default.
7. Re-run the narrow lane first, then the closest higher-confidence lane.
8. Record the generated run directory or `latest/summary.txt` when handing off
   evidence across sessions.
9. Use `inventory.md` to pick the next repair batch instead of scanning terminal
   scrollback or rerunning a slow suite just to recover the list.
10. Record the decision in `docs/reports/test-suite-repair-ledger-2026-04-24.md`
   if the change affects doctrine, historical interpretation, or future repair work.

## Guardrails

- Do not delete or relax tests just to make the suite green.
- Do not convert a runtime bug into a test update.
- Do not trust `.claude/settings.json` alone when the active contract is
  canonical-first or harness-aware.
- Do not keep file-existence checks as the only evidence for portability,
  governance, verification, or installability claims.
- Do not make optional or legacy Docker stacks look like default-lane product
  requirements just because they still exist in `docker-compose.cognitive-os.yml`.

## Required References

- `docs/architecture/behavioral-test-contracts.md`
- `docs/reports/test-suite-repair-ledger-2026-04-24.md`

## Done When

- the failure is classified with evidence;
- runtime and tests agree with current product behavior;
- the validation lane passes;
- the run artifact under `.cognitive-os/reports/test-runs/` can be inspected;
- `inventory.md` exists for the validation run;
- the repository now proves more real behavior than before the repair.
