// SCOPE: both
// OpenCode project plugin: Cognitive OS primitive guard.
// Loaded from .opencode/plugins/cos-primitive-guard.js by OpenCode.
// Emits content-free primitive-interventions rows and throws for blocking actions.

import { mkdirSync, appendFileSync, statSync } from "node:fs"
import { join, relative } from "node:path"

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
    ...row,
    target_ref: sanitize(row.target_ref),
  }
  appendFileSync(join(dir, "primitive-interventions.jsonl"), JSON.stringify(payload) + "\n")
}

function classifyBash(command) {
  const text = String(command || "")
  if (/^\s*git\s+(reset|clean\s+-f|restore|rebase|branch\s+-D)\b/i.test(text)) {
    return {
      primitive_id: "destructive-git-blocker",
      primitive_source: "hooks/destructive-git-blocker.sh",
      action_kind: "block",
      reason_code: "destructive_git_op",
      target_ref: "git-destructive-op",
      source_metric: ".cognitive-os/metrics/git-op-blocks.jsonl",
    }
  }
  if (/^\s*rm\s+-[a-zA-Z]*[rR][a-zA-Z]*\b/i.test(text)) {
    return {
      primitive_id: "destructive-rm-blocker",
      primitive_source: "hooks/destructive-rm-blocker.sh",
      action_kind: "block",
      reason_code: "destructive_file_op",
      target_ref: "rm-recursive",
      source_metric: ".cognitive-os/metrics/rm-op-blocks.jsonl",
    }
  }
  if (/(^|[;&|\s])(brew\s+upgrade|pip[0-9.]*\s+install\s+(-U|--upgrade)|uv\s+(sync\s+--upgrade|pip\s+install\s+.*(--upgrade|-U))|npm\s+(update|upgrade)|pnpm\s+(update|upgrade)|yarn\s+(upgrade|up)|go\s+get\s+.*@)/i.test(text)) {
    return {
      primitive_id: "skill-router",
      primitive_source: "hooks/skill-router-bash-gate.sh",
      action_kind: "block",
      reason_code: "dependency_update_bypass",
      target_ref: "dependency-update-command",
      source_metric: ".cognitive-os/metrics/skill-routing.jsonl",
    }
  }
  return null
}

function classifyRead(root, filePath) {
  if (!filePath) return null
  try {
    const size = statSync(filePath).size
    if (size <= 40000) return null
    return {
      primitive_id: "large-file-advisor",
      primitive_source: "hooks/large-file-advisor.sh",
      action_kind: "advise",
      reason_code: "large_file_read",
      target_ref: "large-file",
      source_metric: ".cognitive-os/metrics/large-file-reads.jsonl",
      tool: "read",
      size_bucket: size > 400000 ? "gt-400kb" : "gt-40kb",
      relative_path_hash: sanitize(relative(root, filePath)).slice(0, 16),
    }
  } catch {
    return null
  }
}

export const CosPrimitiveGuard = async (ctx) => {
  const root = projectRoot(ctx)
  return {
    "tool.execute.before": async (input, output) => {
      const toolName = input?.tool || output?.tool || "unknown"
      if (toolName === "bash") {
        const row = classifyBash(output?.args?.command || input?.args?.command || "")
        if (row) {
          emitIntervention(root, { ...row, tool: "bash" })
          throw new Error(`COS primitive ${row.primitive_id} blocked ${row.reason_code}`)
        }
      }
      if (toolName === "read") {
        const row = classifyRead(root, output?.args?.filePath || input?.args?.filePath)
        if (row) {
          emitIntervention(root, row)
        }
      }
    },
  }
}
