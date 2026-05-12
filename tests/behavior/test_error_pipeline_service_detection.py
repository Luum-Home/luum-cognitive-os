"""Behavior tests for hooks/error-pipeline.sh service detection.

These verify the post-Tier-1-portability-refactor contract: service detection
is config-driven via .cognitive-os/private/service-map.yaml; absent that,
detection falls back to the basename of `cd <dir>` in the command. No
downstream consumer-project identifiers are hardcoded in the hook.
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path



HOOK = Path(__file__).resolve().parent.parent.parent / "hooks" / "error-pipeline.sh"


def _extract_detect_service(hook_path: Path) -> str:
    """Pull the detect_service() function body out of the hook for isolated test."""
    src = hook_path.read_text()
    start = src.index("detect_service() {")
    # walk until matching closing brace at column 0
    end = src.index("\n}\n", start) + 3
    return src[start:end]


def _run_detect(tmp_path: Path, cmd: str, working_directory: str = "",
                service_map_yaml: str | None = None) -> str:
    """Run detect_service in a sandbox and return the printed service name."""
    project_dir = tmp_path / "proj"
    (project_dir / ".cognitive-os" / "private").mkdir(parents=True)

    if service_map_yaml is not None:
        (project_dir / ".cognitive-os" / "private" / "service-map.yaml").write_text(
            service_map_yaml
        )

    func = _extract_detect_service(HOOK)
    payload = json.dumps({"tool_input": {"working_directory": working_directory}})

    script = textwrap.dedent(f"""
        set -uo pipefail
        PROJECT_DIR={project_dir!s}
        {func}
        detect_service "$1" "$2"
    """)

    result = subprocess.run(
        ["bash", "-c", script, "_", cmd, payload],
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, "PROJECT_DIR": str(project_dir)},
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    return result.stdout.strip()


def test_unknown_when_no_map_and_no_cd(tmp_path):
    """Absent service-map.yaml and no `cd <dir>` token -> 'unknown'."""
    out = _run_detect(tmp_path, cmd="go test ./...")
    assert out == "unknown"


def test_cd_fallback_extracts_basename(tmp_path):
    """No map, but command contains `cd <dir>` -> basename of dir."""
    out = _run_detect(tmp_path, cmd="cd services/api-gateway && go build")
    assert out == "api-gateway"


def test_cd_fallback_works_with_absolute_path(tmp_path):
    out = _run_detect(tmp_path, cmd="cd /opt/work/billing && pytest")
    assert out == "billing"


def test_custom_service_map_match(tmp_path):
    """Custom service-map entry whose regex matches the command -> that name."""
    yaml = textwrap.dedent("""
        services:
          - name: payments-svc
            match: 'payments|pay-svc'
          - name: billing-svc
            match: 'billing'
    """).strip()
    out = _run_detect(tmp_path, cmd="go test ./payments/...", service_map_yaml=yaml)
    assert out == "payments-svc"


def test_custom_service_map_first_match_wins(tmp_path):
    """Order matters: first matching entry wins."""
    yaml = textwrap.dedent("""
        services:
          - name: alpha
            match: 'svc'
          - name: beta
            match: 'svc'
    """).strip()
    out = _run_detect(tmp_path, cmd="go test ./svc/...", service_map_yaml=yaml)
    assert out == "alpha"


def test_no_fallback_table_when_map_missing(tmp_path):
    """Legacy hardcoded service names are NOT detected
    when no service-map is present and no cd <dir> token appears. This is
    the regression guard for the Tier-1 portability refactor."""
    out = _run_detect(tmp_path, cmd="go test ./legacy-service-alpha/...")
    # Without a service-map and without a `cd <dir>`, we get unknown -- the
    # previous hardcoded fallback would have returned the legacy service name.
    assert out == "unknown"


def test_service_map_works_against_working_directory(tmp_path):
    """Match regex is applied against command + working_directory."""
    yaml = textwrap.dedent("""
        services:
          - name: orders-api
            match: 'orders'
    """).strip()
    out = _run_detect(
        tmp_path,
        cmd="go test ./...",
        working_directory="/repo/services/orders",
        service_map_yaml=yaml,
    )
    assert out == "orders-api"
