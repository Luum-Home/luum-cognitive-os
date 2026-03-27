#!/usr/bin/env bash
# Hook: agent-bus-monitor (SessionStart)
# Checks Valkey connectivity and reports active agents from previous sessions.
# OFF by default — enable via AGENT_BUS_ENABLED=true environment variable.

set -euo pipefail

# Only run if explicitly enabled
if [ "${AGENT_BUS_ENABLED:-false}" != "true" ]; then
    exit 0
fi

# Check if redis-cli is available
if ! command -v redis-cli &>/dev/null; then
    echo "agent-bus: redis-cli not found, skipping bus monitor" >&2
    exit 0
fi

VALKEY_HOST="${VALKEY_HOST:-localhost}"
VALKEY_PORT="${VALKEY_PORT:-6379}"

# Check Valkey connectivity
if redis-cli -h "$VALKEY_HOST" -p "$VALKEY_PORT" PING 2>/dev/null | grep -q "PONG"; then
    echo "agent-bus: Valkey connected at ${VALKEY_HOST}:${VALKEY_PORT}" >&2

    # Check for active agent channels
    CHANNELS=$(redis-cli -h "$VALKEY_HOST" -p "$VALKEY_PORT" PUBSUB CHANNELS "cos:agent:*:heartbeat" 2>/dev/null || true)
    if [ -n "$CHANNELS" ]; then
        AGENT_COUNT=$(echo "$CHANNELS" | wc -l | tr -d ' ')
        echo "agent-bus: ${AGENT_COUNT} agent channel(s) detected from previous session" >&2
    fi
else
    echo "agent-bus: Valkey not reachable at ${VALKEY_HOST}:${VALKEY_PORT}, file fallback active" >&2
fi

# Check file-based fallback for recent agents
FALLBACK_DIR=".cognitive-os/agent-bus"
if [ -d "$FALLBACK_DIR" ]; then
    AGENT_DIRS=$(find "$FALLBACK_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
    if [ "$AGENT_DIRS" -gt 0 ]; then
        echo "agent-bus: ${AGENT_DIRS} agent(s) in file fallback from previous session" >&2
    fi
fi

exit 0
