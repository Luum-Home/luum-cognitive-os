# Provenance Scan Guardrail

`provenance-scan` is the Cognitive OS guardrail for provenance hygiene in agent-assisted projects. It is intentionally project-agnostic: the SO ships the scanner, wrapper, hook, tests, and default policy shape; each adopting project supplies its own forbidden source terms and import/path allowlists.

## What it blocks

- Developer-local paths such as real `/Users/...`, `/home/...`, Windows `C:\Users\...`, and non-canonical `Projects/...` references. <!-- cos-allow-provenance-scan cos-allow-absolute-path cos-allow-local-privacy-pattern: documented placeholder examples -->
- Project/source names configured in `manifests/provenance-scan.yaml` or `.cognitive-os/provenance-scan.yaml`.
- Sensitive provenance language when it points at local/private origins, for example “copied from private repo …” or “adapted from /Users/…”. <!-- cos-allow-provenance-scan cos-allow-absolute-path cos-allow-local-privacy-pattern: documented blocked examples -->
- Explicitly forbidden Go, Python, and TypeScript import roots.
- Go `replace` directives and Python `sys.path` hacks that point at host-local or external source paths.

## What it allows

- Repo-relative canonical paths.
- Explicit placeholders such as `/Users/...` when documenting a pattern rather than leaking an operator path.
- Temporary paths under `/tmp/`, `/var/folders/`, and other configured `allowed_absolute_paths`.
- Imports listed in per-language allowlists.

## Integration points

- CLI: `scripts/provenance-scan --json`
- Make: `make provenance-scan`
- Hook: `hooks/provenance-scan.sh`
- Pre-commit: `.githooks/pre-commit`
- Release lane: `scripts/cos-patch-release validate`

## Configuration

Default project config lives at `manifests/provenance-scan.yaml`:

```yaml
provenance:
  forbidden_terms:
    - ExampleSourceRepo
  forbidden_paths:
    - "(?i)Projects/ExampleSourceRepo[A-Za-z0-9._/-]*"
  allowed_import_roots:
    go:
      - github.com/example/product
    ts:
      - "@example/"
    python:
      - example_package
  allowed_absolute_paths:
    - /tmp/
```

Use `# cos-allow-provenance-scan` only for deliberate examples or tests. Prefer fixing text or moving private terms into project-local config over suppressing findings.
