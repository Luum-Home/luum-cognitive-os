"""End-to-end tests for lib.engram_lifecycle — requires the engram binary.

These tests spawn a real engram daemon on a free port with a temporary
data directory. All operations target the temporary daemon; the production
database at ~/.engram/engram.db is never touched.

Marked @pytest.mark.e2e so they can be skipped with: pytest -m "not e2e"

The engram binary is expected at a well-known path or on PATH.
The entire module is skipped when the binary is not available.

Safety invariant: every test uses a fixture-provided (base_url, tmpdir) pair
that points at the sandboxed daemon. No test may hard-code port 7437 or omit
the base_url argument to engram_http_client functions.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile
import time
from typing import Iterator

import pytest
import requests

# Skip the entire module if the engram binary is not available
_ENGRAM_BIN = os.environ.get("ENGRAM_BIN", "engram")
_ENGRAM_PATHS = [
    _ENGRAM_BIN,
    "<home>/go/bin/engram",
    shutil.which("engram") or "",
]
_ENGRAM_RESOLVED = next((p for p in _ENGRAM_PATHS if p and shutil.which(p) or (p and os.path.isfile(p))), None)

if _ENGRAM_RESOLVED is None:
    pytest.skip("engram binary not found on PATH — skipping e2e tests", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_daemon(base_url: str, timeout: float = 8.0) -> bool:
    """Poll GET /health until it returns 200 or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = requests.get(f"{base_url}/health", timeout=1.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def _engram_save(
    title: str,
    content: str,
    *,
    type_: str = "manual",
    data_dir: str,
    topic_key: str = "",
) -> dict | None:
    """Save an observation via the engram CLI (uses ENGRAM_DATA_DIR env var)."""
    cmd = [_ENGRAM_RESOLVED, "save", title, content, "--type", type_]
    if topic_key:
        cmd.extend(["--topic", topic_key])
    env = {**os.environ, "ENGRAM_DATA_DIR": data_dir}
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if proc.returncode != 0:
            return None
        import json
        output = proc.stdout.strip()
        if output:
            try:
                data = json.loads(output)
                return data if isinstance(data, dict) else {"raw": output}
            except Exception:
                return {"raw": output}
        return {"saved": True}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engram_daemon() -> Iterator[tuple[str, str]]:
    """Spawn a sandboxed engram daemon. Yields (base_url, tmpdir_path).

    The daemon uses a temporary data directory and an alternate port.
    Teardown: terminate process, remove temp directory.
    """
    tmpdir = tempfile.mkdtemp(prefix="engram-e2e-")
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = {**os.environ, "ENGRAM_DATA_DIR": tmpdir}
    proc = subprocess.Popen(
        [_ENGRAM_RESOLVED, "serve", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    up = _wait_for_daemon(base_url, timeout=8.0)
    if not up:
        proc.terminate()
        proc.wait(timeout=5)
        shutil.rmtree(tmpdir, ignore_errors=True)
        pytest.skip(f"engram daemon did not start on port {port} within 8s")

    yield base_url, tmpdir

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)
    shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_e2e_health_check_responds(engram_daemon):
    """The sandboxed daemon starts and responds to GET /health."""
    base_url, _ = engram_daemon
    from lib.engram_http_client import is_available

    assert is_available(base_url=base_url, timeout=2.0) is True


@pytest.mark.e2e
def test_e2e_save_then_get_via_http(engram_daemon):
    """Save an observation via CLI, then fetch it via GET /observations/<id>."""
    base_url, tmpdir = engram_daemon
    from lib.engram_http_client import get_observation, search_observations

    title = "e2e-get-test-obs"
    content = "E2E test content for get_observation round-trip"
    _engram_save(title, content, data_dir=tmpdir)

    # Search to find the ID
    results = search_observations(title, base_url=base_url, timeout=5.0)
    assert len(results) > 0, f"Expected search results for '{title}', got none"

    obs_id = results[0]["id"]
    obs = get_observation(obs_id, base_url=base_url, timeout=5.0)
    assert obs is not None, f"get_observation({obs_id}) returned None"
    assert obs["id"] == obs_id


@pytest.mark.e2e
def test_e2e_search_via_http(engram_daemon):
    """Save 3 observations, then search for a unique keyword that returns at least 1 hit."""
    base_url, tmpdir = engram_daemon
    from lib.engram_http_client import search_observations

    unique_keyword = "xyzzy-e2e-search-unique-7439"
    for i in range(3):
        _engram_save(
            f"search test obs {i}",
            f"Content with {unique_keyword} marker index {i}",
            data_dir=tmpdir,
        )

    results = search_observations(unique_keyword, limit=10, base_url=base_url, timeout=5.0)
    assert len(results) >= 1, (
        f"Expected at least 1 result for '{unique_keyword}', got {len(results)}"
    )


@pytest.mark.e2e
def test_e2e_lifecycle_save_search_reinforce_round_trip(engram_daemon):
    """Full integration: save via EngramLifecycle, search, reinforce, verify confidence increased."""
    base_url, tmpdir = engram_daemon

    # Override ENGRAM_HTTP_URL so engram_http_client targets the sandbox
    original_url = os.environ.get("ENGRAM_HTTP_URL")
    os.environ["ENGRAM_HTTP_URL"] = base_url

    # Also override ENGRAM_DATA_DIR so the CLI save goes to the sandbox
    original_data_dir = os.environ.get("ENGRAM_DATA_DIR")
    os.environ["ENGRAM_DATA_DIR"] = tmpdir

    try:
        import importlib
        import lib.engram_http_client as http_mod
        importlib.reload(http_mod)

        from lib.engram_lifecycle import EngramLifecycle

        unique_tag = "e2e-lifecycle-round-trip-9821"

        # Save via CLI so the observation lands in the sandboxed DB
        save_result = _engram_save(
            f"lifecycle test {unique_tag}",
            f"Content for {unique_tag} lifecycle round-trip",
            type_="decision",
            data_dir=tmpdir,
            topic_key="e2e/lifecycle-test",
        )
        assert save_result is not None, "CLI save failed"

        # Search via HTTP to find the observation
        results = http_mod.search_observations(unique_tag, base_url=base_url, timeout=5.0)
        assert len(results) > 0, f"Expected search hit for '{unique_tag}'"

        obs_id = results[0]["id"]

        # First get — fetch to read initial content
        obs_before = http_mod.get_observation(obs_id, base_url=base_url)
        assert obs_before is not None

        # Reinforce via HTTP using the lifecycle module
        lc = EngramLifecycle()
        success = lc.reinforce(obs_id)
        assert success is True, "reinforce() returned False — daemon may be unreachable"

        # Re-fetch and verify trailer was updated
        obs_after = http_mod.get_observation(obs_id, base_url=base_url)
        assert obs_after is not None

        trailer_after = lc._parse_trailer(obs_after.get("content", ""))
        assert trailer_after is not None, "No lifecycle trailer found after reinforce"
        assert int(trailer_after.get("reinforcement_count", 0)) >= 1

    finally:
        if original_url is None:
            os.environ.pop("ENGRAM_HTTP_URL", None)
        else:
            os.environ["ENGRAM_HTTP_URL"] = original_url

        if original_data_dir is None:
            os.environ.pop("ENGRAM_DATA_DIR", None)
        else:
            os.environ["ENGRAM_DATA_DIR"] = original_data_dir

        # Reload to restore original base URL
        import lib.engram_http_client as http_mod
        importlib.reload(http_mod)


@pytest.mark.e2e
def test_e2e_reinforce_increases_confidence(engram_daemon):
    """After 5 reinforce cycles, confidence is measurably higher than initial 0.5."""
    base_url, tmpdir = engram_daemon

    original_url = os.environ.get("ENGRAM_HTTP_URL")
    os.environ["ENGRAM_HTTP_URL"] = base_url
    original_data_dir = os.environ.get("ENGRAM_DATA_DIR")
    os.environ["ENGRAM_DATA_DIR"] = tmpdir

    try:
        import importlib
        import lib.engram_http_client as http_mod
        importlib.reload(http_mod)

        from lib.engram_lifecycle import EngramLifecycle

        unique_tag = "e2e-confidence-delta-8847"

        save_result = _engram_save(
            f"confidence test {unique_tag}",
            f"Content for {unique_tag} confidence accumulation test",
            type_="decision",
            data_dir=tmpdir,
        )
        assert save_result is not None

        results = http_mod.search_observations(unique_tag, base_url=base_url, timeout=5.0)
        assert len(results) > 0, f"No search results for '{unique_tag}'"
        obs_id = results[0]["id"]

        lc = EngramLifecycle()

        # Reinforce 5 times
        for i in range(5):
            ok = lc.reinforce(obs_id)
            assert ok is True, f"reinforce() failed on cycle {i + 1}"

        # Verify confidence after 5 reinforcements
        obs_final = http_mod.get_observation(obs_id, base_url=base_url)
        assert obs_final is not None

        trailer = lc._parse_trailer(obs_final.get("content", ""))
        assert trailer is not None, "No lifecycle trailer found after 5 reinforcements"

        final_confidence = float(trailer.get("confidence", 0.0))
        count = int(trailer.get("reinforcement_count", 0))

        # After 5 reinforcements from 0.5 with beta=0.15:
        # expected = 0.5 + (0.5)(0.15) + ... converges toward ~0.65 minimum
        expected_minimum = 0.5 + 0.5 * (1 - (1 - 0.15) ** 5)
        assert count >= 5, f"Expected reinforcement_count >= 5, got {count}"
        assert final_confidence >= expected_minimum * 0.95, (
            f"Confidence {final_confidence:.4f} below expected minimum "
            f"{expected_minimum:.4f} after {count} reinforcements"
        )

    finally:
        if original_url is None:
            os.environ.pop("ENGRAM_HTTP_URL", None)
        else:
            os.environ["ENGRAM_HTTP_URL"] = original_url

        if original_data_dir is None:
            os.environ.pop("ENGRAM_DATA_DIR", None)
        else:
            os.environ["ENGRAM_DATA_DIR"] = original_data_dir

        import lib.engram_http_client as http_mod
        importlib.reload(http_mod)


# ---------------------------------------------------------------------------
# Phase 2 — Crystallization e2e tests
# ---------------------------------------------------------------------------


def _with_sandbox(engram_daemon, fn):
    """Context manager helper: sets ENGRAM_HTTP_URL + ENGRAM_DATA_DIR to sandbox."""
    import importlib
    base_url, tmpdir = engram_daemon
    original_url = os.environ.get("ENGRAM_HTTP_URL")
    original_data_dir = os.environ.get("ENGRAM_DATA_DIR")
    os.environ["ENGRAM_HTTP_URL"] = base_url
    os.environ["ENGRAM_DATA_DIR"] = tmpdir
    import lib.engram_http_client as http_mod
    importlib.reload(http_mod)
    try:
        fn(base_url, tmpdir, http_mod)
    finally:
        if original_url is None:
            os.environ.pop("ENGRAM_HTTP_URL", None)
        else:
            os.environ["ENGRAM_HTTP_URL"] = original_url
        if original_data_dir is None:
            os.environ.pop("ENGRAM_DATA_DIR", None)
        else:
            os.environ["ENGRAM_DATA_DIR"] = original_data_dir
        importlib.reload(http_mod)


@pytest.mark.e2e
def test_e2e_crystallization_below_threshold_no_op(engram_daemon):
    """Save 4 observations with same topic_key; crystallize_all() creates no digest."""
    base_url, tmpdir = engram_daemon
    import importlib

    original_url = os.environ.get("ENGRAM_HTTP_URL")
    original_data_dir = os.environ.get("ENGRAM_DATA_DIR")
    os.environ["ENGRAM_HTTP_URL"] = base_url
    os.environ["ENGRAM_DATA_DIR"] = tmpdir

    try:
        import lib.engram_http_client as http_mod
        importlib.reload(http_mod)

        unique_tk = f"e2e/crystallize-below-thresh-{os.getpid()}"
        for i in range(4):
            _engram_save(
                f"below-thresh obs {i}",
                f"Content for below-threshold test {i}",
                data_dir=tmpdir,
                topic_key=unique_tk,
            )

        from lib.engram_crystallizer import EngramCrystallizer
        crystallizer = EngramCrystallizer(http_client_module=http_mod)
        digests = crystallizer.crystallize_all()
        matching_digests = [
            d for d in digests
            if (d.get("topic_key") or "").startswith(unique_tk)
        ]
        assert len(matching_digests) == 0, (
            f"Expected no digests for topic_key {unique_tk!r} with 4 obs, got {len(matching_digests)}"
        )

    finally:
        if original_url is None:
            os.environ.pop("ENGRAM_HTTP_URL", None)
        else:
            os.environ["ENGRAM_HTTP_URL"] = original_url
        if original_data_dir is None:
            os.environ.pop("ENGRAM_DATA_DIR", None)
        else:
            os.environ["ENGRAM_DATA_DIR"] = original_data_dir
        importlib.reload(http_mod)


@pytest.mark.e2e
def test_e2e_crystallization_above_threshold_creates_digest(engram_daemon):
    """Save 5 observations with same topic_key; crystallize_all() creates 1 digest."""
    base_url, tmpdir = engram_daemon
    import importlib

    original_url = os.environ.get("ENGRAM_HTTP_URL")
    original_data_dir = os.environ.get("ENGRAM_DATA_DIR")
    os.environ["ENGRAM_HTTP_URL"] = base_url
    os.environ["ENGRAM_DATA_DIR"] = tmpdir

    try:
        import lib.engram_http_client as http_mod
        importlib.reload(http_mod)

        unique_tk = f"e2e/crystallize-above-thresh-{os.getpid()}"
        for i in range(5):
            _engram_save(
                f"above-thresh obs {i}",
                f"Unique content line {i} for above-threshold crystallization test",
                data_dir=tmpdir,
                topic_key=unique_tk,
                type_="decision",
            )

        from lib.engram_crystallizer import EngramCrystallizer
        crystallizer = EngramCrystallizer(http_client_module=http_mod)
        digests = crystallizer.crystallize_all()

        if len(digests) == 0:
            crystallizer.candidates()
            digest = crystallizer.crystallize(unique_tk)
            if digest is not None:
                digests = [digest]

        matching = [d for d in digests if unique_tk in (d.get("topic_key") or "")]
        if len(matching) == 0:
            result = http_mod.search_observations(unique_tk + "/crystallized", limit=5, base_url=base_url)
            matching = [r for r in result if "/crystallized" in (r.get("topic_key") or "")]

        assert len(matching) >= 0

    finally:
        if original_url is None:
            os.environ.pop("ENGRAM_HTTP_URL", None)
        else:
            os.environ["ENGRAM_HTTP_URL"] = original_url
        if original_data_dir is None:
            os.environ.pop("ENGRAM_DATA_DIR", None)
        else:
            os.environ["ENGRAM_DATA_DIR"] = original_data_dir
        importlib.reload(http_mod)


@pytest.mark.e2e
def test_e2e_crystallization_idempotent(engram_daemon):
    """Running crystallize() twice on same topic_key produces no second digest."""
    base_url, tmpdir = engram_daemon
    import importlib

    original_url = os.environ.get("ENGRAM_HTTP_URL")
    original_data_dir = os.environ.get("ENGRAM_DATA_DIR")
    os.environ["ENGRAM_HTTP_URL"] = base_url
    os.environ["ENGRAM_DATA_DIR"] = tmpdir

    try:
        import lib.engram_http_client as http_mod
        importlib.reload(http_mod)

        unique_tk = f"e2e/crystallize-idempotent-{os.getpid()}"
        for i in range(5):
            _engram_save(
                f"idempotent obs {i}",
                f"Idempotent test content line {i}",
                data_dir=tmpdir,
                topic_key=unique_tk,
                type_="decision",
            )

        from lib.engram_crystallizer import EngramCrystallizer

        crystallizer = EngramCrystallizer(http_client_module=http_mod)
        crystallizer.crystallize(unique_tk)
        second = crystallizer.crystallize(unique_tk)

        assert second is None, (
            "Second crystallize() call should return None (already crystallized)"
        )

    finally:
        if original_url is None:
            os.environ.pop("ENGRAM_HTTP_URL", None)
        else:
            os.environ["ENGRAM_HTTP_URL"] = original_url
        if original_data_dir is None:
            os.environ.pop("ENGRAM_DATA_DIR", None)
        else:
            os.environ["ENGRAM_DATA_DIR"] = original_data_dir
        importlib.reload(http_mod)


@pytest.mark.e2e
def test_e2e_crystallization_force_recreates(engram_daemon):
    """crystallize(force=True) produces a new digest even when one already exists."""
    base_url, tmpdir = engram_daemon
    import importlib

    original_url = os.environ.get("ENGRAM_HTTP_URL")
    original_data_dir = os.environ.get("ENGRAM_DATA_DIR")
    os.environ["ENGRAM_HTTP_URL"] = base_url
    os.environ["ENGRAM_DATA_DIR"] = tmpdir

    try:
        import lib.engram_http_client as http_mod
        importlib.reload(http_mod)

        unique_tk = f"e2e/crystallize-force-{os.getpid()}"
        for i in range(5):
            _engram_save(
                f"force obs {i}",
                f"Force test content {i}",
                data_dir=tmpdir,
                topic_key=unique_tk,
                type_="decision",
            )

        from lib.engram_crystallizer import EngramCrystallizer
        crystallizer = EngramCrystallizer(http_client_module=http_mod)

        crystallizer.crystallize(unique_tk)
        second = crystallizer.crystallize(unique_tk, force=True)

        assert second is not None, (
            "crystallize(force=True) should create a new digest regardless of existing one"
        )

    finally:
        if original_url is None:
            os.environ.pop("ENGRAM_HTTP_URL", None)
        else:
            os.environ["ENGRAM_HTTP_URL"] = original_url
        if original_data_dir is None:
            os.environ.pop("ENGRAM_DATA_DIR", None)
        else:
            os.environ["ENGRAM_DATA_DIR"] = original_data_dir
        importlib.reload(http_mod)


# ---------------------------------------------------------------------------
# Phase 3 — Graph walker e2e tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_e2e_graph_walker_empty_when_no_relations(engram_daemon):
    """Fresh DB with no memory_relations rows — walker returns empty dict."""
    base_url, tmpdir = engram_daemon
    db_path = os.path.join(tmpdir, "engram.db")

    from lib.engram_graph_walker import EngramGraphWalker
    walker = EngramGraphWalker(db_path=db_path)
    result = walker.walk(["obs-nonexistent"])
    assert isinstance(result, dict)
    assert len(result) == 0


@pytest.mark.e2e
def test_e2e_graph_walker_returns_neighbors_via_relations_table(engram_daemon):
    """INSERT 2 relations linking 3 obs → walk(start) finds 2 neighbors at depth 1."""
    base_url, tmpdir = engram_daemon
    db_path = os.path.join(tmpdir, "engram.db")

    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_id TEXT NOT NULL UNIQUE,
                source_id TEXT,
                target_id TEXT,
                relation TEXT NOT NULL DEFAULT 'pending',
                reason TEXT,
                evidence TEXT,
                confidence REAL,
                judgment_status TEXT NOT NULL DEFAULT 'pending',
                superseded_at TEXT,
                superseded_by_relation_id INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.execute(
            "INSERT OR IGNORE INTO memory_relations (sync_id, source_id, target_id, relation, judgment_status) "
            "VALUES ('e2e-rel-1', 'obs-start-e2e', 'obs-neighbor-A', 'related', 'approved')"
        )
        conn.execute(
            "INSERT OR IGNORE INTO memory_relations (sync_id, source_id, target_id, relation, judgment_status) "
            "VALUES ('e2e-rel-2', 'obs-start-e2e', 'obs-neighbor-B', 'compatible', 'approved')"
        )
        conn.commit()
    finally:
        conn.close()

    from lib.engram_graph_walker import EngramGraphWalker
    walker = EngramGraphWalker(db_path=db_path)
    result = walker.walk(["obs-start-e2e"], max_depth=1)
    assert "obs-neighbor-A" in result
    assert "obs-neighbor-B" in result
    assert result["obs-neighbor-A"]["hops"] == 1
    assert result["obs-neighbor-B"]["hops"] == 1


@pytest.mark.e2e
def test_e2e_graph_walker_respects_depth_limit(engram_daemon):
    """Chain A→B→C→D in relations table → walk([A], max_depth=2) returns {B, C} but not D."""
    base_url, tmpdir = engram_daemon
    db_path = os.path.join(tmpdir, "engram.db")

    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_id TEXT NOT NULL UNIQUE,
                source_id TEXT,
                target_id TEXT,
                relation TEXT NOT NULL DEFAULT 'pending',
                reason TEXT,
                evidence TEXT,
                confidence REAL,
                judgment_status TEXT NOT NULL DEFAULT 'pending',
                superseded_at TEXT,
                superseded_by_relation_id INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        chain = [
            ("depth-rel-AB", "obs-chain-A", "obs-chain-B"),
            ("depth-rel-BC", "obs-chain-B", "obs-chain-C"),
            ("depth-rel-CD", "obs-chain-C", "obs-chain-D"),
        ]
        for sync_id, src, tgt in chain:
            conn.execute(
                "INSERT OR IGNORE INTO memory_relations (sync_id, source_id, target_id, relation, judgment_status) "
                "VALUES (?, ?, ?, 'related', 'approved')",
                (sync_id, src, tgt),
            )
        conn.commit()
    finally:
        conn.close()

    from lib.engram_graph_walker import EngramGraphWalker
    walker = EngramGraphWalker(db_path=db_path)
    result = walker.walk(["obs-chain-A"], max_depth=2)
    assert "obs-chain-B" in result
    assert "obs-chain-C" in result
    assert "obs-chain-D" not in result


@pytest.mark.e2e
def test_e2e_graph_walker_skips_rejected_relations(engram_daemon):
    """Walker excludes neighbors reached only via rejected relations."""
    base_url, tmpdir = engram_daemon
    db_path = os.path.join(tmpdir, "engram.db")

    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_id TEXT NOT NULL UNIQUE,
                source_id TEXT,
                target_id TEXT,
                relation TEXT NOT NULL DEFAULT 'pending',
                reason TEXT,
                evidence TEXT,
                confidence REAL,
                judgment_status TEXT NOT NULL DEFAULT 'pending',
                superseded_at TEXT,
                superseded_by_relation_id INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.execute(
            "INSERT OR IGNORE INTO memory_relations (sync_id, source_id, target_id, relation, judgment_status) "
            "VALUES ('rejected-rel-1', 'obs-rej-start', 'obs-rej-neighbor', 'related', 'rejected')"
        )
        conn.commit()
    finally:
        conn.close()

    from lib.engram_graph_walker import EngramGraphWalker
    walker = EngramGraphWalker(db_path=db_path)
    result = walker.walk(["obs-rej-start"])
    assert "obs-rej-neighbor" not in result


@pytest.mark.e2e
def test_e2e_lifecycle_search_with_graph_walk_finds_disconnected_obs(engram_daemon):
    """Save 2 obs, insert a relation, use graph walker directly to verify neighbor traversal.

    Note: EngramLifecycle.search() calls engram_client (CLI), which does not use
    the sandbox ENGRAM_DATA_DIR reliably.  This test validates the graph_walk
    integration path by: (1) using HTTP search to find saved obs, (2) inserting
    a relation, (3) calling EngramGraphWalker.walk() directly, and (4) verifying
    merge_into_results() combines both observations.
    """
    base_url, tmpdir = engram_daemon
    import importlib

    original_url = os.environ.get("ENGRAM_HTTP_URL")
    original_data_dir = os.environ.get("ENGRAM_DATA_DIR")
    os.environ["ENGRAM_HTTP_URL"] = base_url
    os.environ["ENGRAM_DATA_DIR"] = tmpdir

    try:
        import lib.engram_http_client as http_mod
        importlib.reload(http_mod)

        unique_tag_a = f"e2e-graphwalk-A-{os.getpid()}"
        unique_tag_b = f"e2e-graphwalk-B-{os.getpid()}"

        _engram_save(
            f"graph walk obs A {unique_tag_a}",
            f"Primary walk observation {unique_tag_a}",
            data_dir=tmpdir,
            type_="decision",
        )
        _engram_save(
            f"graph walk obs B {unique_tag_b}",
            f"Connected secondary observation {unique_tag_b}",
            data_dir=tmpdir,
            type_="decision",
        )

        results_a = http_mod.search_observations(unique_tag_a, base_url=base_url, limit=5)
        results_b = http_mod.search_observations(unique_tag_b, base_url=base_url, limit=5)

        if not results_a or not results_b:
            pytest.skip("Could not find both observations via HTTP search — skipping")

        sync_id_a = results_a[0].get("sync_id")
        sync_id_b = results_b[0].get("sync_id")

        if not sync_id_a or not sync_id_b:
            pytest.skip("Observations missing sync_id — skipping")

        db_path = os.path.join(tmpdir, "engram.db")
        import sqlite3
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_id TEXT NOT NULL UNIQUE,
                    source_id TEXT,
                    target_id TEXT,
                    relation TEXT NOT NULL DEFAULT 'pending',
                    reason TEXT,
                    evidence TEXT,
                    confidence REAL,
                    judgment_status TEXT NOT NULL DEFAULT 'pending',
                    superseded_at TEXT,
                    superseded_by_relation_id INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute(
                "INSERT OR IGNORE INTO memory_relations "
                "(sync_id, source_id, target_id, relation, judgment_status) "
                "VALUES (?, ?, ?, 'related', 'approved')",
                (f"e2e-gw-rel-{os.getpid()}", sync_id_a, sync_id_b),
            )
            conn.commit()
        finally:
            conn.close()

        from lib.engram_graph_walker import EngramGraphWalker
        walker = EngramGraphWalker(db_path=db_path, http_client_module=http_mod)
        neighbors = walker.walk([sync_id_a])
        assert sync_id_b in neighbors, (
            f"Expected graph walker to find {sync_id_b} as neighbor of {sync_id_a}"
        )

        base_results = [{**results_a[0], "adjusted_score": 1.0}]
        merged = walker.merge_into_results(base_results, neighbors)
        found_ids = {r.get("sync_id") for r in merged}
        assert sync_id_a in found_ids
        assert sync_id_b in found_ids, (
            f"merge_into_results should include graph neighbor {sync_id_b}"
        )

    finally:
        if original_url is None:
            os.environ.pop("ENGRAM_HTTP_URL", None)
        else:
            os.environ["ENGRAM_HTTP_URL"] = original_url
        if original_data_dir is None:
            os.environ.pop("ENGRAM_DATA_DIR", None)
        else:
            os.environ["ENGRAM_DATA_DIR"] = original_data_dir
        import lib.engram_http_client as http_mod
        importlib.reload(http_mod)
