from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_duplication_audit.py"
spec = importlib.util.spec_from_file_location("primitive_duplication_audit", MODULE_PATH)
assert spec and spec.loader
primitive_duplication_audit = importlib.util.module_from_spec(spec)
sys.modules["primitive_duplication_audit"] = primitive_duplication_audit
spec.loader.exec_module(primitive_duplication_audit)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_detects_python_function_repeat_and_common_home(tmp_path: Path) -> None:
    body = """
def shared_logic(value: str) -> str:
    normalized = value.strip().lower()
    parts = []
    for item in normalized.split('-'):
        if item:
            parts.append(item.replace('_', '-'))
    return '/'.join(parts)
"""
    write(tmp_path / "scripts/a.py", body)
    write(tmp_path / "scripts/b.py", body.replace("shared_logic", "other_logic"))

    data = primitive_duplication_audit.audit(tmp_path, ["scripts"], min_tokens=10, shingle_size=4, threshold=0.95, primitive_threshold=0.95)

    finding = next(item for item in data["findings"] if item["kind"] == "python-function-repeat")
    assert finding["recommendation"] == "extract-common-python-helper"
    assert finding["common_home"] == "lib/"


def test_detects_shell_function_repeat_with_shell_common_home(tmp_path: Path) -> None:
    fn = """
log_step() {
  local name="$1"
  local status="$2"
  printf '%s:%s\\n' "$name" "$status"
  if [ "$status" = "failed" ]; then
    return 1
  fi
  return 0
}
"""
    write(tmp_path / "hooks/a.sh", fn)
    write(tmp_path / "hooks/b.sh", fn.replace("log_step", "log_other"))

    data = primitive_duplication_audit.audit(tmp_path, ["hooks"], min_tokens=10, shingle_size=4, threshold=0.95, primitive_threshold=0.95)

    finding = next(item for item in data["findings"] if item["kind"] == "bash-function-repeat")
    assert finding["common_home"] == "hooks/_lib/"
    assert finding["consumer_relevance"] == "consumer-project-relevant"


def test_ignores_awk_blocks_that_look_like_shell_functions(tmp_path: Path) -> None:
    script = r"""
awk '
  found {
    if ($0 ~ /^[[:space:]]*-/) print
  }
' input.txt
"""
    write(tmp_path / "hooks/a.sh", script)
    write(tmp_path / "hooks/b.sh", script.replace("input.txt", "other.txt"))

    data = primitive_duplication_audit.audit(tmp_path, ["hooks"], min_tokens=10, shingle_size=4, threshold=0.95, primitive_threshold=0.95)

    assert [item for item in data["findings"] if item["kind"] == "bash-function-repeat"] == []


def test_ignores_symlink_alias_exact_copy(tmp_path: Path) -> None:
    source = tmp_path / "hooks/reaper-daemon-launcher.sh"
    alias = tmp_path / "hooks/reaper-heartbeat.sh"
    write(source, "#!/usr/bin/env bash\n" + "echo same\n" * 30)
    alias.symlink_to(source.name)

    data = primitive_duplication_audit.audit(tmp_path, ["hooks"], min_tokens=10, shingle_size=4, threshold=0.95, primitive_threshold=0.95)

    assert [item for item in data["findings"] if item["kind"] == "exact-copy"] == []
    assert data["summary"]["files_scanned"] == 1


def test_ignores_trivial_main_dispatch_wrappers(tmp_path: Path) -> None:
    left = """
def main() -> int:
    args = build_parser().parse_args(); return int(args.func(args))
"""
    right = left
    write(tmp_path / "scripts/a.py", left)
    write(tmp_path / "scripts/b.py", right)

    data = primitive_duplication_audit.audit(tmp_path, ["scripts"], min_tokens=10, shingle_size=4, threshold=0.95, primitive_threshold=0.95)

    assert [item for item in data["findings"] if item["kind"] == "python-function-repeat"] == []


def test_allowlist_can_suppress_known_finding(tmp_path: Path) -> None:
    body = """
def shared_logic(value: str) -> str:
    normalized = value.strip().lower()
    parts = []
    for item in normalized.split('-'):
        if item:
            parts.append(item.replace('_', '-'))
    return '/'.join(parts)
"""
    write(tmp_path / "scripts/a.py", body)
    write(tmp_path / "scripts/b.py", body.replace("shared_logic", "other_logic"))
    write(
        tmp_path / "manifests/primitive-duplication-allowlist.yaml",
        """
entries:
  - kind: python-function-repeat
    left: scripts/a.py::shared_logic
    right: scripts/b.py::other_logic
    action: suppress
    classification: intentional-isolation
    reason: Test fixture keeps both sides separate.
""",
    )

    data = primitive_duplication_audit.audit(
        tmp_path,
        ["scripts"],
        min_tokens=10,
        shingle_size=4,
        threshold=0.95,
        primitive_threshold=0.95,
        allowlist_path=tmp_path / "manifests/primitive-duplication-allowlist.yaml",
    )

    assert [item for item in data["findings"] if item["kind"] == "python-function-repeat"] == []


def test_detects_yaml_structural_repeat(tmp_path: Path) -> None:
    left = """
name: alpha
settings:
  enabled: true
  retries: 2
items:
  - id: one
    path: scripts/one.sh
"""
    right = """
name: beta
settings:
  enabled: false
  retries: 3
items:
  - id: two
    path: scripts/two.sh
"""
    write(tmp_path / "manifests/a.yaml", left)
    write(tmp_path / "manifests/b.yaml", right)

    data = primitive_duplication_audit.audit(tmp_path, ["manifests"], min_tokens=10, shingle_size=4, threshold=0.95, primitive_threshold=0.95)

    finding = next(item for item in data["findings"] if item["kind"] == "yaml-structural-repeat")
    assert finding["recommendation"] == "extract-manifest-base-or-profile"
    assert finding["common_home"] == "manifests/"


def test_cli_writes_reports(tmp_path: Path, monkeypatch) -> None:
    write(tmp_path / "scripts/a.py", "def a():\n    return 'same'\n" * 20)
    write(tmp_path / "scripts/b.py", "def b():\n    return 'same'\n" * 20)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "primitive_duplication_audit.py",
            "--project-root",
            str(tmp_path),
            "--include",
            "scripts",
            "--min-tokens",
            "10",
            "--threshold",
            "0.5",
        ],
    )

    assert primitive_duplication_audit.main() == 0
    assert (tmp_path / "docs/06-Daily/reports/primitive-duplication-latest.json").exists()
    assert "Primitive Duplication Audit" in (tmp_path / "docs/06-Daily/reports/primitive-duplication-latest.md").read_text(encoding="utf-8")


def test_baseline_ratchet_reports_new_findings(tmp_path: Path) -> None:
    body = """
def shared_logic(value: str) -> str:
    normalized = value.strip().lower()
    parts = []
    for item in normalized.split('-'):
        if item:
            parts.append(item.replace('_', '-'))
    return '/'.join(parts)
"""
    write(tmp_path / "scripts/a.py", body)
    write(tmp_path / "scripts/b.py", body.replace("shared_logic", "other_logic"))

    data = primitive_duplication_audit.audit(tmp_path, ["scripts"], min_tokens=10, shingle_size=4, threshold=0.95, primitive_threshold=0.95)
    baseline_path = tmp_path / "manifests/python-helper-duplication-baseline.json"
    primitive_duplication_audit.write_baseline(baseline_path, data)

    ratcheted = primitive_duplication_audit.apply_baseline_ratchet(data, baseline_path)

    assert ratcheted["ratchet"]["status"] == "pass"
    assert ratcheted["ratchet"]["new_findings"] == 0

    write(tmp_path / "scripts/c.py", body.replace("shared_logic", "third_logic"))
    changed = primitive_duplication_audit.audit(tmp_path, ["scripts"], min_tokens=10, shingle_size=4, threshold=0.95, primitive_threshold=0.95)
    changed = primitive_duplication_audit.apply_baseline_ratchet(changed, baseline_path)

    assert changed["ratchet"]["status"] == "fail"
    assert changed["ratchet"]["new_findings"] >= 1
