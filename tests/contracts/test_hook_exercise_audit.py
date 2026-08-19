# SCOPE: os-only
"""Prueba del escalon de tres niveles de scripts/hook_exercise_audit.py.

La clasificacion se ejercita sobre fuentes SINTETICAS escritas en ``tmp_path``.
El corpus real (``tests/**``) y el registro real (``cognitive-os.yaml``) se leen,
nunca se escriben, y solo para verificar invariantes estructurales del reporte.

Los hooks sinteticos se llaman ``zz-quokka-*`` / ``zz-tapir-*`` a proposito: este
archivo vive dentro de ``tests/contracts/``, que ES parte del corpus que el script
audita. Nombrar un hook real aca le acreditaria cobertura desde su propio test.

Familias cubiertas:

  trigger        nombre pasado como argumento de un Call -> EXERCISED
  discriminador  literal presente y nunca pasado a nada  -> NAMED_ONLY
                 sin ningun test                          -> NO_TEST
  ceguera        indireccion (CASES = [...]; run(CASES[0])) -> UNCLASSIFIABLE
                 archivo que no parsea                      -> UNCLASSIFIABLE
  precedencia    prueba positiva > ceguera > mencion
  falsacion      la posicion ``func`` de un Call NO es un argumento;
                 un literal en un baseline de deuda no acredita nada
  denominadores  todo porcentaje del reporte trae su denominador y su ceguera
  read-only      la corrida no escribe un byte en el corpus
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = REPO_ROOT / "scripts" / "hook_exercise_audit.py"

# El script recorre ~1000 archivos de test y los parsea; una corrida completa
# ronda los 15s y el timeout global de pytest.ini es 30. Las corridas de CLI se
# comparten a nivel de modulo para no pagarlas de nuevo en cada test.
pytestmark = pytest.mark.timeout(180)

sys.path.insert(0, str(REPO_ROOT / "scripts"))

import hook_exercise_audit as hea  # noqa: E402

# Hooks sinteticos: ningun registro real los contiene.
QUOKKA = "zz-quokka-gate"
TAPIR = "zz-tapir-gate"


# --------------------------------------------------------------------------- #
# Andamiaje
# --------------------------------------------------------------------------- #
def _classify(tmp_path: Path, hook: str, files: dict[str, str]) -> tuple[str, dict]:
    """Clasifica ``hook`` contra un corpus sintetico ``{nombre: fuente}``."""
    sources: list[tuple[Path, str]] = []
    for name, body in files.items():
        path = tmp_path / name
        path.write_text(body, encoding="utf-8")
        sources.append((path, body))
    evidence = hea.build_evidence_index(sources)
    needles = hea.hook_needles(hook, f"hooks/{hook}.sh")
    tests = [hea.evidence_key(path) for path, _ in sources]
    return hea.classify_hook(needles, tests, evidence)


@pytest.fixture(autouse=True)
def _subdirs(tmp_path: Path) -> None:
    """Dos subcorpus independientes para los tests que comparan dos hooks."""
    (tmp_path / "a").mkdir(exist_ok=True)
    (tmp_path / "b").mkdir(exist_ok=True)


# --------------------------------------------------------------------------- #
# trigger
# --------------------------------------------------------------------------- #
def test_name_passed_as_call_argument_is_exercised(tmp_path: Path) -> None:
    level, detail = _classify(
        tmp_path,
        QUOKKA,
        {
            "test_a.py": (
                "import subprocess\n"
                "def test_runs():\n"
                f"    subprocess.run(['bash', 'hooks/{QUOKKA}.sh'], check=False)\n"
            )
        },
    )
    assert level == hea.EXERCISED, detail


def test_name_in_keyword_argument_is_exercised(tmp_path: Path) -> None:
    level, _ = _classify(
        tmp_path,
        QUOKKA,
        {"test_a.py": f"def test_x():\n    run(hook='hooks/{QUOKKA}.sh')\n"},
    )
    assert level == hea.EXERCISED


def test_name_nested_inside_call_argument_is_exercised(tmp_path: Path) -> None:
    """El literal viaja adentro de una lista que ES el argumento."""
    level, _ = _classify(
        tmp_path,
        QUOKKA,
        {"test_a.py": f"def test_x():\n    run(['a.sh', 'hooks/{QUOKKA}.sh'])\n"},
    )
    assert level == hea.EXERCISED


# --------------------------------------------------------------------------- #
# discriminador
# --------------------------------------------------------------------------- #
def test_bare_literal_is_named_only(tmp_path: Path) -> None:
    level, detail = _classify(
        tmp_path,
        QUOKKA,
        {
            "test_a.py": (
                "def test_x():\n"
                f"    assert 'hooks/{QUOKKA}.sh' in REGISTERED\n"
            )
        },
    )
    assert level == hea.NAMED_ONLY, detail


def test_literal_in_call_func_position_is_not_an_argument(tmp_path: Path) -> None:
    """`{...}.issubset(post)` menciona el hook; no se lo pasa a nadie.

    Es el caso real que separa esta medicion de la ingenua: el set literal esta
    adentro del subarbol del Call, pero en ``func``, no en ``args``.
    """
    level, _ = _classify(
        tmp_path,
        QUOKKA,
        {"test_a.py": f"def test_x():\n    assert {{'hooks/{QUOKKA}.sh'}}.issubset(post)\n"},
    )
    assert level == hea.NAMED_ONLY


def test_dead_literal_bound_to_unused_name_is_named_only(tmp_path: Path) -> None:
    """Un nombre que nadie lee no es indireccion: no hay uso que resolver."""
    level, _ = _classify(
        tmp_path,
        QUOKKA,
        {"test_a.py": f"UNUSED = ['hooks/{QUOKKA}.sh']\n\ndef test_x():\n    assert True\n"},
    )
    assert level == hea.NAMED_ONLY


def test_hook_with_no_tests_is_no_test(tmp_path: Path) -> None:
    level, detail = _classify(tmp_path, QUOKKA, {})
    assert level == hea.NO_TEST
    assert detail == {}


def test_debt_baseline_literal_lands_in_no_evidence_bag(tmp_path: Path) -> None:
    """Herencia de hook_quality_audit: KNOWN_* lista defectos, no cobertura.

    El literal no cae en NINGUNA de las tres bolsas, asi que no puede acreditar
    ni EXERCISED ni NAMED_ONLY. Es la misma exclusion que hace que
    ``discover_behavior_tests`` ni siquiera devuelva este archivo.
    """
    body = (
        f"KNOWN_FAILURES = ['hooks/{QUOKKA}.sh']\n\n"
        "def test_x():\n    assert KNOWN_FAILURES\n"
    )
    bags = hea.file_evidence(tmp_path / "test_a.py", body)
    assert bags["parsed"]
    assert QUOKKA not in bags["call"]
    assert QUOKKA not in bags["indirect"]
    assert QUOKKA not in bags["plain"]


def test_file_credited_without_visible_evidence_is_unclassifiable(tmp_path: Path) -> None:
    """Guardia de divergencia: si las dos tecnicas no coinciden, no se adivina.

    Un archivo acreditado por ``discover_behavior_tests`` en el que esta medicion
    no ve el nombre en ninguna bolsa no se clasifica como mencion vacia: se
    declara no juzgable.
    """
    level, detail = _classify(
        tmp_path,
        QUOKKA,
        {
            "test_a.py": (
                f"KNOWN_FAILURES = ['hooks/{QUOKKA}.sh']\n\n"
                "def test_x():\n    assert KNOWN_FAILURES\n"
            )
        },
    )
    assert level == hea.UNCLASSIFIABLE, detail


# --------------------------------------------------------------------------- #
# ceguera
# --------------------------------------------------------------------------- #
def test_indirection_is_unclassifiable(tmp_path: Path) -> None:
    """El caso que el encargo nombra: el literal esta en la lista, el uso afuera."""
    level, detail = _classify(
        tmp_path,
        QUOKKA,
        {
            "test_a.py": (
                f"CASES = ['hooks/{QUOKKA}.sh', 'hooks/other.sh']\n\n"
                "def test_x():\n"
                "    run(CASES[0])\n"
            )
        },
    )
    assert level == hea.UNCLASSIFIABLE, detail
    assert detail[hea.UNCLASSIFIABLE] == [str(tmp_path / "test_a.py")]


def test_unparseable_file_is_unclassifiable(tmp_path: Path) -> None:
    level, detail = _classify(
        tmp_path,
        QUOKKA,
        {"test_a.py": f"def test_x(:\n    run('hooks/{QUOKKA}.sh')\n"},
    )
    assert level == hea.UNCLASSIFIABLE, detail


def test_unclassifiable_is_not_counted_as_named_only(tmp_path: Path) -> None:
    """La distincion que justifica el script: ciego != mencion vacia."""
    indirect, _ = _classify(
        tmp_path / "a",
        QUOKKA,
        {"test_a.py": f"CASES = ['hooks/{QUOKKA}.sh']\n\ndef test_x():\n    run(CASES[0])\n"},
    )
    named, _ = _classify(
        tmp_path / "b",
        QUOKKA,
        {"test_a.py": f"def test_x():\n    assert 'hooks/{QUOKKA}.sh' in REG\n"},
    )
    assert indirect == hea.UNCLASSIFIABLE
    assert named == hea.NAMED_ONLY
    assert indirect != named


# --------------------------------------------------------------------------- #
# precedencia entre archivos
# --------------------------------------------------------------------------- #
def test_positive_proof_beats_blindness(tmp_path: Path) -> None:
    level, detail = _classify(
        tmp_path,
        QUOKKA,
        {
            "test_a.py": f"CASES = ['hooks/{QUOKKA}.sh']\n\ndef test_x():\n    run(CASES[0])\n",
            "test_b.py": f"def test_y():\n    run('hooks/{QUOKKA}.sh')\n",
        },
    )
    assert level == hea.EXERCISED
    assert detail[hea.UNCLASSIFIABLE]  # la ceguera del otro archivo queda registrada


def test_blindness_beats_bare_mention(tmp_path: Path) -> None:
    level, _ = _classify(
        tmp_path,
        QUOKKA,
        {
            "test_a.py": f"CASES = ['hooks/{QUOKKA}.sh']\n\ndef test_x():\n    run(CASES[0])\n",
            "test_b.py": f"def test_y():\n    assert 'hooks/{QUOKKA}.sh' in REG\n",
        },
    )
    assert level == hea.UNCLASSIFIABLE


def test_two_hooks_in_one_file_are_classified_independently(tmp_path: Path) -> None:
    body = (
        f"CASES = ['hooks/{TAPIR}.sh']\n\n"
        "def test_x():\n"
        "    run(CASES[0])\n"
        f"    run('hooks/{QUOKKA}.sh')\n"
    )
    quokka, _ = _classify(tmp_path / "a", QUOKKA, {"test_a.py": body})
    tapir, _ = _classify(tmp_path / "b", TAPIR, {"test_a.py": body})
    assert quokka == hea.EXERCISED
    assert tapir == hea.UNCLASSIFIABLE


# --------------------------------------------------------------------------- #
# el reporte completo, sobre el repo real
# --------------------------------------------------------------------------- #
def _cli(*args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, str(ARTIFACT), *args],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        timeout=170,
        check=False,
    )


@pytest.fixture(scope="module")
def cli_json() -> "subprocess.CompletedProcess[str]":
    proc = _cli("--json")
    assert proc.returncode in (0, 1), proc.stderr
    return proc


@pytest.fixture(scope="module")
def cli_report(cli_json: "subprocess.CompletedProcess[str]") -> dict:
    return json.loads(cli_json.stdout)


@pytest.fixture(scope="module")
def cli_text() -> "subprocess.CompletedProcess[str]":
    proc = _cli()
    assert proc.returncode in (0, 1), proc.stderr
    return proc


def test_levels_partition_the_registry(cli_report: dict) -> None:
    """Todo hook cae en exactamente una cubeta y la suma da el denominador."""
    totals = cli_report["totals"]
    assert set(totals) == set(hea.LEVELS)
    assert sum(totals.values()) == cli_report["denominator_total"]
    assert cli_report["denominator_total"] == len(cli_report["hooks"])


def test_measurable_denominator_excludes_blindness(cli_report: dict) -> None:
    assert (
        cli_report["denominator_measurable"]
        == cli_report["denominator_total"] - cli_report["totals"][hea.UNCLASSIFIABLE]
    )
    assert cli_report["blind_ratio"] == pytest.approx(
        cli_report["totals"][hea.UNCLASSIFIABLE] / cli_report["denominator_total"], abs=1e-4
    )


def test_no_test_set_matches_hook_quality_audit(cli_report: dict) -> None:
    """El conjunto NO_TEST tiene que ser el de behavior_tests vacio, no otro.

    Si estas dos mediciones se separan, una de las dos esta mintiendo; el punto
    de importar ``discover_behavior_tests`` es que no puedan separarse.
    """
    from hook_quality_audit import discover_behavior_tests, registered_hooks

    registry = registered_hooks()
    expected = {
        hook for hook, entry in registry.items()
        if not discover_behavior_tests(hook, entry["script"])
    }
    reported = {r["hook"] for r in cli_report["hooks"] if r["level"] == hea.NO_TEST}
    assert reported == expected


def test_every_printed_percentage_carries_its_denominator(
    cli_text: "subprocess.CompletedProcess[str]",
) -> None:
    text = cli_text.stdout
    assert "DENOMINADORES" in text
    assert "total registrado" in text
    assert "medible" in text
    assert "ceguera" in text
    for line in text.splitlines():
        if "%" in line and "AVISO" not in line and "umbral" not in line:
            assert "/" in line, f"porcentaje sin denominador: {line!r}"


def test_high_blindness_prints_the_non_observation_warning(
    cli_report: dict, cli_text: "subprocess.CompletedProcess[str]"
) -> None:
    if cli_report["blind_ratio"] >= hea.BLINDNESS_ALARM:
        assert "no-observacion" in cli_text.stdout
    else:
        assert "no-observacion" not in cli_text.stdout


def test_exit_code_follows_the_repo_convention(
    cli_report: dict, cli_text: "subprocess.CompletedProcess[str]"
) -> None:
    assert cli_text.returncode == (1 if cli_report["findings"] else 0)


def test_findings_are_justified_not_bulk(cli_report: dict) -> None:
    """Un hallazgo trae escrito por que lo es; los demas quedan como deuda."""
    for row in cli_report["findings"]:
        assert row["finding_reason"], row["hook"]
    debt = [
        r for r in cli_report["hooks"]
        if r["level"] == hea.NO_TEST and not r["finding"]
    ]
    for row in debt:
        assert row["criticality"] not in hea.CRITICALITY_WARRANTING_TEST
        assert row["maturity"] not in hea.MATURITY_WARRANTING_TEST


def test_run_is_read_only(cli_report: dict) -> None:
    """La corrida no escribe en el corpus que audita."""
    watched = sorted((REPO_ROOT / "tests" / "unit").glob("test_*.py"))[:50]
    before = {p: p.stat().st_mtime_ns for p in watched}
    _cli("--json")
    after = {p: p.stat().st_mtime_ns for p in watched}
    assert before == after
