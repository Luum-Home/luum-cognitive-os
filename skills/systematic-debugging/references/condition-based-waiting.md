# Condition-Based Waiting

## Overview

Flaky tests often guess at timing with arbitrary delays. This creates race conditions where tests pass on fast machines but fail under load or in CI.

**Core principle:** Wait for the actual condition you care about, not a guess about how long it takes.

## When to Use

**Use when:**
- Tests have arbitrary delays (setTimeout, sleep, Thread.sleep())
- Tests are flaky (pass sometimes, fail under load)
- Tests timeout when run in parallel
- Waiting for async operations to complete
- Waiting for Docker containers to be ready (health checks)

## Core Pattern

```typescript
// WRONG: Guessing at timing
await new Promise(r => setTimeout(r, 50));

// RIGHT: Waiting for condition
await waitFor(() => getResult() !== undefined);
```

## Common Patterns

### Waiting for service health in integration tests
```typescript
await waitFor(
  () => fetch('http://localhost:{port}/health').then(r => r.ok).catch(() => false),
  'service health check',
  30000
);
```

### Waiting for async message processing
```typescript
await waitFor(
  () => db.findOne({ transactionId }).then(r => r?.status === 'processed'),
  'transaction processed via message broker',
  10000
);
```

## Implementation

```typescript
async function waitFor<T>(
  condition: () => T | undefined | null | false,
  description: string,
  timeoutMs = 5000
): Promise<T> {
  const startTime = Date.now();
  while (true) {
    const result = condition();
    if (result) return result;
    if (Date.now() - startTime > timeoutMs) {
      throw new Error(`Timeout waiting for ${description} after ${timeoutMs}ms`);
    }
    await new Promise(r => setTimeout(r, 10));
  }
}
```

## When Arbitrary Timeout IS Correct

Only when testing actual timing behavior (debounce, throttle). Always document WHY.
