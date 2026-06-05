# Tool Adoption Report — Duplicate-Code Quality Stack — 2026-06-05

## Decision

Adopt a COS-owned duplicate-code primitive with optional external adapters:

- `jscpd` — primary external lexical clone detector.
- `PMD CPD` — optional copy/paste detector adapter for supported languages.
- `Semgrep` — optional common-logic/policy-pattern lane, not clone proof.
- `dupl` and `golangci-lint` — optional Go-specific duplicate/common-logic lanes.
- `ast-grep` — optional AST policy-pattern lane.

The primitive must keep a dependency-free fallback so every consumer install gets a report before optional tools are installed.

## Evidence

- jscpd official site: https://jscpd.dev/ — advertises duplicate scanning across 223+ languages/formats and Rabin-Karp powered detection.
- jscpd GitHub: https://github.com/kucherenko/jscpd — package/API surface for CLI and finder/tokenizer packages.
- PMD CPD docs: https://pmd.github.io/pmd/pmd_userdocs_cpd.html — CPD is the PMD copy-paste detector; supported languages are surfaced by `pmd cpd --help`.
- Semgrep supported languages: https://semgrep.dev/docs/supported-languages — Generic is generally available.
- Semgrep generic mode: https://semgrep.dev/docs/writing-rules/generic-pattern-matching — generic mode can scan unsupported languages but does not understand their syntax; use as policy-pattern lane.
- ast-grep official site: https://ast-grep.github.io/ — polyglot structural search/rewrite tool.

## Anonymized implementation evidence

The implementation is based on anonymized patterns observed in local SO adopters. This report intentionally avoids enumerating consumer project names or their project-specific duplicate-quality lanes.

## Adoption boundary

- Dev/CI/full/headless install profiles include the tools in `manifests/dependencies.yaml`.
- Default/core profile remains lightweight.
- `scripts/cos-quality-duplicates` owns wrapper logic so consumers do not need project-local custom scripts.
- `cos_init.py` projects the wrapper to `.cognitive-os/bin/` for consumer projects.
