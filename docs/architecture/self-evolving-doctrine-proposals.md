# Self-Evolving Doctrine Proposals

The doctrine proposer is the second headless self-improvement loop:

```text
control-plane evidence -> doctrine amendment proposal -> human review
```

It complements the operational proposer from ADR-134. ADR-134 proposes bounded
fix work. ADR-135 proposes changes to the doctrine that governs future work.

## Command

```bash
scripts/cos-doctrine-proposer --profile core --json
```

To persist the generated proposal:

```bash
scripts/cos-doctrine-proposer --profile core --write
```

The output path is:

```text
docs/proposals/doctrine-amendment-<timestamp>.md
```

## Safety contract

Generated doctrine proposals:

- are `status: proposed`;
- have `runtime_effect: none`;
- do not edit live rules;
- do not edit hooks;
- do not edit skills;
- do not flip ADR status;
- do not mutate lifecycle manifests.

## Evidence sources

| Evidence | Doctrine pressure |
|---|---|
| `direct-main-bypass.jsonl` | emergency bypasses need audit/review cadence |
| false-positive ledger | gates should parse scoped/semantic fields before substring fallback |
| demotion loop | warnings need expiry, owner, or explicit deferral |
| silent-failure audit | maintainer-cache allowlists are not Shape-B transferable |
| self-improvement proposal policy | self-improvement remains propose-only until signed evidence exists |

## Cross-instance learning

Cross-instance learning remains blocked by ADR-132 Shape-B triggers. The current
system may collect consumer evidence manually, but it does not yet federate
Engram, locks, skill registries, or runtime markers across machines.

That is deliberate. The doctrine proposer can name the boundary; it cannot
erase it.
