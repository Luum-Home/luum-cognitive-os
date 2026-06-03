from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "dod_check",
    ROOT / "packages" / "quality-gates" / "skills" / "dod-check" / "scripts" / "check_dod.py",
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_classify_critical_for_release_or_version() -> None:
    assert module.classify(["VERSION", "cmd/cos/VERSION"]) == "critical"


def test_recommends_hook_syntax_for_hook_changes() -> None:
    assert module.recommended_command(["hooks/example.sh"]) == "bash -n hooks/example.sh"


def test_hygiene_blocks_secret_paths() -> None:
    checks = {check.name: check for check in module.check_hygiene(["secrets/token.txt"])}
    assert checks["blocked_paths_absent"].status == "FAIL"
