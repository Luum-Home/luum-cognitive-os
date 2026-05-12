# MOC: Quality

Tests, audits, gates, security, compliance — everything that enforces correctness and trust.

## Start here

1. [`docs/quality/`](../quality/) — quality framework overview
2. [`docs/agent-quality.md`](../agent-quality.md) — agent output quality rules
3. [`docs/testing/`](../testing/) — testing strategy and lanes

## Test lanes (ADR-072)

Lane registry at `.cognitive-os/test-lanes.yaml` — single source of truth.

- **Audit** (`tests/audit/`) — invariant checks (naming conventions, ADR locations, frontmatter)
- **Contracts** (`tests/contracts/`) — behavioural contracts that must hold across changes
- **Red-team / portability** (`tests/red_team/portability/`) — SCOPE: both proofs (paired with any artifact declaring SCOPE: both via `hooks/scope-marker-portability-gate.sh`)
- **Unit** (`tests/unit/`)
- **Integration** (`tests/integration/`)

Use `cos-test focused/cluster/broad` escalation ladder (ADR-072).

## Gates (hook-enforced)

Many rules are enforced as PreToolUse / PostToolUse hooks rather than agent instructions. See [`rules/RULES-COMPACT.md`](../../rules/RULES-COMPACT.md) §1-15. Examples:

- `scope-marker-portability-gate.sh` — blocks commit if SCOPE: both artifacts lack paired tests
- `protected-config-write-guard.sh` — blocks writes to control-plane paths without `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`
- `git-commit-scope-guard.sh` — blocks bare `git commit` (must specify scope)
- `secret-detector` — credential leak prevention
- See `hooks/` for the full list

## Trust & evidence

- [`docs/agent-quality.md`](../agent-quality.md) — TRUST_REPORT requirements
- [ADR-105 Bilateral Claim Verification Contract](../adrs/ADR-105-claim-verification-contract.md)
- [ADR-244 Trust report claim validator must enforce](../adrs/ADR-244-trust-report-claim-validator-must-enforce.md)
- [`docs/anti-hallucination.md`](../anti-hallucination.md)

## Security

- [`docs/security/`](../security/) — security policies
- [ADR-013 Security stack](../adrs/ADR-013-security-stack.md)
- [`docs/RED-TEAM-COVERAGE.md`](../RED-TEAM-COVERAGE.md) + [`docs/RED-TEAM-CHANGELOG.md`](../RED-TEAM-CHANGELOG.md)
- See `aguara-integration` rule (189 security rules)

## Compliance & Legal

- [`docs/legal/`](../legal/) — license policy, AGPL/SSPL/BSL blocks, license-faq
- [ADR-006 AGPL license compliance](../adrs/ADR-006-agpl-license-compliance.md)
- [ADR-142 Compliance audit air-gapped surface](../adrs/ADR-142-compliance-audit-air-gapped-surface.md)
- [ADR-270 Legal compliance workflow automation](../adrs/ADR-270-legal-compliance-workflow-automation.md)

## Code-review

- [`docs/quality/`](../quality/) + the `code-review` skill
- `/ultrareview` — multi-agent cloud review (user-triggered, billed)
- `/pr-review` — single-pass review skill

## Related MOCs

- [decisions.md](decisions.md) — ADRs that defined the quality regime
- [workflow.md](workflow.md) — when in the SDD cycle each gate fires

Last updated: 2026-05-12
