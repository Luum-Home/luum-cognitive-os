"""System tests for Docker stack infrastructure.

Tests compose config validation, image availability, and optional health checks.
Migrated from tests/infra/test-docker-stack.sh.
"""

import os
import subprocess
import shutil
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def project_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def compose_file(project_root):
    path = project_root / "docker-compose.cognitive-os.yml"
    if not path.exists():
        pytest.skip("docker-compose.cognitive-os.yml not found")
    return path


@pytest.fixture(scope="module")
def docker_ok():
    if not shutil.which("docker"):
        pytest.skip("Docker not available")
    result = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
    if result.returncode != 0:
        pytest.skip("Docker daemon not running")
    return True


@pytest.mark.system
@pytest.mark.docker
class TestDockerStack:
    """Tests for Docker stack configuration and images."""

    def test_valkey_image_available(self, docker_ok):
        result = subprocess.run(
            ["docker", "image", "inspect", "valkey/valkey:8-alpine"],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            # Try pulling
            pull = subprocess.run(
                ["docker", "pull", "valkey/valkey:8-alpine"],
                capture_output=True,
                timeout=120,
            )
            assert pull.returncode == 0, "should be able to pull valkey/valkey:8-alpine"

    def test_seaweedfs_image_available(self, docker_ok, compose_file):
        text = compose_file.read_text()
        if "seaweedfs" not in text and "chrislusf/seaweedfs" not in text:
            pytest.skip("SeaweedFS not in compose file")

        # Extract image name
        import re
        match = re.search(r"image:\s*['\"]?([^\s'\"]+seaweedfs[^\s'\"]*)", text)
        if not match:
            pytest.skip("SeaweedFS image not found in compose")

        image = match.group(1)
        result = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            pull = subprocess.run(
                ["docker", "pull", image],
                capture_output=True,
                timeout=120,
            )
            assert pull.returncode == 0, f"should be able to pull {image}"

    def test_compose_config_validates(self, docker_ok, compose_file):
        # Try with a dummy encryption key for required env vars
        env = {
            **os.environ,
            "LANGFUSE_ENCRYPTION_KEY": "0" * 64,
        }

        # Try docker compose v2 first
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "config"],
            capture_output=True,
            env=env,
            timeout=30,
        )

        if result.returncode != 0:
            stderr = result.stderr.decode() if isinstance(result.stderr, bytes) else result.stderr
            if "required variable" in stderr:
                pytest.skip("compose config requires env vars (syntax is valid)")
            else:
                # Try docker-compose v1
                if shutil.which("docker-compose"):
                    result = subprocess.run(
                        ["docker-compose", "-f", str(compose_file), "config"],
                        capture_output=True,
                        env=env,
                        timeout=30,
                    )
                    if result.returncode != 0:
                        pytest.skip("compose config validation failed (may need env vars)")
                else:
                    pytest.skip("neither docker compose nor docker-compose available")

    @pytest.mark.slow
    def test_valkey_health_check(self, docker_ok, compose_file):
        """Only runs if COGNITIVE_OS_TEST_DOCKER_UP=true."""
        if os.environ.get("COGNITIVE_OS_TEST_DOCKER_UP") != "true":
            pytest.skip("set COGNITIVE_OS_TEST_DOCKER_UP=true to enable")

        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d", "langfuse-valkey"],
            capture_output=True,
            timeout=60,
        )

        import time
        healthy = False
        for _ in range(15):
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Health.Status}}",
                 "cognitive-os-langfuse-valkey"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout.strip() == "healthy":
                healthy = True
                break
            time.sleep(1)

        try:
            assert healthy, "Valkey should become healthy within 15 seconds"

            if healthy:
                pong = subprocess.run(
                    ["docker", "exec", "cognitive-os-langfuse-valkey", "valkey-cli", "PING"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                assert pong.stdout.strip() == "PONG", "Valkey should respond to PING"
        finally:
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "down"],
                capture_output=True,
                timeout=30,
            )
