---
type: quality-synthesis
source: docs/09-Quality/security/credential-safe-runner-red-team-2026-05-05.md
provenance: "Dated (2026-05-05) adversarial review of the qwen-fallback-smoke credential-safe runner, documenting attack findings and the mitigations added to prevent secret exposure through the approved execution path."
---

## What it is

An adversarial (red-team) review of one specific SO primitive — the `qwen-fallback-smoke` credential-safe runner — modeling an attacker who can ask the agent to run commands and modify ordinary repository files, with the explicit goal of extracting `.env`-sourced secrets while appearing to use legitimate SO tooling. Documents six specific attacks, the mitigation added for each, and the residual risk that remains.

## Key mechanics

- **Threat model**: repository policy already blocks direct reads of sensitive file classes (env files, key/cert files, secret directories, git config), but the runtime may be fully permissive, so policy alone is not a hard sandbox boundary. The primitive must prevent leakage through its own approved path and make malicious changes to that path visible before it runs.
- **Six attack/mitigation pairs**:
  1. Modifying the allowlisted wrapper script to leak secret values before running it -> mitigated with a pinned content hash (`command_integrity.sha256`) that the runner checks and aborts on mismatch, recording the hash in the audit trail. Residual risk: someone able to edit both the script and its integrity manifest defeats this, so manifest changes need code review.
  2. Passing unrelated inherited parent-process secrets into the child process -> mitigated by rebuilding the child's environment from an explicit inherited-key allowlist plus approved provider keys and forced flags, instead of copying the full parent environment minus a blocklist. Residual risk: some inherited utility variables remain necessary for execution.
  3. Pointing the runner at a different secret-bearing file (e.g. an alternate name or an absolute out-of-repo path) -> mitigated by a manifest-pinned single-file allowlist plus rejection of absolute/out-of-project paths. Residual risk: a symlinked env file resolving outside the project is separately rejected by path resolution.
  4. Printing exact secret values to stdout/stderr -> mitigated by exact-value redaction, with tests covering stdout, stderr, JSON output, and the audit trail.
  5. Printing encoded variants of secret values (base64, hex, URL-encoded) -> mitigated by extending redaction to cover those encodings in addition to exact values. Residual risk: redaction cannot prove safety against arbitrary transformations, e.g. per-character leaks or exfiltration outside the observed output stream.
  6. Flooding the transcript with excessive output -> mitigated by a `max_output_chars` cap on model-visible stdout/stderr, with the audit recording a truncation count. Residual risk: the child process can still consume time/resources until timeout.
  - A seventh item confirms approval-gating (`--approve` or an approval env flag) was already required before this review and is now covered by tests.
- **Security boundary statement**: explicitly framed as "a stronger operational boundary, not a sandbox" — it stops accidental leakage and several obvious malicious mutations of the approved path, but does not stop a fully privileged malicious agent that bypasses the primitive entirely if the surrounding runtime permits direct file access. A true cryptographic/OS-enforced boundary would require running credentialed operations in a separate constrained process/container/VM with read access limited to an allowlisted synthetic secrets file, network egress limited to the target provider endpoint, a read-only repository mount or immutable script artifact, no access to the operator's broader home directory/shell history/key material/cloud credentials/browser profiles/password stores, and append-only external audit logs.
- **Tests added/strengthened**: approval requirement, rejection of unknown script IDs, rejection of non-allowlisted secret-file keys, rejection of non-allowlisted inherited parent secrets, redaction of allowlisted values if printed, rejection of non-allowlisted/out-of-project secret files, integrity-verification failure on modified allowlisted scripts, redaction of exact and encoded secret values, bounded model-visible output, and manifest invariants requiring integrity pinning, file allowlisting, sanitized child environment, redaction, and bounded output.
- **Live proof**: the runner was executed end-to-end through the credential-safe primitive using real repo-local secret values; the visible output showed all four smoke checks passing without exposing secret values, and the audit row captured key names, the command hash, return code, redaction count, truncation count, and output lengths.

## Relations & where used

- The credential-safe-runner sub-score (81/100) in `cognitive-os-attack-surface-inventory.md` traces to this review.
- Referenced as an example of durable, executable adversarial testing in `cognitive-os-agent-security-research-2026-05-05.md`'s "false-completion claims" control row (scored High) and its P1 backlog item calling for adversarial tests on the dispatch/fallback path.

## Status / caveats

Explicitly dated 2026-05-05 — a point-in-time red-team pass against one named primitive (`qwen-fallback-smoke`), not a general claim about all SO credential handling. The doc itself is explicit that the primitive is an operational boundary, not a sandbox, and enumerates residual risk for every mitigation rather than claiming the attack surface is fully closed.
