# Testing Anti-Patterns

**Load this reference when:** writing or changing tests, adding mocks, or tempted to add test-only methods to production code.

## Overview

Tests must verify real behavior, not mock behavior. Mocks are a means to isolate, not the thing being tested.

**Core principle:** Test what the code does, not what the mocks do.

**Following strict TDD prevents these anti-patterns.**

## The Iron Laws

```
1. NEVER test mock behavior
2. NEVER add test-only methods to production classes
3. NEVER mock without understanding dependencies
```

## Anti-Pattern 1: Testing Mock Behavior

**The violation:** Asserting on mock elements instead of real component behavior.

**Gate Function:**
```
BEFORE asserting on any mock element:
  Ask: "Am I testing real component behavior or just mock existence?"
  IF testing mock existence: STOP - Delete the assertion or unmock the component
```

## Anti-Pattern 2: Test-Only Methods in Production

**The violation:** Adding destroy(), reset(), _testOnly_*() methods to production classes.

**Gate Function:**
```
BEFORE adding any method to production class:
  Ask: "Is this only used by tests?"
  IF yes: STOP - Put it in test utilities instead
```

## Anti-Pattern 3: Mocking Without Understanding

**The violation:** Mocking a method that has side effects the test depends on.

**Gate Function:**
```
BEFORE mocking any method:
  1. Ask: "What side effects does the real method have?"
  2. Ask: "Does this test depend on any of those side effects?"
  3. Ask: "Do I fully understand what this test needs?"

  IF depends on side effects: Mock at lower level
  IF unsure: Run test with real implementation FIRST
```

## Anti-Pattern 4: Incomplete Mocks

**The Iron Rule:** Mock the COMPLETE data structure as it exists in reality, not just fields your immediate test uses.

## Anti-Pattern 5: Integration Tests as Afterthought

Testing is part of implementation, not optional follow-up. TDD prevents this by design.

## Common Project-Specific Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Mocking DB in integration tests | Use TestContainers or real test DB |
| Not using mock flags for external providers | Set PROVIDER_MOCK=true in test env |
| Testing mock providers instead of business logic | Test the service method, not the HTTP mock |
| Incomplete WireMock/nock stubs | Mirror real API response fully |

## Quick Reference

| Anti-Pattern | Fix |
|--------------|-----|
| Assert on mock elements | Test real component or unmock it |
| Test-only methods in production | Move to test utilities |
| Mock without understanding | Understand dependencies first, mock minimally |
| Incomplete mocks | Mirror real API completely |
| Tests as afterthought | TDD - tests first |
| Over-complex mocks | Consider integration tests |

## The Bottom Line

**Mocks are tools to isolate, not things to test.**

If TDD reveals you're testing mock behavior, you've gone wrong.
