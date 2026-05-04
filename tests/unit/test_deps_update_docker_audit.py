import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "deps-update.sh"
PYTHON = shutil.which("python3") or "/usr/bin/python3"


def _run_deps_update_with_fake_docker(tmp_path: Path, compose: str, docker_script: str) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "deps-update.sh").write_text(SCRIPT.read_text())
    (repo / "docker-compose.cognitive-os.yml").write_text(compose)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "python3").symlink_to(PYTHON)
    docker = fake_bin / "docker"
    docker.write_text(docker_script)
    docker.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin"
    return subprocess.run(
        ["bash", str(scripts / "deps-update.sh"), "--audit"],
        cwd=repo,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_digest_pinned_images_are_not_reported_as_newer_digest_candidates(tmp_path: Path) -> None:
    result = _run_deps_update_with_fake_docker(
        tmp_path,
        "services:\n  db:\n    image: postgres:17-alpine@sha256:abc123\n",
        """#!/usr/bin/env bash
if [ "$1" = "inspect" ]; then
  echo 'postgres@sha256:abc123'
  exit 0
fi
exit 1
""",
    )

    assert result.returncode == 0, result.stderr
    assert "status: pinned digest reference" in result.stdout
    assert "may have newer digest" not in result.stdout
    assert "Docker:   0 floating tag update candidate(s), 0 unverified, 1 pinned exact reference(s)" in result.stdout


def test_floating_tag_digest_mismatch_is_actionable_review_candidate(tmp_path: Path) -> None:
    result = _run_deps_update_with_fake_docker(
        tmp_path,
        "services:\n  paperclip:\n    image: reeoss/paperclipai-paperclip:latest\n",
        """#!/usr/bin/env bash
if [ "$1" = "inspect" ]; then
  echo 'reeoss/paperclipai-paperclip@sha256:old'
  exit 0
fi
if [ "$1" = "buildx" ] && [ "$2" = "version" ]; then
  exit 0
fi
if [ "$1" = "buildx" ] && [ "$2" = "imagetools" ] && [ "$3" = "inspect" ]; then
  echo 'Name:      docker.io/reeoss/paperclipai-paperclip:latest'
  echo 'Digest:    sha256:new'
  exit 0
fi
exit 1
""",
    )

    assert result.returncode == 0, result.stderr
    assert "REVIEW: floating tag digest differs" in result.stdout
    assert "Docker:   1 floating tag update candidate(s), 0 unverified, 0 pinned exact reference(s)" in result.stdout
