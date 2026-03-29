#!/bin/sh
# Auto-create Paperclip config + bootstrap CEO, then start the server.
# Used as Docker entrypoint for automated COS setup.
set -e

CONFIG_DIR="${PAPERCLIP_HOME:-/paperclip}/instances/${PAPERCLIP_INSTANCE_ID:-default}"
CONFIG_FILE="$CONFIG_DIR/config.json"
BOOTSTRAP_MARKER="$CONFIG_DIR/.bootstrapped"

# Step 1: Create config if missing
if [ ! -f "$CONFIG_FILE" ]; then
  echo "[COS] Creating Paperclip config at $CONFIG_FILE ..."
  mkdir -p "$CONFIG_DIR"
  cat > "$CONFIG_FILE" << EOF
{
  "\$meta": {
    "version": 1,
    "updatedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "source": "onboard"
  },
  "company": {
    "name": "${PAPERCLIP_COMPANY_NAME:-Cognitive OS}",
    "slug": "${PAPERCLIP_COMPANY_SLUG:-cognitive-os}"
  },
  "database": {
    "mode": "postgres",
    "url": "${DATABASE_URL}"
  },
  "logging": {
    "level": "info",
    "mode": "cloud"
  },
  "server": {
    "host": "${HOST:-0.0.0.0}",
    "port": ${PORT:-3100},
    "deploymentMode": "${PAPERCLIP_DEPLOYMENT_MODE:-authenticated}",
    "exposure": "${PAPERCLIP_DEPLOYMENT_EXPOSURE:-private}"
  }
}
EOF
  echo "[COS] Config created."
fi

# Step 2: Start the server in background, then bootstrap CEO
echo "[COS] Starting Paperclip server..."
node --import ./server/node_modules/tsx/dist/loader.mjs server/dist/index.js &
SERVER_PID=$!

# Step 3: Bootstrap CEO if not already done
if [ ! -f "$BOOTSTRAP_MARKER" ]; then
  echo "[COS] Waiting for server to be ready..."
  for i in $(seq 1 30); do
    if curl -sf http://localhost:${PORT:-3100}/api/health > /dev/null 2>&1; then
      echo "[COS] Server ready. Running bootstrap..."
      INVITE_URL=$(pnpm paperclipai auth bootstrap-ceo 2>&1 | grep "Invite URL:" | sed 's/.*Invite URL: //')
      if [ -n "$INVITE_URL" ]; then
        echo "[COS] ============================================"
        echo "[COS] Bootstrap CEO invite URL:"
        echo "[COS]   $INVITE_URL"
        echo "[COS] ============================================"
        touch "$BOOTSTRAP_MARKER"
      fi
      break
    fi
    sleep 1
  done
fi

# Keep the server running
wait $SERVER_PID
