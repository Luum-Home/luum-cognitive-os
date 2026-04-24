<!-- SCOPE: os-only -->
---
name: test-contract-repair
description: Repair failing or misleading tests without greenwashing. Classify the contract, confirm history, fix runtime when needed, and strengthen structural checks into behavioral proof.
invoke: /test-contract-repair
version: 1.0.0
audience: os-dev
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

## Workflow

1. Reproduce the failure in the smallest targeted lane.
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
6. Re-run the narrow lane first, then the closest higher-confidence lane.
7. Record the decision in `docs/reports/test-suite-repair-ledger-2026-04-24.md`
   if the change affects doctrine, historical interpretation, or future repair work.

## Guardrails

- Do not delete or relax tests just to make the suite green.
- Do not convert a runtime bug into a test update.
- Do not trust `.claude/settings.json` alone when the active contract is
  canonical-first or harness-aware.
- Do not keep file-existence checks as the only evidence for portability,
  governance, verification, or installability claims.

## Required References

- `docs/architecture/behavioral-test-contracts.md`
- `docs/reports/test-suite-repair-ledger-2026-04-24.md`

## Done When

- the failure is classified with evidence;
- runtime and tests agree with current product behavior;
- the validation lane passes;
- the repository now proves more real behavior than before the repair.
