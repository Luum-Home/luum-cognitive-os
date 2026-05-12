# MOC: Quality

Tests, audits, gates, security, compliance — everything that enforces correctness and trust.

## Start here

1. [`docs/09-Quality/quality/`](../quality/) — quality framework overview
2. [`docs/07-Capabilities/root/agent-quality.md`](../agent-quality.md) — agent output quality rules
3. [`docs/09-Quality/testing/`](../testing/) — testing strategy and lanes

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

- [`docs/07-Capabilities/root/agent-quality.md`](../agent-quality.md) — TRUST_REPORT requirements
- [ADR-105 Bilateral Claim Verification Contract](../adrs/ADR-105-claim-verification-contract.md)
- [ADR-244 Trust report claim validator must enforce](../adrs/ADR-244-trust-report-claim-validator-must-enforce.md)
- [`docs/04-Concepts/root/anti-hallucination.md`](../anti-hallucination.md)

### Closure trust signal (ADR-275 Phase 3)

Quantifies "did this 'done' claim go through the atomic close primitive or
was it a manual edit?" — feeds the trust score per ADR-244.

- `scripts/cos-closure-trust-signal.py` — emits HIGH|MEDIUM|LOW|ZERO band
  based on `closure-trail.jsonl` coverage of verified-done items in
  `pending-truth-latest.json`
- Wired into `cos-control-plane-audit` hourly + pre-public lanes as the
  `closure-trust-signal` audit ID (see `manifests/control-plane-audits.yaml`)
- Audit trail: `.cognitive-os/audit/closure-trail.jsonl`
- Closure primitives (ADR-275): `scripts/cos-pending-truth-close` (tasks)
  and `scripts/cos-adr-close` (decisions). See
  [`docs/04-Concepts/architecture/pending-truth-architecture.md`](../architecture/pending-truth-architecture.md)
  for the full 4-layer architecture.

## Security

- [`docs/09-Quality/security/`](../security/) — security policies
- [ADR-013 Security stack](../adrs/ADR-013-security-stack.md)
- [`docs/01-Build-Log/root/RED-TEAM-COVERAGE.md`](../RED-TEAM-COVERAGE.md) + [`docs/01-Build-Log/root/RED-TEAM-CHANGELOG.md`](../RED-TEAM-CHANGELOG.md)
- See `aguara-integration` rule (189 security rules)

## Compliance & Legal

- [`docs/09-Quality/legal/`](../legal/) — license policy, AGPL/SSPL/BSL blocks, license-faq
- [ADR-006 AGPL license compliance](../adrs/ADR-006-agpl-license-compliance.md)
- [ADR-142 Compliance audit air-gapped surface](../adrs/ADR-142-compliance-audit-air-gapped-surface.md)
- [ADR-270 Legal compliance workflow automation](../adrs/ADR-270-legal-compliance-workflow-automation.md)

## Code-review

- [`docs/09-Quality/quality/`](../quality/) + the `code-review` skill
- `/ultrareview` — multi-agent cloud review (user-triggered, billed)
- `/pr-review` — single-pass review skill

## Related MOCs

- [decisions.md](decisions.md) — ADRs that defined the quality regime
- [workflow.md](workflow.md) — when in the SDD cycle each gate fires

Last updated: 2026-05-12
