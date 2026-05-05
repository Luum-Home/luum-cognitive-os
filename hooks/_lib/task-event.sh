#!/usr/bin/env bash
# SCOPE: both
# Shared JSONL task-event metric helper.

cos_log_task_event() {
  local metrics_file="$1"
  local action="$2"
  local reason="${3:-}"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

  local entry="{\"timestamp\":\"$timestamp\",\"action\":\"$action\",\"reason\":\"$reason\"}"
  echo "$entry" >> "$metrics_file" 2>/dev/null || true
}
