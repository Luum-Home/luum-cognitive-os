# Primitive Coverage Spike Plan — 2026-04-30

## Goal

Build the first generic `primitive-coverage` spike: a repository index and
coverage reporter for agentic/operational primitives that does **not** require
loading a whole codebase into an agent context window.

The spike should prove three integrations:

1. **Graph base** — Tree-sitter first, SCIP-compatible model later.
2. **Custom primitive rules** — Semgrep/ast-grep style rule adapters, with a
   dependency-free fallback for local tests.
3. **Coverage reports** — JSON, Markdown, and SARIF for CI/PR surfaces.

## Non-Goals

- Do not require Semgrep, ast-grep, Tree-sitter, Sourcegraph, Kythe, or SCIP to
  be installed for the first testable spike.
- Do not replace the existing COS-specific audits immediately.
- Do not let agents read a complete repository as prompt context.
- Do not perform automatic destructive reductions in this spike.

## Architecture

```text
primitive_coverage/
  adapters/
    cognitive-os.yaml
    claude-code.yaml
    github-actions.yaml
    openapi.yaml
    backstage.yaml
    generic.yaml
  indexers/
    tree_sitter.py
    scip.py
    markdown.py
    runtime_logs.py
    static_rules.py
    cos_audits.py
  reports/
    json_report.py
    markdown.py
    sarif.py
  model.py
  scanner.py
scripts/
  primitive_coverage.py
```

The first implementation may use Python package naming (`primitive_coverage`) for
importability while preserving report terminology as `primitive-coverage`.

## Adapter Contract

Each adapter describes primitive families and discovery patterns:

```yaml
adapter: cognitive-os
families:
  skill:
    patterns: ["skills/**/SKILL.md", ".codex/skills/**/SKILL.md"]
    required_signals: ["declared", "documented"]
  hook:
    patterns: ["hooks/**/*.sh", "packages/**/hooks/**/*.sh"]
    required_signals: ["declared", "wired", "tested"]
```

## Coverage Row Contract

```json
{
  "primitive_id": "hook:hooks/pre-commit-gate.sh",
  "family": "hook",
  "path": "hooks/pre-commit-gate.sh",
  "signals": {
    "declared": true,
    "wired": true,
    "tested": true,
    "documented": false,
    "runtime_seen": false,
    "owner": false,
    "proof": true
  },
  "status": "partial",
  "score": 57,
  "gaps": ["missing_documentation", "runtime_not_seen"]
}
```

## Spike Acceptance Criteria

1. `python3 scripts/primitive_coverage.py --adapter cognitive-os --format json`
   emits a valid JSON report.
2. The same CLI can emit Markdown and SARIF.
3. Reports include at least skills, hooks, rules, scripts, docs, and workflows.
4. The scanner consumes existing COS outputs when present:
   - `docs/06-Daily/reports/primitive-row-audit-latest.json`
   - `docs/06-Daily/reports/claim-proof-latest.json`
   - `docs/06-Daily/reports/reduction-backlog-latest.json`
   - `docs/06-Daily/reports/primitive-usage-map-latest.json`
5. Tests prove behavior with a synthetic repo, not only file existence.
6. The weekly primitive gap workflow can run the spike in report-only mode.

## Execution Phases

### Phase 1 — Minimal generic framework

- Add model dataclasses.
- Add adapter YAML files.
- Add generic filesystem/Markdown/workflow discovery.
- Add fallback static-rule engine.
- Add JSON, Markdown, SARIF reporters.
- Add CLI.

### Phase 2 — COS adapter bridge

- Load existing COS audit JSON reports when available.
- Merge row audit/claim proof/reduction backlog/usage map signals into generic
  primitive rows.
- Keep the old scripts as sources of truth until the generic scanner matures.

### Phase 3 — External engines

- Add optional Tree-sitter backend.
- Add optional Semgrep/ast-grep invocation and parser.
- Add optional SCIP importer.
- Fail gracefully when tools are absent.

### Phase 4 — CI gate

- Add report-only workflow step.
- Later add regression gates: no new high gaps, no new claim-without-proof,
  no new orphan primitives.

## First-Slice Decision

Use a dependency-free Python scanner for the first slice. This creates the
contract and report shape now. Tree-sitter/Semgrep/SCIP become optional engines
behind stable interfaces, not blockers for the first working product.
