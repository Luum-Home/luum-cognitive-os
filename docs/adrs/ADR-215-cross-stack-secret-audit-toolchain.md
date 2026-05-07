# ADR-215 — Cross-Stack Secret Audit Toolchain

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — slice 1 substrate active
**Date**: 2026-05-06
**Related**: ADR-212, ADR-208, ADR-203, ADR-211, ADR-145
**Source**: Q3 tool-adoption review (cross-stack secret/credential/PII detection),
`.cognitive-os/strategy/audit/secrets-and-leaks-2026-05-06.md`,
`.cognitive-os/strategy/04-license-repo-and-corrections-log.md`

---

## Context

Cognitive OS already has secret-protection primitives: `hooks/secret-detector.sh`
(dual-mode pre/post tool-use redactor), `hooks/confidentiality-enforcer.sh`
(operator-path / sensitive-content guard), `hooks/dangerous-env-flag-detector.sh`,
`scripts/cos-credential-safe-run`, `skills/secret-audit`, plus three rules
(`confidentiality-protection.md`, `credential-management.md`).

The 2026-05-06 secrets audit (gitleaks + trufflehog + custom regex) demonstrated
two structural gaps that mirror the licence-audit gap closed by ADR-212:

1. **No release-readiness audit CLI**. Each hook fires per-event but there is
   no single command an operator can run to ask: *"is this repository safe to
   publish — no real secrets, no env files, no private keys, no PII leaks?"*
   The audit had to be assembled ad-hoc.

2. **No canonical toolchain policy**. The audit chose `gitleaks` + `trufflehog`
   + custom regex by orchestrator instinct, not by a manifest-backed decision
   the OS could enforce or reproduce. Future audits would re-decide the same
   question.

Effectiveness evidence is also imbalanced: `confidentiality-enforcer.jsonl` has
197 rows (active hook), but `secret-redactions.jsonl` has **0 rows** — meaning
the secret-detector hook either never fired, never produced output, or only
matches narrow patterns. The ad-hoc audit found the operator email leak in
9 preserve-manifest files that the active hooks had never flagged in 30 days.

Per the dogfood-evidence pattern recorded in
`.cognitive-os/strategy/04-license-repo-and-corrections-log.md`, the
orchestrator repeatedly bypassed canonical primitives because none existed for
release-readiness secret audit. ADR-212 set the model for
licence audits; this ADR closes the symmetric gap for secrets.

## Market review

| Tool | Coverage | License | Approach | Best for |
|---|---|---|---|---|
| gitleaks (Zricethezav/Mend) | Multi-stack regex + Shannon entropy | MIT | Local scan, ~200 rule packs, fast | Primary fast scan, CI gate |
| trufflehog (Truffle Security) | Multi-stack with ~700 verifiable detectors | AGPL-3.0 (binary use OK; library use copyleft) | Optionally calls provider APIs to confirm if a secret is live | Primary depth, only if AGPL caveat understood |
| detect-secrets (Yelp) | Python-first, plugin model | Apache-2.0 | Baseline + diff scanning, mature pre-commit integration | Secondary; pre-commit hook surface |
| ggshield (GitGuardian) | SaaS-backed multi-stack | MIT (CLI) / SaaS | High-quality detectors, requires API key | Secondary; only with operator GitGuardian account |
| git-secrets (AWS Labs) | AWS-focused regex | Apache-2.0 | Lightweight pre-commit | Niche AWS-only; deprecated for general use |
| ScanCode Toolkit (AboutCode/nexB) | File-level multi-stack | Apache-2.0 | Deep source/license/credential scanning | Forensic escalation when CLI tools disagree |
| Semgrep secrets (r2c) | Source-pattern based | LGPL (CLI), commercial cloud | Semantic + AI assist | Optional, overlaps with code-review skills |

## Supply-chain and license caveats

- **trufflehog is AGPL-3.0**. Using its CLI binary as a tool is permitted; embedding its library would propagate AGPL. ADR-006 forbids AGPL deps in COS code, so trufflehog is allowed only as an installed scanner CLI invoked via `subprocess`/`exec`, never imported.
- **trufflehog's `--only-verified` flag** sends candidate secrets to provider APIs to test liveness. We forbid this flag in default runs (privacy + accidental disclosure of tokens). Operators may enable it explicitly with `--verify-live` only when remediating known leaks.
- **gitleaks GitHub Actions** must be pinned by reviewed immutable commit SHA; mutable tags are blocked, mirroring ADR-212's Trivy posture.
- **ggshield** requires an external API key; treated as optional, never default.

## Decision

Adopt a manifest-backed cross-stack secret audit policy with:

1. **Primary toolchain**: `gitleaks` + `trufflehog`. Both run by default; either
   producing a real-secret finding fails the audit. Verifiable-mode is opt-in,
   never default.
2. **Secondary scanner**: `detect-secrets` for Python-heavy paths and pre-commit
   integration. Optional unless operator opts in.
3. **Forensic escalation**: ScanCode Toolkit when primary tools disagree or a
   release/legal review requires file-level evidence.
4. **Commercial / SaaS tools** (GitGuardian, Snyk, Doppler-secrets-detection):
   optional, never required for pre-launch readiness.

## Enforcement

Add:

- `manifests/cross-stack-secret-audit.yaml` (mirroring `cross-stack-license-audit.yaml`).
- `lib/cross_stack_secret_audit.py`.
- `scripts/cos-cross-stack-secret-audit` Python entrypoint.
- `scripts/cos secret audit [--json] [--strict] [--verify-live]` shell dispatch
  (mirroring `cos license audit`).
- `scripts/install-gitleaks-trufflehog.sh` (primary-toolchain installer).
- Optional `scripts/install-detect-secrets.sh`, `scripts/install-ggshield.sh`.
- Wrapper scripts: `scripts/secret-audit-gitleaks.sh`,
  `scripts/secret-audit-trufflehog.sh` for individual runs with consistent
  output paths under `.cognitive-os/reports/secret-audit/`.

The audit MUST:

- verify scanner availability and version posture;
- block known compromised gitleaks/trufflehog versions (initial blocklist:
  none confirmed at 2026-05-06; populated as incidents emerge);
- scan GitHub workflows for unsafe scanner action usage by mutable tag;
- run gitleaks with `--redact` so report does not echo raw secret values;
- run trufflehog WITHOUT `--only-verified` by default (privacy);
- emit JSON conforming to schema `cross-stack-secret-audit-report/v1`,
  consumable by ADR-201 (Maintainer) and ADR-211 (Service-Mode Readiness Gate);
- classify findings into `valid` (real secret), `suspect` (entropy-positive
  but unverified), `placeholder` (known test fixture / example value), `corrupt`
  (parser garbage like the `"skill":"matias"` pattern recorded in research/07).

The manifest MUST declare:

- known placeholder fingerprints (`[REDACTED]`, `sk-ant-api03-deadbeef…FAKEKEYFORTEST0`,
  Slack `T00000000/B00000000`, Postgres dev DSNs behind env-var substitution);
- allowlist for path patterns where secrets are intentional fixtures
  (`tests/fixtures/`, `docs/examples/`, etc.);
- block-on-find list (real keys: Anthropic `sk-ant-`, OpenAI `sk-`, GitHub
  `ghp_/gho_/ghs_/ghu_/ghr_`, AWS `AKIA[A-Z0-9]{16}`, SSH private key blocks,
  JWTs, raw `.env` content);
- redact-on-detect rules for operator paths (`/Users/<name>`), personal emails,
  internal hostnames.

Hooks integration:

- `hooks/secret-detector.sh` continues as PreToolUse/PostToolUse redactor;
  reframed as **session-scoped detector** (per-tool-call protection).
- New hook `hooks/secret-audit-pre-commit.sh` runs gitleaks (fast mode) on
  staged content before commits land. Registered per ADR-110 in
  `apply-efficiency-profile.sh` standard+full profiles.
- Release-readiness gate (ADR-211) calls `cos secret audit --strict` as part
  of public-claim verification.


## Implementation status — 2026-05-06

Active first slice:

- `manifests/cross-stack-secret-audit.yaml` declares the canonical gitleaks + trufflehog policy, sensitive local filename surfaces, placeholder allowlists, and report paths.
- `lib/cross_stack_secret_audit.py` audits scanner availability, mutable secret-scanner GitHub Actions, sensitive local surfaces, and summarizes existing redacted scanner reports.
- `scripts/cos-cross-stack-secret-audit` plus `scripts/cos secret audit` expose the operator command.
- `tests/unit/test_cross_stack_secret_audit.py` and `tests/behavior/test_cross_stack_secret_audit_cli.py` cover the active substrate.

Not yet active: scanner run wrappers, pre-commit integration, curated baseline, and ADR-211 hard gate consumption. Until those land, the repo is protected by a whole-repo audit command but not yet by automatic release blocking.

## Consequences

### Positive

- One multi-stack audit path covers Python, Go, Node, shell, docs, fixtures.
- Closes the orchestrator-bypass pattern documented in research/04 dogfood
  evidence #7 + #15 + #16.
- Symmetric with ADR-212; operators learn one CLI shape, apply it to two
  domains.
- Schema-versioned output enables ADR-201 (Maintainer) and ADR-211 (Service-
  Mode Readiness Gate) to consume verdicts deterministically.
- Removes the "secret-redactions.jsonl is empty" effectiveness gap by
  registering a real wired audit and a real wired pre-commit hook.

### Negative / trade-offs

- gitleaks + trufflehog are two binaries instead of one (mirror of Trivy's
  single-binary trade-off in ADR-212).
- trufflehog AGPL caveat requires explicit doc + enforcement that the binary
  is invoked via subprocess, never imported into COS code.
- Operator must install scanners (or run `cos secret audit` to be told what's
  missing) — adds one onboarding step.
- Manifest placeholder allowlist requires curation as new test fixtures land;
  pre-commit hook reminds operator to extend allowlist when a fixture trips
  detection.

## Alternatives rejected

- **Single tool (gitleaks only)**: rejected. Lower coverage of verifiable
  detectors; no protection against fragile regex evasion that trufflehog's
  entropy + structure heuristics catch.
- **Trufflehog only**: rejected. AGPL means we must keep it as CLI-only;
  building a CLI-only single-tool path produces a fragile dependency on a
  copyleft tool.
- **Build native COS detector**: rejected. Reinventing well-maintained scanners
  with 200-700 rule packs is the exact pattern ADR-208 (Imported Pattern
  Closure Contract) tells us to avoid.
- **SaaS-only (GitGuardian / Snyk)**: rejected for pre-launch core. Acceptable
  as opt-in operator integrations.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_cross_stack_secret_audit.py tests/behavior/test_cross_stack_secret_audit_cli.py -q
scripts/cos secret audit --json
scripts/cos secret audit --strict           # exit 1 on findings
bash -n scripts/install-gitleaks-trufflehog.sh scripts/secret-audit-gitleaks.sh scripts/secret-audit-trufflehog.sh
```

The tests must prove:

- unsafe scanner workflow usage by mutable tag is flagged;
- known-bad scanner versions (when populated) are blocked;
- placeholder fingerprints in manifest do not produce findings;
- a real-secret-shaped fixture in a non-allowlisted path produces a finding
  classified `valid`;
- `--only-verified` / `--verify-live` is rejected by default and only enabled
  with explicit operator flag;
- output schema validates against `cross-stack-secret-audit-report/v1`.

## Implementation slices

1. `manifests/cross-stack-secret-audit.yaml` skeleton (placeholder fingerprints,
   path allowlists, block-on-find rules).
2. `lib/cross_stack_secret_audit.py` + tool-availability + version policy +
   workflow-pinning policy (mirror of cross_stack_license_audit.py shape).
3. `scripts/install-gitleaks-trufflehog.sh` with brew-first + curl fallback,
   matching ADR-212's installer pattern.
4. Wrapper scripts: `scripts/secret-audit-gitleaks.sh`,
   `scripts/secret-audit-trufflehog.sh` with structured JSON output to
   `.cognitive-os/reports/secret-audit/`.
5. `scripts/cos-cross-stack-secret-audit` Python entrypoint + `cos secret`
   subcommand wiring in `scripts/cos`.
6. `hooks/secret-audit-pre-commit.sh` registration in `apply-efficiency-profile.sh`
   (standard + full profiles).
7. Service-mode readiness integration: ADR-211 nivel 9 ("Public claim gate
   passes") consumes `cos secret audit --strict` exit code.
8. Tests: unit (manifest validation, version policy, classification),
   behavior (CLI smoke, pre-commit hook, allowlist round-trip).

## Migration / coexistence

- Existing `hooks/secret-detector.sh` continues to operate per-tool-use; this
  ADR does NOT replace it.
- Existing `secret-redactions.jsonl` continues for hook-level redactions; the
  new audit emits a separate stream `cross-stack-secret-audit.jsonl` plus
  per-run reports under `.cognitive-os/reports/secret-audit/`.
- Existing `cos-credential-safe-run` is unchanged; it remains the in-process
  credential injection guard.
- The June 2026 review window aligns with ADR-058 / ADR-211 review cadence;
  re-evaluate after first 30 days of pre-commit hook firings.

## Open questions

- Should the OS bundle a baseline `.gitleaks.toml` config in `manifests/` or
  rely on gitleaks defaults? Recommendation: bundle one, treat upstream defaults
  as input rather than authority.
- Does ADR-211 nivel 9 want a SOFT (warn) or HARD (block) gate by default?
  Recommendation: HARD for service-mode public release; SOFT for self-hosted
  operator-driven release.
- detect-secrets baseline file (`.secrets.baseline`) — committed or gitignored?
  Recommendation: committed, as it represents the audited-and-allowed set.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
