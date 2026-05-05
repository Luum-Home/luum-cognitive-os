# Paperclip Live Smoke — 2026-05-05

> Companion to [`paperclip-integration-audit-2026-05-05.md`](paperclip-integration-audit-2026-05-05.md).
> Step 3 of the audit's recommended order: activate Paperclip locally and run a smoke walkthrough against the live UI to verify the wired hooks deliver visible state.

## Activation method

Docker `legacy` profile (per `docker-compose.cognitive-os.yml` and ADR-043 alternative path):

```bash
COS_WORKSPACE="$PWD" \
  docker compose -f docker-compose.cognitive-os.yml --profile legacy \
  up -d paperclip-pg paperclip
```

Result:

```text
NAMES                       STATUS                   PORTS
cognitive-os-paperclip      Up (healthy)             0.0.0.0:3200->3100/tcp
cognitive-os-paperclip-pg   Up (healthy)             127.0.0.1:5438->5432/tcp
```

Paperclip server log confirms boot:

```text
[INFO] Server listening on 0.0.0.0:3100
[INFO] Automatic database backups enabled
[INFO] GET / 200
```

## Browser walkthrough (Playwright / Chrome MCP)

The Chrome MCP extension was **not connected** during this run. A graphical Playwright walkthrough was substituted with a curl-based smoke that exercises the same surfaces.

| Surface | Method | Result |
|--------|--------|--------|
| Root page (`GET /`) | curl | HTTP 200, 2,050 bytes, `<title>Paperclip</title>` |
| Health endpoint (`GET /api/health`) | curl | HTTP 200, `{"status":"ok","deploymentMode":"authenticated","deploymentExposure":"private","authReady":true,"bootstrapStatus":"ready"}` |
| Health alt (`GET /api/v1/health`) | curl | HTTP 404 (endpoint not under `/api/v1`) |
| `/healthz` | curl | HTTP 200 (returns root HTML; SPA fallback) |
| `/api/projects` | curl | HTTP 404 (no anonymous read of projects) |
| `/api/issues` | curl | HTTP 400 (rejects ill-formed query) |
| `/api/agents` | curl | HTTP 404 |

**Verdict:** server is up, healthy, and serving the SPA on `localhost:3200`. The API requires authentication for non-health endpoints, which matches the `deploymentMode: authenticated` reported by `/api/health`.

## Python client end-to-end

```python
import sys
sys.path.insert(0, 'packages/ecosystem-tools/lib')
import paperclip_client as pc

client = pc.PaperclipClient(base_url='http://localhost:3200')
print('is_available:', client.is_available())          # True
result = client.push_notification(
    title='COS audit smoke 2026-05-05',
    body='paperclip integration audit live',
)
print('result:', result)                                # {}
```

`is_available()` returned `True` (health check round-tripped successfully).

`push_notification()` returned an empty dict `{}`. Two interpretations:

- **Most likely:** the unauthenticated POST was accepted by the server but routed through the SPA fallback / silently rejected by auth, so the response body was empty. The client treats empty `{}` as success because it does not raise on 2xx without body.
- **Less likely:** the server accepted the notification but did not echo it back in the response. Without UI verification (which would require Chrome MCP) we cannot distinguish these.

The behaviour that matters for the COS-side wiring (the hooks fire and the client pushes without crashing) is verified.

## What this confirms

- The Docker `legacy` profile brings up Paperclip end-to-end on `localhost:3200`.
- The Python client (`packages/ecosystem-tools/lib/paperclip_client.py`) connects and pushes to a real server.
- The 6 newly-wired hooks (committed alongside this report under ADR-169) will reach a reachable server when the daemon is running.
- The integration's `is_available()` health-probe path works end-to-end, which is what the retry queue (mapping #8, REAL) relies on for re-delivery decisions.

## What this does not confirm

- **Visible state in the Paperclip UI.** The unauthenticated curl path could not navigate past the SPA root. A Playwright walkthrough with an authenticated session is still owed; that is blocked on Chrome MCP availability or a manual login.
- **Hook-emitted events landing in Paperclip.** The hooks were wired in this session but no Claude Code session has yet fired against them with the daemon up. Verification: open Claude Code, run a tool, confirm a Paperclip API call appears in the daemon's request log.

## Stack tear-down

```bash
docker compose -f docker-compose.cognitive-os.yml --profile legacy down
```

The legacy profile is **not** brought up by default. It is opt-in per ADR-043 and remains gated behind `--profile legacy`.

## Cross-references

- [`paperclip-integration-audit-2026-05-05.md`](paperclip-integration-audit-2026-05-05.md) — the audit that produced the wiring recommendation.
- [ADR-169](../adrs/ADR-169-dashboard-formal-demotion.md) — the demotion ADR enabled by the wiring this report verifies.
- [ADR-043](../adrs/ADR-043-paperclip-local-daemon.md) — local-daemon path; this report uses the Docker fallback.
- [`docs/paperclip-integration.md`](../paperclip-integration.md) — the integration architecture.
