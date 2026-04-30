<!-- SCOPE: both -->
<!-- TIER: 2 -->
# Supply Chain Defense Protocol

## Context
In March 2026, the TeamPCP attack compromised Trivy, LiteLLM, npm, PyPI, and Docker Hub by manipulating git tags and Docker image tags. This protocol prevents similar attacks against Cognitive OS.

## Attack Vectors Mitigated

### 1. Docker Image Tag Manipulation
**Attack**: Attacker compromises registry, changes what `:latest` or `:v1.0.0` points to.
**Defense**: Pin ALL Docker images to SHA256 digests (`image@sha256:abc123...`), not tags.

### 2. Git Tag Manipulation
**Attack**: Attacker with repo access rewrites git tags to point to malicious commits.
**Defense**: `cos install` pins to commit hashes in cos-lock.yaml, verifies on update.

### 3. Dependency Confusion
**Attack**: Attacker publishes malicious package with same name in public registry.
**Defense**: cos audit runs 5 security gates before any package is installed.

### 4. Prompt Injection via Skills
**Attack**: Malicious skill contains "ignore previous instructions" in SKILL.md.
**Defense**: cos audit Gate 3 (injection scanner) detects prompt injection patterns.

## Rules (Always Active)

### Docker Images
- NEVER use `:latest` tag in production docker-compose files
- ALWAYS pin to SHA256 digest: `image: name@sha256:xxxx`
- Verify digests after any `docker compose pull`
- Rotate images on a schedule (monthly) with fresh digest verification

### cos Packages
- cos-lock.yaml stores the commit hash of every installed package
- `cos update` verifies new commit is a descendant of the old (no force-push)
- Per-file integrity hashes stored in lockfile (not just manifest hash)
- Gate 3 (injection scanner) validates skill content before install

### CI/CD Pipelines
- Pin GitHub Actions to commit SHA, not tags: `uses: action@sha256:xxx`
- Verify all pipeline dependencies before execution
- Isolate CI credentials with minimal scope and short TTL
- Monitor for unexpected dependency updates

### Monitoring
- Track Docker image digests in `.cognitive-os/metrics/image-digests.jsonl`
- Alert on digest changes without explicit update command
- Log all `cos install` and `cos update` operations with full audit trail

## Response Checklist (If Compromised)
1. Stop all Docker containers immediately
2. Rotate ALL credentials (API keys, tokens, passwords)
3. Verify Docker image digests against known-good values
4. Check cos-lock.yaml for unexpected changes
5. Review git log for unauthorized commits
6. Run `cos audit` on all installed packages
7. Check GitHub Actions workflow files for modifications
8. Report to security team and upstream maintainers
