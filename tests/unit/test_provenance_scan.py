from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "provenance_scan.py"


def run_scan(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--json", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def write_config(root: Path, body: str = "") -> Path:
    path = root / "manifests" / "provenance-scan.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "schema_version: provenance-scan/v1\n"
        "provenance:\n"
        "  forbidden_terms: [FinOpenPOS, private-core]\n"
        "  allowed_absolute_paths: [/tmp/]\n"
        "  allowed_import_roots:\n"
        "    go: [github.com/example/app, github.com/spf13/cobra]\n"
        "    python: [app, pytest]\n"
        "    ts: ['@example/', react]\n"
        "  forbidden_import_roots:\n"
        "    go: [github.com/private/]\n"
        "  exclude_globs: []\n"
        f"{body}",
        encoding="utf-8",
    )
    return path


def payload(proc: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(proc.stdout)


def test_blocks_local_paths_and_source_terms(tmp_path: Path) -> None:
    cfg = write_config(tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "copied from private repo FinOpenPOS at /Users/me/Projects/source\n",  # cos-allow-provenance-scan cos-allow-absolute-path cos-allow-local-privacy-pattern: deliberate scanner fixture
        encoding="utf-8",
    )

    proc = run_scan(tmp_path, "--config", str(cfg), str(doc))

    assert proc.returncode == 1
    categories = {item["category"] for item in payload(proc)["findings"]}
    assert {"forbidden-path", "forbidden-term", "provenance-language"} <= categories


def test_allows_tmp_and_marker(tmp_path: Path) -> None:
    cfg = write_config(tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "/tmp/build is acceptable\n"
        "copied from private repo X  # cos-allow-provenance-scan\n",
        encoding="utf-8",
    )

    proc = run_scan(tmp_path, "--config", str(cfg), str(doc))

    assert proc.returncode == 0, proc.stderr
    assert payload(proc)["status"] == "pass"


def test_go_import_allowlist_and_replace(tmp_path: Path) -> None:
    cfg = write_config(tmp_path)
    go_mod = tmp_path / "go.mod"
    go_mod.write_text(
        "module github.com/example/app\n\n"
        "require github.com/private/lib v0.0.0\n"
        "replace github.com/example/app/lib => /Users/me/Projects/lib\n",  # cos-allow-provenance-scan cos-allow-absolute-path cos-allow-local-privacy-pattern: deliberate scanner fixture
        encoding="utf-8",
    )
    source = tmp_path / "main.go"
    source.write_text('package main\nimport "github.com/private/lib"\n', encoding="utf-8")

    proc = run_scan(tmp_path, "--config", str(cfg), str(go_mod), str(source))

    assert proc.returncode == 1
    categories = {item["category"] for item in payload(proc)["findings"]}
    assert "forbidden-go-import" in categories
    assert "external-go-replace" in categories


def test_python_path_hack_detected(tmp_path: Path) -> None:
    cfg = write_config(tmp_path)
    source = tmp_path / "app.py"
    source.write_text("import sys\nsys.path.insert(0, '/Users/me/Projects/core')\n", encoding="utf-8")  # cos-allow-provenance-scan cos-allow-absolute-path cos-allow-local-privacy-pattern: deliberate scanner fixture

    proc = run_scan(tmp_path, "--config", str(cfg), str(source))

    assert proc.returncode == 1
    assert any(item["category"] == "python-path-hack" for item in payload(proc)["findings"])


def test_wrapper_uses_repo_script(tmp_path: Path) -> None:
    assert (ROOT / "scripts" / "provenance-scan").exists()
    assert (ROOT / "hooks" / "provenance-scan.sh").exists()


def test_ts_import_allowlist_blocks_unapproved_root(tmp_path: Path) -> None:
    cfg = write_config(tmp_path)
    source = tmp_path / "index.ts"
    source.write_text("import React from 'react'\nimport secret from '@private/sdk'\n", encoding="utf-8")

    proc = run_scan(tmp_path, "--config", str(cfg), str(source))

    assert proc.returncode == 1
    assert any(
        item["category"] == "unapproved-ts-import" and item["matched"] == "@private/sdk"
        for item in payload(proc)["findings"]
    )


def test_prefers_project_cognitive_os_config(tmp_path: Path) -> None:
    cfg = tmp_path / ".cognitive-os" / "provenance-scan.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        "schema_version: provenance-scan/v1\n"
        "provenance:\n"
        "  forbidden_terms: [PrivateThing]\n",
        encoding="utf-8",
    )
    doc = tmp_path / "README.md"
    doc.write_text("PrivateThing\n", encoding="utf-8")

    proc = run_scan(tmp_path, str(doc))

    assert proc.returncode == 1
    data = payload(proc)
    assert data["config"] == ".cognitive-os/provenance-scan.yaml"
    assert any(item["category"] == "forbidden-term" for item in data["findings"])


def test_go_replace_allows_relative_target_inside_repo(tmp_path: Path) -> None:
    cfg = write_config(tmp_path)
    nested = tmp_path / "backend" / "apps" / "api"
    nested.mkdir(parents=True)
    go_mod = nested / "go.mod"
    go_mod.write_text(
        "module github.com/example/app/backend/apps/api\n\n"
        "replace github.com/example/app => ../../..\n",
        encoding="utf-8",
    )

    proc = run_scan(tmp_path, "--config", str(cfg), str(go_mod))

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert payload(proc)["status"] == "pass"


def test_go_replace_blocks_relative_target_outside_repo(tmp_path: Path) -> None:
    cfg = write_config(tmp_path)
    go_mod = tmp_path / "module" / "go.mod"
    go_mod.parent.mkdir()
    go_mod.write_text(
        "module github.com/example/app/module\n\n"
        "replace github.com/example/app => ../../outside\n",
        encoding="utf-8",
    )

    proc = run_scan(tmp_path, "--config", str(cfg), str(go_mod))

    assert proc.returncode == 1
    assert any(item["category"] == "external-go-replace" for item in payload(proc)["findings"])


def _sha256(term: str) -> str:
    import hashlib

    return hashlib.sha256(term.lower().encode("utf-8")).hexdigest()


def test_hashed_term_policy_flags_token_without_clear_text_config(tmp_path: Path) -> None:
    cfg = write_config(tmp_path, f"  forbidden_term_sha256: [{_sha256('secret-client')}]\n")
    assert "secret-client" not in cfg.read_text(encoding="utf-8")
    doc = tmp_path / "README.md"
    doc.write_text("ported from the Secret-Client billing module\nsecretclientx is a different word\n", encoding="utf-8")

    proc = run_scan(tmp_path, "--config", str(cfg), str(doc))

    assert proc.returncode == 1
    hits = [item for item in payload(proc)["findings"] if item["category"] == "forbidden-term"]
    assert [(item["line"], item["matched"]) for item in hits] == [(1, "secret-client")]


def test_hashed_path_policy_flags_projects_path_only(tmp_path: Path) -> None:
    cfg = write_config(tmp_path, f"  forbidden_path_sha256: [{_sha256('secret-client')}]\n")
    doc = tmp_path / "README.md"
    doc.write_text(
        "see ~/Projects/secret-client/api for the original\n"  # cos-allow-absolute-path cos-allow-local-privacy-pattern: deliberate scanner fixture
        "the secret-client word outside a path is not a path finding\n",
        encoding="utf-8",
    )

    proc = run_scan(tmp_path, "--config", str(cfg), str(doc))

    assert proc.returncode == 1
    hits = [item for item in payload(proc)["findings"] if item["category"] == "forbidden-path"]
    assert [item["line"] for item in hits] == [1]


def test_hashed_policy_rejects_non_digest_entries(tmp_path: Path) -> None:
    cfg = write_config(tmp_path, "  forbidden_term_sha256: [secret-client]\n")
    doc = tmp_path / "README.md"
    doc.write_text("nothing\n", encoding="utf-8")

    proc = run_scan(tmp_path, "--config", str(cfg), str(doc))

    assert proc.returncode != 0
    assert "SHA-256" in proc.stderr
