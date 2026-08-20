# SCOPE: os-only
"""Portability proof for scripts/measure_event_cadence.py.

El marcador dice `os-only`, y esta prueba lo FALSIFICA en los dos sentidos en vez
de repetirlo: corre el script desde un cwd ajeno (que funcione no depende del
directorio) y verifica que su unica atadura al repo sea relativa a su propia
ubicacion, no una ruta absoluta escrita a mano. `os-only` aca significa "lee la
telemetria y los manifiestos de ESTE repo", no "solo anda si te parás en la raiz".
"""

from __future__ import annotations

import gzip
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts" / "measure_event_cadence.py"


def _row(ts: str, event: str, hook: str) -> str:
    return json.dumps({"timestamp": ts, "event": event, "hook": hook,
                       "duration_ms": 1, "session_id": ""})


def test_scope_marker_is_declared_and_carries_no_absolute_path() -> None:
    """Sonda de falsificacion: una ruta absoluta del checkout rompe el marcador."""
    text = ARTIFACT.read_text(encoding="utf-8")
    assert text.splitlines()[1].strip() == "# SCOPE: os-only"
    assert str(REPO_ROOT) not in text, (
        "el script embebe la ruta absoluta de ESTE checkout; deja de ser portable "
        "entre clones del mismo repo, que es lo minimo que os-only tiene que dar"
    )
    assert "/Users/" not in text and "/home/" not in text


def test_measures_a_synthetic_repo_from_an_arbitrary_cwd(tmp_path: Path) -> None:
    """Corre de verdad: dos sesiones sinteticas, una con 3 Stop y otra con 1.

    Es la sonda que importa. Si el script contara filas en vez de ocurrencias del
    evento, o si ignorara el .gz rotado, este assert cambia de valor.
    """
    fake = tmp_path / "clone"
    (fake / "scripts").mkdir(parents=True)
    (fake / "cos_lib").mkdir()
    (fake / ".cognitive-os" / "metrics" / ".archive").mkdir(parents=True)
    (fake / "scripts" / "measure_event_cadence.py").write_text(
        ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")
    (fake / "cos_lib" / "__init__.py").write_text("", encoding="utf-8")
    (fake / "cos_lib" / "measurement.py").write_text(
        (REPO_ROOT / "cos_lib" / "measurement.py").read_text(encoding="utf-8"),
        encoding="utf-8")

    metrics = fake / ".cognitive-os" / "metrics"
    # Sesion 1 vive en el ROTADO: si el script leyera solo el archivo vivo, esta
    # sesion desapareceria y Stop mediria 1 ocurrencia en vez de 4.
    rotado = [
        _row("2026-01-01T00:00:00Z", "SessionStart", "witness-start"),
        _row("2026-01-01T00:00:01Z", "Stop", "witness-stop"),
        _row("2026-01-01T00:00:02Z", "Stop", "witness-stop"),
        _row("2026-01-01T00:00:03Z", "Stop", "witness-stop"),
    ]
    with gzip.open(metrics / ".archive" / "hook-timing-20260101-000000.jsonl.gz",
                   "wt", encoding="utf-8") as fh:
        fh.write("\n".join(rotado) + "\n")
    (metrics / "hook-timing.jsonl").write_text("\n".join([
        _row("2026-01-02T00:00:00Z", "SessionStart", "witness-start"),
        _row("2026-01-02T00:00:01Z", "Stop", "witness-stop"),
        # Dos hooks distintos sobre la MISMA ocurrencia: contar filas daria 5.
        _row("2026-01-02T00:00:01Z", "Stop", "otro-hook"),
    ]) + "\n", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(fake / "scripts" / "measure_event_cadence.py"),
         "--json", "--event", "Stop"],
        cwd=tmp_path,                      # cwd AJENO al clon, a proposito
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)

    assert data["sessions"] == 2, "no delimito las sesiones por SessionStart"
    stop = data["events"]["Stop"]
    assert stop["occurrences"] == 4, (
        "esperaba 4 ocurrencias (3 del rotado + 1 del vivo). 1 significa que "
        "ignoro el .gz; 5 significa que conto filas y no ocurrencias"
    )
    assert stop["max_per_session"] == 3
    assert stop["census"]["blind"], "un censo sin ceguera declarada no es un censo"


def test_zero_rows_is_reported_as_blindness_not_as_a_finding(tmp_path: Path) -> None:
    """La sonda contraria: un evento sin filas no puede salir como 'cero'."""
    fake = tmp_path / "clone"
    (fake / "scripts").mkdir(parents=True)
    (fake / "cos_lib").mkdir()
    (fake / ".cognitive-os" / "metrics" / ".archive").mkdir(parents=True)
    (fake / "scripts" / "measure_event_cadence.py").write_text(
        ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")
    (fake / "cos_lib" / "__init__.py").write_text("", encoding="utf-8")
    (fake / "cos_lib" / "measurement.py").write_text(
        (REPO_ROOT / "cos_lib" / "measurement.py").read_text(encoding="utf-8"),
        encoding="utf-8")
    (fake / ".cognitive-os" / "metrics" / "hook-timing.jsonl").write_text(
        _row("2026-01-01T00:00:00Z", "SessionStart", "witness-start") + "\n",
        encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(fake / "scripts" / "measure_event_cadence.py"),
         "--json", "--event", "TaskCreated"],
        cwd=tmp_path, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    ev = json.loads(proc.stdout)["events"]["TaskCreated"]
    assert ev["observed"] is False
    assert ev["max_per_session"] is None, (
        "un evento no observado no puede devolver un maximo: 'no vi' y 'vi cero' "
        "dejarian de distinguirse, que es la falla #1 de cos_lib/measurement.py"
    )
