# Arquitectura — derivar en vez de declarar la muerte del contenido

- Fecha: 2026-08-20
- Alcance: `scripts/*census*.py`, `scripts/*audit*.py`, `cos_lib/measurement.py`,
  `tests/contracts/test_shipped_audits_declare_population.py`, `scripts/lint-shell.sh`,
  `manifests/`. Diseño, no implementación.
- Método: read-only. No corrí la suite. Todo número de este informe lleva pegado el
  comando que lo produce; lo que no pude reproducir está marcado como tal.
- Restricción respetada: no toqué ningún archivo fuera de este informe.

---

## Resumen ejecutivo

**La tesis pierde, y por dos motivos, no uno.** El coordinador ya aceptó el primero
(el veredicto no tiene dónde aterrizar). El segundo lo medí acá y contradice la mitad
optimista que quedaba en pie: **derivar tampoco está resuelto**. El caso `CONFIG_FILE`
lo detectaba `shellcheck` de estantería —lo reproduzco abajo— y sobrevivió 112 días
porque el barrido del gate se define con `find scripts -maxdepth 1` y el archivo está
en `scripts/_lib/`. En la misma familia: el gate que obliga a declarar población elige
su corpus con un regex de **nombre de archivo** (`audit|_scan|verify|check`), mira 13
de 67 scripts `SCOPE: both` y no ve a ninguno que se llame *census*.

Convergen, y son más de cuatro: **siete instrumentos con la misma forma**, diez que ya
construyen `Census`. La forma es un **join bipartito** entre dos censos sobre una clave
compartida, con cuatro cuadrantes más ceguera más ausencia declarada.

**El contrato que propongo agrega un campo decisivo: `corpus_closure`.** Un corpus
cerrado autoriza a dictar veredicto y salir 1; uno abierto sólo puede emitir candidato.
Ésa es la frontera entre detectar y decidir, y no depende del tipo de artefacto.
**Costo**: declarar cuesta 4,13 commits por artefacto contra 2,34 de derivar, pero la
comparación es tramposa y explico por qué. La combinación correcta es **N derivaciones
para la membresía + UN ledger para la decisión**, nunca N ledgers.

---

## Correcciones a las premisas del encargo

1. **No son cuatro derivaciones: son siete, y dos nacieron hoy sin trackear.**
   El encargo nombra cuatro. `git status --porcelain -- scripts/` devuelve además
   `?? scripts/dead_content_census.py`, `?? scripts/skip_absence_census.py` y
   `?? scripts/hook_artifact_derivation.py`, y `scripts/audit_instrument_productivity.py`
   ya está commiteado y tiene exactamente la misma forma. **`dead_content_census.py` es
   el instrumento que este encargo pide diseñar**, ya escrito, con las tres formas
   (campo-de-un-solo-valor, referencia-colgante, variable-escrita-nunca-leída) que
   cubren los casos 2, 4 y 3 del encargo. Diseñar sin nombrarlo habría sido reinventar
   algo que estaba en el árbol mientras yo leía.

2. **El registro común ya existe a medias y el encargo no lo menciona.**
   `cos_lib/measurement.py` no lo usan dos scripts sino diez:
   ```
   grep -rln "from cos_lib.measurement import" --include="*.py" scripts cos_lib tests lib
   ```
   Y `tests/contracts/test_shipped_audits_declare_population.py` ya es el gate que obliga
   a construir `Census`, con baseline de igualdad exacta y dos tests anti-colchón
   (`test_el_baseline_no_lista_scripts_ya_migrados`, `..._inexistentes`). El diseño que
   se pide es **extender eso**, no fundar nada.

3. **Dos de los seis casos ya están cerrados en HEAD, así que el encargo describe un
   estado de hace unas horas.** `grep -n "CONFIG_FILE" scripts/_lib/settings-driver-claude-code.sh`
   devuelve hoy dos comentarios, uno de ellos `# No CONFIG_FILE here on purpose`, y
   `ls hooks/rate-limit-protection.sh` devuelve *No such file*. No cambia la tesis;
   cambia qué queda por hacer.

4. **`CONFIG_FILE` son 112 días, no 111.** Nació en `387c9fc56` (2026-04-30,
   `feat(adr-064)`), se retiró hoy: `git log --format='%h %ad' --date=short -S'CONFIG_FILE="' -- scripts/_lib/settings-driver-claude-code.sh`.

5. **No pude reproducir "1321 locks con `status: active`".** `.cognitive-os/runtime/edit-locks`
   tiene hoy 47 entradas y son directorios, no JSON de primer nivel; y
   `python3 scripts/dead_content_census.py --form A` devuelve **0** hallazgos ahora mismo.
   El *caso* sí es real y está documentado por partida doble en el propio código
   (`scripts/edit-coop.sh:155` y `:436`); el **número no lo pude recontar**, y lo trato
   como no verificado.

6. **`INACTIVE_STATES` no está sin usar: está definido tres veces con contenidos
   distintos.** Corrijo la corrección que me llegó a mitad de tarea:
   ```
   grep -rn "INACTIVE_STATES" --include="*.py" . | grep -v '^./.git'
   ```
   `scripts/active_primitive_index.py:19` incluye `"candidate"`;
   `scripts/cos_manifest_tier_claim_audit.py:31` y
   `tests/contracts/test_primitive_runtime_reality.py:17` no. Tres lectores, dos
   semánticas. No es contenido muerto: es una **divergencia silenciosa**, que es peor,
   porque los tres están vivos y contestan distinto.

7. **Confirmo lo de `sunset_criteria` y lo agravo.** `grep -c "sunset_criteria" manifests/primitive-lifecycle.yaml`
   → 671, y `grep -oE "^\s+[a-z_]*(date|deprecat|sunset|expires|removal)[a-z_]*:" manifests/primitive-lifecycle.yaml | sort | uniq -c`
   devuelve **una sola clave: `sunset_criteria`, 671 veces**. Cero campos con fecha en
   25.692 líneas.

8. **"Un instrumento con falsos positivos produce trabajo falso" es correcto pero
   incompleto.** El modo de falla que encontré medido en este repo es el opuesto y no
   está en el encargo: **un instrumento con el corpus corto produce silencio**, y el
   silencio no se ve nunca. Los falsos positivos los caza el primero que lee la lista;
   un `maxdepth 1` no lo caza nadie.

---

## Las cuatro derivaciones existentes: ¿convergen?

**Sí, y en algo más específico que "tienen forma parecida": los siete son el mismo
join.** Lado a lado, tal como están escritos:

| instrumento | población izquierda (quién declara) | población derecha (quién consume) | clave del join | cubeta-hallazgo | ausencia declarada | ceguera declarada |
|---|---|---|---|---|---|---|
| `config_knob_census.py` | hojas escalares de `cognitive-os.yaml` (236) | índice de tokens sobre 13.324 archivos de `hooks/ scripts/ cos_lib/ lib/ packages/ tests/ docs/ …` | nombre de la hoja | `sin_lector_en_este_repo` (52) | `EXAMPLE_PATH_PREFIXES` | `nombre_generico_no_discriminable` (29) |
| `state_lifecycle_census.py` | familias de archivos en `.cognitive-os/runtime` + `/metrics` | líneas de código que matchean `WRITE_PAT` / `GOVERN_PAT` / `RESET_PAT` | prefijo estable del nombre de familia | `gobierna-sin-reset`, `nadie-lo-lee` | `manifests/state-retention.yaml` | token corto, heurística govern, sesiones vivas |
| `hook_surface_census.py` | `hooks/*.sh` ∪ registro de `harness.hooks` | 9 superficies de registro (driver, settings, artefactos, dispatcher, policy, perfiles) | basename del hook | `disagreements` entre dos auditorías previas | 3 ledgers (`allowlist`, `classification`, `EXCLUDED`) | comentarios del driver (los descuenta con `strip_comments`) |
| `audit_hook_registration.py` | `harness.hooks` del yaml | superficies de alcanzabilidad + telemetría **viva y rotada** | script basename | `orphans` | `omission_declared` | `unreachable_but_observed` |
| `audit_instrument_productivity.py` | hooks de clase instrumento | corridas + artefacto escrito + consumidor del artefacto | ruta del artefacto | `no-consumer`, `no-producer`, `starved` | — | `idle` (nunca corrió en la ventana) |
| `dead_content_census.py` *(commiteado `1fa75ac69` mientras yo escribía)* | registros de una población / entradas de manifiesto / variables de un script | valores distintos / path en disco / lecturas en el mismo script | campo, path, nombre de variable | formas A, B, C | — | **ninguna** (ver defecto abajo) |
| `skip_absence_census.py` *(untracked)* | condiciones de `pytest.skip` | ruta literal resuelta (symlinks vía `locate_primitive.py`) | ruta | skip por ruta equivocada, ausencia real | dependencia opcional presente | condición no resoluble estáticamente |

**Lo que comparten, verificado, no impresionista:**

1. Los siete anclan la raíz en el repo del archivo (`Path(__file__).resolve().parent.parent`),
   no en el cwd. `audit_hook_registration.py` explica por qué en el `--help` del `--root`:
   *un auditor anclado en cwd no falla, audita el árbol equivocado y sale verde por vacío*.
2. Los siete usan el mismo contrato de salida `0 / 1 / 2`.
3. Los siete separan **tres** desenlaces donde un instrumento ingenuo tendría uno:
   encontré / no encontré / no pude mirar. Y cinco de siete agregan un cuarto:
   **la ausencia está declarada con motivo**, que no es hallazgo ni ceguera.
4. Los siete normalizan antes de unir: familias de archivo, basenames, tokens con y sin
   guión (`config_knob_census.py` usa **dos** tokenizadores y dice por qué: con uno solo
   inventaba huérfanas).

**Dónde NO convergen, que es lo que hay que arreglar:**

```
scripts/dead_content_census.py     scope=AUSENTE  census=0
scripts/skip_absence_census.py     scope=both     census=0
scripts/config_knob_census.py      scope=os-only  census=2
scripts/state_lifecycle_census.py  scope=os-only  census=1
scripts/hook_surface_census.py     scope=os-only  census=0
scripts/audit_hook_registration.py scope=os-only  census=0
scripts/audit_instrument_productivity.py scope=os-only census=0
```
(reproducible con un `for f in …; do grep -m1 "^# SCOPE:" "$f"; grep -c "Census(" "$f"; done`)

Sólo **2 de 7** construyen `Census`. Los otros cinco reimplementan a mano las mismas
cubetas con nombres distintos, y `dead_content_census.py` —el instrumento nuevo, el que
existe para censar contenido muerto— publica `[A] campo-de-un-solo-valor: 0` **sin
población**: el cero pelado que `cos_lib/measurement.py` existe para hacer irrepresentable.

**Conclusión de esta sección: la abstracción existe y está probada siete veces; lo que
falta no es descubrirla sino hacerla obligatoria.**

---

## El contrato de una derivación

Propongo extender `Census`, no reemplazarlo — el tipo ya resuelve población, ceguera,
`how` y el `None`-vs-`0.0`. Le faltan tres cosas, y las tres salieron de mirar los siete.

### 1. El join explícito

```
Derivation(
    left  = Side(name, enumerated_by, count),   # quién declara
    right = Side(name, enumerated_by, count),   # quién consume
    key   = "basename del script",              # sobre qué se unen
    census = Census(...),                       # lo de siempre
    corpus_closure = "closed" | "open",
    decided_by = "manifests/dead-content.yaml#<population-id>" | None,
)
```

`enumerated_by` es un **comando**, con la misma validación de `looks_runnable` que ya
tiene `how`. El motivo es la evidencia de la sección siguiente: la mitad de las fallas
reales de este repo no están en la lógica del instrumento sino en **cómo enumeró su
corpus**, y hoy esa enumeración vive enterrada en una función privada donde nadie la lee.

### 2. Las cubetas son un enum, no strings libres

Los cuatro cuadrantes del join, más los dos desenlaces que no son cuadrantes:

| cubeta | significado | ¿es hallazgo? |
|---|---|---|
| `VIVO` | declarante y consumidor presentes | no |
| `CONTENIDO_MUERTO` | se declara y nadie lo consume | sí, si el corpus es cerrado |
| `LECTURA_COLGANTE` | se consume y nadie lo declara | sí, siempre (el lector está en el repo) |
| `AUSENCIA_DECLARADA` | no hay consumidor **y hay motivo escrito** | no |
| `CIEGO` | el instrumento no puede discriminar | no, y nunca cuenta como cero |
| `CANDIDATO` | contenido muerto sobre corpus **abierto** | no gatea; va a triage |

Que sean un enum importa por composición: hoy `hook_surface_census.py` existe **porque
dos auditorías previas usan vocabularios distintos** (`lost` contra `profile_gated`) y
alguien tuvo que escribir un tercer instrumento de 10 KB para desempatarlas. Con
vocabulario compartido, el desempate es una comparación, no un script.

### 3. `corpus_closure`, el campo que decide si se puede gatear

- `closed`: **todo consumidor posible está dentro del corpus enumerado**. Ejemplos reales:
  las superficies de registro de un hook (son nueve archivos, enumerables); los lectores
  de una variable de shell dentro de su propio script; una entrada de manifiesto que
  apunta a un path del repo.
- `open`: puede haber un consumidor fuera. Ejemplo real: una clave de `cognitive-os.yaml`
  que lee un proyecto consumidor instalado. `config_knob_census.py` ya es honesto acá
  —su cubeta se llama `sin_lector_en_este_repo`, no "sin lector"— y esa honestidad es
  precisamente lo que el contrato tiene que volver estructural.

**Regla dura: sólo una derivación `closed` puede devolver exit 1.** Una `open` devuelve 0
y emite candidatos. Un instrumento que gatea sobre corpus abierto convierte "no lo
encontré acá" en "no existe", que es exactamente el defecto que esta sesión persiguió
doce veces, sólo que ahora automatizado y bloqueando merges.

### 4. Composición

Dos derivaciones se componen sólo si sus `key` viven en el mismo dominio — mismo criterio
que el `WindowMismatch` que `Census` ya implementa para las ventanas temporales. Propongo
`KeyMismatch` con el mismo trato: excepción, no conclusión. Unir por basename un censo que
normalizó symlinks contra otro que no lo hizo produce diferencias que parecen hallazgos.

---

## Cómo se prueba que una derivación no nació ciega

El encargo dice que el positivo sembrado en el corpus es lo que prueba que el barrido
llega. **Tengo el caso real que lo demuestra, y es de una herramienta de estantería, no
de un instrumento casero.**

### La prueba: shellcheck ya detectaba `CONFIG_FILE`, y el gate no lo miraba

```bash
git show c888aa1ba^:scripts/_lib/settings-driver-claude-code.sh > /tmp/drv.sh
shellcheck -s bash -f gcc /tmp/drv.sh | grep SC2034
# /tmp/drv.sh:39:1: warning: CONFIG_FILE appears unused. Verify use (or export
#   if used externally). [SC2034]
```

`shellcheck` está instalado en esta máquina (0.11.0). El archivo es shell, vive en
`scripts/`, y el repo tiene un gate de shellcheck. Y sin embargo:

```bash
sed -n '56,64p' scripts/lint-shell.sh
# collect_files() {
#     find "${PROJECT_ROOT}/scripts" -maxdepth 1 -name "*.sh" -type f | sort
#     find "${PROJECT_ROOT}/hooks" -name "*.sh" -type f | grep -v '/hooks/_archived/'
# }
```

**`scripts/_lib/` está a profundidad 2.** El detector era correcto, estaba instalado, y su
barrido no llegaba. 112 días.

Y el segundo piso del mismo defecto, en el baseline que ese gate usa como referencia:

```bash
cat scripts/shellcheck-baseline.txt   # 21 líneas, todas comentarios
# "This file was generated on 2026-04-20."
# "ShellCheck was NOT installed on the developer's macOS machine at capture time."
# "VIOLATION COUNT AT CAPTURE TIME: unknown"
```

Un ratchet cuya referencia significa **"no pude mirar"** y se lee como **"no había nada"**.
Es la falla #1 de `cos_lib/measurement.py`, cometida por el gate que debería prevenirla.

### El tercer piso: el gate de población tampoco alcanza su corpus

```bash
python3 - <<'PY'
import re, pathlib
RE = re.compile(r"audit|_scan|verify|check")          # el filtro real del gate
SCOPE = re.compile(r"^#\s*SCOPE:\s*(\S+)", re.M)
both = [p.name for p in sorted(pathlib.Path("scripts").glob("*.py"))
        if (m := SCOPE.search(p.read_text(errors="ignore")[:2000])) and m.group(1) == "both"]
print(len(both), sum(1 for n in both if RE.search(n)), sum(1 for n in both if not RE.search(n)))
PY
# 67 13 54
```

De **67** scripts `SCOPE: both` —los que se instalan en el proyecto de un tercero— el gate
mira **13** e ignora **54**. Entre los ignorados está `skip_absence_census.py`, que shippea
y publica conteos sin construir `Census`. La palabra `census` no está en el regex.
**La población del gate es una lista fija disfrazada de censo**, que es exactamente el
veredicto que `docs/06-Daily/reports/listas-fijas-vs-censo-2026-08-19.md` emitió hace un día
sobre otras cinco listas.

### Los cuatro tests que propongo por derivación

1. **Negativo en fixture** — lo que ya se hace: el detector no marca lo sano.
2. **Positivo sembrado EN EL CORPUS REAL** — el test nombra un caso conocido presente en
   HEAD y exige que el instrumento lo devuelva. No un fixture: el árbol. Cuesta un caso
   testigo por derivación y caza el `re.M` faltante que el encargo menciona.
3. **Prueba de alcance del corpus** — assert de que `enumerated_by` contiene un artefacto
   **profundo y conocido** (`scripts/_lib/…`, `packages/*/hooks/…`). Éste es el test que
   habría cazado el `maxdepth 1` el 30 de abril.
4. **Anti-lista-fija** — la selección de población no puede ser un literal ni un regex de
   nombre de archivo salvo con motivo escrito. El precedente ya existe: el propio gate de
   población se llama a sí mismo *"Censo, no lista: se recalcula del árbol, así que un
   script nuevo entra solo"* — y después filtra por nombre.

Y el meta-test, uno solo para todas: **ninguna derivación puede devolver `0` sin declarar
población**. Hoy `dead_content_census.py` lo hace y el gate no lo ve.

---

## Detectar vs decidir: dónde va la frontera

**La frontera no pasa entre casos ni entre tipos de artefacto: pasa por la clausura del
corpus.** Ése es el criterio, y es verificable por el propio instrumento.

### Los seis casos, cortados

| caso | ¿corpus cerrado? | veredicto derivable | qué faltó de verdad |
|---|---|---|---|
| `expires_at` no leído | cerrado (lectores en el repo) | sí | aterrizaje: hoy `edit-coop.sh:153` lo honra, pero tardó 96 días |
| `status: "active"` de cardinalidad 1 | cerrado | sí | **aterrizaje, y está probado**: `edit-coop.sh:155` y `:436` documentan dos veces que el campo no se consulta, y el campo sigue |
| `CONFIG_FILE` asignado y nunca leído | cerrado (el propio archivo) | sí, **y ya estaba detectado** | ruta del hallazgo: el corpus del gate no llegaba |
| `rate-limit-protection` → archivo borrado | cerrado (referencia colgante) | sí | aterrizaje |
| 52 claves sin lector | **abierto** | no: sólo candidato | **decisión** — nadie sabe si hay consumidor afuera |
| `opencode_projection` leída y nunca escrita | cerrado para el hecho, abierto para la consecuencia | el hecho sí; "¿opencode está vivo?" no | **decisión de roadmap** |

**Cuatro detectables con veredicto, dos que necesitan a una persona.** Pero el corte
importante no es 4–2: es que **de los cuatro detectables, tres ya habían sido detectados**
—dos escritos en comentarios de `edit-coop.sh`, uno por shellcheck— y sobrevivieron igual.
Hay una tercera categoría que el encargo no tiene y que la evidencia impone:

> **Detectado, escrito, y sin aterrizaje.** El veredicto existió, quedó en prosa
> (comentario de código, informe, bloque verificado de una regla) y el siguiente que pasa
> tiene que re-derivarlo. `rules/rate-limiting.md` es el mismo patrón un nivel más arriba:
> el bloque "estado real, verificado 2026-08-15" derivó que el limitador no está
> registrado, lo escribió, y la conclusión vive en un párrafo de markdown.

Con eso, la frontera queda en tres tramos, no dos:

1. **Detectar** — corpus cerrado, join limpio → veredicto y exit 1. No hace falta marca.
2. **Decidir** — corpus abierto → candidato + **una fila de decisión por población**.
3. **Aterrizar** — todo veredicto, cerrado o abierto, necesita destino escrito **legible
   por máquina**, o se re-deriva. Éste es el tramo que hoy no existe.

### El aterrizaje, en dos niveles

**Nivel 1 — la marca va en el valor.** Coincido con la propuesta que me llegó:
`status: "DEAD:2026-08-20:ADR-064"` y no un `deprecated: true` hermano; un campo hermano
no impide que el original siga contestando que sí, y sería la séptima instancia de la
forma que estamos arreglando.

**Le agrego la contrapartida que la propuesta no nombra, y una regla de ruteo:** romper al
lector viejo es deseable en una superficie que **reporta** y es un incidente en una que
**gobierna**. Un `status` que sólo alimenta un dashboard puede romperse ruidosamente hoy;
uno que decide si un lock bloquea a otra sesión rompe una sesión de trabajo. La regla:

> La marca en el valor se aplica sin más trámite si la superficie cae en `solo-reporta`.
> Si cae en `gobierna`, **primero se arregla el lector, después se marca.**

Y esa clasificación no es criterio humano: `state_lifecycle_census.py` ya la computa
(`gobierna-sin-reset` / `gobierna-con-ciclo` / `solo-reporta` / `nadie-lo-lee`, vía
`GOVERN_PAT`). El ruteo del aterrizaje lo dicta un instrumento que existe.

**Nivel 2 — `manifests/dead-content.yaml`, una fila por población.** Seis filas de arranque,
no miles de marcas. Lo decisivo del diseño es la **clave de la fila**:

```yaml
# clave = (instrumento, cubeta). NO (instrumento, caso).
- id: config-knobs-sin-lector-en-este-repo
  derivation: scripts/config_knob_census.py --form 4
  bucket: sin_lector_en_este_repo
  corpus_closure: open
  decision: candidato            # candidato | muerto-aceptado | vivo-fuera-del-repo
  decided_by: <operador>
  decided_on: 2026-08-20
  members_at_decision: 52        # foto, no fuente de verdad
  reason: >
    El consumidor puede vivir en un proyecto instalado. Se decide por lote
    cuando exista el censo del lado consumidor.
```

Tres propiedades que lo hacen no-degenerar en el manifiesto a mano que el encargo prohíbe:

- **Crece con las decisiones, no con los casos.** 52 claves = 1 fila. Si mañana son 60, la
  fila no se toca; el instrumento recalcula la membresía.
- **`members_at_decision` es una foto con fecha, no una lista.** Cuando el número se mueve,
  el gate avisa que la decisión se tomó sobre otra población — que es el mismo servicio que
  `Census.compare_with` presta con las ventanas.
- **Se le aplican los tres tests anti-colchón que ya existen** en
  `test_shipped_audits_declare_population.py`: una fila para una cubeta vacía es un asiento
  libre donde aterriza una regresión; una fila para una cubeta que ya no existe es un
  fantasma; agrandar el archivo para apagar un rojo es la trampa.

**Un solo ledger, no uno por dominio.** La evidencia de que la fragmentación es el modo de
falla por defecto está medida: `hooks/_lib/registration-allowlist.txt` (179 líneas) y
`tests/contracts/EXCLUDED_HOOKS.txt` (125) comparten **105 basenames**, y
`manifests/hook-registration-classification.yaml` (643 líneas) es un tercer registro de lo
mismo. Tres motivos escritos por separado para el mismo hecho, tres lugares para
desactualizarse. `listas-fijas-vs-censo-2026-08-19.md` ya midió que el allowlist **no aporta
nada al gate** y sobrevive sólo porque cinco tests lo leen.

---

## Costo de mantenimiento, con la evidencia que encontré

```bash
git log --since=2026-05-01 --oneline -- 'manifests/' | wc -l                       # 545
git log --since=2026-05-01 --oneline -- 'scripts/*audit*.py' 'scripts/*census*.py' \
        'scripts/*_check*.py' 'scripts/check_*.py' | wc -l                          # 204
ls manifests/*.yaml | wc -l                                                        # 132
ls scripts/*audit*.py scripts/*census*.py | wc -l                                  #  87
git log --since=2026-05-01 --numstat --pretty=tformat: -- 'manifests/' \
  | awk '{a+=$1;d+=$2} END{print "+"a" -"d}'                                        # +165870 -66205
git log --since=2026-05-01 --numstat --pretty=tformat: -- 'scripts/*audit*.py' \
        'scripts/*census*.py' 'scripts/check_*.py' | awk '{a+=$1;d+=$2} END{print "+"a" -"d}'
                                                                                    # +27444 -1629
```

| | declarar (manifests) | derivar (instrumentos) |
|---|---|---|
| artefactos | 132 | 87 |
| commits desde 2026-05-01 | 545 | 204 |
| **commits por artefacto** | **4,13** | **2,34** |
| líneas +/− | +165.870 / −66.205 | +27.444 / −1.629 |
| proporción de commits `fix` | 132/311 ≈ 42% | 65/129 ≈ 50% |

Y el caso extremo del lado declarativo: `manifests/primitive-lifecycle.yaml` acumula **163
commits** y **25.692 líneas**, con **671 `sunset_criteria` en prosa y cero campos con fecha**.
Es el manifiesto que el encargo cita como la maquinaria que ya existe para declarar la muerte
de artefactos, y tiene adentro la misma forma que estamos censando: un campo declarado que
se valida por presencia y que ningún código puede comparar contra el reloj.

**La lectura honesta, que no es la que favorece a la tesis:**

1. **Por artefacto, derivar sale 1,8× más barato en commits y 6× más barato en líneas
   agregadas.** El manifiesto carga el **contenido** (N filas que envejecen una por una);
   el instrumento carga el **criterio** (una regla). Eso escala a favor de derivar.
2. **Pero la mitad de los commits de instrumentos son `fix`**, y hoy tuve tres ejemplos del
   mismo día en el log: `8a2d75c93 perf(audit): que instrument-productivity deje de recorrer
   68 veces el mismo árbol`, `aa570d644 fix(retention): que el audit sume el árbol y lo
   compare contra el techo global`, `7a5efb0ea fix(gate): corregir mi propia medición de esta
   mañana y dejar de copiar la ventana ciega`. Una derivación se rompe cuando el repo cambia
   de forma, y este repo cambia de forma todos los días.
3. **El costo que no está en el `git log` es el que importa**: cuatro instrumentos
   (`hook_projection_drift_audit.py` 23 KB, `hook_surface_classifier.py` 20 KB,
   `hook_surface_census.py` 10 KB, `audit_hook_registration.py` 6 KB) contestan **la misma
   pregunta** —¿este hook está registrado?— y dos de ellos se contradicen, lo que obligó a
   escribir el tercero para desempatar. 60 KB para una pregunta con respuesta binaria. Ése
   es el gasto real de derivar sin registro: no mantener N instrumentos, sino **no saber que
   el instrumento N+1 ya existía**.
4. **Y el costo de creer**: 54 de 67 scripts que shippean quedan fuera del gate que los
   haría honestos. Un instrumento cuyo veredicto no se puede creer cuesta lo mismo de
   mantener y vale cero.

**Veredicto de costo, con su contrapartida nombrada:** la tesis "derivar es más barato que
declarar" **se sostiene por artefacto y se cae por sistema**. Lo barato es la membresía; lo
caro es la decisión y la confianza. Por eso el diseño no elige: **deriva la membresía y
declara la decisión**, con la restricción de que la declaración sea O(decisiones) y no
O(casos). Lo que sí queda refutado sin matices es la forma fuerte del encargo —*"ninguno
necesitaba una marca humana"*—: dos de los seis la necesitan, y de los otros cuatro, tres ya
habían sido derivados y murieron en un comentario por no tener dónde escribirse.

---

## Lo que NO diseñé y por qué

- **La escalera de seguridad —de veredicto a acción borrada—.** Es de otro arquitecto por
  encargo explícito. Mi diseño se detiene en el veredicto escrito y su fila de decisión; qué
  autoriza a borrar y con qué reversibilidad, no es mío. **Punto de acople:** la cubeta
  `gobierna` / `solo-reporta` de `state_lifecycle_census.py` y el campo `corpus_closure`
  son los dos insumos que esa escalera necesita, y los dos ya son computables.
- **La migración de los 54 scripts `SCOPE: both` que el gate no ve.** Es implementación, y
  además cambia qué shippea el instalador: se reporta, no se aplica. Mismo criterio que usó
  `listas-fijas-vs-censo-2026-08-19.md` con sus cuatro listas.
- **El esquema campo por campo de `manifests/dead-content.yaml`.** Diseñé la clave de la fila
  (`(instrumento, cubeta)`) y las tres propiedades anti-degeneración, que es lo que decide si
  el archivo escala o se convierte en el manifiesto a mano que hay que evitar. El resto del
  esquema es una decisión de detalle que gana quien lo implemente.
- **Qué hacer con las 52 claves.** Es la decisión del operador y el ejemplo canónico del
  corpus abierto. Un arquitecto que la resuelva por su cuenta demuestra el punto contrario
  al de su propio diseño.
- **No toqué `dead_content_census.py` ni `skip_absence_census.py`** aunque encontré defectos
  concretos en los dos (cero sin población; `SCOPE: both` sin `Census`). Otro agente los está
  escribiendo ahora mismo: cuando los leí los dos estaban sin trackear, y mientras yo redactaba
  este informe el primero se commiteó como `1fa75ac69` —sigue sin línea `# SCOPE:` y sigue con
  `grep -c "Census(" scripts/dead_content_census.py` → 0—. Los reporto para que su autor los cierre.
- **No corrí la suite** (la máquina está cargada, y el encargo lo prohíbe). Corrí dos
  instrumentos read-only, `config_knob_census.py --form 4` y `dead_content_census.py --form A`.

---

## Prototipo

Ninguno. Todo lo que este diseño propone probar ya era observable con `git`, `grep`,
`shellcheck` y los instrumentos que el repo tiene. Escribir un prototipo habría sido el
octavo instrumento sobre la misma pregunta, que es el defecto que este informe mide.
