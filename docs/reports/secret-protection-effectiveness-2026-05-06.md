# Secret Protection Effectiveness Audit — 2026-05-06

> **Scope of this report**: per-tool-call hook wiring effectiveness. Asks:
> *"When an agent runs Bash/Edit/Write, does our `secret-detector.sh` hook
> actually fire and redact?"* Tied to a specific implementation slice
> (matcher fix `Edit|Write` → `Bash|Edit|Write`) with tests.
>
> **Companion report (different scope)**:
> [`secret-audit-release-readiness-2026-05-06.md`](./secret-audit-release-readiness-2026-05-06.md)
> covers the whole-repo release-readiness scan via ADR-215's `cos secret
> audit`. The two reports are intentionally separate: this one is *what
> gets blocked when an agent runs a tool*; the other is *what's in the repo*.

## Verdict

The secret/sensitive-data mesh was **real but not exhaustive**.

The uncomfortable finding is not that COS had no protection; it had several useful producers. The finding is that the most relevant producer for literal secrets (`secret-detector.sh`) was only wired on `Edit|Write`, not `Bash`, while its own implementation and tests assumed `Bash|Edit|Write`. That meant a pasted token in a shell command could bypass the redaction primitive in the active Claude projection.

This slice fixes that wiring gap and one observability bug in `confidentiality-enforcer` metrics.

## Q1. Profile / active registration matrix

Current active `.claude/settings.json` after the fix:

| Hook | Event | Matcher | Status |
|---|---|---|---|
| `secret-detector.sh` | `PreToolUse` | `Bash|Edit|Write` | ✅ fixed this slice |
| `confidentiality-enforcer.sh` | `PostToolUse` | `Edit|Write` | ✅ active |
| `dangerous-env-flag-detector.sh` | `SessionStart` | global | ✅ active but skipped in current timing stream |
| `session-sanity.sh` | `SessionStart` | global | ✅ active but skipped in current timing stream |

Canonical generator update:

- `scripts/_lib/settings-driver-claude-code.sh` now emits a dedicated `PreToolUse Bash|Edit|Write` group for `secret-detector.sh`.
- The rest of the edit/write-only hooks remain in `Edit|Write`; they are not accidentally run on Bash.
- `scripts/apply-efficiency-profile.sh` summary now reflects the split.

## Q2. Firing frequency from `hook-timing.jsonl`

From the current `.cognitive-os/metrics/hook-timing.jsonl` sample available in this repo:

| Hook | Timed invocations | Events | Execution statuses |
|---|---:|---|---|
| `secret-detector` | 16 | `PreToolUse: 16` | `ok: 16` |
| `confidentiality-enforcer` | 14 | `PostToolUse: 14` | `ok: 14` |
| `session-sanity` | 2 | `SessionStart: 2` | `skipped: 2` |
| `dangerous-env-flag-detector` | 2 | `SessionStart: 2` | `skipped: 2` |

Important caveat: `confidentiality-enforcer.jsonl` has 197 rows, but `hook-timing.jsonl` only shows 14 current invocations for that hook. The timing stream is useful for current active wiring, not a complete historical count.

## Q3. Pattern coverage

`secret-detector.sh` is intentionally high-precision and now covers these literal shapes:

- AWS access key IDs: `AKIA...`, `ASIA...`
- GitHub PAT prefixes: `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`
- Slack xox tokens
- Slack incoming webhook URLs
- Stripe live secret keys
- OpenAI classic and `sk-proj-` keys
- Anthropic `sk-ant-` keys
- npm tokens
- private-key block headers

This is still not equivalent to market scanners:

| Detector | Approximate breadth | Role |
|---|---:|---|
| `secret-detector.sh` | ~10 high-confidence families | per-tool-call redaction |
| `gitleaks` | ~200 rule families + entropy | whole-repo/history scan |
| `trufflehog` | ~700 detector families, optional verification | depth/forensic scan |

Conclusion: COS should not try to replace gitleaks/trufflehog. `secret-detector.sh` should stop obvious live mistakes during tool execution; ADR-215 `cos secret audit` should handle release/readiness breadth.

## Q4. `confidentiality-enforcer` true-positive / false-positive signal

Telemetry before this fix:

| Stream | Rows | Parseable rows | Interpretation |
|---|---:|---:|---|
| `confidentiality-enforcer.jsonl` | 197 | 3 | ❌ observability bug: most rows were malformed |
| `secret-redactions.jsonl` | 0 | 0 | No redactions recorded |
| `credential-safe-runs.jsonl` | 2 | not sampled | Manual runner exists but is not a broad automatic gate |
| `missing-secrets.jsonl` | 0 | 0 | No env-var hygiene warnings recorded |

The malformed confidentiality rows came from this pattern:

```bash
VIOLATION_COUNT=$(echo "$PYTHON_OUTPUT" | grep -c '{' || echo "1")
```

When `grep -c` returned zero matches, command substitution captured both `0` and fallback `1`, producing invalid JSON like `"violations":0\n1`. This slice replaces that with an `awk` count that always emits a single integer. Tests now parse the emitted metrics JSON for both warning/block paths.

Because only 3 historical rows are parseable, we cannot honestly estimate a 30-sample false-positive base rate from existing data. The correct next step is to collect new valid rows after this fix.

## Q5. Counterfactual against today's external scan

Today's redacted whole-repo scan artifacts showed:

| Source | Findings |
|---|---:|
| `gitleaks-git-20260506T231032Z.json` | 25 |
| `gitleaks-fs-20260506T231032Z.json` | 831 |
| `trufflehog-sanitized-20260506T231032Z.jsonl` | 158 |

Counterfactual before this slice:

- Bash-pasted AWS/GitHub/OpenAI-style literals: **not protected in active settings**, because `secret-detector.sh` was not wired for Bash.
- Edit/Write literals matching the narrow pattern set: protected if routed through Claude Write/Edit.
- Files already present in history, vendored references, archives, metrics, ignored `.env`, and zipped/reference material: not protected by per-event hooks.
- Personal email/path leaks: mostly outside `secret-detector`; handled partially by `confidentiality-enforcer`, but its telemetry was mostly malformed.

Counterfactual after this slice:

- Bash, Edit, and Write now all hit `secret-detector.sh` for high-confidence literal token redaction.
- Anthropic keys, Slack webhook URLs, npm tokens, `sk-proj-`, and private-key headers now have direct tests.
- Whole-repo/history coverage still belongs to ADR-215 scanners, not to the hook.

## Q6. Wiring and producer-without-consumer gaps

Skill invocation evidence across `skill-usage.jsonl`, `skill-invocations.jsonl`, `skill-metrics.jsonl`, and `skill-feedback.jsonl`:

| Skill | Recorded invocations in sampled streams |
|---|---:|
| `secret-audit` | 0 |
| `security-audit` | 0 |
| `audit-integrity` | 0 |
| `pattern-audit` | 0 |

This confirms the producer-without-consumer pattern again: security skills existed, but nothing forced them into release/readiness or dependency-adoption flows.

ADR-215 is the consumer path for secrets. The remaining closure work is:

1. Scanner wrappers: stable `gitleaks` / `trufflehog` runners with redaction.
2. Baseline curation: distinguish fixtures/examples from real leaks.
3. Pre-commit hook: staged-content fast scan.
4. ADR-211 integration: `cos secret audit --strict` as service/public-release readiness gate.
5. ADR-202 integration: `secret-never-touch` surfaces cannot be projected/exported.

## Fixes applied in this slice

- Registered `secret-detector.sh` for `PreToolUse Bash|Edit|Write` in active `.claude/settings.json` and canonical `settings-driver-claude-code.sh`.
- Kept edit/write-only hooks out of Bash by splitting `secret-detector` into its own group.
- Fixed malformed `confidentiality-enforcer.jsonl` writes.
- Expanded `secret-detector.sh` high-confidence patterns for Anthropic, OpenAI project keys, Slack webhooks, npm tokens, and private-key headers.
- Added tests for registration, new redaction patterns, and parseable confidentiality metrics.

## Validation

```bash
python3 -m pytest tests/unit/test_secret_detector_updated_input.py tests/unit/test_secret_detector_registration.py tests/behavior/test_confidentiality_enforcer.py -q
# 19 passed
```
