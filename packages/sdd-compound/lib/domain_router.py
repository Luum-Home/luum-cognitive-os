# scope: both
"""Domain-specific evaluator routing for SDD verify.

Analyzes affected file paths to classify the domain of a change and returns
domain-specific evaluation criteria and focus areas for the verify phase.

Python 3.9+ compatible.
"""

from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path pattern -> domain mapping
# ---------------------------------------------------------------------------
# Each entry is (substring_or_prefix, domain).  Order matters: first match wins
# for individual files, but overall domain is determined by majority vote.

_PATH_RULES: List[Tuple[str, str]] = [
    # Security (check before backend — auth paths are security-first)
    ("/auth/", "security"),
    ("/security/", "security"),
    ("/crypto/", "security"),
    ("/encryption/", "security"),
    ("/acl/", "security"),
    ("/rbac/", "security"),
    ("/oauth/", "security"),
    ("/jwt/", "security"),
    ("/permissions/", "security"),

    # Database
    ("/migrations/", "database"),
    ("/migrate/", "database"),
    ("/seeds/", "database"),
    ("/schema/", "database"),
    ("/models/", "database"),
    ("/entities/", "database"),
    ("/repositories/", "database"),
    ("/repository/", "database"),

    # Infrastructure
    ("docker-compose", "infrastructure"),
    ("Dockerfile", "infrastructure"),
    (".github/", "infrastructure"),
    ("/ci/", "infrastructure"),
    ("/cd/", "infrastructure"),
    ("/terraform/", "infrastructure"),
    ("/pulumi/", "infrastructure"),
    ("/helm/", "infrastructure"),
    ("/k8s/", "infrastructure"),
    ("/kubernetes/", "infrastructure"),
    ("/infra/", "infrastructure"),
    ("/deploy/", "infrastructure"),
    ("Makefile", "infrastructure"),
    (".env", "infrastructure"),
    ("nginx", "infrastructure"),

    # API
    ("/api/", "api"),
    ("/controllers/", "api"),
    ("/handlers/", "api"),
    ("/routes/", "api"),
    ("/endpoints/", "api"),
    ("/graphql/", "api"),
    ("/grpc/", "api"),
    ("/proto/", "api"),
    ("/openapi/", "api"),
    ("/swagger/", "api"),
    ("openapi.yaml", "api"),
    ("openapi.json", "api"),
    ("swagger.yaml", "api"),
    ("swagger.json", "api"),

    # Frontend
    ("/components/", "frontend"),
    ("/pages/", "frontend"),
    ("/views/", "frontend"),
    ("/styles/", "frontend"),
    ("/css/", "frontend"),
    ("/assets/", "frontend"),
    ("/public/", "frontend"),
    ("/hooks/ui/", "frontend"),
    ("/screens/", "frontend"),
    ("/layouts/", "frontend"),

    # Backend (broad catch-all — checked last)
    ("/services/", "backend"),
    ("/usecases/", "backend"),
    ("/use_cases/", "backend"),
    ("/use-cases/", "backend"),
    ("/domain/", "backend"),
    ("/application/", "backend"),
    ("/internal/", "backend"),
    ("/pkg/", "backend"),
    ("/cmd/", "backend"),
    ("/src/", "backend"),
    ("/lib/", "backend"),
]

# File extension hints (lower priority than path patterns)
_EXTENSION_HINTS: Dict[str, str] = {
    ".tsx": "frontend",
    ".jsx": "frontend",
    ".vue": "frontend",
    ".svelte": "frontend",
    ".css": "frontend",
    ".scss": "frontend",
    ".less": "frontend",
    ".html": "frontend",
    ".sql": "database",
    ".tf": "infrastructure",
    ".hcl": "infrastructure",
    ".proto": "api",
}


# ---------------------------------------------------------------------------
# Domain evaluation configurations
# ---------------------------------------------------------------------------

_DOMAIN_CONFIGS: Dict[str, dict] = {
    "backend": {
        "domain": "backend",
        "display_name": "Backend",
        "focus_areas": [
            "Architecture compliance (clean architecture layers, dependency direction)",
            "Error handling (no swallowed errors, proper error types, stack traces)",
            "Database query efficiency (N+1 prevention, index usage, connection pooling)",
            "Concurrency safety (race conditions, mutex usage, goroutine leaks)",
            "Input validation at service boundaries",
            "Proper use of dependency injection",
            "Logging and observability (structured logs, trace IDs)",
        ],
        "evaluation_criteria": {
            "architecture_compliance": {
                "weight": 0.25,
                "description": "Follows clean architecture; domain has no infrastructure imports",
            },
            "error_handling": {
                "weight": 0.20,
                "description": "Errors propagated correctly; no silent failures; proper error types",
            },
            "db_queries": {
                "weight": 0.20,
                "description": "No N+1 queries; proper indexing; connection management",
            },
            "concurrency": {
                "weight": 0.15,
                "description": "Thread/goroutine safety; proper locking; no data races",
            },
            "testing": {
                "weight": 0.20,
                "description": "Unit tests cover critical paths; mocks used correctly",
            },
        },
        "verification_commands": [
            "go build ./... || yarn build",
            "go test ./... -race -short || yarn test",
            "golangci-lint run ./... || eslint .",
        ],
        "red_flags": [
            "Domain layer importing infrastructure packages",
            "Raw SQL without parameterized queries",
            "Missing error checks on I/O operations",
            "Shared mutable state without synchronization",
        ],
    },

    "frontend": {
        "domain": "frontend",
        "display_name": "Frontend",
        "focus_areas": [
            "Accessibility (ARIA attributes, semantic HTML, keyboard navigation)",
            "Responsive design (breakpoints, mobile-first, viewport units)",
            "Bundle size impact (tree-shaking, lazy loading, code splitting)",
            "Component patterns (single responsibility, proper prop drilling vs context)",
            "State management (no prop drilling anti-patterns, proper store usage)",
            "Performance (unnecessary re-renders, memo usage, virtual lists)",
            "Cross-browser compatibility",
        ],
        "evaluation_criteria": {
            "accessibility": {
                "weight": 0.25,
                "description": "WCAG 2.1 AA compliance; ARIA labels; keyboard navigation works",
            },
            "responsive_design": {
                "weight": 0.15,
                "description": "Works on mobile, tablet, desktop; no horizontal scroll",
            },
            "bundle_size": {
                "weight": 0.15,
                "description": "No unnecessary large dependencies; tree-shakeable imports",
            },
            "component_patterns": {
                "weight": 0.25,
                "description": "Components follow SRP; proper separation of concerns",
            },
            "testing": {
                "weight": 0.20,
                "description": "Component tests; interaction tests; snapshot tests where useful",
            },
        },
        "verification_commands": [
            "yarn build || npm run build",
            "yarn test || npm test",
            "yarn lint || npm run lint",
        ],
        "red_flags": [
            "Inline styles for layout (use CSS modules or styled-components)",
            "Missing alt text on images",
            "Direct DOM manipulation outside refs",
            "Large synchronous imports without lazy loading",
        ],
    },

    "infrastructure": {
        "domain": "infrastructure",
        "display_name": "Infrastructure",
        "focus_areas": [
            "Security (secrets not hardcoded, least privilege, network policies)",
            "Scalability (horizontal scaling, resource limits, auto-scaling configs)",
            "Cost implications (instance sizes, storage types, data transfer)",
            "Idempotency (re-running the same infra change is safe)",
            "Disaster recovery (backups, multi-AZ, failover configuration)",
            "Monitoring and alerting (health checks, metrics, log aggregation)",
            "Version pinning (base images, tool versions, provider versions)",
        ],
        "evaluation_criteria": {
            "security": {
                "weight": 0.30,
                "description": "No hardcoded secrets; least privilege; encrypted at rest/transit",
            },
            "scalability": {
                "weight": 0.20,
                "description": "Resource limits set; horizontal scaling possible; no single points of failure",
            },
            "cost": {
                "weight": 0.15,
                "description": "Resource sizing appropriate; no over-provisioning; spot/preemptible considered",
            },
            "idempotency": {
                "weight": 0.20,
                "description": "Re-running is safe; state changes are additive; rollback possible",
            },
            "observability": {
                "weight": 0.15,
                "description": "Health checks present; metrics exported; logs structured",
            },
        },
        "verification_commands": [
            "docker compose config --quiet 2>&1 || true",
            "terraform validate || true",
            "hadolint Dockerfile || true",
        ],
        "red_flags": [
            "Secrets in plain text or environment variable defaults",
            "No resource limits on containers",
            "Using :latest tag for base images",
            "Missing health check definitions",
        ],
    },

    "database": {
        "domain": "database",
        "display_name": "Database",
        "focus_areas": [
            "Migration safety (reversible, no data loss, backward compatible)",
            "Index strategy (covering indexes, no redundant indexes, query plans)",
            "Data integrity (constraints, foreign keys, NOT NULL where needed)",
            "Performance (query complexity, batch sizes, connection limits)",
            "Backward compatibility (old code can still read new schema)",
            "Seed data correctness (idempotent seeds, no production data leaks)",
            "Transaction boundaries (ACID compliance, deadlock prevention)",
        ],
        "evaluation_criteria": {
            "migration_safety": {
                "weight": 0.30,
                "description": "Migrations are reversible; no destructive changes without data backup plan",
            },
            "indexes": {
                "weight": 0.20,
                "description": "Proper indexes for query patterns; no redundant indexes",
            },
            "data_integrity": {
                "weight": 0.25,
                "description": "Constraints enforced; referential integrity maintained; nullability correct",
            },
            "performance": {
                "weight": 0.15,
                "description": "No full table scans on large tables; batch operations for bulk data",
            },
            "backward_compat": {
                "weight": 0.10,
                "description": "Schema change is backward compatible with running code",
            },
        },
        "verification_commands": [
            "migrate validate || true",
            "sqlfluff lint . || true",
        ],
        "red_flags": [
            "DROP COLUMN or DROP TABLE without data migration plan",
            "ALTER TABLE on large tables without considering lock time",
            "Missing indexes on foreign key columns",
            "Unbounded queries (no LIMIT on potentially large result sets)",
        ],
    },

    "security": {
        "domain": "security",
        "display_name": "Security",
        "focus_areas": [
            "Authentication (proper token validation, session management, MFA support)",
            "Authorization (RBAC/ABAC enforcement, permission checks on every endpoint)",
            "Encryption (TLS everywhere, secrets encrypted at rest, key rotation)",
            "Input validation (sanitization, parameterized queries, XSS prevention)",
            "OWASP Top 10 compliance (injection, broken auth, SSRF, etc.)",
            "Audit logging (who did what when, tamper-proof logs)",
            "Rate limiting and abuse prevention",
        ],
        "evaluation_criteria": {
            "authentication": {
                "weight": 0.25,
                "description": "Tokens validated correctly; session expiry enforced; no credential leaks",
            },
            "authorization": {
                "weight": 0.25,
                "description": "Every endpoint checks permissions; no privilege escalation paths",
            },
            "encryption": {
                "weight": 0.20,
                "description": "Sensitive data encrypted; proper key management; no weak algorithms",
            },
            "input_validation": {
                "weight": 0.20,
                "description": "All user input sanitized; parameterized queries; output encoding",
            },
            "audit_trail": {
                "weight": 0.10,
                "description": "Security-relevant actions logged; logs are tamper-resistant",
            },
        },
        "verification_commands": [
            "semgrep --config=auto . || true",
            "trivy fs . || true",
        ],
        "red_flags": [
            "Hardcoded credentials or API keys",
            "Missing authentication middleware on endpoints",
            "Using MD5 or SHA1 for password hashing",
            "SQL string concatenation instead of parameterized queries",
            "CORS set to allow all origins in production config",
        ],
    },

    "api": {
        "domain": "api",
        "display_name": "API",
        "focus_areas": [
            "Contract compliance (request/response schemas match documentation)",
            "Versioning strategy (URL vs header versioning, deprecation policy)",
            "Rate limiting (per-client, per-endpoint, global limits)",
            "Documentation (OpenAPI spec up to date, examples provided)",
            "Error responses (consistent error format, proper HTTP status codes)",
            "Pagination (cursor-based preferred, proper metadata)",
            "Idempotency (POST/PUT operations are safe to retry)",
        ],
        "evaluation_criteria": {
            "contracts": {
                "weight": 0.25,
                "description": "API contracts match implementation; no undocumented fields",
            },
            "versioning": {
                "weight": 0.15,
                "description": "Breaking changes properly versioned; deprecation notices present",
            },
            "rate_limiting": {
                "weight": 0.15,
                "description": "Rate limits configured and documented; proper 429 responses",
            },
            "documentation": {
                "weight": 0.20,
                "description": "OpenAPI/Swagger spec updated; examples provided; errors documented",
            },
            "error_handling": {
                "weight": 0.25,
                "description": "Consistent error format; proper HTTP status codes; error details helpful",
            },
        },
        "verification_commands": [
            "swagger-cli validate openapi.yaml || true",
            "spectral lint openapi.yaml || true",
        ],
        "red_flags": [
            "Breaking change without version bump",
            "200 OK returned for error conditions",
            "Inconsistent error response format across endpoints",
            "Missing pagination on list endpoints",
            "No rate limiting on public endpoints",
        ],
    },
}

# Default config for mixed or unclassifiable domains
_DEFAULT_CONFIG: dict = {
    "domain": "mixed",
    "display_name": "Mixed / General",
    "focus_areas": [
        "Correctness (logic errors, edge cases, off-by-one)",
        "Security (no hardcoded secrets, input validation)",
        "Performance (no obvious bottlenecks, proper caching)",
        "Maintainability (clear naming, no dead code, DRY)",
        "Test coverage (critical paths tested, edge cases covered)",
    ],
    "evaluation_criteria": {
        "correctness": {
            "weight": 0.30,
            "description": "Code does what the spec says; edge cases handled",
        },
        "security": {
            "weight": 0.20,
            "description": "No security vulnerabilities introduced",
        },
        "performance": {
            "weight": 0.15,
            "description": "No obvious performance regressions",
        },
        "maintainability": {
            "weight": 0.15,
            "description": "Code is readable, well-structured, follows conventions",
        },
        "testing": {
            "weight": 0.20,
            "description": "Tests cover critical paths and edge cases",
        },
    },
    "verification_commands": [
        "# Run project build",
        "# Run project tests",
        "# Run project linter",
    ],
    "red_flags": [
        "No tests for new functionality",
        "Swallowed exceptions or errors",
        "Hardcoded magic numbers without constants",
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _classify_file(filepath: str) -> Optional[str]:
    """Classify a single file path into a domain. Returns None if unclassifiable."""
    # Normalize path separators and ensure a leading slash for consistent matching
    normalized = filepath.replace("\\", "/")
    # Prepend "/" so patterns like "/internal/" match paths starting with "internal/"
    prefixed = "/" + normalized if not normalized.startswith("/") else normalized

    # Check path patterns first (higher priority)
    for pattern, domain in _PATH_RULES:
        if pattern in prefixed:
            return domain

    # Fall back to extension hints
    for ext, domain in _EXTENSION_HINTS.items():
        if normalized.endswith(ext):
            return domain

    return None


def detect_domain(affected_files: List[str]) -> str:
    """Analyze file paths to classify the domain of a change.

    Uses majority-vote across all classified files. If no files can be
    classified, or the vote is a tie with no clear winner, returns 'mixed'.

    Args:
        affected_files: List of file paths (relative or absolute).

    Returns:
        Domain string: 'backend', 'frontend', 'infrastructure', 'database',
        'security', 'api', or 'mixed'.
    """
    if not affected_files:
        return "mixed"

    votes: Dict[str, int] = {}
    for filepath in affected_files:
        domain = _classify_file(filepath)
        if domain is not None:
            votes[domain] = votes.get(domain, 0) + 1

    if not votes:
        return "mixed"

    # Security domain takes priority if it has any votes (security changes
    # deserve security-focused evaluation even if they are a minority).
    if "security" in votes:
        return "security"

    # Otherwise, majority vote
    max_count = max(votes.values())
    winners = [d for d, c in votes.items() if c == max_count]

    if len(winners) == 1:
        return winners[0]

    # Tie — return 'mixed'
    return "mixed"


def get_evaluator_config(domain: str) -> dict:
    """Return domain-specific evaluation criteria and focus areas.

    Args:
        domain: One of 'backend', 'frontend', 'infrastructure', 'database',
                'security', 'api', or 'mixed'.

    Returns:
        Dict with keys: domain, display_name, focus_areas, evaluation_criteria,
        verification_commands, red_flags.
    """
    return _DOMAIN_CONFIGS.get(domain, _DEFAULT_CONFIG).copy()


def format_verify_context(affected_files: List[str]) -> str:
    """Convenience function: detect domain and format evaluation context as
    a markdown string suitable for injection into an sdd-verify prompt.

    Args:
        affected_files: List of file paths affected by the change.

    Returns:
        Markdown-formatted string with domain evaluation criteria.
    """
    domain = detect_domain(affected_files)
    config = get_evaluator_config(domain)

    lines: List[str] = []
    lines.append(f"## Domain-Specific Evaluation: {config['display_name']}")
    lines.append(f"")
    lines.append(f"Detected domain: **{config['domain']}**")
    lines.append(f"")

    lines.append("### Focus Areas")
    for area in config["focus_areas"]:
        lines.append(f"- {area}")
    lines.append("")

    lines.append("### Evaluation Criteria (weighted)")
    for name, criterion in config["evaluation_criteria"].items():
        weight_pct = int(criterion["weight"] * 100)
        lines.append(f"- **{name}** ({weight_pct}%): {criterion['description']}")
    lines.append("")

    lines.append("### Verification Commands")
    for cmd in config.get("verification_commands", []):
        lines.append(f"```")
        lines.append(cmd)
        lines.append(f"```")
    lines.append("")

    lines.append("### Red Flags to Watch For")
    for flag in config.get("red_flags", []):
        lines.append(f"- {flag}")
    lines.append("")

    return "\n".join(lines)
