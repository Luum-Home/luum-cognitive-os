# Docker Image Review — 2026-05-04

## Scope

Reviewed the Docker follow-ups from dependency maintenance:

1. `ghcr.io/automaker-org/automaker:latest` fails with `manifest unknown`.
2. `python:3.13-slim@sha256:739e7213785e88c0f702dcdc12c0973afcbd606dbf021a589cab77d6b00b579d` was pulled locally during audit/apply, but compose pins must not be rewritten automatically.
4. `scripts/deps-update.sh --audit` counted digest-pinned references as possible newer digests because it compared remote config/manifest output against local repo digests.

## Decisions

| Image | Decision | Why |
|---|---|---|
| `ghcr.io/automaker-org/automaker:latest` | **Removed from reference compose.** | The tag is not pullable locally and upstream AutoMaker documents cloning the repo and using its source-build Docker Compose flow, not a stable public GHCR image. Keeping a broken image in `docker-compose.cognitive-os.yml` makes `--profile ui` fail before COS code is exercised. |
| `python:3.13-slim@sha256:739e7213785e88c0f702dcdc12c0973afcbd606dbf021a589cab77d6b00b579d` | **Keep pinned digest unchanged.** | Pulling a pinned digest only populates the local Docker cache; it is not evidence that the reference compose digest should change. `deps-update.sh` intentionally never edits compose digest pins. |
| Docker audit wording | **Changed from update-warning to classification.** | Digest-pinned refs are exact references; they are no longer reported as "may have newer digest". Floating tags with a remote mismatch are update candidates, unavailable remote digests are unverified, and pinned refs are counted separately. |

## Changed files

- `scripts/deps-update.sh` — classifies Docker audit results as floating-tag update candidates, unverified remotes, and pinned exact references instead of treating pinned digest refs as possible updates.
- `tests/integration/test_platform_services.py` — converted the Automaker container test to an explicit skip until a stable public image digest exists.
- `packages/ecosystem-tools/skills/automaker-bridge/SKILL.md` — replaced the dead image reference with a source-build note.

## Re-enable criteria

Only re-add AutoMaker to the reference compose stack when all are true:

1. Upstream publishes a public image that `docker pull` can fetch unauthenticated.
2. The image is pinned by digest, not `:latest`.
3. `tests/integration/test_platform_services.py::TestAutomakerService` can start the service and hit `/health` without requiring private credentials.

## Current audit result after follow-up

`bash scripts/deps-update.sh --audit` now reports:

```text
Docker:   0 floating tag update candidate(s), 0 unverified, 5 pinned exact reference(s)
```

This closes the previous five-image manual digest warning as audit noise: all five compose image references are exact digest references. Future image freshness work is an explicit pin-advance review, not an automatic dependency update.
