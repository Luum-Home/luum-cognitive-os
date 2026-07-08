---
type: concept-synthesis
source: docs/04-Concepts/architecture/language-agnostic-duplication-tooling-audit-2026-06-05.md
provenance: "Cognitive OS needs duplicate-code detection portable across languages/projects, not scoped to a single Node/Go/Python/C++ repo."
---

## What it is
Tooling audit (2026-06-05) recommending a portable, multi-lane duplicate-code detection primitive for consumer projects, implemented as ADR-334.

## Key mechanics
- Local consumer discovery: `~/.cognitive-os/installations.json` (via `scripts/cos-registry.sh`, consumed by `scripts/auto-update-projects.sh --list`) is the canonical registry; a filesystem marker scan (reusing `discover_projects` from `scripts/cos-token-savings-audit`) finds registry-stale projects via `cognitive-os.yaml`, `.cognitive-os/install-meta.json`, or `.cognitive-os/version`. Fleet output redacts paths unless `--show-paths`.
- Recommended lanes: `lexical` (jscpd, 223+ languages, primary default; fallback to dependency-free shingle/block scan), `function` (dependency-free normalized function/block scanner for Python/Bash/C-like text, optional language adapters), `policy` (Semgrep Generic mode / ast-grep for repeated policy smells — advisory, not clone-proof), `fleet` (registry-first then marker-scan discovery, read-only audits).
- Existing internal precedent to extend: `scripts/primitive_duplication_audit.py`, `manifests/python-helper-duplication-baseline.json`, `--fail-on-new` — default report/audit mode, `--write-baseline`, enforce fail-on-new only after a baseline exists.
- Proposed CLI: `scripts/cos-quality-duplicates --project-root . --mode audit --json`, `--write-baseline`, `--fail-on-new`, `--fleet --source <root> --json`. Outputs: `.cognitive-os/reports/quality-duplicates/latest.{json,md}`, optional `.cognitive-os/baselines/quality-duplicates.json`.
- Config contract under `cognitive-os.yaml: quality.duplicates` — `enabled`, `mode` (audit|fail-on-new|strict), `include`/`exclude`, `baseline` path, per-lane toggles, thresholds (`min_tokens: 80`, `min_lines: 8`, `similarity: 0.82`).
- External tool comparison: jscpd (223+ languages, strongest default), PMD CPD (narrower, Java/Apex-focused, 16 other languages), Semgrep (not a clone detector; Generic mode doesn't understand syntax).

## Relations & where used
ADR-334 (implemented as portable primitive, two-layered: external adapters plannable via `manifests/dependencies.yaml`/`cos-deps-install`; project-local scanner stays dependency-free by default). Sources: jscpd.dev, pmd.github.io/pmd/pmd_userdocs_cpd.html, semgrep.dev/docs/supported-languages, semgrep.dev/docs/writing-rules/generic-pattern-matching.

## Status / caveats
Acceptance criteria for the next implementation slice (at audit time): fallback scanner exits 0 without Node/Go/Semgrep; baseline write + fail-on-new only after new duplicate; `--fleet --json` distinguishes registry vs marker-scan-only projects; existing `primitive_duplication_audit.py` tests keep passing; docs linked from entrypoints README. ADR-334 marks this adopted/implemented.
