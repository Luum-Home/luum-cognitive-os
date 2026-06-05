# Language-Agnostic Duplicate-Code Tooling Audit — 2026-06-05

## Question

Cognitive OS should incorporate duplicate-code detection that works across projects and languages, not only inside a single Node, Go, Python, or C++ repository. The target is a portable agentic primitive that consumer projects can run locally, CI can ratchet, and maintainers can use to mine proven local patterns from repositories already using the OS.

## Local consumer discovery

There are two existing discovery paths:

1. `~/.cognitive-os/installations.json`, maintained by `scripts/cos-registry.sh` and consumed by `scripts/auto-update-projects.sh --list`, is the canonical registry for projects installed from this SO source.
2. A filesystem marker scan can find additional or registry-stale projects by looking for `cognitive-os.yaml`, `.cognitive-os/install-meta.json`, or `.cognitive-os/version`. `scripts/cos-token-savings-audit` already contains a read-only marker-scanning implementation (`discover_projects`) that can be reused rather than reinvented.

A current registry sample confirmed multiple SO installations from this source clone, and marker scanning found additional candidate projects. The implementation keeps those project identities out of documentation and reports by default; fleet output redacts paths unless `--show-paths` is explicitly passed.

## Local patterns worth porting

### 1. jscpd as broad lexical duplicate detector

Local SO adopter evidence showed `jscpd` recurring as the cross-language baseline without requiring the SO to publish adopter identities or project-specific lane details.

Portable lesson: make `jscpd` the first external lane, but do not hardcode Node project assumptions. Resolve it through a configured env var, repo-local package manager if available, operator-installed global binary, or a safe ephemeral runner. Emit JSON/Markdown reports and support audit vs strict modes.

### 2. AST/function-level detectors for semantic-ish repeats

Local evidence also showed language-aware follow-up checks because lexical clone detection alone misses repeated business logic with renamed identifiers.

Portable lesson: the SO primitive should provide a dependency-free generic function/block scanner for Python/Bash/C-like text, then optional language adapters when local dependencies exist. Findings should be advisory until a per-project baseline exists.

### 3. Common-logic pattern scans

Some duplicate-quality signals are repeated *policy shape*, not just identical code.

Portable lesson: duplicate-code tooling should be one primitive family with lanes: lexical clones, normalized functions, and repeated policy smells. The SO should avoid pretending all of these are the same signal.

### 4. Baselines and ratchets

The SO already has `scripts/primitive_duplication_audit.py`, `manifests/python-helper-duplication-baseline.json`, and `--fail-on-new` support. This is a good internal model: treat current debt as visible baseline, then fail only when new duplicate identities appear.

Portable lesson: a consumer-facing primitive should default to report/audit mode, support `--write-baseline`, and enforce `--fail-on-new` only after a project baseline exists.

## External tool check

- `jscpd` is the strongest language-agnostic default: its official site currently advertises duplicate detection across 223+ languages and formats, including JavaScript, Python, Java, Go, Rust, C++, TypeScript, Ruby, SQL, Markdown, YAML, and framework file formats.
- PMD CPD is useful but narrower; PMD documentation says PMD is mainly Java/Apex and CPD supports 16 other languages. That is a good optional adapter, not the universal default.
- Semgrep is not a clone detector, but it is a strong policy-pattern lane. Its official docs list Generic as a GA language and warn that generic mode does not understand syntax, so it should be used for repeated smells, not duplicate-code proof.

## Proposed SO primitive family

### New command surface

Introduce a project-scope/both-scope command family such as:

```bash
scripts/cos-quality-duplicates --project-root . --mode audit --json
scripts/cos-quality-duplicates --project-root . --write-baseline
scripts/cos-quality-duplicates --project-root . --fail-on-new
scripts/cos-quality-duplicates --fleet --source <cos-source-root> --json
```

The command should produce:

- `.cognitive-os/reports/quality-duplicates/latest.json`
- `.cognitive-os/reports/quality-duplicates/latest.md`
- optional `.cognitive-os/baselines/quality-duplicates.json`

### Lanes

1. `lexical`: `jscpd` when available; fallback to dependency-free normalized shingle/block scan.
2. `function`: dependency-free normalized function body scan, plus optional stack-specific adapters when available.
3. `policy`: optional Semgrep/ast-grep common-logic rules, with clear status `not_available`, `timeout`, `advisory`, or `blocking`.
4. `fleet`: discover consumer projects through registry first and marker scan second; run read-only audits; summarize by project without leaking paths unless `--show-paths` is passed.

### Config contract

Add project config under `cognitive-os.yaml`:

```yaml
quality:
  duplicates:
    enabled: true
    mode: audit              # audit | fail-on-new | strict
    include: []              # default inferred from git/project stack
    exclude: []              # merged with safe defaults
    baseline: .cognitive-os/baselines/quality-duplicates.json
    lanes:
      lexical: true
      function: true
      policy: advisory
    thresholds:
      min_tokens: 80
      min_lines: 8
      similarity: 0.82
```

### Implementation path

1. Extract reusable pieces from `scripts/primitive_duplication_audit.py` into `lib/duplication_audit.py` without breaking the existing SO-only primitive.
2. Add `scripts/cos-quality-duplicates` as the consumer-facing CLI wrapper.
3. Add `scripts/cos-consumer-discover` or reuse/extract discovery from `cos-token-savings-audit` so fleet scans can list OS adopters consistently with `scripts/auto-update-projects.sh`.
4. Add a default dependency/tool resolver that checks configured binaries, local toolchains, global installs, and safe ephemeral runners.
5. Add tests:
   - unit: repeated Python/Bash/function/block detection;
   - behavior: baseline ratchet pass/fail;
   - integration: temp consumer project with `cognitive-os.yaml` and no Node toolchain still produces a fallback report;
   - optional adapter tests skipped unless `jscpd`, `semgrep`, `golangci-lint`, or `dupl` are available.
6. Project a skill or rule entry so agents know to run this lane after multi-file refactors and before claiming “zero duplicate” quality.

## Recommended adoption decision

Adopt `jscpd` as the primary external lexical clone detector, but wrap it in a COS-owned portable primitive with fallback scanning, report contracts, and baseline ratchets. Do not make `jscpd` a hard runtime dependency for all projects. Treat PMD CPD, `dupl`, `golangci-lint`, Semgrep, ast-grep, and TS/JS `ts-morph` scans as optional adapters selected by stack/tool availability.

This matches the local evidence: mature consumer implementations use a multi-lane approach rather than a single universal detector, and the strongest repeated pattern is “audit first, baseline, then fail-on-new.”

## Acceptance criteria for the next implementation slice

1. `scripts/cos-quality-duplicates --project-root <tmp-consumer> --json` exits `0` without Node, Go, or Semgrep installed by using the fallback scanner.
2. `scripts/cos-quality-duplicates --write-baseline` writes a stable baseline, and `--fail-on-new` fails only after a new duplicate appears.
3. `scripts/cos-quality-duplicates --fleet --json` finds registry projects from `~/.cognitive-os/installations.json` and marks marker-scan-only projects separately.
4. Existing `scripts/primitive_duplication_audit.py` tests keep passing.
5. Docs link the primitive from `docs/00-MOCs/entrypoints/README.md` and quality docs.

## Implementation update — ADR-334

ADR-334 adopts this investigation as an implemented portable primitive. The implementation is intentionally two-layered:

- External adapters are installable/plannable through `manifests/dependencies.yaml` and the existing `cos-deps-install` install/update flow.
- The project-local scanner remains dependency-free by default, so every consumer install gets a usable duplicate-code report even before optional tools are installed.

Source checks used for the adoption decision:

- jscpd official site: https://jscpd.dev/ — primary external clone detector; current official claim is 223+ languages/formats.
- PMD CPD docs: https://pmd.github.io/pmd/pmd_userdocs_cpd.html — optional copy/paste detector adapter.
- Semgrep supported languages: https://semgrep.dev/docs/supported-languages — broad SAST/pattern tool with Generic generally available.
- Semgrep generic mode: https://semgrep.dev/docs/writing-rules/generic-pattern-matching — generic mode can match unsupported languages but does not understand syntax, so it is not clone proof.
