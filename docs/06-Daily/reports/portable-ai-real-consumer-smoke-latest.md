# Portable `.ai` Real Consumer Smoke — Latest

Generated: 2026-05-10T18:39:23+00:00
Status: `pass`
Mode: `read-only-consumer-shadow`

- available registered consumers: 5
- tested consumer shadows: 2
- passing shadows: 2
- overlay files: 389

## Consumer shadows

| Consumer | Harness | Project status | Smoke | Primitive files | Actual unchanged |
|---|---|---|---|---:|---|
| `consumidor-b` | `claude` | `pass` | `pass` | 307 | `True` |
| `cos-consumer-e2e-drill` | `codex` | `pass` | `pass` | 307 | `True` |

This smoke never writes to registered consumer repositories. It projects the generated `.ai` overlay into temporary consumer shadows and checks the real consumer `.ai` snapshot is unchanged.
