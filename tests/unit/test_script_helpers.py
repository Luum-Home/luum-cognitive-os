from __future__ import annotations

import json
from pathlib import Path

from lib.primitive_file_inventory import primitive_files
from lib.script_helpers import object_map, object_maps, read_json_or, read_yaml_dict, sha256_file, shingles


def test_script_helpers_parse_files_and_shape_values(tmp_path: Path) -> None:
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text("enabled: true\n", encoding="utf-8")
    json_path = tmp_path / "row.json"
    json_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
    blob = tmp_path / "blob.txt"
    blob.write_text("hello", encoding="utf-8")

    assert read_yaml_dict(yaml_path) == {"enabled": True}
    assert read_json_or(json_path, {}) == {"ok": True}
    assert read_json_or(tmp_path / "missing.json", {"fallback": True}) == {"fallback": True}
    assert sha256_file(blob) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert object_map({"a": 1}) == {"a": 1}
    assert object_map(["nope"]) == {}
    assert object_maps([{"a": 1}, "skip", {"b": 2}]) == [{"a": 1}, {"b": 2}]


def test_shingles_and_primitive_file_inventory(tmp_path: Path) -> None:
    assert shingles(["a", "b", "c"], 2) == {"a b", "b c"}
    assert shingles(["a"], 2) == {"a"}

    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "sample.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (tmp_path / "skills" / "demo").mkdir(parents=True)
    (tmp_path / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
    (tmp_path / "skills" / "demo" / "notes.md").write_text("not a primitive skill entry\n", encoding="utf-8")

    found = {path.relative_to(tmp_path).as_posix() for path in primitive_files(tmp_path)}
    assert "hooks/sample.sh" in found
    assert "skills/demo/SKILL.md" in found
    assert "skills/demo/notes.md" not in found
