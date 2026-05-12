# ADR Verification Evidence Contract

## Purpose

ADR verification must prove that a decision is true in the repository, not merely
that the ADR number appears somewhere. The ADR-067 section contract already
requires a `## Verification` section with a fenced code block for ADR-067 and
later. This document tightens the evidence model so that the code block is a
meaningful, repeatable assertion.

## Problem

A patch can satisfy the current structural contract with a weak command such as:

```bash
grep -rn 'ADR-262' docs/ scripts/ tests/ | head -20
```

That command proves only textual mention. It does not prove that the decision's
implementation files exist, that behavior works, that negative cases fail, or
that an audit gate enforces the boundary. This creates documentation theater:
the ADR appears compliant while the underlying decision may be unimplemented or
untested.

## Evidence levels

| Level | Meaning | Examples | Acceptable for implemented ADRs? |
|---|---|---|---|
| `strong` | Executes behavior, contract, audit, or smoke proof tied to the decision. | `python3 -m pytest tests/unit/test_x.py -q`, `scripts/foo-audit --fail-on-block`, `bash -n hooks/foo.sh` | Yes |
| `medium` | Proves declared implementation surfaces exist or compile, but not behavior alone. | `test -e lib/foo.py`, `python3 -m py_compile lib/foo.py` | Only with at least one strong command, or for non-runtime decisions |
| `weak` | Searches for ADR mentions or lists files without asserting the decision. | `grep -rn 'ADR-262' ...`, `find . -name '*foo*'`, `ls docs/adrs/ADR-262*` | No |
| `invalid` | Empty, placeholder, non-deterministic, or references missing paths. | `true`, `echo TODO`, `false # replace later` in accepted ADR | No |

## Contract

For ADR-067 and later:

1. `## Verification` MUST contain at least one fenced code block.
2. A generic ADR-number grep MUST NOT be the only verification command.
3. If `implementation_status` is `implemented` or `partial`, verification MUST
   include at least one strong command or an explicit `verification.level` waiver
   explaining why behavior cannot be executed locally.
4. If `implementation_files` is non-empty, every declared path MUST resolve
   on disk. This is unconditional: `status: accepted` with
   `implementation_status: implemented` is still a disk-verifiable claim. Globs
   are allowed only when they match at least one repository path. Presence alone
   is not enough for a runtime behavior claim.
5. A §Operational Guide backfill MUST NOT treat the ADR's own §Decision prose
   as implementation evidence. Operational guidance may explain how to operate
   verified files, tests, hooks, or scripts; it cannot promote or justify
   `implementation_status: implemented` by restating the decision.
6. If the ADR is `proposed`, `exploration`, or `not-applicable`, verification may
   prove decision-state/document integrity instead of runtime behavior, but it
   must say so explicitly.

## Frontmatter shape

ADRs may declare verification metadata to make the audit deterministic:

```yaml
verification:
  level: strong
  commands:
    - python3 -m pytest tests/unit/test_example.py -q
  proves:
    - behavior_contract
    - negative_case
```

Valid `level` values are:

- `strong`
- `medium`
- `weak`
- `not-applicable`

The audit derives a level from code blocks when frontmatter is absent, but
frontmatter is preferred for new ADRs because it makes intent explicit and keeps
future audits stable.

## Migration pattern

Replace weak grep-only blocks with one of these:

### Implemented code ADR

```bash
python3 -m py_compile lib/example.py
python3 -m pytest tests/unit/test_example.py tests/contracts/test_example_contract.py -q
```

### Audit/control-plane ADR

```bash
python3 scripts/example_audit.py --project-dir . --json --fail-on-block
python3 -m pytest tests/unit/test_example_audit.py -q
```

### Hook ADR

```bash
bash -n hooks/example-hook.sh
python3 -m pytest tests/unit/test_example_hook.py -q
```

### Decision-state ADR

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q -k 'ADR_262 or verification'
```

## Enforcement plan

1. Add `scripts/adr_verification_audit.py` to classify ADR verification evidence.
2. Add contract tests proving weak grep-only verification is blocked.
3. Update `scripts/cos_new_adr.py` so new ADR drafts produce structured
   verification metadata and a non-theatrical default command.
4. Backfill existing weak ADRs with stronger commands where evidence exists.
5. Wire the audit into ACC or the documentation-truth lane after the backfill
   stabilizes.
6. Keep `scripts/audit_adrs.py` as the minimum hard gate for declared
   `implementation_files` existence; specialized audits may add allowlists or
   richer behavior checks, but must not weaken the disk-existence contract.
