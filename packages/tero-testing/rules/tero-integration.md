# Tero -- HTTP Testing with Chaos Engineering

## Overview

Tero is an HTTP testing tool with built-in chaos engineering primitives from the [garagon](https://github.com/garagon) ecosystem. It provides deterministic HTTP testing with fault injection, latency simulation, connection drops, and payload corruption.

## Installation

```bash
go install github.com/garagon/tero@latest
```

## Integration with Cognitive OS

### When to Use Tero

| Scenario | Use Tero? | Why |
|----------|-----------|-----|
| Unit testing HTTP handlers | No | Use Go's httptest or framework-native testing |
| Integration testing with chaos | Yes | Tero adds fault injection that httptest lacks |
| Resilience testing | Yes | Simulate timeouts, 5xx errors, connection drops |
| Load testing with failures | Yes | Controlled chaos under load |
| CI/CD pipeline testing | Optional | Add as a test stage for resilience validation |

### Usage Patterns

#### Basic HTTP Test
```bash
tero test --url http://localhost:3000/api/health --expect-status 200
```

#### Chaos: Latency Injection
```bash
tero chaos --url http://localhost:3000/api/users \
  --latency 2000ms \
  --expect-timeout-handling
```

#### Chaos: Fault Injection
```bash
tero chaos --url http://localhost:3000/api/orders \
  --inject-500 0.3 \
  --expect-retry
```

#### Chaos: Connection Drop
```bash
tero chaos --url http://localhost:3000/api/payments \
  --drop-connection 0.1 \
  --expect-circuit-breaker
```

### Integration with SDD Pipeline

Tero can be used in the `sdd-verify` phase for resilience validation:

1. After `sdd-apply` produces new HTTP endpoints
2. Run `tero test` for basic functionality
3. Run `tero chaos` for resilience under failure
4. Include results in the verify report

### Metrics

Test results can be output as JSON and appended to `.cognitive-os/metrics/tero-results.jsonl`:

```bash
tero test --url $ENDPOINT --output json >> .cognitive-os/metrics/tero-results.jsonl
```

## Graceful Degradation

If tero is not installed, testing falls back to standard HTTP testing tools (curl, httptest, etc.). Tero is an enhancement, not a requirement.

## Contextual Trigger

This rule is loaded when: tero, chaos testing, fault injection, resilience testing, http chaos.
