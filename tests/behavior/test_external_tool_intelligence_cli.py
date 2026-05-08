from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_script(name: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(ROOT / "scripts" / name), *args], cwd=cwd or ROOT, text=True, capture_output=True, check=False)


def test_cos_tool_inventory_cli_json(tmp_path: Path) -> None:
    write(tmp_path / "requirements.txt", "fastmcp>=1\n")

    proc = run_script("cos-tool-inventory", "--repo", str(tmp_path), "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "external-tool-inventory/v1"
    assert any(item["id"] == "fastmcp" for item in payload["items"])


def test_cos_tool_adoption_audit_cli_detects_findings(tmp_path: Path) -> None:
    write(tmp_path / "requirements.txt", "litellm>=1\n")
    manifest = tmp_path / "manifest.yaml"
    write(
        manifest,
        """
schema_version: external-tools-adoption/v1
tools:
  - id: litellm
    verdict: REMOVE
    package_names: [litellm]
    evidence: {consumers: [], tests: []}
""",
    )

    proc = run_script("cos-tool-adoption-audit", "--repo", str(tmp_path), "--manifest", str(manifest), "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "block"
    assert payload["findings"][0]["code"] == "removed-tool-still-used"


def test_cos_tool_radar_render_cli_combined(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    overlay = tmp_path / "overlay.yaml"
    write(
        manifest,
        """
schema_version: external-tools-adoption/v1
tools:
  - id: semgrep
    verdict: INTEGRATE
    domain: security
    package_names: [semgrep]
""",
    )
    write(
        overlay,
        """
schema_version: cos-project-tool-overlay/v1
local_tools:
  - id: semgrep
    source: os-radar
    local_status: enabled
    reason: security CI
""",
    )

    proc = run_script("cos-tool-radar-render", "--manifest", str(manifest), "--overlay", str(overlay), "--mode", "combined", "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "combined"
    assert payload["effective_project_view"][0]["cos_verdict"] == "INTEGRATE"


def test_cos_tool_research_check_cli_blocks_incomplete_packet(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.yaml"
    write(candidate, "id: new-tool\nlicense: MIT\n")

    proc = run_script("cos-tool-research-check", str(candidate), "--json")

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "external-tool-research-check/v1"
    assert payload["status"] == "block"
