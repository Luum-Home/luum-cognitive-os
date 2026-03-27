# Rebranding Checklist

When touching code that references old brand names:

- **Rename**: Update old brand name to new brand name in Go packages, variables, comments, log messages, error strings
- **Preserve DB**: Do NOT rename database column names, table names, or migration files
- **Preserve API**: Do NOT rename JSON field names in API request/response contracts
- **Preserve headers**: Do NOT rename custom HTTP headers that are part of the mobile API contract
- **Preserve bundle IDs**: Do NOT change app bundle IDs (App Store / Play Store registration)

When in doubt, preserve external-facing names and rename internal-only references.
