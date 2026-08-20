# SCOPE: both
"""Un conteo es una afirmación sobre una población. Este módulo hace imposible
publicar el conteo sin publicar la población.

Origen: 2026-08-19. Cinco veces en una sola sesión se reportó un número que
significaba "el instrumento no puede ver este caso" y se leyó como "el caso no
ocurrió". Las cinco tienen la misma forma —contar un proxy sin chequear si su
ausencia significa *no* o significa *no puedo ver*— y ninguna se habría evitado
con más disciplina:

    1. filas del archivo vivo, ignorando los .gz rotados   -> "nunca disparó"
    2. dos fuentes sobre ventanas temporales distintas     -> "muestreo del 5%"
    3. CLOSED sobre el total en vez de sobre lo medible    -> "0% de adherencia"
    4. "9 passed" sin leer qué cubre ese passed            -> "el test es ciego"
    5. el banner en tool_result, que un `cat` del archivo
       también imprime, sin exigir is_error                -> 101 en vez de 88

La conclusión que produjo este módulo: el arreglo no es acordarse de chequear,
es que el tipo de salida no permita representar el error. Un ``Census`` no se
puede construir perdiendo casos, y no devuelve ``0.0`` cuando no hay nada
medible: devuelve ``None``. "No pude ver" y "vi cero" dejan de ser el mismo
valor.

El modelo previo en este repo es ``scripts/skill_adherence_loop.py``, que ya
declaraba UNMEASURABLE junto a sus veredictos y advertía en su propia salida que
un cero bajo ceguera alta no es un lazo cerrado sino un lazo no observado. Es la
misma idea que Kyverno emitiendo ``pass`` además de ``fail``: una guarda que
evalúa y no emite nada es indistinguible de una guarda rota.

Lo que este tipo NO puede hacer, dicho para que nadie se confíe: no impide que
alguien lea ``census.buckets["X"]`` y publique ese entero suelto. Hace que el
camino honesto sea el más corto, no que el deshonesto sea imposible.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

__all__ = ["Census", "CensusError", "NotReproducible", "WindowMismatch", "looks_runnable"]

# Por encima de esta fracción de ceguera, todo cero del censo se anota como no
# observado en vez de como hallazgo.
BLIND_WARNING_THRESHOLD = 0.20


# Cabezas de comando que producen salida verificable. La lista es corta a
# proposito: no busca ser exhaustiva, busca que una frase en prosa no pase por
# comando. Un runner que falte se agrega; un token con `/` o con sufijo de
# script ya alcanza sin tocar esta lista.
RUNNERS = frozenset(
    {
        "awk", "bash", "cat", "comm", "curl", "diff", "docker", "find", "gh",
        "git", "go", "grep", "head", "jq", "ls", "make", "node", "npm", "npx",
        "pytest", "python", "python3", "rg", "sed", "sh", "sort", "sqlite3",
        "tail", "uniq", "uv", "wc", "xargs", "yq", "zsh",
    }
)

_SCRIPT_SUFFIXES = (".py", ".sh", ".bash", ".zsh", ".ts", ".js", ".go")


def looks_runnable(command: str) -> bool:
    """Forma de comando, no ejecutabilidad. Distingue orden de prosa.

    Verdadero cuando la cabeza es un runner conocido, o cuando algun token
    nombra una ruta (`/`) o un script. Lo que NO hace, dicho para que nadie se
    confie: no corre nada, no chequea que el archivo exista (eso es del gate,
    que si sabe donde esta el repo) y no verifica que el comando reproduzca el
    numero. Es la barrera contra "lo verifique a mano", no contra un comando
    equivocado.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if not tokens:
        return False
    if Path(tokens[0]).name in RUNNERS:
        return True
    return any("/" in t or t.endswith(_SCRIPT_SUFFIXES) for t in tokens)


class CensusError(ValueError):
    """Un censo que perdería casos, o que no declara su ceguera."""


class NotReproducible(CensusError):
    """Un censo cuyo `how` no es un comando que otro pueda correr."""


class WindowMismatch(CensusError):
    """Dos censos comparados sobre ventanas distintas. Falla #2, hecha imposible."""


@dataclass(frozen=True)
class Census:
    """Resultado de una medición, con su población y su ceguera pegadas.

    ``buckets`` son los desenlaces que el instrumento SÍ pudo juzgar.
    ``blind`` son las razones por las que no pudo juzgar el resto. ``blind`` no
    tiene default a propósito: declarar qué no podés ver es parte de medir, y
    un instrumento que de verdad lo ve todo lo afirma escribiendo
    ``blind={"ninguna": 0}`` — que es una afirmación, no una omisión.

    ``how`` es el comando que reproduce este censo. Va pegado al número por el
    mismo motivo que ``sources``: leer el productor tiene que costar cero. Sin
    él, verificar un conteo cuesta una búsqueda, y bajo varios hilos en paralelo
    el camino barato —consumir el número y seguir— gana siempre.
    """

    subject: str
    sources: tuple[str, ...]
    buckets: Mapping[str, int]
    blind: Mapping[str, int]
    how: str
    window: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise CensusError("un censo sin sujeto no dice qué contó")
        if not self.sources:
            raise CensusError(
                f"{self.subject}: falta declarar de dónde se leyó. La falla #1 fue "
                "contar el archivo vivo sin sus rotados; nombrar las fuentes la "
                "hace visible en la propia salida."
            )
        if not self.buckets:
            raise CensusError(f"{self.subject}: un censo sin desenlaces no mide nada")
        if not self.blind:
            raise CensusError(
                f"{self.subject}: falta declarar la ceguera. Si el instrumento ve "
                'todos los casos, afirmalo con blind={"ninguna": 0}.'
            )
        if not self.how.strip():
            raise NotReproducible(
                f"{self.subject}: falta el comando que reproduce este censo. Un "
                "conteo sin su comando obliga a quien lo lee a buscar el "
                "instrumento, y bajo presión nadie lo busca: lo consume."
            )
        if not looks_runnable(self.how):
            raise NotReproducible(
                f"{self.subject}: how={self.how!r} no tiene forma de comando. "
                "Se espera algo que otro pueda pegar en una terminal y obtener "
                "el mismo número, no una descripción de lo que hiciste."
            )
        for name, counts in (("buckets", self.buckets), ("blind", self.blind)):
            for key, value in counts.items():
                if not isinstance(value, int) or isinstance(value, bool):
                    raise CensusError(f"{self.subject}: {name}[{key!r}] no es un entero")
                if value < 0:
                    raise CensusError(f"{self.subject}: {name}[{key!r}] es negativo")
        solapadas = set(self.buckets) & set(self.blind)
        if solapadas:
            raise CensusError(
                f"{self.subject}: {sorted(solapadas)} está en buckets y en blind a la vez"
            )

    # ── población ────────────────────────────────────────────────────────────
    @property
    def population(self) -> int:
        """Todos los casos considerados. Por construcción no se pierde ninguno."""
        return self.measurable + self.blind_total

    @property
    def measurable(self) -> int:
        return sum(self.buckets.values())

    @property
    def blind_total(self) -> int:
        return sum(self.blind.values())

    @property
    def blind_ratio(self) -> float | None:
        """``None`` sobre población vacía: no hay ceguera que reportar, ni 0.0."""
        if self.population == 0:
            return None
        return self.blind_total / self.population

    @property
    def mostly_blind(self) -> bool:
        r = self.blind_ratio
        return r is not None and r > BLIND_WARNING_THRESHOLD

    # ── lectura ──────────────────────────────────────────────────────────────
    def count(self, bucket: str) -> int:
        if bucket not in self.buckets:
            raise CensusError(
                f"{self.subject}: {bucket!r} no es un desenlace declarado "
                f"(hay {sorted(self.buckets)}). Pedir un desenlace inexistente "
                "devolvería 0 y ese 0 es exactamente el error que este módulo evita."
            )
        return self.buckets[bucket]

    def share(self, bucket: str) -> float | None:
        """Fracción SOBRE LO MEDIBLE, nunca sobre la población.

        ``None`` cuando no hay nada medible — la falla #3 fue publicar el
        cociente sobre el total y leer el resultado como incumplimiento.
        """
        n = self.count(bucket)
        return None if self.measurable == 0 else n / self.measurable

    def is_a_finding(self, bucket: str) -> bool:
        """¿Este conteo afirma algo, o es una no-observación?

        Un cero bajo ceguera alta no es un hallazgo. Devolver ``False`` acá es
        el punto entero del módulo.
        """
        return self.count(bucket) > 0 or not self.mostly_blind

    def describe(self, bucket: str) -> str:
        n = self.count(bucket)
        s = self.share(bucket)
        pct = "n/d" if s is None else f"{100 * s:.1f}%"
        txt = f"{n} de {self.measurable} medibles ({pct})"
        if self.blind_total:
            txt += f", {self.blind_total} fuera de alcance"
        if n == 0 and self.mostly_blind:
            txt += "  <- NO es un hallazgo: es una no-observación"
        return txt

    # ── comparación ──────────────────────────────────────────────────────────
    def compare_with(self, other: "Census") -> tuple[int, int]:
        """Compara poblaciones. Se niega si las ventanas no coinciden.

        La falla #2 fue comparar dos fuentes sobre rangos temporales distintos y
        concluir "muestreo del 5%" sobre lo que era un censo completo. Acá eso es
        una excepción, no una conclusión.
        """
        if self.window != other.window:
            raise WindowMismatch(
                f"ventanas distintas: {self.subject}={self.window!r} vs "
                f"{other.subject}={other.window!r}. Alineá las ventanas antes de "
                "comparar; comparar sin alinear ya produjo una conclusión falsa."
            )
        return self.population, other.population

    # ── salida ───────────────────────────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "sources": list(self.sources),
            "how": self.how,
            "window": self.window,
            "population": self.population,
            "measurable": self.measurable,
            "buckets": dict(self.buckets),
            "blind": dict(self.blind),
            "blind_total": self.blind_total,
            "blind_ratio": self.blind_ratio,
            "notes": list(self.notes),
        }

    def render(self) -> str:
        out = [
            f"{self.subject}",
            f"  fuentes: {', '.join(self.sources)}",
            f"  reproducir: {self.how}",
        ]
        if self.window:
            out.append(f"  ventana: {self.window}")
        out.append(f"  poblacion: {self.population}  medibles: {self.measurable}")
        for key in self.buckets:
            out.append(f"    {key:24s} {self.describe(key)}")
        if self.blind_total:
            out.append("  fuera del alcance del instrumento:")
            for key, value in self.blind.items():
                if value:
                    out.append(f"    {key:24s} {value}")
        for note in self.notes:
            out.append(f"  nota: {note}")
        if self.mostly_blind:
            r = self.blind_ratio or 0.0
            out += [
                "",
                f"  AVISO: {100 * r:.1f}% de los casos quedan fuera del alcance de este",
                "  instrumento. No se cuentan ni a favor ni en contra. Un cero acá no",
                "  es un resultado: es una no-observación.",
            ]
        return "\n".join(out)

    def exit_code(self, *, findings: str | tuple[str, ...]) -> int:
        """0 sin hallazgos, 1 con hallazgos. La convención del repo."""
        keys = (findings,) if isinstance(findings, str) else findings
        return 1 if any(self.is_a_finding(k) and self.count(k) for k in keys) else 0
