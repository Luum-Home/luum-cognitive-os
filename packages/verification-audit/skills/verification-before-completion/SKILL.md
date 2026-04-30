<!-- SCOPE: both -->
---
name: verification-before-completion
description: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims
version: 1.0.0
last-updated: 2026-03-21
source: superpowers (obra/superpowers)
tech: verification
audience: project
summary_line: "Use when about to claim work is complete, fixed, or passing, before committing…"

platforms: ["claude-code"]
prerequisites: []
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | Tests passing |

## Project Verification Commands

**Always run the appropriate verification for the service you changed:**

| Service | Verification Command | Path |
|---------|---------------------|------|
| BFF Ninja | `yarn test` | `mobile/bff-ninja` |
| Onboarding | `yarn test` | `micro-services/onboarding` |
| users-core (unit) | `make utest` | `micro-services/users-core/users-core` |
| users-core (all) | `make test` | `micro-services/users-core/users-core` |
| users-auth | `make test` | `micro-services/users-auth/users-auth` |
| monolith | `yarn test` | `services/acme-gateway` |
| wallet-go | `go test ./...` | `wallet-go` |
| contracts | `npx hardhat test` | contracts directory |
| Mobile App | `yarn test` | `mobile/app` |

**For multi-service changes, verify ALL affected services.**

## Red Flags - STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", etc.)
- About to commit/push/PR without verification
- Trusting agent success reports
- Relying on partial verification
- Thinking "just this once"
- Tired and wanting work over
- **ANY wording implying success without having run verification**

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence != evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter != compiler |
| "Agent said success" | Verify independently |
| "I'm tired" | Exhaustion != excuse |
| "Partial check is enough" | Partial proves nothing |
| "Different words so rule doesn't apply" | Spirit over letter |

## Key Patterns

**Tests:**
```
CORRECT: [Run test command] [See: 34/34 pass] "All tests pass"
WRONG:   "Should pass now" / "Looks correct"
```

**Regression tests (TDD Red-Green):**
```
CORRECT: Write -> Run (pass) -> Revert fix -> Run (MUST FAIL) -> Restore -> Run (pass)
WRONG:   "I've written a regression test" (without red-green verification)
```

**Build:**
```
CORRECT: [Run build] [See: exit 0] "Build passes"
WRONG:   "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
CORRECT: Re-read plan -> Create checklist -> Verify each -> Report gaps or completion
WRONG:   "Tests pass, phase complete"
```

**Agent delegation:**
```
CORRECT: Agent reports success -> Check VCS diff -> Verify changes -> Report actual state
WRONG:   Trust agent report
```

## Engram Integration

**After completing verification, save significant results:**
```
mem_save(
  title: "Verified: {what was verified}",
  type: "discovery",
  project: "{project}",
  content: "**What**: {verification performed}\n**Why**: {what triggered the verification}\n**Where**: {services/files verified}\n**Learned**: {any unexpected findings during verification}"
)
```

**Only save when verification reveals something non-obvious.** Routine "tests pass" doesn't need saving.

## Project Constitutional Gate Reference

- **Gate 3: Test Before Merge** - Verification is the enforcement mechanism for this gate
- **Gate 5: Backward Compatible APIs** - Verify BFF endpoints don't break mobile contract
- **Gate 6: Idempotent Operations** - Verify financial operations with duplicate requests

## When To Apply

**ALWAYS before:**
- ANY variation of success/completion claims
- ANY expression of satisfaction
- ANY positive statement about work state
- Committing, PR creation, task completion
- Moving to next task
- Delegating to agents

**Rule applies to:**
- Exact phrases
- Paraphrases and synonyms
- Implications of success
- ANY communication suggesting completion/correctness

## The Bottom Line

**No shortcuts for verification.**

Run the command. Read the output. THEN claim the result.

This is non-negotiable.
