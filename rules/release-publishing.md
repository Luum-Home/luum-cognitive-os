<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Release Publishing

## Purpose

Make Cognitive OS patch releases repeatable, auditable, and safe from the known failure modes discovered while publishing `v0.29.3` through `v0.29.6`.

## Rule

Patch releases MUST use `scripts/cos-patch-release` instead of an ad hoc shell sequence.

A patch release MUST:

1. Prepare release metadata with `scripts/cos-patch-release prepare --version X.Y.Z`.
2. Validate with `scripts/cos-patch-release validate`.
3. Publish with `scripts/cos-patch-release publish --version X.Y.Z` or follow its dry-run plan exactly.
4. Land through `scripts/merge-to-main.sh`; never push directly to `main`.
5. Use `uv sync --extra testing --locked` in CI release dependency setup.
6. Verify the GitHub release with `gh release view vX.Y.Z`.

A patch release MUST NOT use `make test-laptop` as the only release gate while the broad lane has unrelated dependency or state drift. Use the patch lane first; promote back to broad only after the broad lane is repaired.

## Rationale

The `v0.29.3` to `v0.29.6` release sequence exposed repeatable release hazards:

- Direct pushes to `main` are correctly blocked by the merge queue guard.
- CI release validation failed when Python test dependencies were missing.
- Broad laptop validation can fail from unrelated optional dependencies or local state.
- Unlocked `uv sync` can dirty `uv.lock` and make GoReleaser refuse to publish.

Encoding these lessons as a primitive makes future patch releases safer and easier to audit.

## Examples

### Good

```bash
scripts/cos-patch-release prepare --version 0.29.7 --title "Patch Release Primitive"
scripts/cos-patch-release validate
scripts/cos-patch-release doctor --version 0.29.7 --allow-warnings
scripts/cos-patch-release publish --version 0.29.7 --message "release: v0.29.7"
```

### Bad

```bash
git push origin main
git tag v0.29.7
git push origin v0.29.7
```

This bypasses the merge queue and release diagnostics.

## Related

- `scripts/cos-patch-release` — executable primitive.
- `skills/patch-release/SKILL.md` — operator workflow.
- `.github/workflows/cos-binary-release.yml` — GoReleaser publishing workflow.
- `scripts/merge-to-main.sh` — main branch landing path.

## Contextual Trigger

Triggers: release, patch release, publish, tag, GoReleaser, release doctor, version bump.
