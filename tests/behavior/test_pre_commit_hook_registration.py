"""Behavior tests for the repository pre-commit registration gate."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.behavior, pytest.mark.timeout(30)]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRE_COMMIT = PROJECT_ROOT / ".githooks" / "pre-commit"


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_new_hook_registration_uses_security_profile_json_not_legacy_script(tmp_path: Path) -> None:
    """A hook registered in profile JSON must pass even if set-security-profile.sh is stale."""
    repo = tmp_path / "client"
    cos_root = tmp_path / "cos-root"
    repo.mkdir()

    _run(["git", "init"], repo)
    (repo / "hooks").mkdir()
    (repo / "hooks" / "new-runtime-hook.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
    _run(["git", "add", "hooks/new-runtime-hook.sh"], repo)

    (cos_root / "scripts").mkdir(parents=True)
    (cos_root / "templates" / "security-profiles").mkdir(parents=True)
    (cos_root / "scripts" / "apply-efficiency-profile.sh").write_text(
        "#!/usr/bin/env bash\n# standard hooks: new-runtime-hook.sh\n"
    )
    (cos_root / "scripts" / "set-security-profile.sh").write_text(
        "#!/usr/bin/env bash\n# intentionally stale legacy script\n"
    )
    (cos_root / "templates" / "security-profiles" / "standard.json").write_text(
        '{"hooks": [{"command": "hooks/new-runtime-hook.sh"}]}\n'
    )

    env = {**os.environ, "COS_ROOT": str(cos_root)}
    result = _run(["bash", str(PRE_COMMIT)], repo, env=env)

    assert result.returncode == 0, (
        "pre-commit should trust the generated security profile JSON source of truth, "
        f"not the stale legacy script.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
