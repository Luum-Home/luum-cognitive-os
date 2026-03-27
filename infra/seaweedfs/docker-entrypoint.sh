#!/bin/sh
# SeaweedFS entrypoint — creates default s3.json if not mounted
S3_CONFIG="/etc/seaweedfs/s3.json"

if [ ! -f "$S3_CONFIG" ]; then
  echo "[cognitive-os] No s3.json found, creating default config..."
  mkdir -p /etc/seaweedfs
  cat > "$S3_CONFIG" <<'JSONEOF'
{
  "identities": [
    {
      "name": "agentosadmin",
      "credentials": [
        {
          "accessKey": "agentosadmin",
          "secretKey": "agentossecret"
        }
      ],
      "actions": ["Admin", "Read", "List", "Tagging", "Write"]
    }
  ]
}
JSONEOF
fi

exec /entrypoint.sh "$@"
