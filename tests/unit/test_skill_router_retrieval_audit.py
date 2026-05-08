from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "skill-router-retrieval-audit.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_audit(repo: Path, manifest: Path) -> dict:
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(repo), "--manifest", str(manifest), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout, proc.stderr
    payload = json.loads(proc.stdout)
    payload["returncode"] = proc.returncode
    return payload


def minimal_manifest(extra: str = "") -> str:
    return f"""
schema_version: skill-router-retrieval/v1
policy:
  core_router: lib/skill_router.py
  default_adapter: regex_frontmatter
forbidden_core_imports:
  - module: langchain
    rationale: heavy
adapters:
  - id: regex_frontmatter
    status: active
    default: true
    implementation: lib/skill_router.py
    license_spdx: project
    footprint: zero-extra-deps
    hot_path_allowed: true
    community_pattern: regex/frontmatter
    benchmark_required: true
benchmark:
  script: scripts/skill-router-benchmark.py
  fixtures:
    - id: false-positive
      prompt: "router suggested /auto-rollback"
      expected: none
    - id: positive
      prompt: "audit repo"
      expected_command: /repo-forensics
{extra}
"""


def test_current_repo_skill_router_retrieval_audit_passes() -> None:
    root = SCRIPT.parents[1]
    proc = subprocess.run(["python3", str(SCRIPT), "--project-dir", str(root), "--json"], text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "skill-router-retrieval-audit/v1"
    assert payload["status"] == "pass"
    assert payload["summary"]["adapters"] >= 3


def test_blocks_optional_retrieval_stack_import_in_core_router(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "lib" / "skill_router.py", "import langchain\n")
    write(repo / "scripts" / "skill-router-benchmark.py", "#!/usr/bin/env python3\n")
    manifest = repo / "manifest.yaml"
    write(manifest, minimal_manifest())

    payload = run_audit(repo, manifest)

    assert payload["status"] == "block"
    assert any(f["code"] == "forbidden-core-retrieval-import" for f in payload["findings"])


def test_blocks_missing_default_adapter(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "lib" / "skill_router.py", "import re\n")
    write(repo / "scripts" / "skill-router-benchmark.py", "#!/usr/bin/env python3\n")
    manifest = repo / "manifest.yaml"
    write(manifest, minimal_manifest().replace("default: true", "default: false"))

    payload = run_audit(repo, manifest)

    assert payload["status"] == "block"
    assert any(f["code"] == "default-adapter-cardinality" for f in payload["findings"])


def test_blocks_manifest_without_false_positive_fixture(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "lib" / "skill_router.py", "import re\n")
    write(repo / "scripts" / "skill-router-benchmark.py", "#!/usr/bin/env python3\n")
    manifest = repo / "manifest.yaml"
    write(
        manifest,
        minimal_manifest().replace(
            "    - id: false-positive\n      prompt: \"router suggested /auto-rollback\"\n      expected: none\n",
            "",
        ),
    )

    payload = run_audit(repo, manifest)

    assert payload["status"] == "block"
    assert any(f["code"] == "benchmark-false-positive-fixture-missing" for f in payload["findings"])
