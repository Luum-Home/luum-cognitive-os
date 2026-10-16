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
  # Same intent without publishing the names: HMAC-SHA256(secret key, lowercased name).
  forbidden_term_hmac:   # any token of the line
    - "<hmac-sha256 hex>"
  forbidden_path_hmac:   # any component of a local project path
    - "<hmac-sha256 hex>"
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

## Protected names without publishing them (HMAC)

When the config is committed to a public repo, a clear-text list of private names is itself the leak, and a plain SHA-256 of a short name is no better: anyone who suspects a name hashes it and confirms it. The `*_hmac` keys hold `HMAC-SHA256(key, lowercased name)` instead, with a key that never enters the repo. Matching is per token (a name glued to other letters is not a hit). The unkeyed `*_sha256` keys are rejected.

The same scheme backs `tests/audit/test_no_consumer_domain_leakage.py`.

**Where the secrets live (outside every repo, mode 600):**

- Key: `COS_LEAK_HMAC_KEY` (env) or the file named by `COS_LEAK_HMAC_KEY_FILE`, default `~/.config/luum/leak-hmac.key`. Never printed: the scanner, the test and the generator only report whether it is missing.
- Clear list of names: `COS_CONSUMER_TERMS_FILE`, default `~/.config/luum/leak-terms.txt`. One name per line, `#` comments; plain lines are terms of the anti-leak test, `path:NAME` lines are components of a local project path (`forbidden_path_hmac`).

**Without the key:** in CI (`CI=true`) the scanner exits 2 and the anti-leak test fails, because a gate that cannot verify must not pass. Locally both skip the protected-name check and say so explicitly (scanner warning on stderr, pytest skip reason).

**Setting it up on a new machine** (the key itself comes from whoever holds it, never from the repo):

```bash
mkdir -p ~/.config/luum && chmod 700 ~/.config/luum
# first time only: generate a key, written straight to the file, never shown
( umask 077; python3 -c 'import secrets;print(secrets.token_hex(32))' > ~/.config/luum/leak-hmac.key )
```

**Adding or removing a protected name:** edit `~/.config/luum/leak-terms.txt` and run `python3 scripts/leak_terms_hmac.py`. It rewrites the digest blocks between the `BEGIN/END leak-terms-hmac` markers of the test and of `manifests/provenance-scan.yaml`, sorted, so the same key and list give the same bytes. `--check` exits 1 when the committed digests are out of date. Rotating the key means regenerating with the new key and updating the CI secret in the same change.

**CI secret.** GitHub Actions jobs that run the scanner or the anti-leak test need the key as the repository secret `COS_LEAK_HMAC_KEY`, exposed to the job:

```yaml
    env:
      COS_LEAK_HMAC_KEY: ${{ secrets.COS_LEAK_HMAC_KEY }}
```

The repository owner loads it from the local key file, without printing it:

```bash
gh secret set COS_LEAK_HMAC_KEY -R Luum-Home/luum-cognitive-os < ~/.config/luum/leak-hmac.key
```

Today the scanner runs in CI through `.github/workflows/scope-portability.yml` (its pre-commit behavior test executes `.githooks/pre-commit`, which calls `provenance-scan --staged`); that job declares the env above. Set the secret before pushing a change that touches the job: without it the job fails on purpose.

Use `# cos-allow-provenance-scan` only for deliberate examples or tests. Prefer fixing text or moving private terms into project-local config over suppressing findings.
