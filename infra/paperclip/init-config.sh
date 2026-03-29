#!/bin/sh
# Auto-create Paperclip config + signup + bootstrap CEO, then start the server.
# Used as Docker entrypoint for fully automated COS setup.
# No manual steps needed — admin account created automatically.
set -e

CONFIG_DIR="${PAPERCLIP_HOME:-/paperclip}/instances/${PAPERCLIP_INSTANCE_ID:-default}"
CONFIG_FILE="$CONFIG_DIR/config.json"
BOOTSTRAP_MARKER="$CONFIG_DIR/.bootstrapped"
SERVER_PORT="${PORT:-3100}"
ADMIN_EMAIL="${PAPERCLIP_ADMIN_EMAIL:-admin@cognitive-os.local}"
ADMIN_PASSWORD="${PAPERCLIP_ADMIN_PASSWORD:-CosAdmin2026!}"
ADMIN_NAME="${PAPERCLIP_ADMIN_NAME:-Cognitive OS Admin}"

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
    "port": ${SERVER_PORT},
    "deploymentMode": "${PAPERCLIP_DEPLOYMENT_MODE:-authenticated}",
    "exposure": "${PAPERCLIP_DEPLOYMENT_EXPOSURE:-private}"
  }
}
EOF
  echo "[COS] Config created."
fi

# Step 2: Start the server in background
echo "[COS] Starting Paperclip server..."
node --import ./server/node_modules/tsx/dist/loader.mjs server/dist/index.js &
SERVER_PID=$!

# Step 3: Full auto-bootstrap if not already done
if [ ! -f "$BOOTSTRAP_MARKER" ]; then
  echo "[COS] Waiting for server to be ready..."
  # Wait longer on first boot (corepack downloads pnpm ~10s)
  for i in $(seq 1 60); do
    if curl -sf "http://localhost:${SERVER_PORT}/api/health" > /dev/null 2>&1; then
      echo "[COS] Server ready. Running full auto-bootstrap..."

      # 3a: Generate bootstrap CEO invite
      INVITE_TOKEN=$(node cli/node_modules/tsx/dist/cli.mjs cli/src/index.ts auth bootstrap-ceo 2>&1 | grep "Invite URL:" | sed 's|.*/invite/||')

      if [ -n "$INVITE_TOKEN" ]; then
        echo "[COS] Invite token: $INVITE_TOKEN"

        # 3b: Create admin account via API
        echo "[COS] Creating admin account..."
        curl -s -X POST "http://localhost:${SERVER_PORT}/api/auth/sign-up/email" \
          -H "Content-Type: application/json" \
          -d "{\"name\":\"${ADMIN_NAME}\",\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" > /dev/null 2>&1

        # 3c: Login and capture the full Set-Cookie (includes server-side hash)
        echo "[COS] Logging in..."
        COOKIE=$(curl -sv -X POST "http://localhost:${SERVER_PORT}/api/auth/sign-in/email" \
          -H "Content-Type: application/json" \
          -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" 2>&1 | \
          grep -i "set-cookie:" | sed 's/.*set-cookie: //' | cut -d';' -f1)

        if [ -n "$COOKIE" ]; then
          # 3d: Accept bootstrap invite with full session cookie
          echo "[COS] Accepting bootstrap invite..."
          RESULT=$(curl -s -X POST "http://localhost:${SERVER_PORT}/api/invites/${INVITE_TOKEN}/accept" \
            -H "Content-Type: application/json" \
            -H "Origin: http://localhost:${SERVER_PORT}" \
            -H "Cookie: ${COOKIE}" \
            -d '{"requestType":"human"}' 2>/dev/null)

          if echo "$RESULT" | grep -q "bootstrapAccepted"; then
            # 3e: Create company as seed data
            echo "[COS] Creating company..."
            curl -s -X POST "http://localhost:${SERVER_PORT}/api/companies" \
              -H "Content-Type: application/json" \
              -H "Origin: http://localhost:${SERVER_PORT}" \
              -H "Cookie: ${COOKIE}" \
              -d "{\"name\":\"${PAPERCLIP_COMPANY_NAME:-Cognitive OS}\",\"mission\":\"AI Agent Operating System with governance, quality gates, and persistent memory\"}" > /dev/null 2>&1

            echo "[COS] ============================================"
            echo "[COS] Bootstrap COMPLETE! Ready to use."
            echo "[COS]   Email:    ${ADMIN_EMAIL}"
            echo "[COS]   Password: ${ADMIN_PASSWORD}"
            echo "[COS]   URL:      http://localhost:${PAPERCLIP_PORT:-3200}"
            echo "[COS]   Company:  ${PAPERCLIP_COMPANY_NAME:-Cognitive OS}"
            echo "[COS] ============================================"
            touch "$BOOTSTRAP_MARKER"
          else
            echo "[COS] Bootstrap accept response: $RESULT"
            echo "[COS] You may need to open the invite URL manually."
          fi
        else
          echo "[COS] Login failed (no cookie). Open invite manually:"
          echo "[COS]   http://localhost:${PAPERCLIP_PORT:-3200}/invite/${INVITE_TOKEN}"
        fi
      else
        echo "[COS] Bootstrap CEO command failed."
      fi
      break
    fi
    sleep 1
  done
fi

# Keep the server running
wait $SERVER_PID
