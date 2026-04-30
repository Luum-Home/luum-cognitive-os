<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Credential Management

## Never in Code
- API keys, tokens, passwords -> environment variables only
- .env files -> gitignored
- Docker secrets for production

## Credential Validation
Before using any external service, verify:
1. Required env var exists
2. Not empty/placeholder
3. Not expired (if applicable)
4. Correct format (API key pattern, JWT structure)

## Environment Variable Hygiene

| Category | Pattern | Example |
|----------|---------|---------|
| Database | `{SERVICE}_DB_{PARAM}` | `APP_DB_HOST` |
| External API | `{PROVIDER}_API_KEY` | `STRIPE_API_KEY` |
| Internal service | `{SERVICE}_URL` | `AUTH_SERVICE_URL` |
| Feature flags | `{PROVIDER}_MOCK` | `PAYMENTS_MOCK` |
| Auth | `AUTH_*` or provider-specific | `AUTH_BASE_URL` |

## Prohibited Patterns

- Hardcoded credentials in source files
- Credentials in Docker build args (visible in image layers)
- Credentials in URL parameters (logged by proxies/servers)
- Credentials in commit messages or PR descriptions
- Sharing credentials via chat/email (use vault or env injection)

## Local Development Credentials

Local-only credentials (defined in project config) are acceptable for development. These MUST NOT be used in any non-local environment.

## Validation Script Pattern

Services should validate required credentials at startup:
```typescript
// Node.js example
const required = ['AUTH_BASE_URL', 'AUTH_REALM', 'API_KEY'];
for (const key of required) {
  if (!process.env[key]) {
    throw new Error(`Missing required env var: ${key}`);
  }
}
```

```java
// Spring Boot example - use @Value with validation
@Value("${auth.base-url}")
@NotBlank
private String authBaseUrl;
```

```go
// Go example
func mustGetEnv(key string) string {
    val := os.Getenv(key)
    if val == "" {
        log.Fatalf("Missing required env var: %s", key)
    }
    return val
}
```
