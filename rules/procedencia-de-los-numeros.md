<!-- SCOPE: both -->
# Procedencia de los números

> **Ningún número viaja sin el comando que lo produce.** No "lo verifiqué" — el
> comando, tal que otro pueda correrlo y obtener el mismo número. Si no lo hay,
> se escribe **"relatado, sin verificar"**.

## Por qué existe esta norma

El 2026-08-19, una sesión de catorce horas cometió **diez veces el mismo error**.
No diez errores distintos: el mismo, diez veces.

| # | Se afirmó | Era |
|---|---|---|
| 1 | "6 hooks nunca dispararon" | 2 — se contó el archivo vivo sin sus `.gz` rotados |
| 2 | "la telemetría es muestreo del 5%" | censo completo — dos fuentes sobre ventanas distintas |
| 3 | "0 invocaciones, 0 bypasses" | 16,7% sobre lo medible, 88% de ceguera |
| 4 | "el test de conformidad es ciego" | tenía el defecto correctamente baselineado |
| 5 | "101 bloqueos" | 88 — el banner lo imprime también un `cat` del hook |
| 6 | "19 hooks sin test" | 6 — `TEST_ROOTS` era ciego a 15 de 19 directorios |
| 7 | "1424/1424 sondas" | 1424 passed **+ 3 failed** |
| 8 | "36 hooks nunca corrieron" | 27 corren, invocados por el dispatcher |
| 9 | "la única cabecera con gate no derivó" | los números eran **presencias**, no derivas |
| 10 | "falso positivo del guard" | verdadero positivo — no se leyó su contrato |

**El invariante: se leyó la SALIDA y no el PRODUCTOR.** No se leyó que el jsonl
rota, ni los rangos de fecha, ni qué cubre el test, ni la constante del corpus,
ni el dispatcher, ni el contrato del guard.

## Por qué no alcanza con "acordate de verificar"

Es económico, no moral. **Leer el productor cuesta una llamada y contexto;
consumir el número cuesta cero.** Con muchos hilos en paralelo el camino barato
gana siempre, y este repo tiene evidencia de sobra de que las reglas que piden
recordar no disparan.

Lo que cambia la economía es que **el número no viaje solo**: si llega con el
comando pegado, leer el productor deja de costar.

## La forma

- **En prosa dirigida a una persona** — el comando en el mismo mensaje que el
  número. No en un anexo, no "está en el informe": al lado.
- **En mensajes de commit** — línea `verify:` con el comando y el número que
  produjo, como ya hacen los commits de esta sesión.
- **En manifests sobre sistemas ajenos** — `verified:` (cuándo) y `how:` (con
  qué). Exigido por `tests/contracts/test_external_claims_declare_verification.py`.
- **En la salida de una primitiva** — el reporte dice cómo reproducirse.

## El segundo tramo: correr el instrumento, no reimplementarlo

El caso 3 de la tabla no fue falta de comando: fue **el comando equivocado**.
`scripts/skill_adherence_loop.py` ya existía, ya tenía la categoría
`UNMEASURABLE` y ya imprimía la advertencia exacta que hacía falta —*"un cero en
UNTRACED con ceguera alta NO es un lazo cerrado: es un lazo no observado"*—. En
vez de correrlo se escribió un `Counter` a mano, que no sabía decir "no puedo
ver".

> **Lo que se pierde al reimplementar un instrumento es SIEMPRE su capa de
> declaración de incertidumbre**, que es la parte cara de construir y la que
> nadie reimplementa.

Entonces: **antes de contar algo, buscar si el repo ya lo cuenta.** Si existe, se
corre. Reimplementarlo es el defecto, no el atajo.

## Lo que esta norma NO arregla

No impide correr el comando equivocado: si el comando está mal, el número está
mal aunque esté pegado. Pero de los diez casos, el problema fue **no tener
comando** —un número ajeno o una inferencia propia— en ocho o nueve. Pegarlo los
habría hecho visibles en el momento, no tres horas después.

## Instrumentos que ya la implementan

`cos_lib/measurement.Census` (no se construye sin declarar fuentes ni ceguera) ·
`scripts/external_claim_freshness_audit.py` (fecha y método de toda afirmación
externa) · `tests/contracts/test_shipped_audits_declare_population.py` (un
auditor que shippea no publica un conteo sin su población) ·
`manifests/claude-code-hooks-schema.yaml` (`url` + `verified:` + `how:` por
fuente, el mejor ejemplo del repo).

## Disparador

Toda afirmación con un número. Especialmente las que sostienen una decisión:
recortar, borrar, registrar, desregistrar, mover un presupuesto. Un número
decorativo no la necesita; uno que decide algo, sí.
