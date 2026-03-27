"""Shared fixtures for integration tests."""
import pytest
import os

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "docker: marks tests requiring Docker")
    config.addinivalue_line("markers", "e2e: marks end-to-end tests spanning multiple services")

@pytest.fixture(scope="session")
def docker_available():
    """Check if Docker is available."""
    import shutil
    import subprocess
    if not shutil.which("docker"):
        pytest.skip("Docker not installed")
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True, timeout=10)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("Docker not running")
    return True

@pytest.fixture
def cognitive_os_env():
    """Set up Cognitive OS environment variables for testing."""
    env = {
        "COGNITIVE_OS_PROJECT_DIR": "/tmp/cognitive-os-test",
        "COGNITIVE_OS_SESSION_ID": f"test-session-{os.getpid()}",
        "OPIK_API_URL": "http://localhost:5173/api",
        "OPIK_PROJECT_NAME": "cognitive-os-test",
        "COGNEE_GRAPH_BACKEND": "networkx",
        "COGNEE_VECTOR_STORE": "lancedb",
    }
    old_env = {}
    for k, v in env.items():
        old_env[k] = os.environ.get(k)
        os.environ[k] = v
    yield env
    for k, v in old_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
