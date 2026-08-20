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
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
OPERATOR_METRICS = REPO_ROOT / ".cognitive-os" / "metrics"
RUNTIME_DIR = REPO_ROOT / ".cognitive-os" / "runtime"

_ESCAPE_ENV = "COS_ALLOW_OPERATOR_METRICS_WRITES"

# Archivos de metricas que escribe un daemon con su propio reloj, corra o no
# pytest. Medido el 2026-08-20: el escritor de session-watchdog.jsonl es
# scripts/so_session_watchdog.py --daemon --interval 60, con PPID=1 (desprendido
# en SessionStart). Una fila mide exactamente 335 bytes, que es lo que crecio en
# una ventana OCIOSA de 20 segundos sin un solo test corriendo:
#
#   coverage-history.jsonl   +0     <- eso si lo escribia la suite
#   session-watchdog.jsonl   +335   <- crece sola: no es la suite
#
# Los dos se reportaban IGUAL. Un gate que grita por ruido propio del operador se
# bypassea, y el hallazgo real se va con el bypass.
_KNOWN_DAEMON_PIDFILES: dict[str, tuple[str, str]] = {
    "session-watchdog.jsonl": ("session-watchdog.pid", "so_session_watchdog.py"),
}

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


def _ancestor_pids(pid: int) -> set[int]:
    """Cadena de padres de `pid`, para no acreditar como ajeno a un proceso propio."""
    seen: set[int] = set()
    current = pid
    for _ in range(64):
        if current in (0, 1) or current in seen:
            break
        seen.add(current)
        try:
            out = subprocess.run(
                ["ps", "-p", str(current), "-o", "ppid="],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            current = int(out)
        except (ValueError, OSError, subprocess.SubprocessError):
            break
    return seen


def _daemon_owns_this_growth(
    metrics_name: str,
    runtime_dir: Path = RUNTIME_DIR,
    pidfile_map: dict[str, tuple[str, str]] | None = None,
) -> tuple[bool, str]:
    """Es `metrics_name` de un daemon conocido, vivo y ajeno a esta corrida?

    FALLA CERRADA, y eso es el punto: pidfile ausente, PID muerto, cmdline que no
    coincide (bloquea suplantacion por reuso de PID) o PID que es ancestro de ESTE
    proceso caen todos a False, o sea al bucket estricto. Solo un proceso
    verificablemente vivo, correctamente identificado y ajeno se acredita como
    ruido. "No pude verificar" nunca es "es ruido del operador": esa confusion es
    la que convierte un guard en un permiso.
    """
    entry = (pidfile_map if pidfile_map is not None else _KNOWN_DAEMON_PIDFILES).get(metrics_name)
    if entry is None:
        return False, ""
    pidfile_name, expected_cmd = entry
    try:
        pid = int((runtime_dir / pidfile_name).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False, ""
    if pid <= 0 or pid == os.getpid():
        return False, ""
    try:
        os.kill(pid, 0)
    except OSError:
        return False, ""
    try:
        cmdline = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return False, ""
    if expected_cmd not in cmdline:
        return False, ""
    if pid in _ancestor_pids(os.getpid()):
        return False, ""
    return True, f"PID {pid} vivo, cmdline coincide con {expected_cmd!r}, ajeno a esta corrida"


def _classify_growth(
    grew: list[tuple[str, int, int]],
) -> tuple[list[tuple[str, int, int, str]], list[tuple[str, int, int]]]:
    """Parte la salida de diff_growth() en (ruido-de-daemon, atribuible-a-la-suite)."""
    noise: list[tuple[str, int, int, str]] = []
    suite: list[tuple[str, int, int]] = []
    for name, before, after in grew:
        is_daemon, desc = _daemon_owns_this_growth(name)
        if is_daemon:
            noise.append((name, before, after, desc))
        else:
            suite.append((name, before, after))
    return noise, suite


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

    noise, suite = _classify_growth(grew)
    lines: list[str] = []

    if noise:
        lines.append("\nAVISO (ruido de sesion, NO de la suite) en .cognitive-os/metrics/:")
        for name, size_before, size_after, why in noise:
            lines.append(
                f"  {name}: {size_before} -> {size_after} bytes "
                f"(+{size_after - size_before})  [{why}]"
            )
        lines.append("  Estos archivos crecen con su propio reloj. No fallan la corrida.")

    if suite:
        escaped = os.environ.get(_ESCAPE_ENV, "0") == "1"
        header = "AVISO" if escaped else "FALLO"
        lines.append(f"\n{header}: la suite dejo escrituras en la telemetria del operador:")
        for name, size_before, size_after in suite:
            lines.append(
                f"  {name}: {size_before} -> {size_after} bytes (+{size_after - size_before})"
            )
        if escaped:
            lines.append(f"  [{_ESCAPE_ENV}=1: no se falla la corrida, la lista se imprime igual]")
        else:
            lines.append(
                "  Un test no puede escribir aca. Redirigi el escritor a COS_METRICS_DIR.\n"
                "  Si de verdad es un daemon vivo del operador y no la suite, agregalo a\n"
                f"  _KNOWN_DAEMON_PIDFILES en este conftest -- NO alcances {_ESCAPE_ENV},\n"
                "  que apaga la deteccion entera y se lleva puesto el hallazgo real."
            )

    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line("\n".join(lines))
    else:
        print("\n".join(lines))

    if suite and os.environ.get(_ESCAPE_ENV, "0") != "1" and exitstatus == 0:
        session.exitstatus = 1
