"""
Static checks for the preserved test-lanes workflow lane-registry integration.

Verifies:
1. Every lane in .cognitive-os/test-lanes.yaml falls into exactly one of
   {parallel-safe, serial-stateful, optional}.
2. The preserved workflow YAML exists, parses, and contains the 4 expected jobs
   (setup, parallel-safe, serial-stateful, optional-lanes).
3. Hardcoded lane lists are absent from the workflow file (the matrix must
   use fromJson expressions, not inline arrays).
4. The setup job emits the 3 required outputs.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[2]
LANES_REGISTRY = REPO_ROOT / ".cognitive-os" / "test-lanes.yaml"


def workflow_file(name: str) -> Path:
    """Return active workflow when present, otherwise the ADR-130 preserved disabled file."""
    active = REPO_ROOT / ".github" / "workflows" / name
    if active.exists():
        return active
    disabled = active.with_name(active.name + ".disabled")
    return disabled


WORKFLOW_FILE = workflow_file("test-lanes.yml")


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def lanes() -> dict:
    """Return the raw lanes dict from the registry."""
    assert LANES_REGISTRY.exists(), f"Lane registry not found: {LANES_REGISTRY}"
    data = yaml.safe_load(LANES_REGISTRY.read_text())
    assert "lanes" in data, "Registry YAML must have a top-level 'lanes' key"
    return data["lanes"]


@pytest.fixture(scope="module")
def workflow() -> dict:
    """Return the parsed workflow YAML."""
    assert WORKFLOW_FILE.exists(), f"Workflow file not found: {WORKFLOW_FILE}"
    return yaml.safe_load(WORKFLOW_FILE.read_text())


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return WORKFLOW_FILE.read_text()


# ── Lane registry classification tests ────────────────────────────────────────


class TestLaneClassification:
    def test_every_lane_has_parallel_field(self, lanes):
        missing = [n for n, cfg in lanes.items() if "parallel" not in cfg]
        assert not missing, f"Lanes missing 'parallel' field: {missing}"

    def test_every_lane_in_exactly_one_group(self, lanes):
        """Each lane is parallel XOR serial XOR optional — no overlap, no gap."""
        for name, cfg in lanes.items():
            is_optional = bool(cfg.get("optional"))
            is_parallel = cfg.get("parallel") is True
            is_serial = cfg.get("parallel") is False

            if is_optional:
                # Optional lanes may have any parallel value; they belong to the
                # optional group regardless.
                continue

            assert is_parallel or is_serial, (
                f"Lane '{name}' is not optional but has parallel={cfg.get('parallel')!r} "
                "(must be True or False)"
            )

    def test_parallel_lanes_are_non_optional(self, lanes):
        parallel = [n for n, c in lanes.items() if c.get("parallel") is True and not c.get("optional")]
        assert parallel, "Expected at least one non-optional parallel lane"

    def test_serial_lanes_are_non_optional(self, lanes):
        serial = [n for n, c in lanes.items() if c.get("parallel") is False and not c.get("optional")]
        assert serial, "Expected at least one non-optional serial lane"

    def test_optional_group_non_empty(self, lanes):
        optional = [n for n, c in lanes.items() if c.get("optional")]
        assert optional, "Expected at least one optional lane"

    def test_lane_groups_are_disjoint(self, lanes):
        parallel = {n for n, c in lanes.items() if c.get("parallel") is True and not c.get("optional")}
        serial = {n for n, c in lanes.items() if c.get("parallel") is False and not c.get("optional")}
        optional = {n for n, c in lanes.items() if c.get("optional")}

        assert parallel & serial == set(), f"Lanes in both parallel and serial: {parallel & serial}"
        assert parallel & optional == set(), f"Lanes in both parallel and optional: {parallel & optional}"
        assert serial & optional == set(), f"Lanes in both serial and optional: {serial & optional}"


# ── Workflow structure tests ───────────────────────────────────────────────────


class TestWorkflowStructure:
    def test_workflow_parses_as_yaml(self, workflow):
        assert isinstance(workflow, dict)

    def test_workflow_has_required_jobs(self, workflow):
        jobs = set(workflow.get("jobs", {}).keys())
        required = {"setup", "parallel-safe", "serial-stateful", "optional-lanes"}
        missing = required - jobs
        assert not missing, f"Workflow missing jobs: {missing}"

    def test_setup_job_has_3_outputs(self, workflow):
        outputs = workflow["jobs"]["setup"].get("outputs", {})
        assert set(outputs.keys()) == {"parallel-lanes", "serial-lanes", "optional-lanes"}, (
            f"setup job outputs mismatch: {set(outputs.keys())}"
        )

    def test_parallel_safe_uses_fromjson(self, workflow):
        matrix = workflow["jobs"]["parallel-safe"]["strategy"]["matrix"]
        lane_value = matrix["lane"]
        # In parsed YAML the fromJson expression is a plain string
        assert isinstance(lane_value, str) and "fromJson" in lane_value, (
            f"parallel-safe matrix.lane must use fromJson expression, got: {lane_value!r}"
        )

    def test_serial_stateful_uses_fromjson(self, workflow):
        matrix = workflow["jobs"]["serial-stateful"]["strategy"]["matrix"]
        lane_value = matrix["lane"]
        assert isinstance(lane_value, str) and "fromJson" in lane_value, (
            f"serial-stateful matrix.lane must use fromJson expression, got: {lane_value!r}"
        )

    def test_optional_lanes_uses_fromjson(self, workflow):
        matrix = workflow["jobs"]["optional-lanes"]["strategy"]["matrix"]
        lane_value = matrix["lane"]
        assert isinstance(lane_value, str) and "fromJson" in lane_value, (
            f"optional-lanes matrix.lane must use fromJson expression, got: {lane_value!r}"
        )

    def test_no_hardcoded_lane_list_in_matrix(self, workflow_text):
        """The workflow must not contain inline lane arrays like [unit, audit, ...]."""
        # Match YAML inline sequences that look like lane names inside matrix blocks.
        # A legitimate fromJson expression is a string; inline YAML lists parse
        # differently. We check the raw text for the specific old-style patterns.
        old_parallel = re.search(r"lane:\s*\[unit,\s*audit", workflow_text)
        old_serial = re.search(r"lane:\s*\[integration,\s*behavior", workflow_text)
        old_optional = re.search(r"lane:\s*\[arena,\s*benchmark", workflow_text)

        assert not old_parallel, "Found hardcoded parallel lane list [unit, audit, …]"
        assert not old_serial, "Found hardcoded serial lane list [integration, behavior, …]"
        assert not old_optional, "Found hardcoded optional lane list [arena, benchmark, …]"

    def test_downstream_jobs_need_setup(self, workflow):
        for job_name in ("parallel-safe", "serial-stateful", "optional-lanes"):
            needs = workflow["jobs"][job_name].get("needs", [])
            if isinstance(needs, str):
                needs = [needs]
            assert "setup" in needs, f"Job '{job_name}' must list 'setup' in needs"

    def test_setup_job_parse_step_present(self, workflow_text):
        """The setup job must contain a Python heredoc that reads the YAML registry."""
        assert "test-lanes.yaml" in workflow_text, (
            "setup job parse step must reference .cognitive-os/test-lanes.yaml"
        )
        assert "yaml.safe_load" in workflow_text, (
            "setup job parse step must call yaml.safe_load"
        )


# ── Cross-consistency: registry lanes match workflow grouping logic ────────────


class TestRegistryWorkflowConsistency:
    """Run the same classification logic the workflow script uses and check
    that at least one lane lands in each group."""

    def _classify(self, lanes):
        parallel = [n for n, c in lanes.items() if c.get("parallel") is True and not c.get("optional")]
        serial = [n for n, c in lanes.items() if c.get("parallel") is False and not c.get("optional")]
        optional = [n for n, c in lanes.items() if c.get("optional")]
        return parallel, serial, optional

    def test_groups_cover_all_lanes(self, lanes):
        parallel, serial, optional = self._classify(lanes)
        classified = set(parallel) | set(serial) | set(optional)
        all_lanes = set(lanes.keys())
        uncovered = all_lanes - classified
        assert not uncovered, f"Lanes not covered by any group: {uncovered}"

    def test_groups_are_json_serialisable(self, lanes):
        parallel, serial, optional = self._classify(lanes)
        # GitHub Actions requires JSON arrays for matrix inputs
        assert json.dumps(parallel)
        assert json.dumps(serial)
        assert json.dumps(optional)
