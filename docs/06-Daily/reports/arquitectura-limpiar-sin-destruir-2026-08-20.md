# Arquitectura: limpiar sin destruir

Fecha: 2026-08-20 · Alcance: qué se hace con un veredicto de "esto está muerto"
sin comerse trabajo ajeno. **No** cubre cómo se produce ese veredicto (otro
diseño).

## Resumen ejecutivo

La escalera tiene cinco peldaños de disposición — **R0 observar · R1 lapidar ·
R2 cuarentena · R3 archivar · R4 borrar** — y una regla que la sostiene: **una
corrida mueve un artefacto un solo peldaño**. El default de acción es **R2**,
que es un `mv` dentro del mismo filesystem: cuesta **cero bytes** y se deshace
con otro `mv`. Cruzada con la disposición va un eje de **evidencia** (E0 sin
dueño legible / E1 negativa / E2 positiva) que fija un techo: E0 no pasa de R1,
E1 no pasa de R2, sólo E2 llega a R4. El bug de `kill -0` es exactamente E1
leída como E2. El tope de radio es `max(20, 5%)` por superficie y por corrida, y
al tocarlo **la corrida para**, no avisa y sigue. Todo movimiento escribe una
línea por artefacto —antes de mutar— en un journal append-only con actor,
criterio *con sus valores evaluados* y el comando de recuperación. El día que el
criterio esté mal, el daño máximo del día es un rename, y una **canaria** por
corrida detecta el criterio roto en la máquina donde está roto, antes de tocar
nada.

## Correcciones a las premisas del encargo

1. **"25,7 MiB sobre un techo de 400"** → medido: **22,8 MiB sobre** (422,8 /
   400). Comando: `python3 scripts/state_retention_audit.py --json`. Dirección y
   estado BLOCK confirmados; el número drifteó. Y hay dos hallazgos más que el
   encargo no menciona y que cambian la lectura del presupuesto: **227,2 MiB no
   pertenecen a ninguna superficie registrada** (WARN contra un ratchet de 210),
   contra **195,6 MiB registrados**. O sea: **más de la mitad del árbol está
   fuera del alcance de cualquier reaper**. La presión de disco no se resuelve
   barriendo mejor lo declarado.

2. **"tiene modos — al menos `observe` y `repair-safe`"** → son tres:
   `observe`, `repair-safe`, `repair-before-block`
   (`manifests/state-retention.yaml:39-42`). Pero **no son una escalera de
   acción**: son un eje de **autoridad** — *¿puede el camino automático tocar
   esta superficie?* — sobre una única acción terminal. Entre "reportar" y "la
   acción del reaper" no hay ningún peldaño intermedio. La escalera que el
   encargo esperaba encontrar ahí no existe.

3. **"cubre 14 superficies"** → **15** más una fila de presupuesto
   (`summary.surface_count: 15`, 16 filas en `surfaces[]`). Menor.

4. **"a `runtime/` casi no llega"** → llega, pero **la declaración está mal**, que
   es peor que no llegar. La superficie `edit-locks` declara un solo reaper
   (`edit-coop.sh reap-stale` desde `so-reaper.sh`). **Hay dos borradores**, y el
   no declarado es el que corre siempre:
   - `hooks/edit-lock-session-end.sh` → `edit-coop.sh release-mine` →
     `rm -rf "$d"` (`scripts/edit-coop.sh:405`). **Registrado** como hook Stop:
     `python3 -c '...' edit-lock-session-end.sh` → `1`.
   - `scripts/so-reaper.sh`, el que la manifest sí declara, **no está
     registrado**: mismo comando → `0`.

   La manifest describe el camino que no corre y omite el que corre en cada
   cierre de sesión.

5. **"1.250 locks desaparecieron y nadie sabe quién"** → encontré el mecanismo, y
   no es inatribuible por accidente. `cos_session_id()` cae al literal
   **`default-session`** cuando no hay `COGNITIVE_OS_SESSION_ID` ni
   `CLAUDE_SESSION_ID` (`scripts/edit-coop.sh:45`). `release-mine` borra todo lock
   cuyo `session_id` sea igual al propio. **Dos sesiones sin esa variable se
   llaman las dos `default-session`**, y el Stop de cualquiera borra los locks de
   la otra — como auto-liberación correcta e intencional. Ningún código está
   roto en aislamiento: la identidad simplemente **no discrimina**. No es una
   hipótesis sobre el pasado (no hay journal, los 1.250 no se pueden atribuir
   retroactivamente — ése *es* el hallazgo): es un mecanismo vivo, legible hoy en
   el fuente.

6. **Premisa que no pude confirmar y que cambia el diseño**: la superficie que se
   barre **no tiene dueño legible**. Los **45** directorios de lock vivos tienen
   **cero** `meta.yaml`:
   `cd .cognitive-os/runtime/edit-locks && ls */meta.yaml 2>/dev/null | wc -l` →
   `0`. Consecuencia doble: `release-mine` los saltea a todos (hace `continue` si
   no hay meta) y `reap-stale` sólo puede alcanzarlos por `no-meta-past-grace`
   sobre el mtime del directorio — y hoy reapea 0 porque el más viejo tiene 56
   min contra una gracia de 3600 s:
   `bash scripts/edit-coop.sh reap-stale --dry-run --json` →
   `{"kept":45,"reaped":0,"scanned":45,"grace_seconds":3600}`. **Cualquier peldaño
   redactado como "chequeá el dueño" no tiene qué leer.** De ahí sale el nivel E0
   y su techo en R1.

7. **Observación de alcance, no pedida**: esos 45 locks son sobre archivos bajo
   `/private/tmp/.../scratchpad/`, es decir **fuera del repo**. La superficie se
   declara como `.cognitive-os/runtime/edit-locks/*` y se acota por conteo, pero
   lo que bloquea no está en el checkout.

## Lo que ya existe: sirve como modelo o no

**`manifests/state-retention.yaml` + `state_retention_audit.py` (ADR-199) —
sirve como registro, no como escalera.** Lo que aporta y hay que conservar
entero: la obligación de declarar antes de existir, el `tombstone` como campo de
primera clase (`archive-ref-and-patch`, `compact-in-place`), la medición del
árbol **medido** en vez de la suma de caps declarados, y el ratchet de bytes no
registrados puesto en la realidad y no en un colchón. Eso último es la única
defensa que hoy dice la verdad incómoda (227,2 MiB sin dueño).

Lo que **no** aporta: un peldaño entre reportar y actuar. `retention_mode`
contesta *quién puede ejecutar*; no contesta *qué le pasa a los bytes*. Y su
promoción `observe → repair-safe` es una decisión de operador escrita en prosa
en el `rationale` de cada superficie, sin criterio verificable. Es insuficiente,
pero **el lugar correcto donde poner la escalera**: no hay que inventar un
registro nuevo.

**`scripts/so-reaper.sh` + `cos_lib/session_lifecycle.py` (ADR-119) — sirve como
modelo general, y es lo mejor que hay.** `KEEP_ACTIVE / KEEP_PENDING_CONTENT /
KEEP_RECENT_GRACE / ARCHIVE / RM_ARCHIVED / ERROR_UNREADABLE` ya es una escalera
de disposición con archive-first, ventana de retención (90 d), marcador
`archived.json` con `archived_at_epoch` y `source`, y —clave— un estado
explícito para *no pude inspeccionar con seguridad* que resuelve dejando quieto.
Esa última decisión es la que hay que generalizar: **la duda no es un permiso**.

Lo que le falta para ser el modelo general: (a) no hay peldaño **cuarentena**
entre KEEP y ARCHIVE, y archive ya copia bytes; (b) no hay tope de radio por
corrida; (c) no hay journal por artefacto — la alarma de volumen es un conteo;
(d) es específico de `sessions/`: el modelo de decisión vive en un módulo que
sabe leer `user-requests.jsonl`, `tasks.json`, `parked-edits/`. La forma se
generaliza, la inspección de contenido pendiente no.

**`hooks/_lib/stash-lock.sh` + ADR-117 — sirve, y hay que reusarlo tal cual para
R3 sobre objetos git.** El par ref preservada + patch/name-status es exactamente
un peldaño "archivar" para algo que no es un archivo. No lo reinvento.

**Lo que existe y es el contraejemplo**: `cmd_reap_stale` en
`scripts/edit-coop.sh`. El criterio es cuidadoso —`pid_alive` trata
`PermissionError` como vivo, "nunca reapear ante la duda", gracia de una hora
sobre `expires_at`— y aun así la corrida es **irrecuperable e inatribuible por
construcción**: `shutil.rmtree` directo sin cuarentena, `reaped_samples` cortado
en **5**, salida a stdout, y stdout truncado otra vez por `| head -5` en
`scripts/so-reaper.sh:316`. Un barrido de 1.250 deja como máximo 5 nombres, en
un stream. `release-mine` es peor: imprime sólo un conteo, nunca un nombre.
**El criterio está bien pensado y la corrida es igual de indefendible.** De ahí
la tesis del diseño: el problema no es el criterio, es que no hay peldaños ni
registro.

## La escalera, peldaño por peldaño, y qué evidencia sube cada uno

Dos ejes. La **disposición** (qué le pasa al artefacto) y la **evidencia** (qué
se probó). La evidencia fija un techo; la disposición avanza de a un peldaño.

### Eje de evidencia

| Nivel | Qué es | Ejemplo real | Techo |
|---|---|---|---|
| **E0** `SIN_DUEÑO` | El artefacto no expone ningún campo de propiedad legible. | Los 45 locks sin `meta.yaml`. | **R1** |
| **E1** `NEGATIVA` | "No lo encontré vivo". Ausencia de señal. | `kill -0` fallando; PID no listado. | **R2** |
| **E2** `POSITIVA` | Registro afirmativo de terminación, verificable. | La sesión escribió su marcador terminal; el registro de procesos dice `exited`; la ref archivada se lee. | **R4** |

El bug de `kill -0` es E1 leída como E2 — y `PermissionError` ni siquiera era
E1, era *evidencia de vida*. Nombrar el nivel en la manifest es lo que corta esa
clase; "validamos el criterio" no la corta porque el criterio se veía razonable.

**La identidad también es evidencia.** Antes de aplicar cualquier regla que
compare propiedad, la corrida prueba que su propio identificador **discrimina**:
si `me` cae en un valor degenerado conocido (`default-session`,
`unknown-agent`, cadena vacía), **toda la corrida se degrada a R1**. Es el fix
puntual de `release-mine`, expresado como regla general en vez de como parche.

### Eje de disposición

| Peldaño | Acción | Evidencia que lo habilita | Reversión |
|---|---|---|---|
| **R0** `OBSERVAR` | Contar y reportar. | Ninguna. Default de toda superficie sin fuente de evidencia declarada. | n/a |
| **R1** `LAPIDAR` | El artefacto queda donde está; se escribe una línea nombrándolo candidato. | La regla matcheó. Nada más. | n/a (no se tocó) |
| **R2** `CUARENTENA` | `mv` a `.cognitive-os/quarantine/<sweep-id>/`. Intacto, ruta cambiada para que los consumidores dejen de encontrarlo. | E1 o mejor **+** sin contenido pendiente **+** pasada la gracia **+** lapidado en una corrida anterior. | `mv` de vuelta |
| **R3** `ARCHIVAR` | Empaquetar comprimido el bucket de cuarentena (o ref+patch para objetos git, ADR-117). | R2 **+** sobrevivió la ventana de cuarentena sin que nadie lo reclamara. | desempaquetar |
| **R4** `BORRAR` | `unlink`. | **E2 exclusivamente** **+** retención de archivo vencida **+** la línea de journal del `sweep_id` sigue legible. | ninguna — sólo queda el journal |

**Regla dura: una corrida mueve un artefacto un solo peldaño.** No hay atajo de
R0 a R4 ni de "está muerto" a `rm`. Esa sola restricción es lo que hace
sobrevivible un criterio equivocado: el peor daño que puede hacer un veredicto
malo en una corrida es un rename.

**Default de acción: R2.** No R1 —porque R1 solo es el barredor que nunca corre,
y volvemos a 1.321 locks— y no R3 —porque R3 cuesta bytes y el presupuesto ya
está en BLOCK.

**Techo por defecto de una superficie recién declarada: R1**, hasta que complete
un ciclo de retención entero mostrando en el journal qué *habría* movido. Es la
promoción `observe → repair-safe` de ADR-199, pero con criterio verificable en
vez de prosa: se sube de peldaño cuando existe la evidencia, no cuando alguien
lo escribe en el `rationale`.

## Reversibilidad y su costo en disco

Estado medido hoy (`python3 scripts/state_retention_audit.py --json`): árbol
**422,8 MiB** contra techo **400** — `global-budget-exceeded` nivel **BLOCK**,
disparando. Registrados 195,6; no registrados 227,2 contra ratchet 210 — WARN,
también disparando. **Un diseño que agregue bytes está muerto antes de empezar.**

| Peldaño | Costo en disco | Ventana |
|---|---|---|
| R1 lapidar | ~200 B por artefacto de journal. 1.250 artefactos ≈ **250 KB**. | permanente (el journal vive más que el payload) |
| R2 cuarentena | **cero bytes netos**. `mv` dentro del mismo filesystem es un rename: el payload no se copia. | **24 h** |
| R3 archivar | **negativo**. Comprime algo que ya estaba en disco sin comprimir; JSON/YAML/logs bajan ~8-12x. | 14 d (locks, bus) / 90 d (sesiones, ya es el número de ADR-119) |
| R4 borrar | negativo. | — |

Que R2 sea gratis es la afirmación que carga el diseño, y es la razón por la que
la cuarentena puede ser el default con el presupuesto excedido: mueve bytes de
"superficie registrada" a "superficie de cuarentena", no los suma al árbol.
**Condición**: mismo dispositivo. Si una superficie no puede renombrarse dentro
del filesystem, prefiero prohibir la superficie a convertir la cuarentena en una
copia.

La cuarentena **se declara en `state-retention.yaml` desde el día uno**, con cap
propio, o se convierte en el MiB 228 sin dueño. Y su cap **se resta del cap de la
superficie de origen**, no se suma al árbol.

Ventana de 24 h porque es la escala temporal observada del error: las tres
ediciones perdidas del 19 de agosto se notaron el mismo día, y la cuarta se
salvó por 35 segundos. Una ventana de 24 h las habría cubierto a las cuatro.

**Válvula bajo presión de presupuesto: se acorta la ventana de archivo, nunca se
saltea la cuarentena.** Archivo es donde están los bytes; cuarentena es gratis.
Saltear cuarentena para ahorrar disco es exactamente el verde barato de esta
familia.

## Radio por corrida

Dos topes, con respuestas distintas.

**Tope absoluto, por superficie y por corrida: `max(20, 5% de la población)`.**
Al alcanzarlo la corrida **para**, escribe un registro `radius-exceeded` con lo
que iba a tocar, y no sigue. No "avisa y sigue".

El motivo es la asimetría: parar cuesta disco y un reporte; seguir pasado el
tope es exactamente la corrida que se comió 1.250 cosas. Y una corrida que
quiere tocar 1.250 artefactos o encontró un backlog real —y entonces un operador
tiene que verlo antes de que se mueva— o tiene el criterio roto —y entonces
seguir *es* el daño. Los dos casos se atienden igual: parar y mostrar.

**Tope de tasa: una superficie no puede perder más de X% de su población en 24 h
rodantes, sumando todas las corridas.** Sin esto, el tope por corrida lo derrota
la concurrencia: 60 sesiones borrando 20 cada una hacen 1.200 sin violar nada.
El contador vive en el journal, que ya es la fuente compartida entre sesiones.

**Y para que el barredor conservador igual corra**: la primera corrida después
de declarar una superficie tiene un permiso único `--initial-backlog`, **sólo a
R1**. Lapida toda la población, no mueve un byte, y le deja al operador la lista
completa. Drena el backlog al journal sin tocar nada, que es la única forma
honesta de empezar con 1.321 locks acumulados.

## Atribución: quién, qué, cuándo, con qué criterio

Un journal append-only, `.cognitive-os/logs/state-reap.jsonl`, **una línea por
artefacto** —no por corrida— escrita **antes** de mutar y con fsync.

```json
{"ts":"2026-08-20T14:02:11Z","sweep_id":"7f3a…","surface":"edit-locks",
 "artifact":".cognitive-os/runtime/edit-locks/src--foo--bar.py",
 "from_rung":"R1","to_rung":"R2",
 "actor":{"pid":48213,"ppid":48200,"uid":501,"session_id":"default-session",
          "session_id_degenerate":true,"harness":"claude-code",
          "git_head":"f14dfb689","argv":"edit-coop.sh reap-stale"},
 "criterion":{"rule":"no-expires-owner-dead-past-grace","evidence_tier":"E1",
              "pid":48000,"probe":"os.kill(pid,0)","probe_result":"ESRCH",
              "hb_age_s":4210,"grace_s":3600},
 "recovery":"mv .cognitive-os/quarantine/7f3a…/src--foo--bar.py .cognitive-os/runtime/edit-locks/"}
```

Tres cosas que el código de hoy rompe estructuralmente, y que esto arregla:

1. `reaped_samples` corta en **5** (`scripts/edit-coop.sh`): de 1.250 nombres,
   1.245 son irrecuperables por construcción.
2. La salida va a stdout y pasa por `| head -5` en `scripts/so-reaper.sh:316`:
   truncada por segunda vez.
3. `release-mine` imprime `released N own lock(s)` — **ningún nombre, nunca**.

**Escribir antes de mutar no es un detalle**: un journal escrito después del
borrado pierde justo los registros de la corrida que murió a la mitad, que es la
corrida que más falta hacen.

**El campo auditado es `criterion`, no el conteo.** Cuando algo sale mal la
pregunta nunca es "cuántos" sino "bajo qué regla y con qué valores", y la regla
tiene que traer sus entradas evaluadas o es infalsificable una semana después.
Un journal que dice "reapeados: 1250" no sirve para nada; uno que dice "PID
48000, `os.kill` devolvió ESRCH, evidencia E1" es lo que permite ver, después
del incidente, que E1 nunca debió alcanzar para borrar.

**Cambio en la manifest**: `deleters:` pasa a ser campo requerido, en plural,
listando **todo** camino de código que remueve miembros de la superficie — no el
"reaper" nominal. Y un test que grepea `rm -rf` / `rmtree` contra el `path` de
cada superficie y cruza contra `deleters:` convierte en gate lo que hoy es
prosa. Ese test, hoy, falla sobre `edit-locks`: dos borradores, uno declarado, y
el declarado es el que no está registrado.

## El día que el criterio esté mal

Asumo que va a estar mal. Hoy lo estuvo dos veces (`kill -0` sin distinguir
EPERM de ESRCH; la lane de chaos restaurando bytes previos sin poder distinguir
trabajo de mutación de test). El diseño no apuesta a que la tercera no pase.

1. **Un peldaño por corrida acota el daño del día a un rename.** La recuperación
   no lee, parsea ni transforma contenido: es el `mv` inverso que ya está escrito
   en el campo `recovery` de la línea. Recuperar no requiere entender qué se
   rompió.

2. **La recuperación es un comando, no una arqueología**:
   `cos state recover --sweep <id>` replaya el journal en reversa para una
   corrida entera. Un incidente se deshace citando un id, no reconstruyendo lo
   que pasó.

3. **La canaria** — la pieza que sí amerita prototipo, y la única. Antes de tocar
   nada, cada corrida planta un artefacto que **sabe** que debe conservarse (un
   lock con un PID que acaba de forkear y está vivo; un directorio de sesión con
   contenido pendiente sintético) y corre el criterio contra él. Si el criterio
   dice REAPEAR la canaria, **el criterio está mal ahora, en esta máquina**, y la
   corrida se degrada a R1 y reporta. Esto atrapa la clase `kill -0` en runtime,
   sin saber de antemano qué está mal: un criterio que clasifica como muerto algo
   que se sabe vivo no es un criterio que se valida después, es uno que se
   **rehúsa a ejecutar hoy**. La canaria de propiedad ajena (un PID de otro uid)
   habría matado el bug de `kill -0` la primera vez que corrió.

4. **Pasada la ventana, el journal sobrevive al payload.** Cuarentena cubre 24 h
   y archivo 14-90 d; después la respuesta honesta es "se fue". Ahí el trabajo
   del diseño es otro: que quede la línea diciendo *qué* se fue, *cuándo*, *bajo
   qué regla* y *con qué valores*. Ésa es la diferencia entre el 19 de agosto
   —tres ediciones perdidas, causa inferida— y una pérdida diagnosticable. Los
   journals llevan retención mucho más larga que los payloads porque pesan 200
   bytes: 1.250 artefactos son 250 KB contra un techo de 400 MiB.

5. **La clase que la escalera NO atrapa**, dicha de frente: un criterio
   equivocado en la dirección de *conservar* — algo que debería reapearse y no se
   reapea. Ese error cuesta disco y ruido, y lo acepto explícitamente, por la
   asimetría. El precio de aceptarlo es que la presión de disco se resuelve
   registrando superficies (los 227,2 MiB sin dueño) y no aflojando peldaños.

## Lo que NO diseñé y por qué

- **El veredicto de muerte.** Consumo un veredicto más su nivel de evidencia
  (E0/E1/E2); no lo produzco. Es de otro arquitecto. La única exigencia que le
  pongo desde acá: que **declare el nivel**, porque el techo de la escalera sale
  de ahí y no del veredicto.
- **Archivado de objetos git.** ADR-117 ya tiene el peldaño R3 correcto para
  stashes (ref preservada + patch + name-status). Se reusa tal cual;
  reimplementarlo sería reinvención.
- **Coordinación entre máquinas o entre checkouts.** Todo acá asume un
  filesystem. La cuarentena-como-rename se rompe cruzando dispositivos, y
  prefiero prohibir la superficie a convertirla en copia sin decirlo.
- **Interfaz.** `cos state recover --sweep <id>` es toda la superficie de
  operador que hace falta. Cualquier cosa más es adorno.
- **Reapear los 227,2 MiB no registrados.** Barrer bytes no declarados es, por
  definición, barrer bytes sobre los que nadie escribió una política. Primero se
  registran (`artifacts/aci` 54,7 MiB, `tasks/control-plane-remediation.jsonl`
  50,2 MiB, `external-source-cache/gentle-ai` 14,5 MiB son el 53% del exceso),
  después se les aplica la escalera.
- **Arreglar `cos_session_id`.** La colisión en `default-session` es un bug real
  y está en el fuente de otra gente hoy. Lo reporto; no lo toco (atribución).
  El diseño lo neutraliza sin depender del fix: identidad degenerada → corrida
  degradada a R1.
- **No implementé nada.** Ni la canaria, que es lo único con riesgo de
  viabilidad. Es un diseño; la canaria es el primer experimento que haría.
