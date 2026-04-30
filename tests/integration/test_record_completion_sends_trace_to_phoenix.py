# SCOPE: both
"""Integration test: record_completion._send_otel_trace must deliver a span to Phoenix.

ADR-058 (2026-04-24) Phase 4 — Integration coverage.

This replaces the legacy Langfuse e2e tests (removed from
tests/integration/test_e2e_flows.py in the same commit).

Steps:
  1. Start a local Phoenix collector via subprocess (no Docker required).
  2. Point OTel endpoint at it (PHOENIX_COLLECTOR_ENDPOINT).
  3. Call _send_otel_trace with a realistic payload.
  4. Flush the OTel exporter so the span is ingested synchronously.
  5. Query Phoenix via phoenix.Client().get_spans_dataframe() and
     assert the span is present with the expected attributes.

Design choices:
  - No Docker required: `phoenix serve` runs as a subprocess.
  - Use phoenix.Client() — the arize-phoenix Python client that queries
    the live collector directly.
  - Fail-soft on env: if `arize-phoenix` is not installed in the current
    venv, skip cleanly at module-import time.
  - Timeout: 60s max for the whole test (startup + flush + query).
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterator

import pytest


# ---------------------------------------------------------------------------
# Module-level import gate — skip cleanly when arize-phoenix is not installed.
# ---------------------------------------------------------------------------
_phoenix_available = True
_phoenix_import_error: str | None = None
try:
    import phoenix as _phoenix_module  # noqa: F401
    import phoenix.otel as _phoenix_otel  # noqa: F401
except Exception as exc:  # pragma: no cover — depends on installed extras
    _phoenix_available = False
    _phoenix_import_error = repr(exc)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.e2e,
    pytest.mark.skipif(
        not _phoenix_available,
        reason=f"arize-phoenix not installed ({_phoenix_import_error})",
    ),
    # Phoenix fixture spawns a subprocess and waits ≤30s for its TCP port.
    # The default pytest-timeout (30s) races the fixture wait and kills the
    # test before phoenix can come up. 120s gives the fixture room + the
    # actual test time.
    pytest.mark.timeout(120),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _free_port() -> int:
    """Return a currently-unbound TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_tcp(host: str, port: int, timeout: float = 30.0, interval: float = 0.3) -> bool:
    """Poll a TCP port until it accepts connections or the deadline expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(interval)
    return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def phoenix_server() -> Iterator[dict]:
    """Start `phoenix serve` as a subprocess on a random free port.

    Yields a dict with:
      - endpoint: http://127.0.0.1:<port>  (UI + API)
      - collector_endpoint: http://127.0.0.1:<port>/v1/traces (OTel OTLP HTTP)
      - client: phoenix.Client instance pointed at the endpoint
      - port: int
    """
    import phoenix as px

    port = _free_port()
    host = "127.0.0.1"
    endpoint = f"http://{host}:{port}"
    collector_endpoint = f"{endpoint}/v1/traces"

    # Phoenix reads these env vars to decide bind addr and where the UI lives.
    env = {
        **os.environ,
        "PHOENIX_HOST": host,
        "PHOENIX_PORT": str(port),
        # Ensure no stale env leaks into the subprocess from an outer test run.
        "PHOENIX_COLLECTOR_ENDPOINT": collector_endpoint,
    }

    # Prefer invoking `phoenix` via `python -m phoenix.server.main` because the
    # CLI entrypoint `phoenix` might not be on PATH inside uv's managed venv.
    # `phoenix.server.main` is the canonical ASGI entrypoint.
    cmd = [sys.executable, "-m", "phoenix.server.main", "serve"]

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        # Wait until the TCP port accepts connections.
        if not _wait_for_tcp(host, port, timeout=30.0):
            # Surface whatever Phoenix emitted on stdout/stderr.
            try:
                proc.terminate()
                out, _ = proc.communicate(timeout=5)
            except Exception:
                out = b""
            pytest.skip(
                "phoenix serve did not open port within 30s. "
                f"output head: {out[:1500]!r}"
            )

        client = px.Client(endpoint=endpoint)

        yield {
            "endpoint": endpoint,
            "collector_endpoint": collector_endpoint,
            "client": client,
            "port": port,
        }
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


@pytest.fixture
def otel_env_for_phoenix(phoenix_server, monkeypatch):
    """Point the OTel exporter at the live phoenix_server instance."""
    endpoint = phoenix_server["collector_endpoint"]
    # phoenix.otel.register() honours PHOENIX_COLLECTOR_ENDPOINT.
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", endpoint)
    # Clear competing envs that would redirect OTLP elsewhere.
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    return endpoint


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_record_completion_sends_trace_to_phoenix(
    phoenix_server, otel_env_for_phoenix, tmp_path, monkeypatch
):
    """_send_otel_trace must produce a queryable span in Phoenix.

    Uses SimpleSpanProcessor by installing a direct OTel exporter against the
    live Phoenix collector — this avoids BatchSpanProcessor delays that make
    the assertion window unpredictable.
    """
    # Isolate metrics dir
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    # Reload record_completion so its module-level phoenix.otel.register() picks
    # up the new PHOENIX_COLLECTOR_ENDPOINT from otel_env_for_phoenix.
    import importlib
    import lib.record_completion as rc_mod
    importlib.reload(rc_mod)

    assert rc_mod._otel_tracer is not None, (
        "record_completion._otel_tracer failed to initialise even though "
        "arize-phoenix is installed. Check phoenix.otel.register() import path."
    )

    task_id = "e2e-phoenix-" + uuid.uuid4().hex[:16]
    skill_name = "sdd-apply"
    task_type = "implementation"
    trust_score = 85
    tokens_used = 4200

    rc_mod._send_otel_trace(
        skill_name=skill_name,
        task_type=task_type,
        trust_score=trust_score,
        tokens_used=tokens_used,
        success=True,
        task_id=task_id,
    )

    # Force flush the global tracer provider so the span is exported NOW.
    try:
        from opentelemetry import trace as _otel_trace

        provider = _otel_trace.get_tracer_provider()
        flush = getattr(provider, "force_flush", None)
        if flush is not None:
            flush(timeout_millis=5000)
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"Unable to flush OTel provider: {exc!r}")

    # Query Phoenix for the span. Phoenix may index asynchronously; poll up
    # to 30s before giving up.
    client = phoenix_server["client"]
    start_time = datetime.now(timezone.utc) - timedelta(minutes=2)

    spans_df = None
    deadline = time.monotonic() + 30.0
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            spans_df = client.get_spans_dataframe(start_time=start_time)
        except Exception as exc:
            last_exc = exc
            spans_df = None

        if spans_df is not None and not spans_df.empty:
            # Check we can see at least one row with our skill name.
            # Phoenix stores attributes under 'attributes.<key>' columns when
            # the dataframe is expanded, or inside an 'attributes' dict column.
            col_candidates = [
                "attributes.skill.name",
                "attributes.skill_name",
            ]
            hit = False
            for col in col_candidates:
                if col in spans_df.columns and (spans_df[col] == skill_name).any():
                    hit = True
                    break
            if not hit and "attributes" in spans_df.columns:
                # Flat-dict form
                def _match(row):
                    attrs = row
                    if isinstance(attrs, dict):
                        return attrs.get("skill.name") == skill_name
                    return False

                hit = spans_df["attributes"].apply(_match).any()
            if hit:
                break
        time.sleep(1.0)

    if spans_df is None:
        pytest.fail(
            f"Phoenix get_spans_dataframe raised repeatedly: {last_exc!r}"
        )

    assert not spans_df.empty, (
        "No spans found in Phoenix after flush + 30s poll. "
        "record_completion._send_otel_trace did not deliver."
    )

    # Identify the span row deterministically by task_id (unique per test).
    task_id_cols = [
        c for c in spans_df.columns
        if c in ("attributes.task.id", "attributes.task_id")
    ]
    matching = None
    for col in task_id_cols:
        rows = spans_df[spans_df[col] == task_id]
        if not rows.empty:
            matching = rows
            break
    if matching is None and "attributes" in spans_df.columns:
        matching = spans_df[
            spans_df["attributes"].apply(
                lambda a: isinstance(a, dict) and a.get("task.id") == task_id
            )
        ]

    assert matching is not None and not matching.empty, (
        f"No span found with task.id={task_id}. "
        f"Columns available: {list(spans_df.columns)[:40]}. "
        f"Row count: {len(spans_df)}."
    )

    row = matching.iloc[0]

    def _attr(row_, key: str):
        """Fetch a span attribute by semantic key, tolerating both column layouts."""
        flat_col = f"attributes.{key}"
        if flat_col in row_.index:
            return row_[flat_col]
        if "attributes" in row_.index:
            attrs = row_["attributes"]
            if isinstance(attrs, dict):
                return attrs.get(key)
        return None

    assert _attr(row, "skill.name") == skill_name
    assert _attr(row, "task.type") == task_type
    assert str(_attr(row, "task.id")).startswith("e2e-phoenix-")
    assert int(_attr(row, "trust.score")) == trust_score
    assert int(_attr(row, "tokens.used")) == tokens_used
    assert bool(_attr(row, "completion.success")) is True
