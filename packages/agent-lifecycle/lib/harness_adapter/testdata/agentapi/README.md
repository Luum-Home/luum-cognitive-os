# agentapi msgfmt golden fixtures

**Source**: `coder/agentapi` `lib/msgfmt/testdata/`
**Commit**: `00ff7ffdc4badcf68b3903dd799cf6e2d4370d86`
**License**: MIT, inherited from upstream `coder/agentapi`.

This directory vendors testdata only. It does **not** adopt the agentapi runtime,
HTTP sidecar, or Go parser implementation.

## Update process

```bash
tmp=$(mktemp -d)
git clone --depth 1 --filter=blob:none --sparse https://github.com/coder/agentapi "$tmp"
git -C "$tmp" sparse-checkout set lib/msgfmt/testdata
rm -rf lib/harness_adapter/testdata/agentapi/msgfmt
cp -R "$tmp/lib/msgfmt/testdata" lib/harness_adapter/testdata/agentapi/msgfmt
git -C "$tmp" rev-parse HEAD  # update commit above
```

## COS contract

Fixtures are used to harden harness-output parsing and initialization-state
classification. Do not claim agentapi runtime integration from this fixture
adoption.
