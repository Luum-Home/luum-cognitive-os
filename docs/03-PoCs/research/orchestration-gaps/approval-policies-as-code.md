# Approval Policies as Code: Evaluating Consolidation of COS Hook-Based Policy

**Document type:** Research  
**Date:** 2026-05-06  
**Scope:** Cognitive OS (COS) — hook-as-policy → manifest-as-policy migration  
**Status:** Draft — for architectural review  
**Word count:** ~3,200

---

## Executive Summary

Cognitive OS currently distributes policy enforcement across 219 shell scripts acting as hooks, of which approximately 61 contain allow/deny/block logic. Contemporary agent runtimes — Codex, Claude Code, OpenCode — are converging on declarative permission manifests, while the infrastructure world offers mature policy-as-code frameworks (OPA/Rego, Cedar, Casbin, Cerbos) that could replace the imperative hook layer. This document evaluates each approach, performs a schema comparison, and assesses the migration path for COS.

---

## 1. Problem Statement

COS policy is distributed across four surfaces:

| Surface | Policy artifacts | Enforcement style |
|---|---|---|
| `hooks/*.sh` (219 files, 61 with block logic) | Shell scripts with embedded rules | Imperative, procedural |
| `.cognitive-os/content-policy.yaml` | YAML term/pattern lists | Declarative data, imperative enforcement |
| `.cognitive-os/test-resource-policy.yaml` | YAML lane resource rules | Declarative, consumed by test harness |
| `.claude/settings.json` (185 hook references) | JSON rule arrays + hook wiring | Declarative syntax, imperative delegation |

The hooks implement concerns ranging from `blast-radius` (advisory) and `confidentiality-enforcer` (blocking) to `clarification-gate` and `content-policy`. They share no common schema. Policy intent is encoded in bash logic, making it untestable without running the full Claude Code harness, unreadable by non-engineers, and unmergeable with policies from other runtimes.

The core question: can this be consolidated into a manifest-driven policy layer, and if so, which schema/language is appropriate?

---

## 2. Contemporary Runtime Policy Schemas

### 2.1 Codex `approval-policy` (TOML, OpenAI)

Codex uses a TOML-based configuration at `~/.codex/config.toml` and `.codex/config.toml` (project override). The approval model has three named modes:

- **`untrusted`** — only known-safe read-only operations auto-run; all others prompt
- **`on-request`** — model decides when to escalate (default)
- **`never`** — no approval prompts (headless/CI mode)

A granular mode provides categorical control without per-tool rules:

```toml
approval_policy = { granular = {
  sandbox_approval = true,     # escalation requests
  rules = true,                # exec-policy rule triggers
  mcp_elicitations = true,     # MCP tool prompts
  request_permissions = false, # permission-tool prompts (auto-deny)
  skill_approval = false       # skill script prompts (auto-deny)
} }
```

A separate `requirements.toml` layer provides org-level enforcement that users cannot override:

```toml
[rules.prefix_rules]
pattern = { any_of = ["curl", "wget"] }
decision = "prompt"     # or "forbidden"
justification = "Network egress requires approval"
```

An `approvals_reviewer = "auto_review"` option routes flagged actions through a reviewer subagent that checks for data exfiltration, credential probing, persistent security weakening, and destructive actions — moving policy evaluation from shell scripts to model judgment.

**Assessment:** The Codex schema is the most ergonomic for teams already using TOML. It supports categorical allow/prompt/forbidden decisions and org-level enforcement via `requirements.toml`. However, it does not support rich condition expressions (no attribute matching, no resource-path patterns) and is limited to Codex's own lifecycle events.

### 2.2 Claude Code `settings.json` (JSON, Anthropic)

Claude Code's permission model is JSON-based and uses a three-array structure:

```json
{
  "permissions": {
    "deny":  ["Bash(git push *)", "Read(.env)"],
    "ask":   ["Bash(rm *)"],
    "allow": ["Bash(npm run *)", "Read", "Grep"]
  }
}
```

Evaluation order: **deny → ask → allow**, first match wins. Deny rules set in managed settings (`allowManagedPermissionRulesOnly: true`) cannot be overridden at any lower level.

Rule specifiers support:
- Exact match: `Bash(npm run build)`
- Wildcard: `Bash(npm run *)`, `Edit(/src/**/*.ts)`
- Domain filter: `WebFetch(domain:github.com)`
- MCP tool pattern: `mcp__puppeteer__*`
- Subagent: `Agent(Explore)`

Hooks extend permission evaluation via `PreToolUse` (blocking), `PostToolUse` (non-blocking), and `PermissionRequest` (interactive approval override). Hook decisions are subordinate to deny rules — a hook returning `allow` does not override a matching `deny` rule.

**Assessment:** The most composable of the runtime schemas. The deny-first evaluation model, managed settings hierarchy, sandboxing integration, and 21 lifecycle events make it well-suited for COS. However, it cannot express attribute-based conditions (no `if principal.region == "eu"` style guards), requires shell scripts for complex logic, and offers no formal policy language for auditors.

### 2.3 OpenCode Permission Frontmatter (JSON/YAML, SST)

OpenCode resolves permissions to `allow | ask | deny` at the tool level with glob-based matching and last-rule-wins semantics:

```json
{
  "permission": {
    "bash": {
      "*":        "ask",
      "git *":    "allow",
      "rm *":     "deny"
    },
    "edit":       "deny",
    "external_directory": { "~/projects/**": "allow" }
  }
}
```

Agents defined as Markdown files can override global config with YAML frontmatter:

```yaml
---
description: Code review without edits
mode: subagent
permission:
  edit: deny
  bash: ask
---
```

This is the only runtime that embeds per-agent policies in agent definition files, enabling the policy and the agent to travel together — analogous to Docker's `EXPOSE` declarations or Kubernetes resource limits embedded in pod specs.

**Assessment:** OpenCode's frontmatter model is the most ergonomic for per-agent policy composition. The last-rule-wins semantics (vs. Claude Code's first-match deny-first) create a footgun for complex policies, but the approach aligns well with COS's skill/agent model where each skill could declare its required permissions.

---

## 3. Infrastructure Policy-as-Code Frameworks

### 3.1 OPA / Rego (CNCF, Open Source)

Open Policy Agent is a general-purpose policy engine decoupling policy decision from enforcement. Services query OPA via REST (`POST /v1/data/<path>`) with structured JSON input; OPA evaluates Rego policies and returns structured decisions.

A Rego policy for agent tool authorization looks like:

```rego
package agent.authz
default allow := false

allow if {
  input.principal.role == "developer"
  input.tool_name != "Bash"
}

allow if {
  input.tool_name == "Bash"
  regex.match(`^git (status|log|diff)`, input.tool_input.command)
}
```

**Strengths:** Full boolean logic, iteration, aggregation, cross-resource joins, bundle distribution for centralized policy management, WebAssembly compilation for edge evaluation, and the broadest ecosystem of cloud-native integrations. OPA/Rego is 42–60x slower than Cedar for simple decisions but more expressive for complex multi-factor policies.

**Weaknesses:** Rego is a specialized language with a steep learning curve. It lacks a friendly type system. Mixed declarative/imperative mental model confuses newcomers. For simple allow/deny tables it is dramatically over-engineered.

### 3.2 Cedar Policy Language (AWS, Apache 2.0)

Cedar is a purpose-built authorization DSL with a formal verification foundation. AWS uses it in Amazon Bedrock AgentCore to control tool access:

```cedar
permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"RefundTool__process_refund",
  resource == AgentCore::Gateway::"arn:aws:..."
)
when {
  principal.hasTag("username") &&
  principal.getTag("username") == "John" &&
  context.input.amount < 500
};
```

Evaluation is **forbid-overrides-permit with default deny**: any matching `forbid` produces DENY; at least one matching `permit` with no `forbid` produces ALLOW; no match produces DENY.

**Strengths:** Formally verified (Cedar's type system is verified by automated reasoning), readable by security auditors, 42–60x faster than Rego on simple decisions, native support for entity hierarchies and tag-based attributes. The `when` clause can reference tool input parameters directly — enabling `context.input.amount < 500` as a policy condition.

**Weaknesses:** AWS-ecosystem alignment makes it feel heavy for non-AWS deployments. The entity model (principal/action/resource triple) requires upfront schema design. No bundle distribution mechanism outside AWS Verified Permissions.

### 3.3 Casbin PERM Metamodel

Casbin abstracts authorization into four components (Policy, Effect, Request, Matchers) defined in a `.conf` file:

```ini
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

For AI agents, Casbin's ABAC mode handles MCP tool authorization with multi-dimensional context:

```python
# Policy rule: agent=rag-agent, tool=CustomerData, region=eu, time=business_hours
e.enforce("rag-agent", "CustomerData", "read", {"region": "eu", "time": "09:00"})
```

The PERM metamodel supports RBAC, ABAC, ReBAC, and hybrid models. Multi-agent delegation chains can be expressed as role hierarchies with depth limits.

**Assessment:** Casbin is the most flexible in terms of access control models and has edge deployment support (WebAssembly + V8 isolates). However, the `.conf` metamodel adds indirection that is unusual for developers coming from JSON/YAML-centric tooling.

### 3.4 AWS IAM-Style Policies

AWS IAM's JSON structure is the most widely understood policy schema in infrastructure:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["agent:UseTool"],
    "Resource": ["arn:cos:tools:*:*:bash"],
    "Condition": {
      "StringLike": {"cos:command": "git *"}
    }
  }]
}
```

IAM's principal/action/resource/condition quad maps naturally to agent tool calls. Several governance toolkits (notably the Microsoft Agent Governance Toolkit and OSSA) use ARN-like resource naming for agent tools, extending IAM semantics to the agent domain.

**Assessment:** The pattern is well understood and toolable, but IAM JSON is verbose (YAML doesn't help much) and the condition expression syntax is unintuitive. Best suited for organizations already running IAM-heavy infrastructure.

### 3.5 HashiCorp Sentinel / OPA Gatekeeper (Cloud PaC)

Sentinel (HashiCorp-native, HCP Terraform integration) and OPA Gatekeeper (Kubernetes admission control) represent mature PaC at the infrastructure tier. Both enforce policies at "apply time" in CI/CD pipelines — analogous to COS's `PreToolUse` hooks but operating at the infrastructure provisioning level rather than the agent action level.

The Gatekeeper pattern is relevant as an architectural template: Constraint Templates define the policy logic (Rego) while Constraint resources define parameters. This separation of policy definition from policy instantiation is applicable to agent policy design.

### 3.6 Cerbos (Open Source, YAML-native)

Cerbos externalizes authorization into a Policy Decision Point (PDP) queried over HTTP:

```yaml
apiVersion: api.cerbos.dev/v1
resourcePolicy:
  resource: "agent_tool"
  version: "default"
  rules:
    - actions: ["execute"]
      effect: EFFECT_ALLOW
      roles: ["developer"]
      condition:
        match:
          all:
            of:
              - expr: "request.resource.attr.tool_name.matches('^git ')"
              - expr: "request.resource.attr.destructive == false"
```

Cerbos's `principal/resource/action` model with YAML conditions is the most ergonomic for security teams unfamiliar with Rego or Cedar. The PDP pattern also enables real-time policy revocation ("agent kill switch") — a concern that COS's static hook model cannot address.

---

## 4. Schema Comparison

| Feature | Codex TOML | Claude Code JSON | OpenCode Frontmatter | OPA/Rego | Cedar | Casbin PERM | Cerbos YAML | AWS IAM |
|---|---|---|---|---|---|---|---|---|
| **Format** | TOML | JSON | JSON/YAML | Rego DSL | Cedar DSL | .conf + CSV | YAML | JSON |
| **Default posture** | on-request | deny-first | last-rule-wins | undefined | deny | configurable | deny | deny |
| **Condition expressions** | None | None | Glob only | Full logic | Attribute tags | ABAC matchers | CEL expressions | Condition operators |
| **Attribute-based decisions** | No | No | No | Yes | Yes (tags) | Yes | Yes | Yes |
| **Per-agent policy** | No | No | Frontmatter | External query | External policy | External query | External query | IAM roles |
| **Hierarchical inheritance** | Managed override | Managed > CLI > Local > Project > User | Agent merges global | Bundle namespaces | Entity hierarchy | Role inheritance | Derived roles | IAM hierarchy |
| **Policy distribution** | Project file | MDM / settings.json | opencode.json | Bundle API | AWS Verified Perms | File / DB | PDP HTTP API | IAM JSON |
| **Runtime revocation** | No | No | No | Bundle reload | AWS AVP | File reload | PDP hot reload | IAM policy update |
| **Audit trail** | No | No | No | Decision logs | AVP CloudTrail | Adapter logging | Decision API | CloudTrail |
| **Formal verification** | No | No | No | No | Yes (formally verified) | No | No | No |
| **Learning curve** | Low | Low | Low | High | Medium | Medium | Low-Medium | Medium |
| **COS integration effort** | Medium | Low (native) | Medium | High | High | High | Medium | High |

---

## 5. Expressiveness vs. Ergonomics Tradeoff

The policy landscape forms a clear spectrum:

```
Ergonomic                                        Expressive
    |                                                |
OpenCode   Claude Code   Codex   Cerbos   Cedar   OPA/Rego
frontmatter  settings.json  TOML  YAML   DSL      Rego
    |                                                |
Simple glob    Deny/ask/allow   ABAC      Full boolean logic
matching       with hierarchy   conditions  + iteration + joins
```

**Key finding:** For the 80% case — blocking specific bash commands, restricting file access, controlling subagent spawning — Claude Code's `settings.json` deny/ask/allow arrays with glob patterns are sufficient and already integrated. The remaining 20% — attribute-based decisions ("block if blast radius > threshold"), time-bounded policies, multi-agent delegation chains, real-time revocation — require a richer model.

The optimal architecture for COS is therefore **layered**: keep the Claude Code native layer for static, structural policies (what tools are categorically allowed) and add a lightweight PaC layer for dynamic, contextual policies (when and under what conditions).

---

## 6. COS Hook-as-Policy → Manifest-as-Policy: Migration Path

### 6.1 Current State Taxonomy

COS's 61 policy-bearing hooks fall into five functional categories:

| Category | Example hooks | Migration target |
|---|---|---|
| **Structural allow/deny** | `destructive-rm-blocker.sh`, `confidentiality-enforcer.sh`, `protected-config-write-guard.sh` | Claude Code `permissions.deny` array |
| **Context-injecting guards** | `blast-radius.sh`, `context-budget-meter.sh`, `clarification-gate.sh` | Claude Code `permissions.ask` + `additionalContext` |
| **Quality gates (blocking)** | `completion-gate.sh`, `confidence-gate.sh`, `clarification-interceptor.sh` | Claude Code `Stop` hook (exit 2) |
| **Data-driven policy** | `content-policy.sh` (reads `.cognitive-os/content-policy.yaml`) | Native YAML policy with hook as evaluator, or Cerbos rule |
| **Complex conditional** | `adaptive-bypass.sh`, `dispatch-gate.sh`, `agent-quota-redirect.sh` | OPA or Casbin sidecar, queried from thin hook shim |

### 6.2 Migration Phases

**Phase 1: Extract structural allow/deny to settings.json (Low effort, immediate)**

Hooks that implement categorical blocking (patterns the agent must never execute regardless of context) are direct candidates for `permissions.deny` entries. Examples:

- `destructive-rm-blocker.sh` → `"deny": ["Bash(rm -rf *)", "Bash(rm -r /*)"]`
- `direct-main-guard.sh` → `"deny": ["Bash(git push origin main *)"]`
- `protected-config-write-guard.sh` → `"deny": ["Edit(//.claude/settings.json)", "Edit(//.claude/hooks/*)"]`

This removes shell execution overhead and makes policy visible via `/permissions` UI. Estimated scope: 10–15 hooks.

**Phase 2: Consolidate data-driven policies to YAML manifests (Medium effort)**

`content-policy.sh` already reads `.cognitive-os/content-policy.yaml` — the separation of data from enforcement is correct. The gap is that the hook is still imperative Bash. Phase 2 proposes a thin, generic `policy-eval.sh` hook that:

1. Reads a `policies/*.yaml` directory (one file per concern)
2. Evaluates rules declaratively using `yq` or a lightweight Python evaluator
3. Returns structured `permissionDecision` JSON

Policy YAML format (proposed COS schema):

```yaml
# policies/content-policy.yaml
version: 1
id: content-policy
description: Block prohibited patterns in edited files
trigger:
  events: [PostToolUse]
  tools: [Edit, Write]
rules:
  - id: no-credential-leak
    match:
      tool: Edit
      file_pattern: "**/*.ts"
      content_regex: "(AWS_SECRET|API_KEY|password =)"
    effect: deny
    reason: "Credential leak detected in {file_path}"
  - id: no-flattery
    match:
      tool: Write
      content_regex: "^(Great|Sure|Of course|Absolutely)"
    effect: deny
    reason: "Sycophantic opener blocked"
```

Estimated scope: 8–12 hooks that currently read external config files.

**Phase 3: Context-injecting guards → settings.json ask + additionalContext (Medium effort)**

`blast-radius.sh` is advisory-only (exit 0). It could be expressed as a `PreToolUse` hook that returns `permissionDecision: "ask"` with an `additionalContext` payload when blast radius exceeds a threshold. However, the current hook's value is the _advisory message_, not the block. This is already the correct separation.

The migration here is not to eliminate the hook but to make its threshold configurable in a manifest:

```yaml
# policies/blast-radius.yaml
version: 1
id: blast-radius
trigger:
  events: [PreToolUse]
  tools: [Agent]
thresholds:
  warn: 50
  block: 200
```

The hook becomes a thin evaluator that reads this manifest rather than embedding thresholds in shell code.

**Phase 4: Complex conditional → OPA sidecar (High effort, optional)**

Hooks like `adaptive-bypass.sh`, `dispatch-gate.sh`, and `agent-quota-redirect.sh` implement multi-variable logic: phase × capability level × session state → routing decision. These cannot be expressed in static allow/deny tables.

For these, the recommended migration is a co-located OPA sidecar:

1. Launch `opa run --server --addr 127.0.0.1:8181 policies/` as a `SessionStart` hook
2. Replace complex Bash logic with `curl -s -X POST http://127.0.0.1:8181/v1/data/cos/decision -d "$INPUT"` calls
3. Rego policies live in `policies/*.rego`, version-controlled alongside skills

This approach is **optional and high-effort**. It is only justified if COS needs cross-agent policy inheritance, formal auditability, or real-time policy revocation. For a single-operator OS, the Phase 1–3 migration delivers 80% of the value.

### 6.3 What Cannot Be Migrated to Manifest-as-Policy

Several COS hooks implement behavior that is inherently imperative and must remain as hooks:

| Hook | Reason it stays imperative |
|---|---|
| `auto-rollback-trigger.sh` | Reads git state, executes rollback commands — side-effecting action, not a policy decision |
| `crash-recovery.sh` | State machine with filesystem mutation |
| `agent-checkpoint.sh` | File I/O + session state management |
| `context-budget-meter.sh` | Real-time counter with in-memory state across calls |
| `agent-qwen-bridge.sh` | Router that spawns alternate LLM processes |

The criterion: if a hook's output is a **decision** (allow/deny/ask + optional context injection), it is a policy hook and belongs in a manifest. If its output is a **side effect** (write to disk, spawn process, mutate state), it must remain imperative.

---

## 7. Risks and Trade-offs

### 7.1 Expressiveness Loss

Claude Code's `settings.json` deny/ask/allow syntax cannot express:
- Attribute conditions (`deny if file_size > 10MB`)
- Time bounds (`allow only during business hours`)
- Rate-based decisions (`ask if > 3 identical Bash calls in 60s`)
- Cross-tool dependencies (`deny Edit if Read of same file failed`)

Moving to a YAML manifest layer preserves these in structured data but still requires hook code for evaluation.

### 7.2 Debuggability Regression

Shell hooks are trivially debuggable: `echo '{}' | .claude/hooks/blast-radius.sh`. A Rego/OPA or Cerbos PDP adds a service dependency to the debug path. This is a real operational cost in a single-operator OS.

Mitigation: the YAML-manifest + thin-evaluator approach (Phase 1–3) preserves local debuggability. The OPA sidecar (Phase 4) should be opt-in.

### 7.3 Hook Ordering Guarantees

COS hooks fire in configuration order. A policy manifest layer evaluated by a single generic hook loses per-hook ordering. This matters for hooks like `confidentiality-enforcer.sh` (must fire before `auto-refine.sh` can modify output). Phase 2 migration must preserve ordering through explicit `priority` fields in policy YAML.

### 7.4 Performance Budget

At 61 policy hooks × average 50ms/hook, the current worst-case `PreToolUse` budget is ~3 seconds. Consolidating to a single generic evaluator drops this substantially (one process spawn instead of 61). The OPA HTTP query path adds ~5ms per decision. Both represent improvements.

---

## 8. Recommendations

### Recommendation 1: Adopt a two-layer architecture

Keep the Claude Code native permission layer for structural, categorical policies. Add a lightweight YAML policy manifest layer (COS-native schema) for data-driven and threshold-based policies. Reserve OPA/Cedar for future multi-tenant or enterprise use cases.

**Rationale:** The native layer has zero overhead and is visible in the `/permissions` UI. The YAML manifest layer eliminates the current anti-pattern of embedding thresholds and term lists inside Bash scripts. OPA/Cedar add dependencies and operational complexity that are not yet justified for a single-operator OS.

### Recommendation 2: Migrate 15–20 structural deny/ask hooks to settings.json in a single sprint

Start with hooks that implement categorical blocking without external data dependencies. This yields the largest ergonomics gain (visible in `/permissions` UI, no shell execution) at the lowest migration risk.

**Target hooks for Phase 1:** `destructive-rm-blocker.sh`, `direct-main-guard.sh`, `protected-config-write-guard.sh`, `git-direct-push-guard.sh`, and any hook that implements a single-regex block against a specific command or file path.

### Recommendation 3: Introduce a `policies/` directory with versioned YAML schema

Define a COS-native policy schema (version, id, trigger, rules[]) consumed by a generic `policy-eval.sh` hook. Migrate `content-policy.sh`, `blast-radius.sh` thresholds, and `clarification-gate.sh` configuration to this format. The YAML files become the single source of truth; the hook becomes a stateless evaluator.

This approach does not require OPA, Cedar, or any external dependency. It retains local debuggability and follows the same data-driven pattern COS already uses for `content-policy.yaml` and `test-resource-policy.yaml`.

---

## Sources

1. [Agent approvals & security – Codex | OpenAI Developers](https://developers.openai.com/codex/agent-approvals-security)
2. [Configuration Reference – Codex | OpenAI Developers](https://developers.openai.com/codex/config-reference)
3. [Configure permissions – Claude Code Docs](https://code.claude.com/docs/en/permissions)
4. [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)
5. [Configure permissions – Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/permissions)
6. [Permissions – OpenCode](https://opencode.ai/docs/permissions/)
7. [Open Policy Agent – Integration Guide](https://www.openpolicyagent.org/docs/integration)
8. [Understanding Cedar policies – Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-understanding-cedar.html)
9. [Casbin in 2025: Authorization for the AI Agent Era](https://casbin.apache.org/blog/casbin-2025-ai-agent-era/)
10. [AI Agent Governance Toolkit – Microsoft (GitHub)](https://github.com/microsoft/agent-governance-toolkit)
11. [Hooks: The Enforcement Layer That Turns Agent Policy Into Agent Fact](https://ranjankumar.in/hooks-policy-as-code-agent-enforcement)
12. [AI Agent Hooks and Middleware: Runtime Behavior Control Patterns – Zylos Research](https://zylos.ai/research/2026-03-27-ai-agent-hooks-middleware-runtime-behavior-control)
13. [Trustworthy AI Agents: Policy-as-Code Enforcement – Sakura Sky](https://www.sakurasky.com/blog/missing-primitives-for-trustworthy-ai-part-4/)
14. [OPA vs Sentinel: Enterprise Policy as Code Comparison – policyascode.dev](https://policyascode.dev/guides/opa-vs-sentinel-enterprise/)
15. [Introduction to Policy as Code – CNCF](https://www.cncf.io/blog/2025/07/29/introduction-to-policy-as-code/)
16. [Top 12 Policy as Code Tools – Spacelift](https://spacelift.io/blog/policy-as-code-tools)
17. [AI Agent Authorization & Access Control – Cerbos](https://www.cerbos.dev/features-benefits-and-use-cases/agentic-authorization)
18. [Agentic Configuration Manifests – EmergentMind](https://www.emergentmind.com/topics/agentic-configuration-manifests)
19. [OSSA: AI Agent Manifest Spec](https://openstandardagents.org/)
20. [Dynamic Authorization for AI Agents – Cerbos Blog](https://www.cerbos.dev/blog/dynamic-authorization-for-ai-agents-guide-to-fine-grained-permissions-mcp-servers)
