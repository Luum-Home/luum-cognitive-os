# COS Package Index

Central package index for the Cognitive OS ecosystem. This directory simulates
what a standalone `Luum-Home/cos-packages-index` repository would look like.

## How the Index Works

The `index/packages.yaml` file is the master registry of all known COS packages.
Each entry contains the package name, source repository, path within that repo,
current version, description, and discovery tags.

The `cos search` command can query this index as a `directory` registry source,
providing offline and fast package discovery without hitting the GitHub API.

## Registry Integration

Add the index as a local registry source in `cognitive-os.yaml`:

```yaml
packages:
  registries:
    - name: cos-index
      type: directory
      path: packages/cos-index/index
      enabled: true
      priority: 0
    - name: cos-official
      type: github-topic
      topic: cos-package
      enabled: true
      priority: 1
```

Priority 0 means the local index is checked first, falling back to GitHub search.

## How to Submit a Package

1. Create a `cos-package.yaml` in your package root following the schema in
   `docs/cos-package-spec.md`.
2. Add an entry to `index/packages.yaml` with the required fields.
3. Run `bash scripts/validate-index.sh` to verify the entry is valid.
4. Submit a pull request.

## Scripts

- `scripts/validate-index.sh` -- Validates every entry in the index against
  its actual `cos-package.yaml` (when locally available).
- `scripts/generate-index.sh` -- Regenerates the index by scanning the local
  `packages/` directory. Useful after adding new packages.

## Future: Standalone Repository

When the index moves to its own `Luum-Home/cos-packages-index` repo:

1. The `generate-index.sh` script will use the GitHub API to discover packages
   across multiple repositories tagged with `cos-package`.
2. A GitHub Action will run `validate-index.sh` on every PR.
3. `cos search` will fetch the index from the repo (cached locally).
