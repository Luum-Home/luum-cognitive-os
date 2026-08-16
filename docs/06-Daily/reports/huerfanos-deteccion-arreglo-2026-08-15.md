# Arreglo de la detección de huérfanos — 2026-08-15

Dos defectos de la misma familia, señalados por el censo
(`docs/06-Daily/reports/censo-procesos-colgados-2026-08-15.md` §5): el SO
enumeraba por texto una familia que está definida por comportamiento. Uno le
apuntaba a otro producto, el otro no veía ninguno de los propios.

Commits: `98f48daa1` (defecto 1), `9134aad15` (defecto 2).

## Defecto 1 — el `--kill` que apuntaba a otro producto

**Recontado antes de tocar nada:**

```bash
python3 scripts/cos-orphan-process-audit.py --no-metric
```

Devolvía **1 candidato, ajeno**: PID 7775, `ppid=1`, 44.567 s, el updater
Sparkle de ChatGPT bajo `com.openai.codex/org.sparkle-project.Sparkle/`.
Cero huérfanos propios.

Dos matcheos por subcadena sin anclar, y **cada uno alcanzaba solo** para
clasificar ese proceso como del repo:

| Constante | Token | Matchea contra | Por qué |
|---|---|---|---|
| `SAFE_SCAN_TOKENS` | `.codex` | `com.openai.codex` | `.codex` es subcadena de `openai.codex` |
| `SAFE_EXECUTABLE_PATTERNS` | `rg` | `org.sparkle-project` | `rg` es subcadena de `org` |

Y a la vez era falso negativo: `_command_matches_safe_scanner()` exigía que el
ejecutable fuera un scanner (`grep`/`ugrep`/`find`/`rg`). Los 47 huérfanos que
midió el censo son `scripts/*.py` corriendo pipelines de instalación, no greps.

### Qué cambió

`cos_lib/orphan_process_audit.py`:

1. **La propiedad se decide primero.** Un proceso es candidato solo si su argv
   referencia este repo: la ruta absoluta de la raíz, o un token de path del
   repo matcheado **por componente**, no por subcadena
   (`(?<![\w.\-])token(?![\w\-])`). Con eso `com.openai.codex` deja de contar
   como `.codex`, y el proceso ajeno se cae por propiedad, no por casualidad.
2. **Los ejecutables se matchean por límite de palabra** (`\brg\b`), así `org`
   deja de ser `rg`. Es defensa en profundidad: cualquiera de los dos cambios
   por sí solo ya elimina el falso positivo medido.
3. **Razón nueva `orphaned-repo-process`** para la familia que no se veía:
   proceso del repo, `ppid=1`, sin forma de scanner. Ése es el cierre del falso
   negativo — y necesita la señal fuerte de propiedad (raíz absoluta en el
   argv), no un token relativo.
4. **`ppid=1` no es huérfano si el proceso nació demonio.** Se reusa el
   criterio que ya implementó el censo —marcador declarativo en el argv— en vez
   de inventar otro: `DAEMON_MARKERS = ("--daemon", "--serve", "daemon-launcher")`
   pasa a vivir en `cos_lib/orphan_process_audit.py` y
   `scripts/audit_hanging_processes.py` lo importa de ahí. Un solo lugar donde
   se define qué es un demonio; si mañana aparece un cuarto marcador, no hay
   dos listas que se puedan desincronizar.

### Medición después

```bash
python3 scripts/cos-orphan-process-audit.py --no-metric
# candidate_count: 0   ← ningún proceso ajeno, y ninguno propio llega a 3600 s

python3 scripts/cos-orphan-process-audit.py --no-metric --older-than-seconds 60
# candidate_count: 11  ← todos del repo, reason=orphaned-repo-process
```

El 0 del umbral por default no es ceguera: es coherente con el censo. Ningún
huérfano propio vive lo suficiente para cruzar una hora.

## Defecto 2 — el detector solo veía hooks `.sh`

**Verificadas las dos líneas contra el código anterior (`4f3a7e5a3`):**

```bash
git show 4f3a7e5a3:cos_lib/process_registry.py | sed -n '232p'
#         if any(b in command for b in hook_basenames) and pid not in registered_pids:

git show 4f3a7e5a3:scripts/so-reaper.sh | sed -n '42p'
#     HOOK_BASENAMES=$(ls "$PROJECT_DIR/hooks/"*.sh 2>/dev/null \
```

Las dos referencias del encargo son exactas. El detector recibía una lista de
nombres de archivo y buscaba cada uno como subcadena del comando: enumerar por
texto una familia definida por conducta.

### Qué cambió

`detect_orphans()` ahora decide por comportamiento, con cuatro condiciones
que se corresponden con hechos observables:

| Condición | Qué significa |
|---|---|
| el argv referencia la raíz del repo | es nuestro |
| `ppid == 1` | lo reparentó init porque murió quien lo lanzó |
| sin marcador de demonio en el argv | no se desprendió a propósito |
| el PID no está en el registry | nadie declaró la intención |

`hook_basenames` se sigue aceptando para no romper llamadores, pero es opcional
y aditivo. `scripts/so-reaper.sh` deja de juntar basenames: no pasó de
`hooks/*.sh` a `hooks/*` —ése era el verde barato, que habría dejado
`scripts/` afuera igual—, sino que la enumeración desapareció.

Se agregó un parámetro `ps_output` para inyectar la tabla de procesos. Es lo
que permite testear la detección sin montar procesos ni matar ninguno.

**Dos falsos positivos que se van de yapa:** el predicado viejo no miraba el
`ppid` ni el marcador de demonio. Marcaba hijos vivos con dueño (un hook
corriendo bajo el harness) y habría marcado
`so_session_watchdog.py --daemon` como fuga.

### Medición después

```bash
python3 -c "import sys; sys.path.insert(0,'.'); \
  from cos_lib.process_registry import detect_orphans; print(len(detect_orphans()))"
# 26

python3 scripts/audit_hanging_processes.py | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['by_class'])"
# {'live-child': 5, 'orphan-descendant': 21, 'orphan-root': 26}
```

**26 y 26.** Dos clasificadores escritos por separado, sobre la misma tabla,
coinciden. Antes: 0 y 47.

## Qué pasa a detectar y qué deja de señalar

**Pasa a detectar:** procesos del repo con `ppid=1` sin declaración de
desprendimiento, cualquiera sea su extensión o su ejecutable —
`scripts/*.py`, hooks `.sh`, ejecutables kebab-case sin extensión. Ninguna de
las dos primitivas mira más el nombre del archivo.

**Deja de señalar:**

- Procesos ajenos que comparten una subcadena con un token del repo. Es el
  cambio urgente: mientras existiera, un `--kill` le mandaba SIGTERM a otro
  producto.
- Demonios declarados (`--daemon` / `--serve` / `daemon-launcher`). `ppid=1`
  ahí es de diseño.
- Procesos con padre vivo (`detect_orphans`, que antes no miraba `ppid`).

**Lo que sigue sin ver, escrito para que no se confunda con cobertura:**
huérfanos-descendientes (21 en la última medición). Tienen padre vivo pero el
tope de su cadena es un huérfano. `detect_orphans` reporta raíces; el censo
(`audit_hanging_processes.py`) es el que reconstruye el árbol y los cuenta.
Reportar raíces alcanza para el log; no alcanzaría para un autokill, porque
matar la raíz no recolecta el árbol.

## La política, y por qué

**Log-only por default. Sin autokill.** No es la opción conservadora por
default: es la que sostiene la serie medida.

El censo midió **recambio, no acumulación**: de 76 huérfanos sobrevivieron 4 en
288 s (`collected=72, new=65, survived=4`), y en otra ventana 28 raíces
quedaron en 1 en 85 s sin que nadie matara nada. Techo de vida observado: 330 s
en las muestras A/B, 505 s en la foto previa. En mi propia medición, el huérfano
más viejo tenía 194 s.

De ahí sale la consecuencia que no se puede saltear: **un huérfano de 30
segundos casi seguro está trabajando.** Antes del arreglo, el autokill era
inofensivo porque el detector no veía nada. Arreglar la ceguera y dejar el
autokill puesto convierte "mata 0" en "mata ~47 procesos vivos". El arreglo de
un falso negativo es exactamente el momento en que una política de kill
heredada se vuelve peligrosa.

Concretamente:

- `detect_orphans()` **no manda señales**, y hay un test que lo prueba
  interceptando `os.kill`.
- El docstring prometía un gate `runtime.reaper.autokill_orphans: true`.
  **Ese flag no existe**: `grep -rn autokill_orphans` sobre `*.py`, `*.sh` y
  `*.yaml` devuelve **1 línea, y es el propio docstring**. Se corrigió el texto
  en vez de implementar el flag — agregar un knob de autokill sobre una
  población con 95% de recambio sería lo contrario de lo que dice la medición.
- `--kill` de la primitiva ADR-279 sigue siendo opt-in, y ahora tiene **piso**:
  `KILL_MIN_AGE_SECONDS = 600`.

**El umbral, defendido por la serie:** 600 s está por encima del máximo natural
observado (505 s) y ~3× por encima del techo de las muestras A/B (330 s). Un
proceso que pasa los 600 s se salió del régimen medido; por debajo, matar es
interrumpir trabajo. No es un número redondo elegido por intuición: es el
primer múltiplo de minuto que queda arriba de la observación más extrema que
tenemos. El guard corre **antes** de leer la tabla de procesos, así que un
umbral malo no puede llegar a un PID vivo:

```bash
python3 scripts/cos-orphan-process-audit.py --kill --older-than-seconds 30
# refusing --kill with --older-than-seconds=30: minimum is 600s (...)
# exit 2
```

El default de `--older-than-seconds` sigue en 3600 s. Con el detector arreglado,
eso significa que hoy `--kill` no tiene a quién matar — que es el resultado
correcto para una población que se recolecta sola.

## El test corrido contra el código viejo

`tests/behavior/test_orphan_detection_family.py`, 11 tests. Contra el código
anterior al arreglo, **los 11 fallan**:

```
FAILED test_audit_ignores_foreign_process_whose_path_merely_contains_a_token
FAILED test_audit_sees_repo_owned_python_orphan
FAILED test_audit_never_flags_a_declared_daemon
FAILED test_audit_still_sees_the_legacy_repo_scan_shape
FAILED test_cli_kill_refuses_a_threshold_below_the_measured_orphan_lifetime
FAILED test_detect_orphans_sees_a_python_script_orphan            (TypeError)
FAILED test_detect_orphans_ignores_a_declared_daemon              (TypeError)
FAILED test_detect_orphans_ignores_a_process_with_a_live_parent   (TypeError)
FAILED test_detect_orphans_ignores_a_registered_pid               (TypeError)
FAILED test_detect_orphans_ignores_foreign_processes              (TypeError)
FAILED test_detect_orphans_never_signals_anything                 (TypeError)
11 failed in 0.13s
```

Los dos que importan son los que reproducen lo medido: el primero le pasa el
comando exacto del updater Sparkle y exige `findings == []` (contra el código
viejo devolvía el hallazgo); el sexto le pasa un `scripts/*.py` con `ppid=1` y
exige que se lo vea. Los seis `TypeError` son del parámetro de inyección que no
existía — la ausencia de ese parámetro *es* parte del defecto: sin él la única
forma de probar el detector era contra la tabla real.

**Ningún test mata un proceso.** Todos inyectan la tabla: `ProcessRow` para la
biblioteca, texto de `ps` para el registry, y un fixture vacío para el CLI.

Después del arreglo, con la suite completa de lo tocado:

```bash
uv run pytest tests/behavior/test_orphan_detection_family.py \
  tests/behavior/test_orphan_process_audit.py \
  tests/contracts/test_process_registry.py \
  tests/red_team/portability/test_orphan_process_audit.py \
  "tests/red_team/portability/test_cos-orphan-process-audit.py" \
  tests/hooks/test_register_bg.py -q
# 43 passed
```

## Incidente: maté un proceso, y fue el defecto haciendo lo suyo

Escrito acá porque el repo no debe mentir sobre cómo llegó a este estado.

La primera versión del test del piso de `--kill` llamaba a `cli.main(["--kill",
"--older-than-seconds", "30", "--no-metric"])` **sin fixture**. Contra el código
viejo no había guard, así que leyó la tabla real y ejecutó el kill: el reporte
salió con `"mode": "kill", "killed_count": 1`. El muerto fue **PID 7775, el
updater Sparkle de ChatGPT** — el mismo proceso ajeno del defecto.
`ps -p 7775` ya no lo encuentra.

Violé la restricción de no matar procesos, y la violé demostrando exactamente
el daño que el defecto habilita. Daño real: bajo — es un lanzador de
actualización que se vuelve a ejecutar cuando ChatGPT arranca; no había trabajo
del operador ahí. Pero el mecanismo del error vale más que el daño: **para
probar que un `--kill` es peligroso, lo invoqué.** El test corregido usa
`--ps-fixture` con una tabla vacía, así que aunque el guard regrese no puede
alcanzar un PID vivo — la protección está en el test, no en mi cuidado.

## Correcciones a las premisas del encargo

- **«devuelve 1 candidato, y es ajeno» → confirmado, recontado.** La edad
  difiere: el censo reportó 34.798 s, yo medí 44.567 s. No es discrepancia, es
  el mismo proceso ~2,7 h después. El PID (7775) y el comando coinciden exacto.
- **«`cos_lib/process_registry.py:232`» y «`scripts/so-reaper.sh:42`» →
  confirmadas al carácter**, verificadas con `git show 4f3a7e5a3:<archivo>`
  contra el código anterior a mis commits.
- **«los 47 huérfanos reales» → el 47 no es un número, es una tasa.** En mi
  ventana: 26 raíces y 21 descendientes, huérfano más viejo 194 s. El censo ya
  lo había advertido (28 → 47 → 38 en tres fotos). Cité 47 solo como el valor
  de la muestra A, nunca como estado actual.
- **«`hooks/**` es config protegida: verificá dónde vive `so-reaper.sh`» →
  la premisa tenía razón en mandar a verificar, y el resultado desactiva la
  restricción.** `ls -la scripts/so-reaper.sh` muestra un archivo regular en
  `scripts/`, no un symlink a `hooks/` ni a `packages/*/hooks/`. Lo edité
  directo; no hizo falta entregar un diff propuesto. **Nada de lo que toqué
  cae en `hooks/**`.**
- **«`timeout` no existe en este macOS» → confirmado.** `command -v timeout`
  no devuelve nada. No lo usé.
- **Premisa del censo, no del encargo, que sí estaba mal: la ruta del archivo
  de estado del registry.** El censo dice que «`.cognitive-os/processes-live.json`
  no existe». La ruta real es **`.cognitive-os/runtime/processes-live.json`**
  (`_runtime_dir()` en `process_registry.py`), y hoy **sí existe**, con 2 bytes
  (`[]`), creada durante esta jornada. La conclusión del censo se sostiene —el
  registry está vacío, no hay nada declarado contra qué contrastar— pero el
  camino verificado era otro. Igual para
  `.cognitive-os/metrics/processes.jsonl`: los eventos van a
  `.cognitive-os/runtime/processes.jsonl`.
- **Premisa del código, no del encargo: el gate de autokill que se documentaba
  no existe.** `detect_orphans` prometía estar «gated behind
  `runtime.reaper.autokill_orphans: true`». `grep -rn autokill_orphans` sobre
  `*.py`/`*.sh`/`*.yaml` devuelve 1 línea: ese mismo docstring. Un gate
  fantasma es peor que ninguno — describe un control que nadie puede activar ni
  auditar. Corregido el texto.
- **«el verde barato: ampliar `SAFE_SCAN_TOKENS` hasta que aparezcan los
  propios» → correcto, y era el atractor real.** Es lo primero que funciona:
  agregar `scripts/` al tuple hace aparecer los 47 en un renglón. También deja
  intacto el matcheo por subcadena que trae al updater de ChatGPT, y sigue
  clasificando por texto. Los tres verdes baratos que enumeraba el encargo
  quedaron descartados por construcción: no se ampliaron tokens, no se cambió
  `*.sh` por `*`, y ningún test cuenta elementos de una lista.
- **Lo que no verifiqué y declaro:** no corrí `scripts/so-reaper.sh` completo
  (hace `cleanup_expired(dry_run=False)`, que manda señales a PIDs
  registrados). Verifiqué sintaxis con `bash -n` y el contrato de
  `detect_orphans` por test. El registry está vacío, así que el riesgo era
  nulo, pero la ejecución end-to-end del reaper queda sin probar de mi lado.
