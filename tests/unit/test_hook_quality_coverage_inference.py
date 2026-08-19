"""What may testify that a test covers a hook.

Every case here is written as a DIFFERENTIAL: it asserts that a raw substring
search — the inference this module replaced — WOULD have matched, and that the
current one does not. That way the test proves the behaviour changed without
needing the old code kept around to compare against, and it cannot pass
vacuously on a file where the name never appeared at all.

Origin: 2026-08-19. Emptying four `KNOWN_*` baselines in the hooks schema
conformance test removed that test from the `behavior_tests` of the four hooks
it had just been proven to pass on. Coverage was being credited for being
listed as BROKEN.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "hook_quality_audit", REPO / "scripts" / "hook_quality_audit.py"
)
hqa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hqa)


def _cov(name: str, src: str) -> str:
    """coverage_text on a synthetic file, bypassing the module-level cache."""
    hqa._COVERAGE_TEXT_CACHE.pop(Path(name), None)
    out = hqa.coverage_text(Path(name), src)
    hqa._COVERAGE_TEXT_CACHE.pop(Path(name), None)
    return out


HOOK = "cross-session-peer-context.sh"


@pytest.mark.parametrize(
    "label,src",
    [
        (
            "comment",
            f"# this module used to matter for {HOOK}\ndef test_x():\n    assert True\n",
        ),
        (
            "module docstring",
            f'"""Notes about {HOOK} and friends."""\n\ndef test_x():\n    assert True\n',
        ),
        (
            "function docstring",
            f'def test_x():\n    """Covers everything except {HOOK}."""\n    assert True\n',
        ),
        (
            "KNOWN_ debt baseline",
            f'KNOWN_ROOT_LEVEL_VIOLATIONS = {{\n    "hooks/{HOOK}",\n}}\n\ndef test_x():\n    assert True\n',
        ),
        (
            "annotated KNOWN_ baseline",
            f'KNOWN_X: set[str] = {{"hooks/{HOOK}"}}\n\ndef test_x():\n    assert True\n',
        ),
        (
            "EXPECTED_FAILURES baseline",
            f'EXPECTED_FAILURES = ["hooks/{HOOK}"]\n\ndef test_x():\n    assert True\n',
        ),
    ],
)
def test_prose_and_debt_do_not_count_as_coverage(label: str, src: str) -> None:
    assert HOOK in src, f"{label}: el caso no menciona el hook; seria vacuo"
    assert HOOK not in _cov(f"t_{label}.py", src), (
        f"{label}: el nombre sigue contando como cobertura"
    )


@pytest.mark.parametrize(
    "label,src",
    [
        ("assertion string", f'def test_x():\n    assert run("hooks/{HOOK}") == 0\n'),
        ("plain constant", f'TARGET = "hooks/{HOOK}"\n\ndef test_x():\n    assert TARGET\n'),
        ("non-debt collection", f'CASES = ["hooks/{HOOK}"]\n\ndef test_x():\n    assert CASES\n'),
    ],
)
def test_real_references_still_count(label: str, src: str) -> None:
    assert HOOK in _cov(f"t_{label}.py", src), f"{label}: se perdio cobertura legitima"


def test_unparseable_file_falls_back_instead_of_erasing_coverage() -> None:
    """A syntax error must not silently zero out a file's coverage."""
    broken = f'def test_x(  # sin cerrar\n    "hooks/{HOOK}"\n'
    with pytest.raises(SyntaxError):
        compile(broken, "t.py", "exec")
    assert HOOK in _cov("t_broken.py", broken)


def test_census_declaration_is_recognised() -> None:
    assert hqa._CENSUS_RE.search('HOOK_QUALITY_COVERAGE = "census"\n')
    assert hqa._CENSUS_RE.search("HOOK_QUALITY_COVERAGE: str = \'census\'\n")
    assert not hqa._CENSUS_RE.search('HOOK_QUALITY_COVERAGE = "specific"\n')
    assert not hqa._CENSUS_RE.search('# HOOK_QUALITY_COVERAGE = "census"\n')


def test_conformance_test_declares_census_and_is_not_a_behavior_test() -> None:
    """The census test must land in census_tests, never in behavior_tests.

    Crediting it to behavior_tests would make `critical hook has no
    behavior_tests` unfailable — a gate that cannot go red is not a gate.
    """
    census = hqa.discover_census_tests()
    conformance = "tests/contracts/test_claude_code_hooks_schema_conformance.py"
    assert conformance in census, "el test censo no se declara"
    found = hqa.discover_behavior_tests(
        "cross-session-peer-context", "hooks/cross-session-peer-context.sh"
    )
    assert conformance not in found, "el test censo se colo en behavior_tests"
