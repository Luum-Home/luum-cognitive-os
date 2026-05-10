from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "dashboard"
BUNDLED_NODE = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin"


def test_dashboard_menu_links_real_primitive_runtime_page() -> None:
    sidebar = (ROOT / "dashboard" / "components" / "sidebar.tsx").read_text(encoding="utf-8")
    page = (ROOT / "dashboard" / "app" / "primitives" / "page.tsx").read_text(encoding="utf-8")
    api = (ROOT / "dashboard" / "lib" / "cos-api.ts").read_text(encoding="utf-8")

    assert '{ name: "Primitives", href: "/primitives" }' in sidebar
    assert 'title="Primitive Runtime"' in page
    assert "getPrimitiveProjectionFidelitySummary" in page
    assert "getOpenCodePrimitiveAdapterSmokeSummary" in page
    assert "getPortableAiConsumerSmokeSummary" in page
    assert "getPrimitiveServiceHeadlessSmokeSummary" in page
    assert "getPrimitiveProjectionDrilldown" in page
    assert "getPrimitiveRuntimeEvidenceSummary" in page
    assert "Projection Status Filters" in page
    assert "Runtime Session Drilldown" in page
    assert "Promotion Gaps" in page
    assert "Evidence Links" in page
    assert "Lifecycle-derived" in page
    assert "primitive-projection-fidelity-latest.json" in api
    assert "opencode-primitive-adapter-smoke-latest.json" in api
    assert "portable-ai-consumer-smoke-latest.json" in api
    assert "codebase-itinerary.jsonl" in api
    assert "primitive-interventions.jsonl" in api
    assert "primitive-service-headless-smoke-latest.json" in api


@pytest.mark.timeout(90)
def test_dashboard_builds_primitive_runtime_route() -> None:
    next_bin = DASHBOARD / "node_modules" / ".bin" / "next"
    if not next_bin.exists():
        pytest.skip("dashboard node_modules/.bin/next is unavailable")

    env = os.environ.copy()
    if BUNDLED_NODE.exists():
        env["PATH"] = f"{BUNDLED_NODE}:{env.get('PATH', '')}"

    result = subprocess.run(
        [str(next_bin), "build"],
        cwd=DASHBOARD,
        text=True,
        capture_output=True,
        env=env,
        check=False,
        timeout=90,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "/primitives" in result.stdout
