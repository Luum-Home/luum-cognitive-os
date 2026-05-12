# Cognitive OS Agent Security Research — 2026-05-05

## Executive assessment

Cognitive OS is above-average for an agentic coding harness because it already
has layered hooks, red-team skills, runtime flag documentation, credential-safe
script execution, scanner integrations, and evidence/claim gates. The security
posture is best described as **governed and observable**, not **cryptographically
isolated**. In a `danger-full-access` local runtime, a malicious agent that
ignores policy can still access local files or execute commands unless the host
runtime/sandbox prevents it.

The SO's most important security achievement is that it converts many unsafe
behaviors into governed, testable primitives. Its most important gap is that not
all of those primitives are backed by an OS-level sandbox, network egress policy,
or committed IDE/Claude/Codex deny configuration.

## External research synthesis

### 1. The core risk pattern is the lethal trifecta

Simon Willison's framing is directly applicable: agents become dangerous when
they combine private data, untrusted content, and external communication. The SO
has a `lethal-trifecta-gate`, but the current local runtime can still combine
all three if an operator approves broad shell/network actions or if a script does
so outside the hook path. Source: [Simon Willison, “The lethal trifecta for AI
agents”](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/).

### 2. OpenAI and GitHub explicitly treat internet access as exfil risk

OpenAI Codex cloud disables internet access during the agent phase by default,
warning that enabled access increases risks including prompt injection,
exfiltration of code/secrets, malware/vulnerable dependencies, and license
issues; it recommends minimal domain/method allowlists. Source: [OpenAI Codex
agent internet access](https://developers.openai.com/codex/cloud/internet-access).

GitHub Copilot cloud agent similarly uses a firewall by default to manage data
exfiltration risk, but documents that its firewall has limitations: it applies
only to agent-started processes in the GitHub Actions appliance, not MCP servers
or setup-step processes, and sophisticated attacks may bypass it. Source:
[GitHub Copilot cloud agent firewall](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-firewall).

**Implication for COS:** local `danger-full-access` is weaker than both of these
cloud postures. COS needs a network egress primitive or a documented expectation
that high-risk smokes run in an isolated environment.

### 3. Shell execution must be sandboxed or allow/deny-listed

OpenAI's local shell guide states that arbitrary shell commands are dangerous and
that execution should be sandboxed or protected with strict allow/deny lists.
Source: [OpenAI Local shell guide](https://developers.openai.com/api/docs/05-Methodology/guides/tools-local-shell).

**Implication for COS:** `scripts/security-red-team` and
`scripts/cos-credential-safe-run` are aligned with this guidance, but the rest of
`scripts/` remains a large surface. The next maturity step is a generalized
script risk registry and allowlisted execution profile.

### 4. Claude Code supports file-deny and hook controls, but hooks themselves are privileged

Anthropic documents strict permissions, explicit approval for side-effectful
commands, and `permissions.deny` for sensitive files such as `.env` and
`secrets/**`. It also documents hooks as lifecycle automation, including
PreToolUse blocking and context injection. Sources: [Claude Code
settings](https://code.claude.com/docs/en/settings), [Claude Code
security](https://code.claude.com/docs/en/security), [Claude Code hooks
guide](https://code.claude.com/docs/en/hooks-guide).

**Implication for COS:** repo policy says `.env` is blocked, but committed
`.claude/settings.json` does not currently encode `Read(./.env)` and
`Read(./secrets/**)` denies. Add committed deny rules where compatible, and keep
hook scripts treated as privileged code.

### 5. OWASP maps the same risks: prompt injection, sensitive disclosure, supply chain, excessive agency

OWASP Agentic Security Initiative describes agentic AI as expanding scale,
capabilities, and risk, and provides threat-model-based mitigations. OWASP
LLM06 defines excessive agency as damaging actions caused by unexpected,
ambiguous, or manipulated LLM outputs; mitigation includes secure coding,
input/output sanitization, and SAST/DAST/IAST. Sources: [OWASP Agentic AI
Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/),
[OWASP LLM06 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/).
AWS's agentic AI guidance maps OWASP prompt-injection controls to agent scoping,
threat modeling, prompt-as-code review, evaluation suites, logging, sanitization,
defense-in-depth, and observability. Source: [AWS mapping to OWASP Top 10 for
LLM applications](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-security/owasp-top-ten.html).

**Implication for COS:** current controls cover many OWASP classes, but the
`/security-red-team` score should become an OWASP/ASI mapping, not just a local
custom score.

### 6. MCP is a major control-plane risk

Official MCP security best practices recommend highlighting dangerous command
patterns, warning about sensitive locations, reminding users that MCP servers run
with the same privileges as the client, and executing MCP server commands in a
sandboxed environment with minimal default privileges. Source: [MCP Security
Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices).
MCP authorization guidance relies on OAuth 2.1, Protected Resource Metadata, and
token validation for HTTP-based transports. Source: [MCP Authorization
specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization).

Invariant Labs demonstrates MCP tool poisoning: hidden instructions in tool
descriptions can induce sensitive file access, data transmission, and behavior
hijacking. Source: [Invariant Labs MCP tool poisoning](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks).
Trail of Bits highlights conversation-history theft, insecure credential storage,
and ANSI terminal deception in MCP ecosystems. Source: [Trail of Bits MCP
security](https://www.trailofbits.com/mcp/).

**Implication for COS:** `mcp-scan.sh` is directionally right but insufficient if
not installed/enforced. Add MCP trust-on-first-use pinning, tool-description hash
recording, ANSI sanitization, and credential-store checks.

### 7. Real-world coding agents have had MCP/prompt-injection RCE chains

A Cursor advisory describes arbitrary code execution through prompt injection via
MCP special files: an attacker could chain indirect prompt injection to write MCP
configuration and trigger code execution; remediation blocked writing sensitive
MCP files without approval. Source: [Cursor GHSA-4cxx-hrm3-49rm](https://github.com/cursor/cursor/security/advisories/GHSA-4cxx-hrm3-49rm).

**Implication for COS:** add a protected-file class for MCP configs, rules files,
hook configs, and agent instructions. Treat writes to `.cursor/`, `.claude/`,
`.codex/`, MCP configs, and rules as high-risk operations requiring explicit
approval and red-team tests.

### 8. Recent research says prompt injection is architectural, not just filtering

A 2026 SoK on prompt injection in agentic coding assistants argues that coding
agents with tools, file systems, shell access, and MCP expose critical security
vulnerabilities; it reports a taxonomy spanning delivery vectors, modalities,
and propagation behaviors, and argues for architectural mitigations rather than
ad-hoc filtering. Source: [arXiv:2601.17548](https://arxiv.org/abs/2601.17548).
Another 2026 study evaluates prompt injection/tool poisoning across MCP clients
including Claude Code, Cursor, Cline, Continue, Gemini CLI, and Langflow, noting
differences in static validation, parameter visibility, warnings, sandboxing, and
audit logging. Source: [arXiv:2603.21642](https://arxiv.org/abs/2603.21642).

**Implication for COS:** scanner hooks are useful, but durable security needs
least privilege, sandboxing, explicit trust boundaries, integrity pins, and
observable audit.

## COS control matrix

| Risk | Current COS controls | Current strength | Gap |
|---|---|---:|---|
| Secret file exfiltration | Blocked-path policy, credential-safe runner, secret detector, confidentiality enforcer | Medium | No OS-level filesystem deny in current Codex runtime; committed `.claude/settings.json` lacks explicit `.env`/`secrets` denies. |
| Prompt injection | Parry, Aguara, lethal-trifecta gate, `/red-team`, `/memory-scan` | Medium | Tools are optional/advisory; need tests for hidden Markdown/ANSI/base64/tool-description injection. |
| MCP poisoning | `mcp-scan.sh`, host CLI bridge contract, docs | Medium-low | Need trust-on-first-use, MCP config write guard, ANSI sanitization, MCP credential storage checks. |
| Shell command abuse | Destructive blockers, rate limiter, credential-safe allowlist | Medium | No universal shell sandbox/egress policy; many scripts remain broad. |
| Runtime bypass flags | Runtime env manifest and docs | Medium | Need active-dangerous-flag detector and severity metadata. |
| False-done claims | redteam-harness, plan/orchestrator claim gates, DoD gates | High | Expand beyond ADR-105 verbs to security claims. |
| Supply chain | supply-chain-defense rule, Semgrep, install-surface docs | Medium | Optional installers still use `npx`, `pip`, `npm`, `curl`-like flows; need SBOM/provenance lane. |
| Provider dispatch abuse | LLM dispatch docs, Qwen smoke, metrics | Medium | Need adversarial tests for fake provider metrics and provider-output trust boundaries. |
| Memory poisoning | memory-scan, Engram governance | Medium | Need automated persistence poisoning tests and secret-in-memory audit. |
| DoS/cost abuse | rate limiter, resource checks, budget rules | Medium | Need runaway-agent and huge-output tests across scripts/hooks. |

## Security posture verdict

| Dimension | Score | Rationale |
|---|---:|---|
| Governance coverage | 86 | Many policies, hooks, skills, and docs exist. |
| Secret handling | 72 | Strong new credential-safe path, but local runtime lacks hard filesystem sandbox. |
| MCP/tool safety | 62 | Good detection intent; needs stronger enforcement and pinning. |
| Shell/process safety | 58 | Script surface is large; partial allowlisting only. |
| Auditability | 78 | JSONL metrics and reports exist; need tamper-resistance and redaction tests everywhere. |
| Test coverage | 70 | Red-team harness exists; security-specific tests are just starting. |
| Operational ergonomics | 76 | Good runbooks and skills; risk of bypass fatigue remains. |
| Isolation strength | 45 | The critical weakness: no cryptographic/OS sandbox in current local runtime. |

**Overall security confidence:** `68/100` for local `danger-full-access` usage;
`80+/100` is plausible if paired with deny settings, network egress controls,
MCP pinning, and a constrained runner/container for credentialed workflows.

## Prioritized backlog

### P0 implementation status — 2026-05-05 follow-up

The initial P0 boundary-enforcement pass is now implemented as repository
contracts and hooks:

- committed `.claude/settings.json` `permissions.deny` entries for `.env`,
  `.env.*`, `secrets/**`, key/cert files, `.git/config`, and related credential
  paths;
- `hooks/protected-config-write-guard.sh` plus
  `manifests/protected-config-write-policy.yaml` for `.claude/**`,
  `.codex/**`, `.cursor/**`, MCP configs, hooks, rules, skill frontmatter, and
  security manifests;
- `hooks/network-egress-guard.sh`, `scripts/network_egress_guard.py`, and
  `manifests/network-egress-policy.yaml` for exfiltration-shaped shell commands;
- `scripts/mcp_tofu_audit.py` plus `manifests/mcp-trust-pins.yaml` for MCP
  trust-on-first-use fingerprinting without hashing secret values;
- `tests/security/test_boundary_enforcement_p0.py` adversarial tests for the
  deny settings, protected config writes, network exfil commands, and MCP TOFU
  behavior.

The P0 items below remain the strategic backlog category, but their first
enforceable implementation is now present.

### P1/P2 implementation status — 2026-05-05 follow-up

The next adversarial controls are now present as executable primitives and tests:

- `scripts/dangerous_env_flag_detector.py` and
  `hooks/dangerous-env-flag-detector.sh` detect active high-risk runtime flags
  such as hook suppressions and safety bypasses;
- `scripts/network_sandbox_run.py` provides a real no-network execution boundary
  when Docker is available via `docker run --network none`, with dry-run support
  for CI/contract tests;
- `scripts/mcp_tofu_audit.py` now includes MCP tool-description hashes in server
  fingerprints, so hidden tool-description drift is detectable without hashing
  secret values;
- `scripts/metrics_tamper_audit.py` detects malformed or suspicious metrics rows;
- `scripts/provider_spoof_audit.py` detects offline/mock rows that claim live
  provider delegation;
- `tests/security/test_adversarial_p1_p2.py` covers dangerous flags, network
  sandbox command shape, MCP tool-description drift, ANSI/invisible Unicode,
  symlink mutation, metrics tampering, provider spoofing, and egress exfil
  analysis.

### P0 — Boundary hardening

1. Commit explicit sensitive-file deny configuration for Claude/Codex-compatible
   runtimes where supported: `.env`, `.env.*`, `secrets/**`, credential files,
   MCP config secrets, SSH keys.
2. Add a network egress primitive: default deny for high-risk smokes; explicit
   allowlist for provider endpoints; block POST to arbitrary domains.
3. Add protected config write guard for `.claude/`, `.codex/`, `.cursor/`, MCP
   config files, hooks, rules, and skill frontmatter.
4. Add MCP trust-on-first-use manifest: server command, args, tool descriptions,
   hashes, credential source, last-reviewed date.

### P1 — Automated adversarial tests

5. Expand `tests/security/` with fake `.env` exfil probes, MCP config write
   probes, ANSI/invisible Unicode prompt injection, and encoded-output leaks.
6. Add active dangerous env flag detector for `DISABLE_HOOK_*`,
   `COS_ALLOW_DIRECT_MAIN`, `COS_ALLOW_DESTRUCTIVE_GIT`, and
   `COS_ALLOW_CREDENTIAL_SAFE_ENV`.
7. Add audit-log redaction contracts for every hook/script that writes metrics.
8. Add provider dispatch adversarial tests: fake metrics, provider spoofing,
   fallback-kill-switch bypass, model-output trust confusion.

### P2 — Supply-chain and scanner enforcement

9. Replace optional scanner silent skips with posture reporting: installed,
   missing, disabled, skipped, last-run.
10. Add package-install provenance checks for `npx`, `pip`, `npm`, curl-like
    scripts, and MCP server installers.
11. Add Semgrep/Garak/Promptfoo lanes as explicit opt-in deep tests, referenced
    by `/security-red-team` output.

### P3 — Scoring maturity

12. Map `/security-red-team` findings to OWASP LLM Top 10 / OWASP ASI / MCP
    security categories.
13. Generate `manifests/security-control-ledger.yaml` from local evidence.
14. Track score trend over time in metrics.

## Bottom line

Cognitive OS has unusually rich governance for an AI coding-agent harness. The
main risk is not lack of security concepts; it is that many controls are still
policy/hook-level controls running inside a privileged local runtime. The next
step is to convert the strongest controls into host-enforced boundaries:
filesystem deny, network egress allowlists, MCP pinning, protected config write
guards, and constrained execution for credentialed operations.
