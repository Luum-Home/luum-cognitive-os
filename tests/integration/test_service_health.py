"""Integration tests for Docker reference stacks and local health probes.

This file intentionally does NOT treat every Docker-defined service as a
default-lane runtime requirement. It validates:

1. the compose file remains syntactically valid;
2. reference/legacy stacks still exist in compose when the repo documents them;
3. `cognitive-os.yaml` classifies those stacks correctly (`cloud`, `pip`,
   `disabled`, etc.);
4. local HTTP probes only run when the corresponding stack is explicitly up.

Real stack startup belongs in the testcontainers-based integration lanes
(`tests/integration/test_e2e_flows.py`), not in this contract test.
"""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


SERVICE_CONTRACTS = (
    {
        "runtime_service": "langfuse",
        "expected_mode": "disabled",
        "classification": "legacy-reference",
        "compose_services": (
            "langfuse-pg",
            "langfuse-valkey",
            "langfuse-clickhouse",
            "langfuse-seaweedfs",
            "langfuse-worker",
            "langfuse-web",
        ),
        "profiles": (),
        "local_health": ("langfuse-web", "http://localhost:3100"),
    },
    {
        "runtime_service": "nemo_guardrails",
        "expected_mode": "pip",
        "classification": "reference-stack",
        "compose_services": ("nemo-guardrails",),
        "profiles": (),
        "local_health": ("nemo-guardrails", "http://localhost:8088/v1/rails/configs"),
    },
    {
        "runtime_service": "paperclip",
        "expected_mode": "on_demand",
        "classification": "optional-extension",
        "compose_services": ("paperclip-pg", "paperclip"),
        "profiles": (),
        "local_health": ("paperclip", "http://localhost:3200/api/health"),
    },
    {
        "runtime_service": "memu",
        "expected_mode": "pip",
        "classification": "reference-stack",
        "compose_services": ("memu",),
        "profiles": ("memory",),
        "local_health": ("memu", "http://localhost:8765/health"),
    },
    {
        "runtime_service": "opik",
        "expected_mode": "cloud",
        "classification": "reference-stack",
        "compose_services": ("opik-backend", "opik-mysql", "opik-frontend"),
        "profiles": ("observability",),
        "local_health": ("opik-backend", "http://localhost:5173/is-alive/ping"),
    },
    {
        "runtime_service": "cognee",
        "expected_mode": "pip",
        "classification": "reference-stack",
        "compose_services": ("cognee",),
        "profiles": ("memory",),
        "local_health": ("cognee", "http://localhost:8100/health"),
    },
    {
        "runtime_service": "valkey",
        "expected_mode": "on_demand",
        "classification": "optional-local-backend",
        "compose_services": ("valkey",),
        "profiles": ("legacy",),
        "local_health": ("valkey", None),
    },
    {
        "runtime_service": "jupyter",
        "expected_mode": "pip",
        "classification": "reference-stack",
        "compose_services": ("jupyter",),
        "profiles": (),
        "local_health": ("jupyter", "http://localhost:8888/api/status"),
    },
)


@pytest.fixture(scope="module")
def compose_file(project_root):
    path = project_root / "docker-compose.cognitive-os.yml"
    if not path.exists():
        pytest.skip("docker-compose.cognitive-os.yml not found")
    return path


@pytest.fixture(scope="module")
def docker_compose_available():
    if not shutil.which("docker"):
        pytest.skip("Docker not available")
    result = subprocess.run(
        ["docker", "info"], capture_output=True, timeout=10
    )
    if result.returncode != 0:
        pytest.skip("Docker daemon not running")
    return True


@pytest.fixture(scope="module")
def project_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def runtime_config(project_root):
    return yaml.safe_load((project_root / "cognitive-os.yaml").read_text(encoding="utf-8"))


def _compose_services_for_profiles(compose_file: Path, profiles: tuple[str, ...]) -> list[str]:
    cmd = ["docker", "compose", "-f", str(compose_file)]
    for profile in profiles:
        cmd.extend(["--profile", profile])
    cmd.extend(["config", "--services"])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        pytest.skip("compose config failed (likely missing env vars)")
    return [line for line in result.stdout.strip().splitlines() if line]


@pytest.mark.integration
@pytest.mark.docker
class TestServiceHealth:
    """Contract tests for reference Docker stacks and opt-in local probes."""

    def test_compose_file_validates(self, compose_file, docker_compose_available):
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "config", "--quiet"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0 and "required variable" in result.stderr:
            pytest.skip(
                "compose file requires env vars not set in test environment: "
                + result.stderr.strip().split("\n")[-1]
            )
        assert result.returncode == 0, "compose file should validate"

    @pytest.mark.parametrize(
        "contract",
        SERVICE_CONTRACTS,
        ids=[contract["runtime_service"] for contract in SERVICE_CONTRACTS],
    )
    def test_runtime_mode_matches_product_contract(self, contract, runtime_config):
        services = runtime_config["resources"]["infrastructure"]["services"]
        assert services[contract["runtime_service"]]["mode"] == contract["expected_mode"], (
            f"{contract['runtime_service']} should remain classified as "
            f"{contract['expected_mode']} in cognitive-os.yaml"
        )

    @pytest.mark.parametrize(
        "contract",
        SERVICE_CONTRACTS,
        ids=[contract["runtime_service"] for contract in SERVICE_CONTRACTS],
    )
    def test_reference_services_remain_defined_in_compose(
        self,
        contract,
        compose_file,
        docker_compose_available,
    ):
        services = _compose_services_for_profiles(compose_file, contract["profiles"])
        for service in contract["compose_services"]:
            assert service in services, (
                f"{service} should remain defined as a {contract['classification']} "
                "stack in docker-compose.cognitive-os.yml"
            )

    @pytest.mark.parametrize(
        "contract",
        SERVICE_CONTRACTS,
        ids=[contract["local_health"][0] for contract in SERVICE_CONTRACTS],
    )
    def test_local_health_probe_only_if_reference_stack_is_running(
        self,
        contract,
        docker_compose_available,
    ):
        """Probe localhost only when a developer explicitly started the stack."""
        if not HAS_REQUESTS:
            pytest.skip("requests library not installed")
        label, url = contract["local_health"]
        if url is None:
            pytest.skip(f"{label} does not expose an HTTP health endpoint")
        try:
            resp = requests.get(url, timeout=5)
            assert resp.status_code < 500, f"{label} returned {resp.status_code}"
        except requests.ConnectionError:
            pytest.skip(
                f"{label} not running locally (expected: {contract['runtime_service']} "
                f"is {contract['expected_mode']} and local Docker is only "
                f"{contract['classification']})"
            )
        except requests.Timeout:
            pytest.skip(
                f"{label} timed out (local {contract['classification']} stack may be down)"
            )
