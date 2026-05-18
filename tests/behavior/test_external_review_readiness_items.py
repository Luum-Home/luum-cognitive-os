"""
Behavioral tests for external-review-readiness-plan KEEP-OPEN items.

  A. Lean/core active surface list (--list flag on active_primitive_index.py)
  B. External-review-scenarios manifest schema validity
  C. Proof scripts: lean-core-5min-proof and strict-maintainer-concurrency-proof
     --dry-run mode emits valid JSON with expected fields.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import scripts.active_primitive_index as active_index  # noqa: E402


# ---------------------------------------------------------------------------
# A. Lean/core active surface list
# ---------------------------------------------------------------------------

class TestSurfaceList:
    def _make_manifest(self, tmp_path: Path, primitives: list[dict]) -> Path:
        manifest = tmp_path / "primitive-lifecycle.yaml"
        manifest.write_text(
            yaml.safe_dump({"schema_version": 1, "primitives": primitives}),
            encoding="utf-8",
        )
        return manifest

    def _core_primitive(self, pid: str, state: str = "advisory") -> dict:
        return {
            "id": pid,
            "kind": "hook",
            "owner_adr": "ADR-127",
            "lifecycle_state": state,
            "maturity": "advisory",
            "distribution": "core",
            "governance_class": "runtime-safety",
            "risk_class": "advisory",
            "supported_harnesses": ["claude"],
            "projection_targets": [pid],
            "evidence_commands": [],
            "rollback_or_repair_command": "remove",
            "sunset_criteria": "when no longer needed",
        }

    def test_list_returns_active_core_primitives(self, tmp_path: Path) -> None:
        """--list flag emits one line per active primitive with tab-separated tier\tid."""
        manifest = self._make_manifest(tmp_path, [
            self._core_primitive("hooks/my-guard.sh"),
            self._core_primitive("hooks/another-guard.sh", state="archived"),
        ])
        index = active_index.build_index(manifest_path=manifest, tier="core", project_root=tmp_path)
        active_primitives = [p for p in index["primitives"] if p["active"]]
        # Only the non-archived one should be active
        assert len(active_primitives) == 1
        assert active_primitives[0]["id"] == "hooks/my-guard.sh"
        assert active_primitives[0]["tier"] == "core"

    def test_print_list_output_nonempty(self, tmp_path: Path, capsys) -> None:
        """print_list emits tab-separated lines for active primitives."""
        manifest = self._make_manifest(tmp_path, [
            self._core_primitive("hooks/alpha.sh"),
            self._core_primitive("hooks/beta.sh"),
        ])
        index = active_index.build_index(manifest_path=manifest, project_root=tmp_path)
        active_index.print_list(index)
        captured = capsys.readouterr()
        lines = [ln for ln in captured.out.splitlines() if ln.strip()]
        assert len(lines) == 2, f"expected 2 active primitives, got: {captured.out!r}"
        for line in lines:
            parts = line.split("\t")
            assert len(parts) == 2, f"expected 'tier\\tid' format, got: {line!r}"
            tier, pid = parts
            assert tier == "core"
            assert pid.startswith("hooks/")

    def test_real_manifest_list_nonempty_and_contains_known_hooks(self) -> None:
        """Against the real manifest, --list returns non-empty results with known core hooks."""
        index = active_index.build_index(tier="core")
        primitives = index["primitives"]
        active = [p for p in primitives if p["active"]]
        assert len(active) > 0, "real manifest core tier has no active primitives"
        ids = {p["id"] for p in active}
        # At least one well-known core hook must appear
        known = {"hooks/destructive-git-blocker.sh", "hooks/direct-main-guard.sh"}
        overlap = known & ids
        assert overlap, (
            f"none of the expected core hooks found in active list. "
            f"Found {len(ids)} primitives; known hooks searched: {known}"
        )

    def test_main_list_flag_exits_without_crash(self, tmp_path: Path) -> None:
        """main() with --list does not raise an exception for a valid manifest."""
        manifest = self._make_manifest(tmp_path, [self._core_primitive("hooks/z.sh")])
        rc = active_index.main(["--manifest", str(manifest), "--list", "--tier", "core"])
        assert rc == 0


# ---------------------------------------------------------------------------
# B. External-review-scenarios manifest schema validation
# ---------------------------------------------------------------------------

SCENARIOS_MANIFEST = REPO_ROOT / "manifests" / "external-review-scenarios.yaml"
REQUIRED_SCENARIO_FIELDS = {"id", "description", "failure_mode", "expected_safe_action", "coverage_status", "evidence"}
REQUIRED_CONCURRENCY_SCENARIO_IDS = {"two-ides-same-branch", "two-agents-same-file", "agent-blocked-after-pre-snapshot"}


class TestScenariosManifest:
    def test_manifest_exists(self) -> None:
        assert SCENARIOS_MANIFEST.exists(), f"manifests/external-review-scenarios.yaml not found at {SCENARIOS_MANIFEST}"

    def test_manifest_is_valid_yaml(self) -> None:
        data = yaml.safe_load(SCENARIOS_MANIFEST.read_text(encoding="utf-8"))
        assert isinstance(data, dict), "manifest root must be a mapping"

    def test_manifest_has_schema_version(self) -> None:
        data = yaml.safe_load(SCENARIOS_MANIFEST.read_text(encoding="utf-8"))
        assert "schema_version" in data, "manifest must declare schema_version"

    def test_manifest_has_scenarios_list(self) -> None:
        data = yaml.safe_load(SCENARIOS_MANIFEST.read_text(encoding="utf-8"))
        assert "scenarios" in data, "manifest must have a scenarios list"
        assert isinstance(data["scenarios"], list), "scenarios must be a list"
        assert len(data["scenarios"]) >= 6, (
            f"expected at least 6 scenarios (one per Phase 4 scenario), found {len(data['scenarios'])}"
        )

    def test_each_scenario_has_required_fields(self) -> None:
        data = yaml.safe_load(SCENARIOS_MANIFEST.read_text(encoding="utf-8"))
        for scenario in data["scenarios"]:
            missing = REQUIRED_SCENARIO_FIELDS - set(scenario.keys())
            assert not missing, (
                f"scenario {scenario.get('id', '?')} missing required fields: {missing}"
            )

    def test_concurrency_scenarios_present(self) -> None:
        data = yaml.safe_load(SCENARIOS_MANIFEST.read_text(encoding="utf-8"))
        ids = {s["id"] for s in data["scenarios"]}
        missing = REQUIRED_CONCURRENCY_SCENARIO_IDS - ids
        assert not missing, f"concurrency scenarios missing from manifest: {missing}"

    def test_all_scenarios_have_evidence(self) -> None:
        data = yaml.safe_load(SCENARIOS_MANIFEST.read_text(encoding="utf-8"))
        for scenario in data["scenarios"]:
            evidence = scenario.get("evidence")
            assert evidence, f"scenario {scenario.get('id', '?')} must have non-empty evidence"
            if isinstance(evidence, dict):
                # Must have at least adr or test or notes
                assert evidence.get("adr") or evidence.get("test") or evidence.get("notes"), (
                    f"scenario {scenario.get('id', '?')} evidence must cite an adr, test, or notes"
                )


# ---------------------------------------------------------------------------
# C. Proof scripts dry-run smoke tests
# ---------------------------------------------------------------------------

import importlib.machinery
import importlib.util
import types


def _load_proof_script(name: str):
    """Load an extensionless proof script as a Python module via SourceFileLoader."""
    path = REPO_ROOT / "scripts" / name
    module_name = name.replace("-", "_")
    # If already loaded, return cached version
    if module_name in sys.modules:
        return sys.modules[module_name]
    loader = importlib.machinery.SourceFileLoader(module_name, str(path))
    spec = importlib.util.spec_from_loader(module_name, loader)
    assert spec is not None, f"could not create spec for {path}"
    module = types.ModuleType(module_name)
    module.__spec__ = spec
    module.__file__ = str(path)
    module.__loader__ = loader
    # Must register before exec_module so @dataclass can resolve module namespace
    sys.modules[module_name] = module
    try:
        loader.exec_module(module)
    except Exception:
        del sys.modules[module_name]
        raise
    return module


class TestLeanCore5MinProof:
    def test_dry_run_exits_zero(self) -> None:
        mod = _load_proof_script("cos-lean-core-5min-proof")
        rc = mod.main(["--dry-run"])
        assert rc == 0, "dry-run should exit 0"

    def test_dry_run_json_is_valid(self, capsys) -> None:
        mod = _load_proof_script("cos-lean-core-5min-proof")
        rc = mod.main(["--dry-run", "--json"])
        captured = capsys.readouterr()
        assert rc == 0
        data = json.loads(captured.out)
        assert data["status"] == "dry-run"
        assert data["proof"] == "lean-core-5min"
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) > 0

    def test_dry_run_json_has_residual_debt(self, capsys) -> None:
        mod = _load_proof_script("cos-lean-core-5min-proof")
        mod.main(["--dry-run", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data.get("residual_debt"), list)
        assert len(data["residual_debt"]) > 0

    def test_invalid_timeout_returns_2(self) -> None:
        mod = _load_proof_script("cos-lean-core-5min-proof")
        rc = mod.main(["--dry-run", "--timeout", "5"])
        assert rc == 2


class TestStrictMaintainerConcurrencyProof:
    def test_dry_run_exits_zero(self) -> None:
        mod = _load_proof_script("cos-strict-maintainer-concurrency-proof")
        rc = mod.main(["--dry-run"])
        assert rc == 0

    def test_dry_run_json_is_valid(self, capsys) -> None:
        mod = _load_proof_script("cos-strict-maintainer-concurrency-proof")
        rc = mod.main(["--dry-run", "--json"])
        captured = capsys.readouterr()
        assert rc == 0
        data = json.loads(captured.out)
        assert data["status"] == "dry-run"
        assert data["proof"] == "strict-maintainer-concurrency"
        assert isinstance(data["invariants"], list)
        assert len(data["invariants"]) >= 4

    def test_dry_run_json_has_version(self, capsys) -> None:
        mod = _load_proof_script("cos-strict-maintainer-concurrency-proof")
        mod.main(["--dry-run", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "version" in data
        assert data["version"].startswith("concurrency-proof")

    def test_dry_run_json_has_residual_debt(self, capsys) -> None:
        mod = _load_proof_script("cos-strict-maintainer-concurrency-proof")
        mod.main(["--dry-run", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data.get("residual_debt"), list)
        assert len(data["residual_debt"]) > 0

    def test_invalid_agents_returns_2(self) -> None:
        mod = _load_proof_script("cos-strict-maintainer-concurrency-proof")
        rc = mod.main(["--dry-run", "--agents", "1"])
        assert rc == 2

    def test_real_run_no_deadlock_simulation(self) -> None:
        """Real run (no --dry-run) must pass the tempdir lock simulation invariant."""
        mod = _load_proof_script("cos-strict-maintainer-concurrency-proof")
        report = mod.run_proof(agents=3, timeout_s=30, dry_run=False)
        deadlock_inv = next(
            (i for i in report.invariants if i.id == "no-deadlock-N-agents"), None
        )
        assert deadlock_inv is not None
        assert deadlock_inv.status == "pass", (
            f"no-deadlock simulation failed: {deadlock_inv.evidence}"
        )

    def test_real_run_scenario_manifest_coverage(self) -> None:
        """Real run validates that the scenario manifest covers concurrency scenarios."""
        mod = _load_proof_script("cos-strict-maintainer-concurrency-proof")
        report = mod.run_proof(agents=2, timeout_s=30, dry_run=False)
        manifest_inv = next(
            (i for i in report.invariants if i.id == "scenario-manifest-concurrency-coverage"), None
        )
        assert manifest_inv is not None
        assert manifest_inv.status == "pass", (
            f"scenario manifest coverage check failed: {manifest_inv.evidence}"
        )
