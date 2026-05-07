# Root Cause Tracing

## Overview

Bugs often manifest deep in the call stack. Your instinct is to fix where the error appears, but that's treating a symptom.

**Core principle:** Trace backward through the call chain until you find the original trigger, then fix at the source.

## When to Use

**Use when:**
- Error happens deep in execution (not at entry point)
- Stack trace shows long call chain
- Unclear where invalid data originated
- Need to find which test/code triggers the problem
- Cross-service errors in the project stack (BFF -> microservice -> DB)

## The Tracing Process

### 1. Observe the Symptom
### 2. Find Immediate Cause - What code directly causes this?
### 3. Ask: What Called This? Trace the call chain.
### 4. Keep Tracing Up - What value was passed at each level?
### 5. Find Original Trigger - Where did the bad data originate?

## Project Multi-Service Tracing

For cross-service issues, trace through the architecture layers:

```
Mobile App (headers: API-Key, Device-ID)
    |
    v
BFF / API gateway (JWT validation, request transformation)
    |
    v
Microservice (business logic, DB operations)
    |
    v
External Provider / Database
```

**At each boundary, check:**
1. What data enters this layer?
2. What transformation happens?
3. What data exits to the next layer?
4. Are auth tokens/headers propagated correctly?

## Adding Stack Traces

When you can't trace manually, add instrumentation:

```typescript
// Before the problematic operation
const stack = new Error().stack;
console.error('DEBUG:', { relevantData, stack });
```

**Critical:** Use `console.error()` in tests (not logger - may not show)

## Key Principle

**NEVER fix just where the error appears.** Trace back to find the original trigger.

Fix at source + add validation at each layer = bug structurally impossible.
