# SCOPE: os-only
"""Aisla la telemetria del operador de la suite de tests.

`.cognitive-os/metrics/` es evidencia forense del operador: filas escritas por
hooks reales, en sesiones reales, que despues gobiernan decisiones. Un test que
escribe ahi no ensucia un log: contamina la prueba.

Este conftest vive en la RAIZ del repo a proposito. pytest carga los conftest
desde el rootdir hacia abajo, asi que este corre ANTES que `tests/conftest.py` y
aplica a los 2.290 archivos de test sin que ninguno tenga que colaborar —
incluido el que se escriba la semana que viene.

Dos capas, porque una sola no alcanza:

  1. PREVENCION (`pytest_configure`): exporta `COS_METRICS_DIR` /
     `COGNITIVE_OS_METRICS_DIR` a un directorio descartable. Todo subproceso que
     lance un test lo hereda por `os.environ`, sin parchear `Popen`. Redirige a
     los escritores que honran la convencion.

  2. DETECCION (`pytest_sessionfinish`): huella del directorio real antes y
     despues. Esta capa mira el FILESYSTEM, no el camino de llamada, asi que
     atrapa por igual al hook que hardcodea la ruta y al test que abre el
     archivo con `open(..., "a")`. Es la unica de las dos que no se puede
     esquivar escribiendo directo.

Por que hacen falta las dos, medido el 2026-08-20:

    grep -rl 'cognitive-os/metrics' hooks/*.sh | wc -l          -> 111
    for f in $(grep -rl 'cognitive-os/metrics' hooks/*.sh); do \
        grep -q COS_METRICS_DIR "$f" && echo "$f"; done | wc -l -> 3

96 de 111 hooks construyen la ruta a mano. La capa 1 no los alcanza; la capa 2
si. `tests/audit/test_metrics_isolation.py::test_operator_metrics_ratchet` fija
ese 3 como piso para que solo pueda subir.

Escape documentado: `COS_ALLOW_OPERATOR_METRICS_WRITES=1` degrada el fallo a
aviso. Existe por un motivo acotado y escrito — en esta maquina conviven varias
sesiones vivas del operador escribiendo en el mismo directorio mientras corre la
suite, y esa escritura ajena es indistinguible de la propia desde el
filesystem. El escape NO silencia la lista: los archivos que crecieron se
imprimen igual. Bajar el ruido de verdad es hacer que los 96 hooks honren
`COS_METRICS_DIR`, no mover este umbral.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
OPERATOR_METRICS = REPO_ROOT / ".cognitive-os" / "metrics"

_ESCAPE_ENV = "COS_ALLOW_OPERATOR_METRICS_WRITES"

_before: dict[str, int] = {}
_sandbox: Path | None = None


def fingerprint_metrics_dir(directory: Path) -> dict[str, int]:
    """Nombre -> tamano de cada archivo suelto del directorio.

    Solo el primer nivel: los consumidores leen `metrics/*.jsonl`, y los
    subdirectorios (`.archive/`, `anonymous/`) son espacios segregados a
    proposito. `follow_symlinks=False` para que un symlink no se cuente como el
    archivo al que apunta.
    """
    out: dict[str, int] = {}
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_file(follow_symlinks=False):
                    try:
                        out[entry.name] = entry.stat().st_size
                    except OSError:
                        continue
    except (FileNotFoundError, NotADirectoryError):
        pass
    return out


def diff_growth(before: dict[str, int], after: dict[str, int]) -> list[tuple[str, int, int]]:
    """Archivos que crecieron o aparecieron. (nombre, antes, despues).

    Un archivo que ENCOGIO no se reporta: eso es rotacion, no escritura. Un
    archivo nuevo cuenta como crecimiento desde 0, que es el caso del test que
    estrena un `.jsonl` en el directorio del operador.
    """
    grew: list[tuple[str, int, int]] = []
    for name, size_after in sorted(after.items()):
        size_before = before.get(name, 0)
        if size_after > size_before:
            grew.append((name, size_before, size_after))
    return grew


def pytest_configure(config) -> None:  # noqa: ANN001 - firma de pytest
    global _sandbox, _before
    _sandbox = Path(tempfile.mkdtemp(prefix="cos-test-metrics-"))
    os.environ["COS_METRICS_DIR"] = str(_sandbox)
    os.environ["COGNITIVE_OS_METRICS_DIR"] = str(_sandbox)
    _before = fingerprint_metrics_dir(OPERATOR_METRICS)


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ANN001 - firma de pytest
    after = fingerprint_metrics_dir(OPERATOR_METRICS)
    grew = diff_growth(_before, after)
    if not grew:
        return

    escaped = os.environ.get(_ESCAPE_ENV, "0") == "1"
    header = (
        "AVISO" if escaped else "FALLO"
    ) + ": la suite dejo escrituras en la telemetria del operador"
    lines = [f"\n{header} (.cognitive-os/metrics/):"]
    for name, size_before, size_after in grew:
        lines.append(f"  {name}: {size_before} -> {size_after} bytes (+{size_after - size_before})")
    if escaped:
        lines.append(f"  [{_ESCAPE_ENV}=1: no se falla la corrida, la lista se imprime igual]")
    else:
        lines.append(
            "  Un test no puede escribir aca. Redirigi el escritor a COS_METRICS_DIR "
            f"o corre con {_ESCAPE_ENV}=1 si sabes que hay una sesion viva del "
            "operador escribiendo en paralelo."
        )
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line("\n".join(lines))
    else:
        print("\n".join(lines))

    if not escaped and exitstatus == 0:
        session.exitstatus = 1
