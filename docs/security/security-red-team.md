# Security Red-Team Primitive

`/security-red-team` is the unified Cognitive OS red-team primitive. It gives a
local, deterministic first-pass answer to: "what attack surface do we expose,
what would a malicious agent try, what controls exist, and what should we fix
next?"

## Runner

```bash
scripts/security-red-team
```

Outputs:

- `.cognitive-os/reports/security-red-team/security-red-team-latest.json`
- `.cognitive-os/reports/security-red-team/security-red-team-latest.md`

## Contract

The primitive is intentionally safe-by-default:

- no direct reads of `.env`, `*.key`, `*.pem`, `secrets/*`, or `.git/config`;
- no network calls;
- no optional scanner execution;
- no source mutation;
- generated reports only under `.cognitive-os/reports/security-red-team/`.

## Probe families

1. Surface inventory.
2. Threat model.
3. Abuse probes.
4. Primitive scoring.
5. Mitigation backlog.

## Relationship to existing red-team tools

This primitive does not replace focused tools. It routes to them:

- `/red-team` for Promptfoo prompt red-team evals;
- `/redteam-harness` for false-done/evidence regressions;
- `/pentest-self` for safety mesh probes;
- `/security-audit` for configuration/secrets/infrastructure audit;
- `/vulnerability-scan` for Garak LLM endpoint probes;
- `/memory-scan` for memory poisoning checks.

## Deferred deep-mode backlog

These are intentionally tracked as follow-up work instead of being implied by the
safe default runner:

1. **Provider/metrics audits in deep mode** — wire
   `scripts/provider_spoof_audit.py` and `scripts/metrics_tamper_audit.py` into
   a future `scripts/security-red-team --deep` path that audits current metrics,
   not just primitive presence.
2. **Real Docker no-network smoke** — run an opt-in smoke for
   `scripts/network_sandbox_run.py` with Docker `--network none` when Docker is
   available and local resource policy allows it. CI keeps dry-run coverage.
3. **MCP pins when servers exist** — populate `manifests/mcp-trust-pins.yaml`
   when concrete MCP servers are configured; include tool-description hashes and
   fail on drift.
4. **Expanded adversarial scenarios** — keep adding deterministic scenarios for
   ANSI/invisible Unicode, symlink traversal, provider spoofing, metrics
   tampering, and network egress variants.
