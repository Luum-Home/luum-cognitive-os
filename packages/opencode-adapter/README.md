# OpenCode Adapter

OpenCode adapter package for Cognitive OS primitive projection.

The starter implementation lives in `plugins/cos-primitive-guard.js` and is
validated by `scripts/opencode_primitive_adapter_smoke.py`. It signs only the
primitive subset listed in `docs/reports/opencode-primitive-adapter-smoke-latest.json`;
other OpenCode primitive contracts remain host-plugin-lifecycle-capable backlog.
