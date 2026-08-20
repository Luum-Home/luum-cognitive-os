# Estado que gobierna sin ciclo de vida — edit-locks y las otras tres

Fecha: 2026-08-20 · Repo: `luum-agent-os` · Alcance: `.cognitive-os/runtime/`

## Resumen ejecutivo

De las cuatro "bombas" del censo forense, **una era real y peor de lo descripto,
una es real pero lenta, una no existe y una es un bug distinto del que se le
atribuía**.

`edit-locks/` no necesitaba que yo eligiera un criterio de muerte: **el criterio
ya estaba escrito en cada lock y nadie lo leía**. Cada `meta.yaml` trae
`expires_at` —TTL de 30 minutos, estampado al adquirir y refrescado por
`edit-coop.sh heartbeat`— y ningún lector en el árbol lo comparaba con el reloj.
Medido: **1296 locks vencidos por su propio `expires_at`, 20 vigentes, 0 sin el
campo, el más viejo vencido hace 96 días**, y todos seguían produciendo
`EDIT-LOCK CONFLICT`. El arreglo de raíz es que el predicado de vigencia
(`_lock_is_stale`) honre el campo; la poda pasa a ser higiene y no urgencia.

Quedan **dos** pendientes declarados: `control-plane-audit/findings-state.json`
(2,4 MiB, 3928 hallazgos conocidos, sin podador) y `validation-activity.jsonl`
(187 filas, sin rotación). Ninguna se toca en este commit.

## Correcciones a las premisas del encargo

1. **"Elegí entre PID, heartbeat o antigüedad y decí qué sacrifica cada uno"** —
   la disyuntiva no hacía falta: el lock **declara** su muerte en `expires_at`.
   (Corrección que llegó del propio orquestador a mitad de trabajo, verificada
   acá: `grep -c expires_at hooks/edit-lock-pre-tool.sh` → `0`.)
2. **"`ls | wc -l` da 1283 locks"** — el número se mueve mientras se lo mide: 1284
   al empezar, 1290 durante la prueba, **1321** en la corrida del audit. La
   familia sigue creciendo ahora mismo; cualquier cifra puntual es una foto.
3. **"781 con más de siete días"** — correcto pero es la métrica equivocada. Por
   `mtime` son 781; por su **propio TTL declarado** los muertos son **1296**. La
   antigüedad de archivo subestima el problema en ~500 locks.
4. **"Los locks son archivos"** — son **directorios** (`mkdir` atómico, ADR-098),
   con `meta.yaml` adentro. `find -type f` cuenta metas, no locks.
5. **Bomba (4), `rate-limits.jsonl`: no es bomba, y ninguna de las dos versiones
   previas acertó el motivo.** El censo dijo que la rotación "no existe"; el
   orquestador corrigió que sí existe y podía estar cubierta. Verificado: el hook
   existe pero **`METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"`**, o sea que
   **nunca toca `runtime/`**. Y da igual: `cos_lib/rate_limit_tracker._append_jsonl`
   escribe con `os.replace(tmp, path)`, que **reemplaza el archivo entero por un
   único registro** (medido: 1 línea, 187 bytes). No puede crecer. Lo que hay ahí
   no es un problema de retención sino de pérdida de historia — la función se
   llama `_append_jsonl` y no appendea.
6. **"`manifests/state-retention.yaml` cubre una sola familia y en modo `observe`"**
   — cierto para `runtime/` (la única era `runtime-locks`, `*.lock*`, que **no**
   matchea `runtime/edit-locks/`), pero el manifiesto en total ya declaraba 14
   superficies, tres de ellas fuera de `observe`. La forma correcta de decirlo:
   el contrato existe y a `runtime/` casi no llega.
7. **`kill -0` no distingue "no existe" de "no es tuyo".** Encontrado probando:
   `_pid_alive 1` daba **falso** (EPERM), así que un lock vivo de otro usuario se
   leía como muerto y se limpiaba. Es el falso positivo que más caro sale, y
   estaba en producción, no en mi diseño.
8. **El presupuesto global ya estaba en rojo antes de mi cambio**: el árbol mide
   25,7 MiB por encima del techo de 400 MiB. Registrar `edit-locks` no crea ese
   BLOCK —el audit suma el árbol medido, no las superficies declaradas—, sólo lo
   vuelve **atribuible** en vez de anónimo.

## Cuándo un lock está muerto: el criterio y qué sacrifica

**Criterio: el que el lock declaró.** `now > expires_at`. Nada de heurísticas
sobre antigüedad de archivo.

Por qué gana a las tres opciones que el encargo proponía:

- **No es una hipótesis sobre el lock, es su propia declaración.** Lo escribió
  quien lo tomó, con la semántica correcta (`_iso8601_plus "$LOCK_TTL_SECONDS"`).
- **El falso positivo que más preocupaba —matar la sesión larga— tiene antídoto
  provisto por el mismo primitivo**: `edit-coop.sh heartbeat <file>` refresca
  `heartbeat` y `expires_at`. Una sesión legítima de ocho horas mantiene su lock
  vivo llamando al refresco. Si no refrescó en 96 días, no es una sesión larga.
- **Sacrificio real, y es éste**: una sesión viva que **nunca llama a
  `heartbeat`** pierde su lock a los 30 minutos. Es el contrato que ya estaba
  escrito, no uno nuevo — el TTL de 1800 s estaba en el archivo desde el commit
  de nacimiento.

**Lo que el criterio NO mira, a propósito:** `status: "active"`. Se estampa una
vez y no se actualiza nunca, así que **todos** los cadáveres se declaran activos.
Es la misma familia de defecto —campo escrito, nunca mantenido— dentro del mismo
archivo.

**Fallback** (si `expires_at` falta o no parsea; hoy 0 casos, pero es estado
alcanzable con un meta a medio escribir): exigir **las dos** condiciones, PID
dueño muerto **y** heartbeat pasado el grace. Nunca una sola.

## Quién poda y cuándo

Dos piezas, y la primera hace innecesaria la urgencia de la segunda.

1. **La aplicación del criterio va en el predicado de vigencia**, no en un
   podador: `_lock_is_stale` en `scripts/edit-coop.sh` ahora honra `expires_at`.
   Como `cmd_acquire` y `cmd_check` lo consultan, **el hook bloqueador deja de
   dar `EDIT-LOCK CONFLICT` sobre locks vencidos aunque nunca se borre nada del
   disco**. Costo: cero hooks nuevos, cero latencia de arranque.
2. **La poda es higiene y va en el reaper que ya tiene ciclo.**
   `scripts/edit-coop.sh reap-stale [--dry-run] [--json]`, invocado desde
   `scripts/so-reaper.sh`, que ya corre en `SessionEnd` (vía
   `hooks/session-end-reap.sh`) y opcionalmente por cron. **No** se agregó un hook
   de `SessionStart`: pagaría el costo en cada arranque para borrar algo que ya
   no bloquea a nadie.

Lo que **no** es: una pasada de `rm`. No se borró ni un lock del árbol real del
operador; el barrido lo hará el reaper en su próximo ciclo.

Detalle de implementación relevante: el barrido es **un solo proceso python**
para los 1300+ directorios. Un bucle bash con `sed`+`kill` por lock serían miles
de spawns en la ruta de cierre de sesión.

## `state-retention.yaml`: extenderlo o no, con el argumento

**Extenderlo, sí — pero no era la vía barata que el encargo esperaba, y hay que
decir por qué.**

- ADR-199 define el contrato y `edit-locks` ahora está registrado como superficie
  (`kind: lock`, `path: .cognitive-os/runtime/edit-locks/*`, `max_count: 200`,
  `max_total_mib: 8`, `reaper: session-end`, `tombstone: drop-if-expired`).
- **Registrar no poda.** `scripts/state_retention_audit.py` sólo tiene reapers
  para tres superficies (`reap_stashes`, `compact_ledger`, `reap_bus`); para una
  superficie glob de tipo `lock` **no hay implementación de reaper**. Declararla
  `repair-safe` habría prometido una automatización que la herramienta no hace —
  el mismo motivo escrito en `copy-only-checkpoints`. Queda en **`observe`**, y
  la poda la ejecuta `so-reaper.sh`.
- **Qué haría falta para pasarla a `enforce`/`repair-safe`**: escribir
  `reap_edit_locks()` en `state_retention_audit.py` y ramificarlo en
  `reap_surface()`. **Cuánto borraría hoy: 1296 de 1316 locks** (`grep`+python
  sobre `expires_at`, sección "Las tres corridas"), ~5 MiB. Es una decisión del
  operador, no un olvido: el efecto ya está conseguido sin ella.
- **El manifiesto no puede expresar el TTL real.** `duration()` acepta sólo horas
  y días (`P1H`, `P7D`), y el TTL del lock son 30 minutos. Por eso `max_age: P1H`
  documenta el **grace de poda** (`COS_EDIT_LOCK_REAP_GRACE`), y la autoridad
  sobre la muerte queda en `expires_at`. Está escrito en el `rationale` para que
  nadie lo lea al revés.
- **Lo que NO se hizo: subir el presupuesto.** El árbol está 25,7 MiB sobre el
  techo de 400 MiB desde antes de este trabajo. Registrar la superficie mueve
  ~5 MiB de "no registrado" a "atribuible" y baja `unregistered_mib`; el BLOCK
  global sigue en pie y es de otro dueño (`artifacts/aci` 54,7 MiB,
  `tasks/control-plane-remediation.jsonl` 49,2 MiB).

## Las tres corridas

Sembrado en un directorio de usar y tirar
(`scratchpad/lockproof`), nunca en `.cognitive-os/` real.

Censo previo, sobre el árbol real (read-only):

```
$ python3 - <<'PY'   # lee expires_at de cada meta.yaml
expired_by_own_expires_at=1296 still_current=20 missing_or_unparseable=0 oldest_expired_days=96
$ grep -c expires_at hooks/edit-lock-pre-tool.sh
0
$ git log --oneline -S expires_at -- scripts/edit-coop.sh
bca8fb7c6 feat(coordination): file-level edit locks with rich introspection (ADR-098)
$ git log --oneline -S expires_at -- hooks/edit-lock-pre-tool.sh
(vacío)
```

Es **deuda de origen, no regresión**: el campo nació escrito en el mismo commit
que el primitivo y el hook nunca contuvo la cadena. El lector no se perdió;
nunca se cableó. (Hermano cercano que sí lo hace bien:
`hooks/_lib/validation-lock.sh` compara `expires_at_epoch < now`.)

Semillas: `A` vencido hace 3 meses + PID muerto · `B` vigente + PID vivo mío ·
`C` vigente + PID 1 (proceso vivo de otro usuario) · `D` vencido hace 2 minutos
(dentro del grace) · `E` directorio de lock sin `meta.yaml`.

```
### D1 — el lock VENCIDO deja de bloquear
  A-expired-old    -> hook rc=0   (antes: rc=2 EDIT-LOCK CONFLICT)
  D-expired-recent -> hook rc=0

### D2 — el lock VIGENTE sigue bloqueando y no se poda
  B-live-current -> hook rc=2
  C-pid1-current -> hook rc=2      (este fallaba antes por el EPERM de kill -0)

### poda, dry-run  -> nada desaparece
{"dry_run": true, "kept": 3, "reaped": 2, "grace_seconds": 3600,
 "reaped_samples": [{"lock":"A-expired-old","reason":"expired-past-grace"},
                    {"lock":"E-nometa-old","reason":"no-meta-past-grace"}], "scanned": 5}
### poda, execute
  survivors: B-live-current C-pid1-current D-expired-recent

### D3 — el conflicto legítimo sigue hablando, después de la poda
EDIT-LOCK CONFLICT on B-live-current (ADR-098)
  Held by:    session=seed-B-live-current
  exit_code=2

### árbol real, antes y después
real_lock_dirs=1290    sha256(ls -la)=4908fe0f98604feda8cda386773fef59a3ca322a2bce0f76d10f20bb3d322ce8
real_lock_dirs=1290    sha256(ls -la)=4908fe0f98604feda8cda386773fef59a3ca322a2bce0f76d10f20bb3d322ce8
ALL DIRECTIONS PASS
```

El guion de siembra fue un andamio de scratchpad; **la evidencia que queda
versionada son cuatro tests** en `tests/unit/test_edit_coop.py`
(`test_expired_lock_does_not_block_another_session`,
`test_unexpired_lock_still_blocks_another_session`,
`test_reap_stale_removes_expired_and_keeps_live`,
`test_reap_stale_drops_lock_dir_without_meta`):

```
$ .venv/bin/python -m pytest tests/unit/test_edit_coop.py -q
20 passed in 5.52s
```

## Lo que NO hice y por qué

- **No borré ni un lock del árbol real.** El encargo pedía mecanismo, no pasada
  de `rm`, y `.cognitive-os/` es estado vivo del operador. Los 1296 los barre
  `so-reaper.sh` en su próximo cierre de sesión.
- **No promoví la superficie a `repair-safe`.** Requiere código
  (`reap_edit_locks()` en `state_retention_audit.py`), y el efecto —que el estado
  muerto deje de gobernar— ya está conseguido sin él. Prometerlo en un campo YAML
  sin implementación es exactamente lo que el manifiesto se prohíbe.
- **No toqué `control-plane-audit/findings-state.json`** (bomba 2, real): 2,4 MiB,
  **3928 hallazgos** conocidos que deciden BLOCK, escritos por
  `hooks/control-plane-audit.sh` / `-hourly.sh`, **sin ningún podador**
  (`grep -rn "findings-state" hooks scripts cos_lib packages` → vacío: la ruta se
  construye por partes). Es un colchón manual que sólo crece. Queda declarado,
  sin arreglo: bajarlo sin criterio es exactamente el verde barato que el encargo
  prohíbe, y el criterio de qué hallazgo caduca es una decisión de producto.
- **No toqué `validation-activity.jsonl`** (bomba 3, real y lenta): 187 filas /
  37 KB, decide si un lock de validación ajeno está stale a los 300 s, escrito por
  `hooks/_lib/validation-lock.sh` y `scripts/cos-validation-capsule.sh`, sin
  rotación. Crece despacio; la corrección de fondo es registrarla como superficie
  con rotación, del mismo modo que `edit-locks`.
- **No arreglé `status: "active"`** en `_write_meta`. El campo miente en 1296
  locks, pero ahora **nadie lo consulta para decidir** — el predicado lo ignora
  explícitamente. Arreglarlo sin lector sería agregar mantenimiento a un campo
  muerto.
- **No subí `global_budget.max_total_mib`** ni `max_unregistered_mib`, pese a que
  el audit da BLOCK. El rojo es anterior a este trabajo y sus dueños son otros
  (`artifacts/aci`, `tasks/control-plane-remediation.jsonl`).
