<!-- SCOPE: both -->
---
name: security-red-team
invocation_pattern: on-demand
command: /security-red-team
description: >
  Unified red-team primitive for Cognitive OS: inventories attack surface,
  models threats, runs deterministic abuse probes, scores security controls per
  primitive, and emits a mitigation backlog.
triggers: ["/security-red-team", "/security-redteam", "/sec-red-team"]
audience: os-dev
version: 1.0.0
summary_line: "Unified Cognitive OS security red-team: inventory, threat model, abuse probes, risk scoring, and mitigation backlog."
platforms: ["claude-code", "codex", "bare_cli"]
prerequisites:
  - python3
  - PyYAML
entry: scripts/security-red-team
---

# /security-red-team

> Run a unified local red-team pass against Cognitive OS agentic primitives and
> produce a score-backed risk report.

## Purpose

Use this primitive when the maintainer wants the defender and malicious-attacker
view in one pass. It unifies the older focused primitives (`/red-team`,
`/redteam-harness`, `/pentest-self`, `/security-audit`, `/vulnerability-scan`)
into a deterministic first pass that is safe to run locally without real secret
access or network calls.

## What it does

1. Inventories the local security-relevant surface:
   - hooks;
   - rules;
   - skills;
   - scripts;
   - manifests;
   - red-team/security tests;
   - security docs.
2. Builds a threat model for:
   - secret exfiltration;
   - tool/MCP poisoning;
   - prompt injection;
   - governance bypass;
   - false-done claims;
   - supply-chain compromise.
3. Runs deterministic abuse probes:
   - credential-safe command integrity;
   - credential-safe env boundary;
   - blocked-path policy;
   - red-team scenario coverage;
   - scanner hook presence;
   - runtime flag registry;
   - MCP security surface.
4. Scores primitives across:
   - isolation strength;
   - secret handling;
   - auditability;
   - tamper resistance;
   - least privilege;
   - test coverage;
   - failure-mode clarity;
   - operator ergonomics.
5. Emits a mitigation backlog.

## Run

```bash
scripts/security-red-team
```

Default outputs:

```text
.cognitive-os/reports/security-red-team/security-red-team-latest.json
.cognitive-os/reports/security-red-team/security-red-team-latest.md
```

Print JSON to stdout:

```bash
scripts/security-red-team --json
```

Do not fail the shell on findings:

```bash
scripts/security-red-team --fail-on none
```

## Safety contract

- Does not read `.env`, `*.key`, `*.pem`, `secrets/*`, or `.git/config`.
- Does not execute optional scanners such as Promptfoo/Garak/Semgrep/Parry.
- Does not perform network calls.
- Does not mutate source files; writes only generated reports under
  `.cognitive-os/reports/security-red-team/`.
- Uses structural probes first; deeper live tools remain explicit follow-up
  primitives.

## Follow-up primitives

Use these after `/security-red-team` identifies where to dig deeper:

| Need | Follow-up |
|---|---|
| Prompt injection and jailbreak evals | `/red-team` |
| False-done and evidence-claim regressions | `/redteam-harness` |
| Safety mesh self-pentest | `/pentest-self` |
| Full config/secrets/infrastructure review | `/security-audit` |
| LLM endpoint vulnerability probing | `/vulnerability-scan` |
| Memory poisoning scan | `/memory-scan` |

## Success criteria

- JSON and Markdown reports are generated.
- Every required probe has a PASS/WARN/FAIL status.
- Primitive scores are present.
- Findings include severity, evidence, and recommendation.
- Backlog items point to concrete mitigation actions.

## Deferred deep-mode backlog

Track these follow-ups in `manifests/security-red-team.yaml` under
`deferred_deep_mode_backlog`:

1. Integrate provider/metrics audits into a future `--deep` mode.
2. Run an opt-in real Docker `--network none` smoke when resources allow.
3. Add MCP trust pins when actual MCP servers are configured.
4. Continue expanding deterministic adversarial scenarios for ANSI/invisible
   Unicode, symlink traversal, provider spoofing, metrics tampering, and egress.
