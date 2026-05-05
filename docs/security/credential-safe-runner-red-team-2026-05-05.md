# Credential-Safe Runner Red-Team Review — 2026-05-05

## Scope

This review attacks the `qwen-fallback-smoke` credential-safe primitive as if a
malicious or compromised agent wants to extract `.env` secrets while still using
apparently legitimate SO tooling.

## Threat model

Assume the attacker can ask the agent to run commands in a local workspace and
can modify ordinary repository files during a task. The repository policy still
blocks direct reads of `.env`, `*.key`, `*.pem`, `secrets/*`, and `.git/config`,
but the runtime may be `danger-full-access`, so policy alone is not a
cryptographic sandbox.

The primitive must therefore prevent accidental/authorized leakage through the
approved path, and it must make malicious changes visible before the path runs.

## Attack findings and mitigations

| Attack | Before | Mitigation added | Residual risk |
|---|---|---|---|
| Modify `scripts/smoke-qwen-fallback.sh` to print or exfiltrate secrets, then run the allowlisted wrapper. | The manifest allowlisted the path but did not pin content. | `command_integrity.sha256` pins the script hash and the runner aborts on mismatch. Audit records `command_sha256`. | A malicious actor who can also edit and approve manifest changes can still change policy; require code review for manifest changes. |
| Pass unrelated parent env secrets to the child process. | Child inherited `os.environ.copy()` minus a small blocklist. | Child env is now rebuilt from an inherited-key allowlist plus allowed provider keys and forced flags. | Some inherited utility variables (`PATH`, `HOME`, etc.) remain necessary for execution. |
| Read a different env file such as `secrets.env` or an absolute path outside the repo. | CLI accepted `--env-file`; code checked project containment but not per-script file allowlist. | Manifest now pins `allowed_env_files: [.env]`; absolute/out-of-project paths are rejected. | Symlinked `.env` resolving outside the project is rejected by path resolution. |
| Print exact secret values to stdout/stderr. | Exact loaded values were redacted. | Kept exact-value redaction and added tests covering stdout, stderr, JSON output, and audit. | If a child intentionally prints semantic transformations not covered below, redaction may miss them. |
| Print encoded secret variants. | Base64/hex/urlencoded variants were not explicitly covered. | Runner now redacts exact values plus base64, urlsafe-base64, hex, and URL-encoded variants. | Redaction cannot prove arbitrary transformations safe, e.g. per-character leaks or external network exfiltration. |
| Flood the transcript with huge output. | No output cap. | `max_output_chars` bounds model-visible stdout/stderr and audit records truncation count. | Child can still consume time/resources until timeout. |
| Run without explicit user approval. | Already required `--approve` or approval env flag. | Tests enforce approval requirement. | Approval can become routine; should remain an explicit operator action for high-risk runs. |

## Security boundary statement

The primitive is now a stronger operational boundary, not a sandbox. It protects
against accidental leakage and several obvious malicious mutations of the
approved path. It does not stop a fully privileged malicious agent from ignoring
the primitive and directly reading local files if the outer runtime permits that.

To obtain a cryptographic or OS-enforced boundary, run credentialed smokes in a
separate constrained process/container/VM with:

- read access only to a synthetic env file containing allowlisted keys;
- network egress limited to the provider endpoint;
- a read-only repository mount or an immutable script artifact;
- no access to the operator's broader home directory, shell history, SSH keys,
  cloud credentials, browser profiles, or password stores;
- append-only or external audit logs.

## Tests added or strengthened

- Approval is required.
- Unknown script IDs are rejected.
- Non-allowlisted env-file keys are not passed.
- Non-allowlisted parent env secrets are not inherited.
- Allowlisted parent env values are redacted if printed.
- Non-allowlisted env files and out-of-project env paths are rejected.
- Modified allowlisted scripts fail integrity verification.
- Exact and encoded secret values are redacted.
- Model-visible output is bounded.
- Manifest invariants require command integrity, env-file allowlisting,
  sanitized child environment, redaction, and bounded output.

## Live proof

`qwen-fallback-smoke` passed through the credential-safe primitive with real
repo-local `.env` credentials. The visible output showed the four smoke checks
passing and did not include secret values. The audit row stores key names,
command hash, return code, redaction count, truncation count, and output lengths.
