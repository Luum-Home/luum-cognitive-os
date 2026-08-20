"""Cada test acá corresponde a una falla real de la sesión 2026-08-19.

No son casos inventados: son los cinco errores que se cometieron ese día, uno
por uno, afirmando que el tipo ahora los vuelve imposibles de representar en vez
de meramente evitables. Si alguno de estos tests se afloja, el error vuelve.
"""

from __future__ import annotations

import pytest

from cos_lib.measurement import (
    Census,
    CensusError,
    NotReproducible,
    WindowMismatch,
)


def _censo(**kw):
    base = dict(
        subject="sujeto",
        sources=("fuente",),
        buckets={"ok": 1},
        blind={"ninguna": 0},
        how="python3 -m pytest tests/unit/test_measurement_census.py",
    )
    base.update(kw)
    return Census(**base)


# ── Falla #1: contar el archivo vivo sin sus .gz rotados ────────────────────
def test_un_censo_sin_fuentes_declaradas_no_se_puede_construir() -> None:
    with pytest.raises(CensusError, match="de dónde se leyó"):
        _censo(sources=())


def test_las_fuentes_viajan_en_la_salida_legible() -> None:
    c = _censo(sources=("hook-timing.jsonl", ".archive/hook-timing-*.jsonl.gz"))
    assert ".archive/hook-timing-*.jsonl.gz" in c.render()


# ── Falla #2: comparar dos fuentes sobre ventanas distintas ─────────────────
def test_comparar_ventanas_distintas_es_una_excepcion_no_una_conclusion() -> None:
    a = _censo(subject="a", window="2026-08-14/2026-08-19")
    b = _censo(subject="b", window="2026-08-18/2026-08-19")
    with pytest.raises(WindowMismatch, match="Alineá las ventanas"):
        a.compare_with(b)


def test_ventanas_iguales_comparan_sin_drama() -> None:
    a = _censo(subject="a", window="w", buckets={"ok": 302})
    b = _censo(subject="b", window="w", buckets={"ok": 288})
    assert a.compare_with(b) == (302, 288)


# ── Falla #3: CLOSED sobre el total en vez de sobre lo medible ──────────────
def test_la_fraccion_es_sobre_lo_medible_no_sobre_la_poblacion() -> None:
    """Los números reales del lazo de adherencia de ese día."""
    c = Census(
        subject="adherencia a sugerencias de alta confianza",
        sources=("skill-suggestion.jsonl", "skill-invocations.jsonl"),
        buckets={"CLOSED": 2, "BYPASSED": 0, "UNTRACED": 10},
        blind={"instrumento mudo en la ventana": 90},
        how="python3 -m pytest tests/unit/test_measurement_census.py",
    )
    assert c.population == 102
    assert c.measurable == 12
    # 2/12 = 16.7%, la lectura correcta. NO 2/102 = 2%, que fue la publicada.
    assert c.share("CLOSED") == pytest.approx(2 / 12)
    assert c.share("CLOSED") != pytest.approx(2 / 102)
    assert c.blind_ratio == pytest.approx(90 / 102)


def test_un_cero_bajo_ceguera_alta_no_es_un_hallazgo() -> None:
    c = Census(
        subject="bypasses auditados",
        sources=("skill-bypass.jsonl",),
        buckets={"BYPASSED": 0},
        blind={"el productor nunca escribio": 90},
        how="python3 -m pytest tests/unit/test_measurement_census.py",
    )
    assert c.count("BYPASSED") == 0
    assert c.is_a_finding("BYPASSED") is False
    assert "no-observación" in c.describe("BYPASSED")
    assert c.exit_code(findings="BYPASSED") == 0


def test_un_cero_con_visibilidad_completa_si_es_un_hallazgo() -> None:
    c = Census(
        subject="violaciones",
        sources=("censo completo",),
        buckets={"violaciones": 0},
        blind={"ninguna": 0},
        how="python3 -m pytest tests/unit/test_measurement_census.py",
    )
    assert c.is_a_finding("violaciones") is True
    assert "no-observación" not in c.describe("violaciones")


# ── Falla #5: contar un proxy sin el filtro que lo hace válido ──────────────
def test_ningun_caso_se_pierde_entre_las_categorias() -> None:
    c = Census(
        subject="bloqueos",
        sources=("transcripts",),
        buckets={"bloqueos reales": 88},
        blind={"banner impreso por un cat, sin is_error": 13},
        how="python3 -m pytest tests/unit/test_measurement_census.py",
    )
    assert c.population == c.measurable + c.blind_total == 101


def test_un_desenlace_no_declarado_explota_en_vez_de_devolver_cero() -> None:
    c = _censo(buckets={"ok": 3})
    with pytest.raises(CensusError, match="no es un desenlace declarado"):
        c.count("inexistente")


# ── La ceguera es obligatoria, no opcional ──────────────────────────────────
def test_omitir_la_ceguera_no_se_puede() -> None:
    with pytest.raises(CensusError, match="declarar la ceguera"):
        _censo(blind={})


def test_afirmar_visibilidad_total_es_una_declaracion_explicita() -> None:
    c = _censo(blind={"ninguna": 0})
    assert c.blind_total == 0
    assert c.mostly_blind is False


# ── None, nunca 0.0, cuando no hay nada que medir ───────────────────────────
def test_poblacion_vacia_devuelve_none_y_no_cero() -> None:
    c = Census(
        subject="vacio",
        sources=("f",),
        buckets={"ok": 0},
        blind={"ninguna": 0},
        how="python3 -m pytest tests/unit/test_measurement_census.py",
    )
    assert c.blind_ratio is None
    assert c.share("ok") is None


def test_solapamiento_entre_buckets_y_blind_es_un_error() -> None:
    with pytest.raises(CensusError, match="buckets y en blind"):
        _censo(buckets={"x": 1}, blind={"x": 1})


@pytest.mark.parametrize("valor", [-1, 1.5, True])
def test_conteos_invalidos_se_rechazan(valor) -> None:
    with pytest.raises(CensusError):
        _censo(buckets={"ok": valor})


def test_to_dict_lleva_poblacion_y_ceguera_para_el_consumidor_maquina() -> None:
    d = _censo(buckets={"ok": 4}, blind={"sin permiso": 6}).to_dict()
    for clave in ("population", "measurable", "buckets", "blind", "blind_ratio", "sources"):
        assert clave in d, f"falta {clave}: un consumidor podria publicar el conteo pelado"
    assert d["population"] == 10


# ── Procedencia: el numero no viaja sin el comando que lo reproduce ─────────
def test_un_censo_sin_comando_de_reproduccion_no_se_puede_construir() -> None:
    with pytest.raises(NotReproducible, match="falta el comando"):
        _censo(how="   ")


def test_una_descripcion_en_prosa_no_pasa_por_comando() -> None:
    """El verde barato de esta familia: escribir "lo verifiqué" en el campo."""
    for prosa in ("lo verifiqué a mano", "grepped the file locally", "ver el script"):
        with pytest.raises(NotReproducible, match="no tiene forma de comando"):
            _censo(how=prosa)


def test_el_comando_viaja_en_la_salida_legible_y_en_la_maquina() -> None:
    c = _censo(how="scripts/foo.py --json")
    assert "reproducir: scripts/foo.py --json" in c.render()
    assert c.to_dict()["how"] == "scripts/foo.py --json"
