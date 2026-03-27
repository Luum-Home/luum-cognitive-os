---
name: contract-drift
description: >
  Detect drift between HTTP calls in source code and OpenAPI/Swagger contract
  definitions. Scans for fetch, axios, http.*, requests, and httpx patterns,
  compares against the contract spec, and produces a structured drift report.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-26
license: MIT
metadata:
  author: luum
---

## Purpose

Identify mismatches between the HTTP endpoints used in source code and the
endpoints documented in OpenAPI/Swagger specifications. Catches undocumented
calls, unused contract entries, and method mismatches before they become
production issues.

## Invocation

`/contract-drift [--spec=<path>] [--ignore=<glob,...>] [--src=<dir>]`

## What to Do

### Step 1: Locate the OpenAPI/Swagger Spec (REQ-02)

If `--spec` is provided, use that path directly.

Otherwise, auto-detect by searching for common locations:

```
Search order:
├── openapi.yaml / openapi.yml / openapi.json
├── swagger.yaml / swagger.yml / swagger.json
├── api/openapi.yaml / api/swagger.yaml
├── docs/openapi.yaml / docs/swagger.yaml
├── spec/openapi.yaml / spec/swagger.yaml
└── **/openapi.{yaml,yml,json} (recursive, first match)
```

If no spec is found, report an error:

> No OpenAPI/Swagger specification found. Provide one with `--spec=<path>`
> or place it in a standard location (openapi.yaml, swagger.yaml, api/, docs/, spec/).

### Step 2: Parse the Contract Spec

Load the OpenAPI/Swagger file and extract all defined endpoints:

```
For each path in spec:
├── Method (GET, POST, PUT, PATCH, DELETE)
├── Path (e.g., /api/v1/users/{id})
└── Operation ID (if present)
```

Normalize paths: ensure leading `/`, collapse double slashes, lowercase methods.

### Step 3: Scan Source Files for HTTP Calls (REQ-01)

Scan the source directory (default: project root, or `--src` override).

Use Grep to find HTTP call patterns across supported languages:

#### Go

```
Patterns:
├── http.NewRequest("METHOD", "URL", ...)
├── http.Get("URL")
├── http.Post("URL", ...)
├── http.PostForm("URL", ...)
├── client.Do(req)  → trace back to NewRequest
├── huma.Get(api, "PATH", ...)    (Huma framework routes)
├── huma.Post(api, "PATH", ...)
├── huma.Put(api, "PATH", ...)
├── huma.Patch(api, "PATH", ...)
├── huma.Delete(api, "PATH", ...)
└── r.HandleFunc("PATH", ...).Methods("METHOD")  (gorilla/mux)
```

#### TypeScript / JavaScript

```
Patterns:
├── fetch("URL", { method: "METHOD" })
├── fetch("URL")  → default GET
├── axios.get("URL")
├── axios.post("URL", ...)
├── axios.put("URL", ...)
├── axios.patch("URL", ...)
├── axios.delete("URL")
├── axios({ method: "METHOD", url: "URL" })
├── http.get("URL")
├── http.post("URL")
└── this.http.get<T>("URL")  (Angular HttpClient)
```

#### Python

```
Patterns:
├── requests.get("URL")
├── requests.post("URL", ...)
├── requests.put("URL", ...)
├── requests.patch("URL", ...)
├── requests.delete("URL")
├── httpx.get("URL")
├── httpx.post("URL", ...)
├── httpx.AsyncClient().get("URL")
├── client.get("URL")  (httpx client instance)
└── session.get("URL")  (requests Session)
```

### Step 4: Normalize Dynamic URL Segments

Convert dynamic segments in extracted URLs to `{param}` form:

```
Normalization rules:
├── UUID patterns  → {id}       (e.g., /users/550e8400-... → /users/{id})
├── Numeric IDs    → {id}       (e.g., /users/123 → /users/{id})
├── Template vars  → preserve   (e.g., ${userId} → {userId})
├── Path params    → preserve   (e.g., :id → {id})
├── Query strings  → strip      (e.g., /users?page=1 → /users)
└── Trailing slash → strip      (e.g., /users/ → /users)
```

### Step 5: Apply Ignore Patterns (REQ-04)

Filter out URLs matching ignore patterns (glob syntax):

```
Examples:
├── https://*.third-party.com/**  → skip external APIs
├── /health                       → skip health checks
├── /metrics/**                   → skip metrics endpoints
└── **/internal/**                → skip internal-only routes
```

Default ignores (always applied):
- `http://localhost*` and `https://localhost*` (test URLs)
- `http://127.0.0.1*` and `https://127.0.0.1*`
- `http://0.0.0.0*`

### Step 6: Compare and Classify Drift (REQ-03)

Compare extracted HTTP calls against the contract spec:

```
Classification:
├── Undocumented  → endpoint found in code but NOT in spec
├── Unused        → endpoint defined in spec but NOT found in code
├── Mismatch      → endpoint exists in both but method differs
│                   (e.g., code uses POST, spec says PUT)
└── Matched       → endpoint and method align (no drift)
```

### Step 7: Generate Drift Report (REQ-05)

Produce a structured markdown report:

```markdown
## Contract Drift Report

### Summary
- **Spec**: {spec-path}
- **Source**: {src-dir}
- **Scanned files**: {count}
- **Total endpoints in spec**: {count}
- **Total HTTP calls in code**: {count}
- **Drift detected**: {yes/no}

### Undocumented Endpoints (in code, not in spec)
| Method | Endpoint | File | Line |
|--------|----------|------|------|
| POST   | /api/v1/webhooks | src/webhooks.ts | 42 |

### Unused Contract Entries (in spec, not in code)
| Method | Endpoint | Operation ID |
|--------|----------|-------------|
| DELETE | /api/v1/users/{id} | deleteUser |

### Method Mismatches
| Endpoint | Spec Method | Code Method | File | Line |
|----------|-------------|-------------|------|------|
| /api/v1/orders | PUT | PATCH | src/orders.go | 87 |

### Ignored (filtered by patterns)
| Method | URL | Reason |
|--------|-----|--------|
| GET | https://api.stripe.com/v1/charges | matches *.stripe.com/** |

### Matched (no drift)
{count} endpoints matched correctly.
```

### Step 8: Persist

Save drift report to Engram:

```
mem_save(
  title: "Contract drift scan: {drift-count} issues found",
  topic_key: "contract-drift/latest",
  type: "discovery",
  project: "{project}",
  content: "{full drift report}"
)
```

### Step 9: Return Report

Return the structured envelope with: `status`, `executive_summary`,
`artifacts`, `next_recommended`, and `risks`.

## Rules

- NEVER modify source files or the contract spec — this is a read-only scan
- If no contract spec is found, return an error message immediately (do not scan)
- Dynamic URL segments MUST be normalized before comparison
- Default ignore patterns are ALWAYS applied (localhost, 127.0.0.1, 0.0.0.0)
- User ignore patterns are applied IN ADDITION to defaults
- Report ALL categories even if empty (show "None" for empty sections)
- Method comparison is case-insensitive (GET == get == Get)
- Paths are compared after normalization (strip trailing slash, lowercase)
- Return a structured envelope with: `status`, `executive_summary`, `artifacts`, `next_recommended`, and `risks`
