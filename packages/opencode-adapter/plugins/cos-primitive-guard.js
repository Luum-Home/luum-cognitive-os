// SCOPE: both
// OpenCode project plugin: Cognitive OS primitive guard.
// Loaded from .opencode/plugins/cos-primitive-guard.js by OpenCode.
// Emits content-free primitive-interventions rows and throws for blocking actions.

import { mkdirSync, appendFileSync, statSync, existsSync, readFileSync } from "node:fs"
import { join, relative } from "node:path"
import { spawnSync } from "node:child_process"

const SIGNED_PRIMITIVES = [
  "destructive-git-blocker",
  "destructive-rm-blocker",
  "reinvention-check",
  "large-file-advisor",
  "skill-router",
  "aci-observation-capture",
  "adr-relevance-suggest",
  "adr-section-validator",
  "agent-bash-cwd-enforcer",
  "agent-control-inbound-guard",
  "auto-rollback-trigger",
  "auto-verify",
  "claim-validator",
  "confidence-gate",
  "confidentiality-enforcer",
  "content-policy",
  "context-watchdog",
  "cosd-auth-guard",
  "dispatch-gate",
  "doc-sync-detector",
  "direct-main-guard",
  "secret-detector",
  "protected-config-write-guard",
  "network-egress-guard",
  "token-budget-monitor",
  "prompt-quality-llm",
  "scope-creep-detector",
  "result-truncator",
  "private-mode-gate",
  "trust-score-validator",
]

const PRIMITIVE_SOURCE = Object.freeze({
  "destructive-git-blocker": "hooks/destructive-git-blocker.sh",
  "destructive-rm-blocker": "hooks/destructive-rm-blocker.sh",
  "reinvention-check": "hooks/reinvention-check.sh",
  "large-file-advisor": "hooks/large-file-advisor.sh",
  "skill-router": "hooks/skill-router-bash-gate.sh",
  "aci-observation-capture": "hooks/aci-observation-capture.sh",
  "adr-relevance-suggest": "hooks/adr-relevance-suggest.sh",
  "adr-section-validator": "hooks/adr-section-validator.sh",
  "agent-bash-cwd-enforcer": "hooks/agent-bash-cwd-enforcer.sh",
  "agent-control-inbound-guard": "hooks/agent-control-inbound-guard.sh",
  "auto-rollback-trigger": "hooks/auto-rollback-trigger.sh",
  "auto-verify": "hooks/auto-verify.sh",
  "claim-validator": "hooks/claim-validator.sh",
  "confidence-gate": "hooks/confidence-gate.sh",
  "confidentiality-enforcer": "hooks/confidentiality-enforcer.sh",
  "content-policy": "hooks/content-policy.sh",
  "context-watchdog": "hooks/context-watchdog.sh",
  "cosd-auth-guard": "hooks/cosd-auth-guard.sh",
  "dispatch-gate": "hooks/dispatch-gate.sh",
  "doc-sync-detector": "hooks/doc-sync-detector.sh",
  "direct-main-guard": "hooks/direct-main-guard.sh",
  "secret-detector": "hooks/secret-detector.sh",
  "protected-config-write-guard": "hooks/protected-config-write-guard.sh",
  "network-egress-guard": "hooks/network-egress-guard.sh",
  "token-budget-monitor": "hooks/token-budget-monitor.sh",
  "prompt-quality-llm": "hooks/prompt-quality-llm.sh",
  "scope-creep-detector": "hooks/scope-creep-detector.sh",
  "result-truncator": "hooks/result-truncator.sh",
  "private-mode-gate": "hooks/private-mode-gate.sh",
  "trust-score-validator": "hooks/trust-score-validator.sh",
})

function projectRoot(ctx) {
  return process.env.COGNITIVE_OS_PROJECT_DIR || process.env.OPENCODE_PROJECT_DIR || ctx.worktree || ctx.directory || process.cwd()
}

function sanitize(value) {
  return String(value || "unknown")
    .toLowerCase()
    .replace(/[\n\r\t]+/g, " ")
    .trim()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 96) || "unknown"
}

function emitIntervention(root, row) {
  const dir = join(root, ".cognitive-os", "metrics")
  mkdirSync(dir, { recursive: true })
  const payload = {
    schema_version: "primitive-intervention.v1",
    timestamp: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    session_id: process.env.COGNITIVE_OS_SESSION_ID || process.env.OPENCODE_SESSION_ID || "opencode-plugin-smoke",
    tool_use_id: process.env.COGNITIVE_OS_TOOL_USE_ID || process.env.OPENCODE_TOOL_USE_ID || "opencode-tool-event",
    primitive_family: "hook",
    harness: "opencode",
    source_metric: ".cognitive-os/metrics/primitive-interventions.jsonl",
    ...row,
    primitive_source: row.primitive_source || PRIMITIVE_SOURCE[row.primitive_id] || "unknown",
    target_ref: sanitize(row.target_ref),
  }
  appendFileSync(join(dir, "primitive-interventions.jsonl"), JSON.stringify(payload) + "\n")
}

function loadHookProjection(root) {
  const path = join(root, ".opencode", "cos-hooks.json")
  if (!existsSync(path)) return { events: {} }
  try {
    const parsed = JSON.parse(readFileSync(path, "utf8"))
    return parsed && typeof parsed === "object" ? parsed : { events: {} }
  } catch {
    return { events: {} }
  }
}

function eventSessionId(input) {
  return (
    process.env.COGNITIVE_OS_SESSION_ID ||
    process.env.OPENCODE_SESSION_ID ||
    input?.sessionID ||
    input?.session_id ||
    input?.session?.id ||
    input?.event?.properties?.info?.id ||
    input?.event?.properties?.sessionID ||
    "opencode-session"
  )
}

function projectedHooksFor(projection, nativeEvent) {
  const events = projection?.events || {}
  const direct = events[nativeEvent] || []
  if (nativeEvent === "experimental.session.compacting") {
    return [...direct, ...(events["session.compacted"] || [])]
  }
  return direct
}

function runProjectedHook(root, hook, nativeEvent, input) {
  const script = String(hook?.script || "")
  if (!script || script.includes("..")) return null
  const scriptPath = join(root, script)
  if (!existsSync(scriptPath)) return null
  const timeout = Number(process.env.COS_OPENCODE_HOOK_TIMEOUT_MS || "1500")
  const payload = {
    hook_event: hook.event,
    opencode_event: nativeEvent,
    session_id: eventSessionId(input),
    cwd: root,
    harness: "opencode",
  }
  const result = spawnSync("bash", [scriptPath], {
    cwd: root,
    input: JSON.stringify(payload),
    encoding: "utf8",
    timeout,
    env: {
      ...process.env,
      COGNITIVE_OS_HARNESS: "opencode",
      COGNITIVE_OS_PROJECT_DIR: root,
      OPENCODE_PROJECT_DIR: root,
      COGNITIVE_OS_SESSION_ID: payload.session_id,
      OPENCODE_SESSION_ID: payload.session_id,
    },
  })
  return {
    status: result.status,
    signal: result.signal,
    timedOut: Boolean(result.error && result.error.code === "ETIMEDOUT"),
  }
}

function emitProjectedHookRows(root, projection, nativeEvent, input) {
  const hooks = projectedHooksFor(projection, nativeEvent)
  for (const hook of hooks) {
    const result = runProjectedHook(root, hook, nativeEvent, input)
    emitIntervention(root, {
      primitive_id: hook.id || sanitize(hook.script),
      primitive_source: hook.script || "unknown",
      action_kind: result?.status === 2 ? "block" : result?.timedOut ? "warn" : "observe",
      reason_code: result?.timedOut ? "opencode_projected_hook_timeout" : "opencode_projected_hook",
      target_ref: nativeEvent,
      native_event: nativeEvent,
      hook_event: hook.event,
      hook_status: result?.status ?? null,
      hook_signal: result?.signal ?? null,
    })
  }
}

function row(primitiveId, actionKind, reasonCode, targetRef, extra = {}) {
  return {
    primitive_id: primitiveId,
    primitive_source: PRIMITIVE_SOURCE[primitiveId],
    action_kind: actionKind,
    reason_code: reasonCode,
    target_ref: targetRef,
    ...extra,
  }
}

function classifyBash(command) {
  const text = String(command || "")
  if (/^\s*git\s+(reset|clean\s+-f|restore|rebase|branch\s+-D)\b/i.test(text)) {
    return row("destructive-git-blocker", "block", "destructive_git_op", "git-destructive-op", { source_metric: ".cognitive-os/metrics/git-op-blocks.jsonl" })
  }
  if (/^\s*rm\s+-[a-zA-Z]*[rR][a-zA-Z]*\b/i.test(text)) {
    return row("destructive-rm-blocker", "block", "destructive_file_op", "rm-recursive", { source_metric: ".cognitive-os/metrics/rm-op-blocks.jsonl" })
  }
  if (/(^|[;&|\s])(brew\s+upgrade|pip[0-9.]*\s+install\s+(-U|--upgrade)|uv\s+(sync\s+--upgrade|pip\s+install\s+.*(--upgrade|-U))|npm\s+(update|upgrade)|pnpm\s+(update|upgrade)|yarn\s+(upgrade|up)|go\s+get\s+.*@)/i.test(text)) {
    return row("skill-router", "block", "dependency_update_bypass", "dependency-update-command", { source_metric: ".cognitive-os/metrics/skill-routing.jsonl" })
  }
  if (/\bcd\s+\.\.|\bpushd\b/i.test(text)) {
    return row("agent-bash-cwd-enforcer", "warn", "agent_workdir_drift", "cwd-drift-command")
  }
  if (/agent-control\/inbox|\.cognitive-os\/agent-control/i.test(text)) {
    return row("agent-control-inbound-guard", "block", "agent_control_inbound_write", "agent-control-inbound")
  }
  if (/\bcosd\b.*\b(write|mutate|admin)|curl\s+.*cosd/i.test(text)) {
    return row("cosd-auth-guard", "block", "cosd_auth_required", "cosd-unsafe-call")
  }
  if (/\bgit\s+push\s+origin\s+(main|master)\b/i.test(text)) {
    return row("direct-main-guard", "block", "direct_main_push", "direct-main-push")
  }
  if (/\b(curl|wget|nc)\b.*https?:\/\//i.test(text)) {
    return row("network-egress-guard", "warn", "network_egress_review", "network-egress")
  }
  return null
}

function classifyRead(root, filePath) {
  if (!filePath) return null
  try {
    const size = statSync(filePath).size
    if (size <= 40000) return null
    return row("large-file-advisor", "advise", "large_file_read", "large-file", {
      source_metric: ".cognitive-os/metrics/large-file-reads.jsonl",
      tool: "read",
      size_bucket: size > 400000 ? "gt-400kb" : "gt-40kb",
      relative_path_hash: sanitize(relative(root, filePath)).slice(0, 16),
    })
  } catch {
    return null
  }
}

function classifyTextTool(toolName, args) {
  const text = JSON.stringify(args || {}).toLowerCase()
  if (toolName === "agent") {
    if (text.includes("duplicate primitive") || text.includes("duplicate_helper")) return row("reinvention-check", "warn", "possible_reinvention", "primitive-duplication")
    if (text.includes("adr")) return row("adr-relevance-suggest", "suggest", "adr_relevance", "adr-context")
    if (text.includes("claim completed") || text.includes("no evidence")) return row("claim-validator", "block", "claim_without_evidence", "agent-claim")
    if (text.includes("100% confident") || text.includes("no uncertainty")) return row("confidence-gate", "warn", "overconfidence", "confidence-claim")
    if (text.includes("do everything") || text.includes("unbounded task")) return row("dispatch-gate", "block", "dispatch_scope_too_broad", "agent-dispatch")
  }
  if (["write", "edit", "multiedit"].includes(toolName)) {
    if (text.includes("docs/02-decisions/adrs/") && !text.includes("## status")) return row("adr-section-validator", "warn", "adr_section_missing", "adr-structure")
    if (text.includes("private customer") || text.includes("confidential customer")) return row("confidentiality-enforcer", "block", "confidentiality_boundary", "confidential-content")
    if (text.includes("unsafe content policy fixture")) return row("content-policy", "block", "content_policy_violation", "content-policy")
    if (/api[_-]?key|secret|token/.test(text)) return row("secret-detector", "block", "secret_write_attempt", "secret-like-content")
    if (text.includes(".git/config") || text.includes(".env") || text.includes("cognitive-os.yaml")) return row("protected-config-write-guard", "block", "protected_config_write", "protected-config")
  }
  if (toolName === "agent") {
    if (text.includes("ignore privacy") || text.includes("disable private mode")) return row("private-mode-gate", "block", "private_mode_boundary", "private-mode")
    if (text.includes("no trust report") || text.includes("skip trust report")) return row("trust-score-validator", "warn", "trust_report_missing", "trust-report")
    if (text.includes("huge prompt") || text.includes("low quality prompt")) return row("prompt-quality-llm", "warn", "prompt_quality_review", "prompt-quality")
    if (text.includes("add unrelated feature") || text.includes("scope creep")) return row("scope-creep-detector", "warn", "scope_creep", "scope-creep")
  }
  return null
}

function classifyAfter(toolName, args) {
  const text = JSON.stringify(args || {}).toLowerCase()
  if (text.includes("aci observation") || toolName === "agent") return row("aci-observation-capture", "observe", "aci_observation", "aci-observation")
  if (text.includes("rollback candidate")) return row("auto-rollback-trigger", "advise", "rollback_candidate", "rollback-signal")
  if (text.includes("verification recommended")) return row("auto-verify", "advise", "verification_recommended", "verification-signal")
  if (text.includes("context threshold")) return row("context-watchdog", "advise", "context_budget_checkpoint", "context-threshold")
  if (text.includes("doc sync drift")) return row("doc-sync-detector", "warn", "doc_sync_drift", "doc-sync")
  if (text.includes("token budget exceeded")) return row("token-budget-monitor", "advise", "token_budget_exceeded", "token-budget")
  if (text.includes("result truncated")) return row("result-truncator", "advise", "result_truncated", "result-truncation")
  return null
}

function maybeThrow(rowData) {
  if (["block"].includes(rowData.action_kind)) {
    throw new Error(`COS primitive ${rowData.primitive_id} blocked ${rowData.reason_code}`)
  }
}

export const CosPrimitiveGuard = async (ctx) => {
  const root = projectRoot(ctx)
  const projection = loadHookProjection(root)
  return {
    "session.created": async (input) => {
      emitProjectedHookRows(root, projection, "session.created", input)
    },
    "session.idle": async (input) => {
      emitProjectedHookRows(root, projection, "session.idle", input)
    },
    "tui.prompt.append": async (input) => {
      emitProjectedHookRows(root, projection, "tui.prompt.append", input)
    },
    "session.compacted": async (input) => {
      emitProjectedHookRows(root, projection, "session.compacted", input)
    },
    "experimental.session.compacting": async (input) => {
      emitProjectedHookRows(root, projection, "experimental.session.compacting", input)
    },
    "tool.execute.before": async (input, output) => {
      const toolName = String(input?.tool || output?.tool || "unknown").toLowerCase()
      const args = output?.args || input?.args || {}
      let classified = null
      if (toolName === "bash") classified = classifyBash(args.command || "")
      if (toolName === "read") classified = classifyRead(root, args.filePath || args.file_path)
      if (!classified) classified = classifyTextTool(toolName, args)
      if (classified) {
        emitIntervention(root, { ...classified, tool: toolName })
        maybeThrow(classified)
      }
    },
    "tool.execute.after": async (input, output) => {
      const toolName = String(input?.tool || output?.tool || "unknown").toLowerCase()
      const classified = classifyAfter(toolName, { input: input?.args, output: output?.args || output })
      if (classified) emitIntervention(root, { ...classified, tool: toolName })
    },
  }
}

export { SIGNED_PRIMITIVES }
