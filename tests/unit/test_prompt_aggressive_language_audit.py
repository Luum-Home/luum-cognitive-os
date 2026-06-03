from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "prompt_aggressive_language_audit",
    ROOT / "scripts" / "prompt_aggressive_language_audit.py",
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_classifies_prompt_style_debt() -> None:
    assert module.classify("CRITICAL: You MUST use this skill for every task") == "debt"


def test_allows_security_and_protocol_language() -> None:
    assert module.classify("Credentials in env only; never commit .env files") == "allowed"
    assert module.classify('radius == "CRITICAL" increments critical_radius') == "allowed"
    assert module.classify("Assume IDE hooks do not fire in service mode") == "allowed"


def test_changed_ratchet_filters_default_text_surfaces() -> None:
    assert module.is_default_surface("skills/example/SKILL.md") is True
    assert module.is_default_surface("docs/example.md") is False
    assert module.is_text_surface(ROOT / "skills/example/SKILL.md") is True
    assert module.is_text_surface(ROOT / "scripts/example.py") is False
