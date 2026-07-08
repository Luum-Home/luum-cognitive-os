---
type: quality-synthesis
source: docs/09-Quality/security/security-red-team.md
provenance: "Describes the /security-red-team primitive as the unified, safe-by-default local red-team entry point and how it routes to more specialized security tools."
---

## What it is
Reference doc for `/security-red-team` (`scripts/security-red-team`), the Cognitive OS's unified, local, deterministic red-team primitive. It answers: what attack surface exists, what a malicious agent would try, what controls exist, and what to fix next — without network calls or reading secrets.

## Key mechanics
- **Runner:** `scripts/security-red-team`, writing JSON + Markdown reports to `.cognitive-os/reports/security-red-team/security-red-team-latest.{json,md}`.
- **Safe-by-default contract:** no reads of `.env`, `*.key`, `*.pem`, `secrets/*`, `.git/config`; no network calls; no optional scanner execution; no source mutation; output confined to its own reports directory.
- **Five probe families:** surface inventory, threat model, abuse probes, primitive scoring, mitigation backlog.
- **Routing, not replacement:** delegates to focused tools rather than duplicating them — `/red-team` (Promptfoo prompt evals), `/redteam-harness` (false-done/evidence regressions), `/pentest-self` (safety mesh probes), `/security-audit` (config/secrets/infra audit), `/vulnerability-scan` (Garak LLM endpoint probes), `/memory-scan` (memory poisoning checks).
- **Deferred deep-mode backlog (explicitly not implemented):** a future `--deep` flag wiring `scripts/provider_spoof_audit.py` and `scripts/metrics_tamper_audit.py`; an opt-in real Docker `--network none` smoke test for `scripts/network_sandbox_run.py`; population of `manifests/mcp-trust-pins.yaml` once concrete MCP servers exist; and expanded deterministic adversarial scenarios (ANSI/invisible Unicode, symlink traversal, provider spoofing, metrics tampering, network egress).

## Relations & where used
- Acts as the top-level dispatcher for the OS's security-testing skill family: `/red-team`, `/redteam-harness`, `/pentest-self`, `/security-audit`, `/vulnerability-scan`, `/memory-scan`.
- `manifests/mcp-trust-pins.yaml` — target for future MCP tool-description hash pinning.
- `scripts/provider_spoof_audit.py`, `scripts/metrics_tamper_audit.py`, `scripts/network_sandbox_run.py` — scripts named as deep-mode integration targets, not yet wired into this primitive.

## Status / caveats
- Short reference doc, not an index/stub — it defines an active runner and contract, so it is synthesized in full.
- The "Deferred deep-mode backlog" section is explicitly aspirational/future work; do not treat those four items as implemented capabilities of the current safe-default runner.
