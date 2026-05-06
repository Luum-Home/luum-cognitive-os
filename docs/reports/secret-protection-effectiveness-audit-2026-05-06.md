# Secret / Sensitive Data Protection Effectiveness Audit — 2026-05-06

## Verdict

COS is **partially protected**, not exhaustively protected yet.

The session-scoped primitives (`secret-detector`, `confidentiality-enforcer`, `cos-credential-safe-run`) reduce accidental leakage during individual tool calls, but the repo did not previously have a canonical whole-repository release-readiness audit. ADR-215 now defines that missing layer and this commit wires its first executable substrate as `cos secret audit`.

## What was evaluated

- Existing COS primitives: `hooks/secret-detector.sh`, `hooks/confidentiality-enforcer.sh`, `scripts/cos-credential-safe-run`, `lib/secret_ref.py`, Go security tests, and existing secret/credential docs.
- Installed market scanners: `gitleaks`, `trufflehog`, and `detect-secrets`.
- Whole working tree scan artifacts under `.cognitive-os/reports/secret-audit/` with raw values redacted or excluded from the tracked report.
- New ADR-215 CLI substrate: `scripts/cos secret audit --json`.

## Exhaustive scan summary (redacted)

| Source | Findings | Interpretation |
|---|---:|---|
| `gitleaks-fs-20260506T231032Z.json` | 831 | Filesystem contains many secret-shaped findings, dominated by vendored/reference/plugin material and fixtures. |
| `gitleaks-git-20260506T231032Z.json` | 25 | Tracked history contains secret-shaped findings, mostly in tests/docs by initial sampling; must be classified before public release. |
| `trufflehog-sanitized-20260506T231032Z.jsonl` | 158 | Depth scan found unverified candidates, dominated by reference archives, metrics, and fixtures. |

`cos secret audit --json` also found **34 sensitive local file surfaces** by filename policy, including root `.env`.

## What protected us

- `.env` is ignored/untracked, so the current Git commit path is not directly exposing it.
- `confidentiality-enforcer` is active and has telemetry, including the newer downgrade rule for operator absolute paths in gitignored destinations.
- `secret-detector` has pattern coverage for common tokens and post-write env hygiene, but its effectiveness telemetry is weak for whole-repo assurance.
- `cos-credential-safe-run` provides an allowlisted way to run live smokes without printing values.

## What did not protect us enough

- There was no canonical `cos secret audit` release command before ADR-215; scans were assembled ad-hoc.
- Per-event hooks do not classify existing repo history, vendored references, archives, metrics, or ignored local files.
- Secret-shaped fixtures and examples are not yet curated into a baseline/allowlist, so findings are noisy but still valuable.
- Local ignored `.env` files remain readable by any local process with repository access; ignoring them prevents commit, not exfiltration or unsafe service-mode projection.

## New protection added in this slice

- `manifests/cross-stack-secret-audit.yaml` declares the canonical toolchain and sensitive-surface policy.
- `lib/cross_stack_secret_audit.py` audits scanner availability, mutable GitHub scanner actions, sensitive local filenames, and summarizes existing redacted scan reports.
- `scripts/cos-cross-stack-secret-audit` and `scripts/cos secret audit` expose the operator command.
- Tests cover workflow pinning, sensitive-file reporting without reading values, classification boundaries, strict CLI behavior, and the `cos` route.

## Next hardening slices

1. Add wrapper scripts that run `gitleaks` and `trufflehog` with redaction and stable output names.
2. Curate a committed baseline for fixtures/examples so real leaks are distinguishable from placeholders.
3. Add a pre-commit fast path for staged content.
4. Wire `cos secret audit --strict` into ADR-211 service/public-release readiness after baseline noise is classified.
5. Extend ADR-202 private-content projection guard so `secret-never-touch` surfaces cannot leave local scope.

## Safety note

This report intentionally does not include raw candidate secrets, environment values, or scanner snippets. Raw scan artifacts remain under `.cognitive-os/reports/secret-audit/` and should stay local/private until classified.
