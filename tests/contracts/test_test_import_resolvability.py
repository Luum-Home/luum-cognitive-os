"""El consumidor que faltaba: alguien que lea las dependencias declaradas.

`packages/agent-service/pyproject.toml` declara `httpx` en el extra `testing`
desde el 20 de mayo. Nadie lo lee. No es una dependencia faltante — es un
invariante escrito que ningún camino ejecuta, y por eso se descubrió tres meses
después como `ModuleNotFoundError` en la colección.

Este módulo es ese consumidor. Corre el censo estático de
`scripts/audit_test_import_resolvability.py` sobre los tests VERSIONADOS y exige
igualdad exacta contra `manifests/test-import-exceptions.yaml`.

El control de las tres corridas (`TestGateNoEsParanoico`) está acá y no en un
script suelto a propósito: un gate que se pone rojo con cualquier import es tan
inútil como uno que nunca se pone rojo, y la única forma de saber cuál de los
dos es, es hacerlo fallar y no fallar a pedido.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

audit = importlib.import_module("audit_test_import_resolvability")


@pytest.fixture(scope="module")
def payload() -> dict:
    _, data = audit.build_census()
    data["accepted_exceptions"] = sorted(audit.load_exceptions())
    return data


def _offenders(data: dict) -> set[str]:
    return set(data["declared_not_installed"]) | set(data["undeclared_anywhere"])


class TestCensoDeclaraSuCeguera:
    """Un censo sin población ni ceguera declaradas no se puede publicar."""

    def test_poblacion_no_pierde_archivos(self, payload: dict) -> None:
        c = payload["census"]
        assert c["population"] == c["measurable"] + sum(c["blind"].values())
        assert c["population"] > 1000, (
            "el censo debería ver miles de tests versionados; "
            f"vio {c['population']} — el instrumento se rompió, no el repo"
        )

    def test_la_ceguera_esta_declarada(self, payload: dict) -> None:
        assert payload["census"]["blind"], "un censo sin ceguera declarada miente"


class TestImportsIrresolublesEstanDeclarados:
    """Igualdad exacta: ni un hallazgo sin aceptar, ni una excepción vencida."""

    def test_sin_hallazgos_no_aceptados(self, payload: dict) -> None:
        nuevos = sorted(_offenders(payload) - set(payload["accepted_exceptions"]))
        assert not nuevos, (
            "Estos tests versionados importan, a nivel de módulo, algo que el "
            "entorno de este repo no resuelve. Van a fallar en la COLECCIÓN, no "
            "como un test rojo:\n  "
            + "\n  ".join(
                f"{p}: falta "
                + ", ".join(
                    sorted(
                        set(
                            (
                                payload["declared_not_installed"].get(p)
                                or payload["undeclared_anywhere"][p]
                            )["declared"]
                        )
                        | set(
                            (
                                payload["declared_not_installed"].get(p)
                                or payload["undeclared_anywhere"][p]
                            )["undeclared"]
                        )
                    )
                )
                for p in nuevos
            )
            + "\n\nArreglalo donde está el consumidor que falta (la instalación, "
            "la lane de tests), o declará la inhabilidad con su motivo en "
            "manifests/test-import-exceptions.yaml. Instalarlo en tu venv local "
            "arregla tu máquina y nada más."
        )

    def test_sin_excepciones_vencidas(self, payload: dict) -> None:
        vencidas = sorted(set(payload["accepted_exceptions"]) - _offenders(payload))
        assert not vencidas, (
            "Estas excepciones ya no suprimen nada — el entorno resuelve esos "
            f"imports: {vencidas}. Una excepción que no excepciona es un "
            "colchón: sacala de manifests/test-import-exceptions.yaml."
        )

    def test_cada_excepcion_tiene_motivo(self) -> None:
        for path, reason in audit.load_exceptions().items():
            assert len(reason.strip()) > 40, (
                f"{path}: una excepción sin motivo escrito es un skip disfrazado"
            )


class TestGateNoEsParanoico:
    """Las tres corridas del control, sobre archivos sintéticos.

    Rojo con el import imposible, verde con el satisfecho, y verde SIN TOCARLO
    con el que declara su dependencia como opcional. El tercero es el que
    impide el gate paranoico: `importorskip` y `try/except ImportError` son la
    forma CORRECTA de declarar una dependencia opcional, y un censo que los
    cuenta como defecto cuenta mal.
    """

    def _missing(self, tmp_path: Path, source: str) -> list[str]:
        f = tmp_path / "test_sintetico.py"
        f.write_text(source, encoding="utf-8")
        scanned = audit.scan(f)
        assert scanned.parse_error is None
        fp = audit.first_party_modules()
        return sorted(
            m
            for m in scanned.required
            if not audit.resolvable(m) and m not in fp
        )

    def test_import_imposible_da_rojo(self, tmp_path: Path) -> None:
        assert self._missing(
            tmp_path, "import modulo_que_no_existe_en_ningun_lado\n"
        ) == ["modulo_que_no_existe_en_ningun_lado"]

    def test_import_satisfecho_da_verde(self, tmp_path: Path) -> None:
        assert self._missing(tmp_path, "import json\nimport pytest\n") == []

    def test_dependencia_opcional_declarada_da_verde(self, tmp_path: Path) -> None:
        fuentes = [
            'import pytest\nmodulo_que_no_existe_en_ningun_lado = pytest.importorskip("modulo_que_no_existe_en_ningun_lado")\n',
            "try:\n    import modulo_que_no_existe_en_ningun_lado\nexcept ImportError:\n    modulo_que_no_existe_en_ningun_lado = None\n",
            "try:\n    import tomllib\nexcept ImportError:\n    import modulo_que_no_existe_en_ningun_lado as tomllib\n",
            "def test_algo():\n    import modulo_que_no_existe_en_ningun_lado\n",
        ]
        for src in fuentes:
            assert self._missing(tmp_path, src) == [], src

    def test_el_caso_conocido_sigue_siendo_visible(self, payload: dict) -> None:
        """Regresión del hallazgo que originó esto: no debe volverse invisible."""
        conftest = "packages/agent-service/tests/conftest.py"
        detectado = conftest in _offenders(payload)
        aceptado = conftest in payload["accepted_exceptions"]
        assert detectado == aceptado, (
            f"{conftest}: detectado={detectado} aceptado={aceptado}. Si el "
            "entorno ya resuelve httpx, sacá la entrada del manifiesto; si no, "
            "el censo dejó de verlo y eso es peor que el defecto original."
        )
