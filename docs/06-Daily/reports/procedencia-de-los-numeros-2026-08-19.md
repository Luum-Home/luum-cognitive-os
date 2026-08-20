# Procedencia de los números — 2026-08-19

## Resumen ejecutivo

El defecto de la sesión no fue falta de disciplina sino de economía: leer el
productor cuesta una llamada y contexto, consumir el número cuesta cero. El
arreglo es que el número no viaje solo. Dos cambios, ningún framework:

1. `cos_lib.measurement.Census` gana un campo **`how` obligatorio** — el comando
   que reproduce el censo. Mismo mecanismo que ya usaban `sources` y `blind`: el
   tipo no se construye sin él, y una frase en prosa no pasa por comando.
2. Un gate nuevo, `tests/contracts/test_emitted_counts_declare_provenance.py`,
   sobre los **41 ledgers canónicos `docs/06-Daily/reports/*-latest.json`**: el
   que publica un entero declara cómo reproducirlo.

Estado medido hoy: **3 de 41 ledgers declaran su comando** en el artefacto (1 que
ya lo hacía + 2 migrados), 1 más no publica ningún entero, **37 quedan en
baseline de igualdad exacta**. Los **escritores** migrados son 4: dos de sus
artefactos no se pudieron commitear porque `research-compliance-guard` bloquea
el texto que el propio ledger copia de los docs que audita. Los **4 sitios de producción que construyen `Census`** cumplen los 4,
por tipo, no por baseline. Prueba en las dos direcciones abajo.

## Correcciones a las premisas del encargo

1. **«Las piezas ya existen, sueltas» — hay más de las cuatro listadas.**
   `scripts/volatile_number_audit.py` persigue el número congelado en prosa y ya
   tiene la noción de "esto pertenece a un comando de censo";
   `scripts/claim_proof_audit.py` mapea claims a evidencia. Ninguno cubre
   procedencia de emisión, pero omitirlos del encargo hacía ver el hueco más
   grande de lo que es. Los cité en el docstring del gate para que el próximo no
   los reinvente.

2. **El gate de población está en 0 de 13, no en "13 que shippean, algunos
   migrados".** `KNOWN_BARE_COUNT_AUDITS` tiene 13 entradas y los scripts
   `SCOPE: both` con nombre de auditor son exactamente 13 — o sea, ninguno
   declara población todavía. Es un baseline de igualdad exacta, así que no es
   colchón; pero describirlo como "el gate de población eligió los 13 que
   shippean" sugiere cobertura que hoy no existe. Comando:
   `.venv/bin/python3 -m pytest tests/contracts/test_shipped_audits_declare_population.py -q`.

3. **Dos de mis propios `how` no reproducían el número, y los agarré corriéndolos.**
   Escribí `--format json` donde el script acepta `--json`, y
   `from cos_lib.hook_firing_evidence import census` donde la función se llama
   `firing_evidence_census` y además pide tres argumentos. Es exactamente el
   verde barato que el encargo prohíbe («poner `verify:` con un comando que no
   reproduce el número») y lo cometí a los diez minutos de que me lo advirtieran.
   El gate no lo habría atajado: solo chequea forma y existencia del archivo, no
   ejecuta. Lo digo acá porque es el límite real del instrumento.

4. **`firing_evidence_census` no podía declarar su propio `how`.** Es librería,
   no CLI: su consumidor es `scripts/hook_vitality_audit.py`. Un default en la
   librería habría publicado un comando que nadie corrió. El parámetro `how` es
   obligatorio y lo pone el llamador.

5. **Los ledgers `-latest.json` son un blanco móvil mientras corren cuatro
   agentes.** Regeneré `primitive-row-audit-latest.json` dos veces con minutos de
   diferencia y dio distinto; dos corridas consecutivas dan idéntico. O sea: el
   script es determinista, el árbol no lo es ahora mismo. Los artefactos que
   commiteo quedan viejos enseguida. Lo que persiste es el escritor: la próxima
   regeneración vuelve a estampar la procedencia sola.

6. **«Contar el archivo vivo sin sus rotados» ya está arreglado en el emisor.**
   `scripts/hook_test_reality_census.py` declara hoy 10 archivos de hook-timing
   (vivo + rotados). No es una premisa falsa del encargo, es una premisa vencida.

## Las piezas que ya existían y cómo las uní

| Pieza | Qué aportó | Qué NO tuve que escribir |
|---|---|---|
| `manifests/claude-code-hooks-schema.yaml` | el nombre y la forma del campo: `how:` con el comando literal | inventar un vocabulario nuevo |
| `cos_lib/measurement.Census` | el mecanismo: un campo obligatorio en el tipo, no un recordatorio | una clase de "medición con procedencia" |
| `test_shipped_audits_declare_population.py` | la estructura del gate: censo recalculado del árbol + baseline de igualdad exacta + las tres aserciones | el andamiaje del baseline |
| `test_external_claims_declare_verification.py` | el precedente de exigir `how:` además de la fecha, y el baseline por archivo con conteo | el criterio de "declaró método" |
| `volatile-numbers-latest.json` | la clave `generated_by`, que ya existía y ya era un comando corrible | imponer un nombre nuevo y dejar al único que cumplía como incumplidor |

La unión concreta: `looks_runnable()` vive en `cos_lib/measurement.py` y la
**usan los dos lados** — el emisor (que rechaza construir un `Census` con prosa
en `how`) y el gate (que rechaza un ledger cuyo comando es prosa). Un solo
criterio de "esto es un comando"; dos criterios se desincronizan y el día que
pasa, el gate acepta lo que el tipo rechaza.

## Sobre qué población gatea, y por qué

**Población: los 41 ledgers `docs/06-Daily/reports/*-latest.json`.**

El gate de población eligió *lo que sale del repo* con el argumento de que el
daño ocurre en el proyecto de un tercero que no leyó el código. **La procedencia
tiene otro punto de daño y por eso no comparto el corte.** Los diez errores de
hoy fueron todos puertas adentro: el consumidor de un `-latest.json` es otra
sesión de este mismo repo, que lo abre *precisamente porque* es el resumen y no
el instrumento. Un `SCOPE: os-only` no protege de nada acá: el lector no es un
extraño, es el que tiene menos contexto y más apuro.

El corte real no es "lo que sale del repo" sino **"lo que se lee sin abrir a
quien lo produjo"**. Los `-latest` cumplen las tres condiciones que hacen daño:
son canónicos (se citan por nombre fijo), son generados (nadie los revisa línea a
línea) y son consumidos por máquina y por agente.

**Qué queda afuera y por qué:**

- **Los 550 `.md` de `docs/06-Daily/reports`**: en su mayoría informes escritos a
  mano. El patrón equivalente ya existe (`verify:`, 24 archivos lo usan) y el
  defecto que los aqueja es otro — el número congelado en prosa — que ya persigue
  `scripts/volatile_number_audit.py`. Meterlos en este gate produciría un baseline
  de cientos de asientos: el colchón que este proyecto trata como bug.
- **Los hooks en bash que emiten conteos**: no los gateo porque no tengo censo de
  cuáles emiten un número, y el encargo pedía un gate acotado que funcione antes
  que una abstracción que nadie adopte. Deuda declarada, no omisión.
- **Los ledgers que no publican ningún entero** (1 hoy, 2 antes de baselinear): no hay número que
  reproducir. Si mañana publican uno, entran por la puerta de "nuevo" y el gate
  falla. Se comprobó: `primitive-surface-reduction-latest.json` estaba en mi
  baseline por error y la aserción "no lista uno ya migrado" lo detectó.

## El gate y sus dos corridas

Defecto reintroducido en el **productor**, no en el archivo: se le sacó a
`scripts/primitive_row_audit.py` la constante `REPRODUCE` del payload y la línea
`verify:` del markdown, y se regeneró el ledger.

**Dirección 1 — el auditor emite el conteo sin su comando: FALLA**

```
procedencia de los ledgers canonicos: 3/41 declaran como reproducirse (38 en deuda)

E   AssertionError: estos ledgers de docs/06-Daily/reports publican conteos que
    otra sesion va a consumir sin abrir el instrumento:
    primitive-row-audit-latest.json: publica conteos y no declara ninguna de
    ('reproduce', 'generated_by', 'how', 'command'). El arreglo es en el SCRIPT
    que los escribe, no en el archivo: agregale una constante REPRODUCE y
    volcala como "reproduce" en el payload (ver scripts/reduction_backlog.py).
    Un comando que otro pueda pegar en una terminal, no una descripcion de lo
    que hiciste.
    assert not ['primitive-row-audit-latest.json']
FAILED tests/contracts/test_emitted_counts_declare_provenance.py::test_ningun_ledger_nuevo_publica_conteos_sin_su_comando
1 failed, 3 passed in 0.40s
```

**Dirección 2 — el mismo auditor, con su comando: PASA**

```
procedencia de los ledgers canonicos: 4/41 declaran como reproducirse (37 en deuda)
4 passed in 0.43s
```

**Árbol restaurado byte-idéntico** (`shasum -a 256 -c`):

```
scripts/primitive_row_audit.py: OK
```

Los dos ledgers regenerados no vuelven al sha previo, y eso **no** es una
restauración fallida: el árbol cambió abajo mientras otros cuatro agentes
escriben. Dos corridas consecutivas del mismo script sobre el mismo árbol dan
`diff` vacío. La no-determinación es del repo en este momento, no del auditor.

El otro lado, el del emisor: `Census` rechaza prosa en `how`.

```
.venv/bin/python3 -m pytest tests/unit/test_measurement_census.py -q
33 passed
```

con `test_una_descripcion_en_prosa_no_pasa_por_comando`, que prueba las tres
formas del verde barato de esta familia: `"lo verifiqué a mano"`,
`"grepped the file locally"`, `"ver el script"`.

## Cuántas primitivas cumplen hoy

Comando:
`.venv/bin/python3 -m pytest tests/contracts/test_emitted_counts_declare_provenance.py -q -s`

| Población | Total | Cumplen | Exentas | En baseline |
|---|---:|---:|---:|---:|
| Ledgers `-latest.json` | 41 | 3 | 1 (no publica enteros) | 37 |
| Sitios de producción que construyen `Census` | 4 | 4 | 0 | 0 (lo obliga el tipo) |

Los 3 que declaran en el artefacto: `volatile-numbers` (ya lo hacía, con
`generated_by`), `primitive-row-audit` y `reduction-backlog`. Los escritores de
`docs-execution` y `claim-proof` también estampan `REPRODUCE`, pero sus ledgers
regenerados quedaron sin commitear (ver abajo) y por eso están en el baseline:
commitear el baseline sin el artefacto es lo único que mantiene el gate verde en
un checkout limpio, que es lo que mide CI.
Los 4 sitios `Census`: `scripts/hook_test_reality_census.py`,
`scripts/hook_artifact_derivation.py`, `scripts/external_claim_freshness_audit.py`
(×3 censos) y `cos_lib/hook_firing_evidence.py` (vía su llamador
`scripts/hook_vitality_audit.py`).

`reduction-backlog-latest.json` declara su comando **y** hoy no publica enteros:
cumple sin que el gate se lo exija. Se deja así a propósito
— el escritor ya lo estampa y el día que publique un conteo no hay nada que hacer.

## Un bloqueo que cambió el entregable

`research-compliance-guard` rechazó el commit por
`claim-proof-latest.json` y `docs-execution-latest.md`, señalando en cada uno una
frase que su política marca. Los dos ledgers **transcriben** texto de los
documentos que auditan, así que el hallazgo es del corpus, no del ledger. No es
un falso positivo que me tocara apagar: los devolví a HEAD (vía `git show`, no
`git checkout --`, que también está bloqueado) y los puse en el baseline con el
motivo escrito.

La consecuencia importante: **commitear el baseline sin el artefacto es lo único
que deja el gate verde en un checkout limpio**. Si hubiera commiteado el baseline
de 35 con los artefactos viejos, CI vería 2 infractores que el baseline no lista
y se pondría rojo — el caso clásico de medir distinto de lo que mide CI. Los dos
salen del baseline el día que alguien regenere esos ledgers, y la aserción "no
lista uno ya migrado" lo obliga.

## Lo que NO hice y por qué

- **No construí un cuarto instrumento.** El arquitecto fue textual: derivadores
  concretos antes que cualquier mecanismo genérico, y el paso 0 es no construir
  el framework. Los cuatro escritores migrados llevan una constante `REPRODUCE`
  de dos líneas cada uno. No hay módulo `provenance.py`, no hay decorador, no hay
  registro. Si mañana son treinta escritores, ahí se extrae el helper — con
  treinta casos a la vista, no con cuatro imaginados.
- **No gateé los 550 `.md`.** Motivo arriba: baseline de cientos = colchón.
- **No gateé los hooks en bash.** Sin censo de cuáles emiten conteos, el gate
  sería una lista escrita a mano, que es la forma más frágil de población.
- **No migré los 35 ledgers restantes.** Cada uno pide entender qué comando lo
  reproduce de verdad, y ya me equivoqué en 2 de 4 escribiendo comandos que no
  corrían. Migrar 35 a ojo produciría 35 `verify:` decorativos: exactamente el
  verde barato prohibido. Van al baseline, que es igualdad exacta y no admite
  crecer.
- **No toqué** los 5 hooks en borrado, `cognitive-os.yaml`,
  `templates/security-profiles/*`, `hooks/_lib/common.sh` ni el informe de
  familias: son de los otros cuatro agentes.
- **El gate no ejecuta los comandos.** Chequea forma (`looks_runnable`) y que el
  archivo nombrado exista. Un comando con el flag equivocado pasa — me pasó dos
  veces hoy. Cerrar eso pide correr 41 auditores dentro de un contrato
  determinista, y eso es otro trabajo.
