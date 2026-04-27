<!-- SCOPE: both -->

# Generator + Validator Pair Template

## Pattern

Every infrastructure skill should have TWO parts:
1. **Generator**: Creates the artifact (Dockerfile, CI config, K8s manifest, etc.)
2. **Validator**: Verifies the artifact is correct, secure, and follows best practices

## Generator Template

```yaml
---
name: {name}-generator
description: "Generate {artifact} following best practices"
allowed-tools: [Read, Write, Edit, Bash]
---
```

Steps:
1. Gather requirements (what, where, constraints)
2. Generate the artifact
3. Write to target file
4. Report what was created

## Validator Template

```yaml
---
name: {name}-validator
description: "Validate {artifact} for correctness, security, and best practices"
allowed-tools: [Read, Bash, Grep]
---
```

Steps:
1. Read the artifact
2. Run cheapest checks first (syntax -> lint -> security -> integration)
3. Report findings with severity tiers
4. Suggest fixes for issues found

## Examples

| Domain | Generator | Validator |
|---|---|---|
| Dockerfile | Generate Dockerfile from requirements | Hadolint + security scan |
| GitHub Actions | Generate workflow YAML | actionlint + secret detection |
| Terraform | Generate .tf files | tflint + Checkov + validate |
| Kubernetes | Generate manifests | kubeconform + OPA policies |
| Docker Compose | Generate compose YAML | docker compose config + port conflicts |
| Nginx | Generate nginx.conf | nginx -t + security headers check |

## Key Principles

- Validators run cheapest-first (staged verification pattern from self-improvement-protocol)
- Graceful degradation when validation tools are not installed
- Report what was SKIPPED, not just what PASSED
- Generator outputs MUST be deterministic (same input = same output)
- Validator findings use adversarial review tiers: BLOCKER / CONCERN / SUGGESTION / QUESTION

## Staged Validation Order

```
SYNTAX   (~0.1s)  ->  Can the file be parsed?
LINT     (~2s)    ->  Does it follow best practices?
SECURITY (~5s)    ->  Are there known vulnerabilities?
INTEGRATION (~30s) -> Does it work with the rest of the system?
```

Stop at first failure stage. Do not run expensive checks if syntax is broken.

## Graceful Degradation

When a validation tool is not installed:

```
[SKIPPED] Hadolint not installed — Dockerfile lint skipped
[PASSED]  docker build --check — syntax valid
[PASSED]  No COPY --chown root detected
```

Always report skipped checks so the user knows what was NOT validated.
