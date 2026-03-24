# Secret Hygiene Rules

## Mandatory Practices

1. **Every new env var must be added to `.env.example`** — No exception. If code references `process.env.X`, `os.Getenv("X")`, or `System.getenv("X")`, the var must exist in the corresponding `.env.example` with a placeholder value.

2. **Never hardcode secrets in source** — API keys, passwords, tokens, connection strings must always come from environment variables. The `secret-detector` hook will flag violations.

3. **Use `PROVIDER_*` naming pattern for external services** — All external service credentials follow the pattern:
   - `PROVIDER_API_KEY` (e.g., `IDENTITY_PROVIDER_API_KEY`, `PAYMENT_GATEWAY_API_KEY`)
   - `PROVIDER_API_SECRET` (e.g., `IDENTITY_PROVIDER_API_SECRET`)
   - `PROVIDER_BASE_URL` (e.g., `IDENTITY_PROVIDER_BASE_URL`)

4. **Docker Compose env sections must mirror `.env.example`** — Any env var in `docker-compose.yml` environment blocks should also be in the corresponding service's `.env.example`.

5. **Mock flags follow `PROVIDER_MOCK` pattern** — e.g., `PAYMENT_GATEWAY_MOCK=true`, `CRYPTO_MOCK=true`. These control whether the mock or real provider is used.

## Enforcement

- **PostToolUse hook**: `secret-detector.sh` runs on every `Edit|Write` to source files
- **Audit skill**: `/secret-audit` performs full cross-reference scan
- **Metrics**: Missing secrets logged to `.cognitive-os/metrics/missing-secrets.jsonl`

## Cross-Reference Locations

| Language | Pattern | Where to define |
|----------|---------|----------------|
| TypeScript/Node | `process.env.X` | `.env`, `.env.example`, `docker-compose.yml` |
| Go | `os.Getenv("X")` | `.env`, `config/*.go`, `docker-compose.yml` |
| Java/Spring | `System.getenv("X")`, `@Value("${X}")` | `application.properties`, `.env.example` |
