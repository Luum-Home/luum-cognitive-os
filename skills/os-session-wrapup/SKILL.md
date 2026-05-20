---
name: os-session-wrapup
description: Use when closing or reviewing a Cognitive OS maintainer session after touching agentic primitives, projection settings, harness contracts, or release/public-readiness surfaces. Runs the generic session-wrapup first, then adds an SO-only component-reality check with unproven/dormant counts; do not use in consumer projects.
user-invocable: true
version: 1.0.0
last-updated: 2026-05-20
audience: os-dev
tags:
- session
- maintainer
- dogfooding
- primitives
- reality-check
summary_line: SO-only session close addendum that runs component-reality-check when primitive surfaces changed.
platforms:
- claude-code
- codex
- generic-cli
platform_support:
  generic-cli:
    support_level: documented-only
    evidence:
    - skills/os-session-wrapup/SKILL.md
    - test_os_session_wrapup_addendum_trigger.py
prerequisites: []
routing_patterns:
- pattern: \bos[- ]?session[- ]?wrapup\b
  confidence: 0.95
- pattern: \b(session[- ]?wrapup|wrap\s+up|close\s+session|end\s+session)\b.{0,80}\b(hooks?|skills?|rules?|scripts?|libs?|manifests?|primitives?|agentic\s+primitives?|wiring|surface|classification|unproven|dormant|release|public)\b
  confidence: 0.88
- pattern: \b(todas?\s+las\s+)?primitivas?\b.{0,80}\b(controladas?|unproven|dormant|classification|clasificacion|superficie|wiring|deuda)\b
  confidence: 0.88
- pattern: \b(reality[- ]?check|component[- ]?reality[- ]?check|dogfooding|unproven\s+claims?)\b
  confidence: 0.82
routing_intents:
- intent: os_maintainer_session_close_with_reality_check
  description: Operator is closing or auditing a Cognitive OS maintainer session after changing primitives or wants proof that primitive reality/debt is controlled.
  confidence: 0.9
triggers:
- os-session-wrapup
- /os-session-wrapup
- OS maintainer session close
- component reality addendum for session close
---
<!-- SCOPE: os-only -->
# OS Session Wrapup — Maintainer Reality Addendum

Close a Cognitive OS maintainer session without contaminating the portable
`/session-wrapup` primitive. Use this only in the Cognitive OS source repo or an
SO-maintainer checkout.

## Purpose

Run the normal portable session close, then add an SO-only primitive reality
check when the session touched agentic primitive surfaces or when the operator
asks about dormant/unproven debt.

## When to use

Use this skill when any of these are true:

- The operator invokes `/os-session-wrapup`.
- The operator asks whether primitives are controlled, classified, real,
  dormant, unproven, wired, or ready for public/release claims.
- The session added, removed, merged, or changed files under:
  `hooks/`, `skills/`, `rules/`, `scripts/`, `lib/`, `manifests/`,
  `.cognitive-os/`, `.codex/hooks.json`, or `.claude/settings.json`.
- The session merged worktrees or branches containing primitive changes.
- The session is a dogfooding or reality-check pass.

Do not use this in consumer projects. Consumer projects should use
`/session-wrapup`, `/dod-check`, or `/readiness-check`.

## Steps

### 1. Run the generic session close first

Invoke `/session-wrapup` or follow `skills/session-wrapup/SKILL.md`. Keep its
summary portable and do not add SO-only primitive audit details there.

### 2. Decide whether the SO addendum is required

From the Cognitive OS repo root, inspect uncommitted primitive-surface changes:

```bash
git status --porcelain -- \
  hooks skills rules scripts lib manifests .cognitive-os \
  .codex/hooks.json .claude/settings.json
```

If this command prints rows, or the prompt explicitly asked about primitive
reality/classification/debt, run the component reality check.

### 3. Run component-reality-check as a dry-run

Prefer the deterministic classifier directly:

```bash
python3 scripts/aspirational_audit.py --dry-run --json --project-root .
```

If the operator requested persistence or a trend, use `/component-reality-check`
with the appropriate options instead.

### 4. Report the addendum

Append a short section after the generic session summary:

```text
OS maintainer addendum
- primitive surface changed: yes|no
- component reality: REAL=<n>, ON_DEMAND=<n>, DORMANT=<n>, ASPIRATIONAL=<n>, METADATA=<n>
- dormant+aspirational ratio: <ratio>
- worst offenders: <top 5>
- action: none | follow-up needed | strict audit recommended
```

Do not claim every primitive has deep functional proof. The audit only proves
observable reality classification for the scanned surfaces.

## Contextual Trigger

SO-only. Trigger on Cognitive OS maintainer session close, primitive-surface
changes, release/public-readiness checks, dogfooding, or questions about
unproven/dormant primitive debt.
