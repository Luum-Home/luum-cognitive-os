# Cross-IDE Claim Verification Matrix

## Purpose

Cognitive OS does not treat sub-agent reports as closure authority. A sub-agent can report facts, but the orchestrator must independently verify high-stakes claims before marking work closed, committing plan closure, or pushing closure commits.

This contract is cross-IDE because the core verifier is a plain Python CLI and the enforcement hook runs on the Bash tool surface, which is the portable hook surface projected to Claude Code, Codex, and future harness drivers.

## Operating rule

1. The sub-agent can report, but cannot close.
2. The orchestrator extracts high-stakes claims from the report or commit message.
3. The orchestrator runs deterministic verifiers against the current repository state, not commands supplied by the sub-agent.
4. Closure/archival/wiring/registration claims either have bilateral proof or the plan remains open.
5. Commit/push attempts that carry false closure claims are blocked by the cross-IDE Bash gate.
6. Plans use inline executable evidence:

```md
- [x] task done (verified: command -> expected output)
```

## Matrix

| Claim verb | Complete predicate | Verifier | Hook / gate | Tests |
|---|---|---|---|---|
| `archived` | archive copy present, original absent, no stale config refs | `lib.orchestrator_verify.verify_claim`; `scripts/verify-archived.sh` for explicit archive manifests | `hooks/orchestrator-claim-gate.sh`; `hooks/claim-validator.sh` for Agent reports | `tests/contracts/test_orchestrator_verify.py`; `tests/red_team/portability/verify-archived.bats` |
| `deleted` / `removed` | target absent and no stale config refs | `lib.orchestrator_verify.verify_claim` | `hooks/orchestrator-claim-gate.sh` | `tests/contracts/test_orchestrator_verify.py`; `tests/contracts/test_orchestrator_claim_gate.py` |
| `wired` / `integrated` / `registered` | target exists and is referenced from known config or integration surface | `lib.orchestrator_verify.verify_claim` | `hooks/orchestrator-claim-gate.sh` | `tests/contracts/test_orchestrator_verify.py` |
| `done` / `closed` / `migrated` | claim includes inline executable evidence marker or remains open | `lib.orchestrator_verify.verify_claim`; `scripts/verify_plan_claims.py` | `hooks/plan-claim-validator.sh`; `hooks/orchestrator-claim-gate.sh` | `tests/contracts/test_orchestrator_claim_gate.py`; `tests/red_team/portability/plan-claim-validator.bats` |
| file creation/update claims | claimed artifact exists in the repo | `hooks/claim-validator.sh` | `hooks/claim-validator.sh` on Agent outputs where the harness exposes Agent events | `tests/behavior/test_claim_validator.py` |

## Enforcement surfaces

### Portable Bash gate

`hooks/orchestrator-claim-gate.sh` runs from `PreToolUse` on Bash commands. It inspects `git commit` and `git push` commands and delegates to:

```bash
python3 scripts/orchestrator_claim_gate.py --mode pre-commit --command 'git commit -m "..."'
python3 scripts/orchestrator_claim_gate.py --mode pre-push --command 'git push origin main'
```

The script appends JSONL evidence to:

```text
.cognitive-os/metrics/orchestrator-claim-gate.jsonl
```

### Plan edit gate

`hooks/plan-claim-validator.sh` runs when a harness exposes Edit/Write/MultiEdit hooks. It blocks or warns on bare `[x]` closure lines without `(verified: ...)`.

### Agent output gate

`hooks/claim-validator.sh` runs when a harness exposes Agent completion events. Codex currently does not expose an Agent matcher through the native hook projection, so the portable Bash commit/push gate is the shared baseline.

## Handoff contract for sub-agents

Every sub-agent handoff that claims closure must include a compact, machine-checkable section:

```md
## Verifiable Claims
- verb: archived
  target: hooks/example.sh
  evidence: scripts/verify-archived.sh --archive-dir docs/99-Archive/archive/hooks --source-dir hooks --manifest example.sh --config-globs '.claude/settings.json,cognitive-os.yaml' -> exit 0
- verb: done
  target: .cognitive-os/plans/current.md
  evidence: python3 scripts/verify_plan_claims.py .cognitive-os/plans/current.md -> PASS
```

The orchestrator treats this section as input only. It still runs its own verifier before closure.

## Known limits

- Claims in prose without path-like targets can be detected but may be unverifiable until the agent names the target.
- Codex projection currently relies on Bash commit/push enforcement for shared safety because Agent and Edit/Write hook events are not native in the same way as Claude Code.
- Test-result claims are not auto-executed inside hooks; the gate requires persisted or explicit evidence rather than launching expensive suites during commit.
