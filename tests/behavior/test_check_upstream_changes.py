from __future__ import annotations

import subprocess
from pathlib import Path


def test_check_upstream_changes_discovers_all_plugin_submodules(tmp_path: Path) -> None:
    repo = tmp_path
    source_script = Path(__file__).resolve().parents[2] / "scripts" / "check-upstream-changes.sh"
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "check-upstream-changes.sh"
    script.write_text(source_script.read_text(encoding="utf-8"), encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / ".claude" / "plugins" / "caveman").mkdir(parents=True)
    (repo / ".claude" / "plugins" / "hermes-agent").mkdir(parents=True)
    (repo / ".claude" / "plugins" / "pi-mono").mkdir(parents=True)
    (repo / ".gitmodules").write_text(
        '[submodule ".claude/plugins/hermes-agent"]\n'
        '\tpath = .claude/plugins/hermes-agent\n'
        '\turl = https://example.invalid/hermes-agent.git\n'
        '[submodule ".claude/plugins/caveman"]\n'
        '\tpath = .claude/plugins/caveman\n'
        '\turl = https://example.invalid/caveman.git\n'
        '[submodule ".claude/plugins/pi-mono"]\n'
        '\tpath = .claude/plugins/pi-mono\n'
        '\turl = https://example.invalid/pi-mono.git\n'
        '[submodule "not-a-plugin"]\n'
        '\tpath = vendor/not-a-plugin\n'
        '\turl = https://example.invalid/not-a-plugin.git\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(script)],
        cwd=repo,
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0
    assert "[caveman] Fetch failed" in result.stdout
    assert "[hermes-agent] Fetch failed" in result.stdout
    assert "[pi-mono] Fetch failed" in result.stdout
    assert "not-a-plugin" not in result.stdout
