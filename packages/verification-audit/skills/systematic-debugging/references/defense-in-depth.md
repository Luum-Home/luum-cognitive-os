# Defense-in-Depth Validation

## Overview

When you fix a bug caused by invalid data, adding validation at one place feels sufficient. But that single check can be bypassed by different code paths, refactoring, or mocks.

**Core principle:** Validate at EVERY layer data passes through. Make the bug structurally impossible.

## The Four Layers

### Layer 1: Entry Point Validation
Reject obviously invalid input at API boundary.

```typescript
// NestJS DTO validation (Node services)
@IsNotEmpty() @IsString() email: string;

// Spring Boot Bean Validation (JVM services)
@NotBlank @Email private String email;

// Express.js Zod validation (Node monolith)
const schema = z.object({ email: z.string().email() });
```

### Layer 2: Business Logic Validation
Ensure data makes sense for this operation.

### Layer 3: Environment Guards
Prevent dangerous operations in specific contexts (test vs prod).

### Layer 4: Debug Instrumentation
Capture context for forensics.

## Project Application

For multi-service architectures, defense-in-depth is critical at service boundaries:

1. **API gateway validates** incoming client requests (DTOs, headers)
2. **Backend services validate** requests from gateway (don't trust upstream)
3. **Database constraints** enforce data integrity (NOT NULL, UNIQUE, FK)
4. **Mock flags** prevent accidental calls to production providers

## Key Insight

All four layers are necessary. During testing, each layer catches bugs the others miss.

**Don't stop at one validation point.** Add checks at every layer.
