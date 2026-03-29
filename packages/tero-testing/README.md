# @luum/tero-testing

Tero HTTP testing with chaos engineering integration for Cognitive OS.

## What

Integrates [tero](https://github.com/garagon/tero) into the Cognitive OS testing workflow. Tero provides deterministic HTTP testing with built-in chaos engineering primitives: fault injection, latency simulation, connection drops, and payload corruption.

## Install

```bash
go install github.com/garagon/tero@latest
```

## When to Use

- Testing HTTP endpoints with chaos scenarios (timeouts, 5xx errors, partial responses)
- Verifying service resilience under failure conditions
- Integration test suites that need deterministic failure injection
- Load testing with controlled chaos patterns

## Components

- `rules/tero-integration.md` -- Integration documentation and usage patterns

## Status

WATCH -- Evaluated and documented. No hook implementation yet. Use directly via CLI.

## License

Apache-2.0
