<!-- SCOPE: both -->
---
name: test-driven-development
description: Use when implementing any feature or bugfix, before writing implementation code
version: 1.0.0
last-updated: 2026-03-21
source: superpowers (obra/superpowers)
tech: testing
audience: project
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## When to Use

**Always:**
- New features
- Bug fixes
- Refactoring
- Behavior changes

**Exceptions (ask the user):**
- Throwaway prototypes
- Generated code
- Configuration files

Thinking "skip TDD just this once"? Stop. That's rationalization.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.

## Red-Green-Refactor

### RED - Write Failing Test

Write one minimal test showing what should happen.

**Requirements:**
- One behavior
- Clear name
- Real code (no mocks unless unavoidable)

**Test naming**: Use descriptive names that explain the scenario: `should_[result]_when_[condition]` or `Test[Function]_[Scenario]_[Expected]`.

**Check project test setup**: See `.claude/rules/testing-local.md` for project-specific test frameworks, locations, and commands.

### Verify RED - Watch It Fail

**MANDATORY. Never skip.**

Run the test. Confirm:
- Test fails (not errors)
- Failure message is expected
- Fails because feature missing (not typos)

**Test passes?** You're testing existing behavior. Fix test.

**Test errors?** Fix error, re-run until it fails correctly.

### GREEN - Minimal Code

Write simplest code to pass the test.

Don't add features, refactor other code, or "improve" beyond the test.

### Verify GREEN - Watch It Pass

**MANDATORY.**

Confirm:
- Test passes
- Other tests still pass
- Output pristine (no errors, warnings)

**Test fails?** Fix code, not test.

**Other tests fail?** Fix now.

### REFACTOR - Clean Up

After green only:
- Remove duplication
- Improve names
- Extract helpers

Keep tests green. Don't add behavior.

### Repeat

Next failing test for next feature.

## Good Tests

| Quality | Good | Bad |
|---------|------|-----|
| **Minimal** | One thing. "and" in name? Split it. | `test('validates email and domain and whitespace')` |
| **Clear** | Name describes behavior | `test('test1')` |
| **Shows intent** | Demonstrates desired API | Obscures what code should do |

## Why Order Matters

**"I'll write tests after to verify it works"**

Tests written after code pass immediately. Passing immediately proves nothing:
- Might test wrong thing
- Might test implementation, not behavior
- Might miss edge cases you forgot
- You never saw it catch the bug

**"Deleting X hours of work is wasteful"**

Sunk cost fallacy. The time is already gone. Working code without real tests is technical debt.

**"TDD is dogmatic, being pragmatic means adapting"**

TDD IS pragmatic:
- Finds bugs before commit (faster than debugging after)
- Prevents regressions (tests catch breaks immediately)
- Documents behavior (tests show how to use code)
- Enables refactoring (change freely, tests catch breaks)

**"Tests after achieve the same goals - it's spirit not ritual"**

No. Tests-after answer "What does this do?" Tests-first answer "What should this do?"

Tests-after are biased by your implementation. You test what you built, not what's required.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Tests after achieve same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" |
| "Already manually tested" | Ad-hoc != systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing after. Delete means delete. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |
| "Test hard = design unclear" | Listen to test. Hard to test = hard to use. |
| "TDD will slow me down" | TDD faster than debugging. Pragmatic = test-first. |
| "Manual test faster" | Manual doesn't prove edge cases. You'll re-test every change. |
| "Existing code has no tests" | You're improving it. Add tests for existing code. |

## Red Flags - STOP and Start Over

- Code before test
- Test after implementation
- Test passes immediately
- Can't explain why test failed
- Tests added "later"
- Rationalizing "just this once"
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "It's about spirit not ritual"
- "Keep as reference" or "adapt existing code"
- "Already spent X hours, deleting is wasteful"
- "TDD is dogmatic, I'm being pragmatic"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**

## TDD Examples by Language

### TypeScript (Jest)
```typescript
// RED: Write the test first
describe('UserService', () => {
  it('should_return_user_when_valid_id', async () => {
    const result = await service.findById('valid-id');
    expect(result).toBeDefined();
    expect(result.id).toBe('valid-id');
  });
});
```

### Java (JUnit)
```java
// RED: Write the test first
@Test
void should_return_user_when_valid_id() {
    // Arrange
    // Act
    var result = userService.findById("valid-id");
    // Assert
    assertThat(result).isNotNull();
    assertThat(result.getId()).isEqualTo("valid-id");
}
```

### Go (testing + testify)
```go
// RED: Table-driven test first
func TestTransfer(t *testing.T) {
    tests := []struct{
        name     string
        input    TransferRequest
        expected error
    }{
        {"should_fail_when_insufficient_balance", req, ErrInsufficientBalance},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := svc.Transfer(tt.input)
            assert.ErrorIs(t, err, tt.expected)
        })
    }
}
```

## Mock Boundaries (where mocks are acceptable)

- HTTP calls to external services (WireMock in Java, jest.mock in TS)
- External providers controlled by mock flags
- Cloud storage services
- Message queues in unit tests

**NOT acceptable to mock:**
- Database in integration tests (use TestContainers / real DB)
- Business logic
- Internal service calls within same service

## Engram Integration

**After establishing a new TDD pattern, save it:**
```
mem_save(
  title: "TDD pattern: {what was tested}",
  type: "pattern",
  project: "{project}",
  content: "**What**: {test approach used}\n**Why**: {what it validates}\n**Where**: {service and files}\n**Learned**: {gotchas about testing this}"
)
```

## Constitutional Gate Reference

- **Test Before Merge** - All new code must have tests. TDD ensures this by design.
- Check `.claude/rules/constitutional-gates.md` for project-specific gates that affect testing.

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered

Can't check all boxes? You skipped TDD. Start over.

## Related Skills

- **systematic-debugging** - Use when tests reveal bugs during TDD
- **verification-before-completion** - Verify all tests pass before claiming done
- **testing-patterns** - project-specific test frameworks and conventions (in `.claude/skills/`)

## Final Rule

```
Production code -> test exists and failed first
Otherwise -> not TDD
```

No exceptions without the user's permission.
