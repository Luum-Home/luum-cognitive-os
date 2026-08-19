# El guard de config protegida: qué bloqueaba de más y qué dejaba pasar

**Fecha:** 2026-08-19
**Archivo tocado:** `hooks/protected-config-write-guard.sh`
**Test nuevo:** `tests/hooks/test_protected_config_guard_read_vs_write.py`

## Resumen ejecutivo

El caso que venía en el encargo —un `grep -rln "..." hooks/_lib/` bloqueado— **no se
reproduce**, ni suelto ni en los transcripts. Todos los comandos de solo lectura de la
lista del encargo ya pasaban antes de tocar nada. Lo que sí bloqueaba, 88 veces en los
transcripts del proyecto, eran tres formas distintas: un intérprete que solo **lee**
config protegida (`json.load(open('.claude/settings.json'))`), un heredoc cuyo dueño se
resolvía mal (`mkdir -p d && cat > d/r.md <<MD` se resolvía a `mkdir`), y un informe
escrito con `tee`. En el mismo barrido aparecieron **dos falsos negativos**: la
sustitución de procesos nunca se analizaba, así que `diff <(sed -i s/a/b/ hooks/x.sh) f`
reescribía un archivo protegido detrás de una palabra de comando que es lectora. El
arreglo son tres cambios; cierra los dos agujeros y libera 11 de los 79 bloqueos
históricos, sin agregar ninguno. Queda una familia de falsos positivos **sin tocar a
propósito** (`python3 -c`), fijada en el test, porque arreglarla exige una decisión del
operador sobre el canje falso-positivo / falso-negativo.

## Correcciones a las premisas del encargo

**1. El `grep` del encargo no bloquea, y no bloqueaba.** Reproducido con el payload real
contra el hook de HEAD:

```
grep -rln "context_budget_filter_json()" hooks/_lib/     -> allow (exit 0)
```

`grep` está en `PURE_READERS`, el segmento se salta antes de mirar los paths. Lo mismo
para `cat`, `sed -n`, `head`, `wc -l`, `ls -la`, `find`, `git diff`, `git log --`,
`$(...)` y `<(...)` con lector adentro: los 15 casos de la lista del encargo ya estaban
verdes. El bloqueo que se vio en vivo no salió de ese `grep`: salió de la llamada que lo
envolvía. Un `"$SP/probe.sh" 'grep ... hooks/_lib/'` tiene como palabra de comando
`probe.sh`, que no es un lector conocido, y ahí sí el path protegido en los argumentos
dispara. El banner que se leyó era del comando de afuera, no del `grep`.

**2. No era un bug de parsing de sustitución de procesos, pero la sustitución de procesos
sí era un bug — al revés.** El agente anterior apuntó al lugar correcto con el signo
cambiado: `<(...)` no producía falsos positivos, producía **falsos negativos**, porque
`lift_substitutions` solo levantaba `$(...)`. El cuerpo de un `<(...)` nunca llegaba a
evaluarse como comando.

**3. Mi propio conteo de partida estaba inflado y lo corregí a mitad de camino.** El
primer barrido de transcripts dio 101 bloqueos. Estaba mal: buscaba el banner
`PROTECTED CONFIG WRITE GUARD` en el `tool_result`, y un `cat -n
hooks/protected-config-write-guard.sh` **imprime** ese texto sin haber sido bloqueado.
Exigiendo además `is_error` y el prefijo `PreToolUse:Bash hook error` quedan **88**. Los
13 de diferencia eran comandos que leían el hook, es decir el mismo error que estaba
investigando, cometido por mi herramienta de medición.

**4. `.cognitive-os/metrics/protected-config-write-blocks.jsonl` no existe.** El hook
llama a `primitive_intervention_emit` con ese destino en cada bloqueo; el archivo no está
en el filesystem (`ls` da "No such file or directory"). Las 1500 filas de este guard se
escriben en `primitive-interventions.jsonl`. El nombre del argumento no describe dónde
termina el dato.

## Caracterización: qué dispara el bloqueo

El analizador embebido corta el comando en segmentos y **falla cerrado por segmento**: un
segmento que nombra un path protegido cuenta como escritura *salvo* que su palabra de
comando esté en la lista de lectores (`PURE_READERS`, más un puñado de vetos por bandera
para `sed`, `awk`, `find`, `sort`, `yq`, `git` y los intérpretes). No hay lista negra de
verbos de escritura: la herramienta que se instale mañana está bloqueada por defecto. Ese
diseño es correcto y no se tocó.

Los caminos por los que un path llega a la lista de destinos son cinco:

1. **`tool_input.file_path`** de Edit / Write / MultiEdit.
2. **Redirecciones** (`REDIRECT`) sobre el texto del comando, sin mirar quién escribe.
3. **Segmentos** cuya palabra de comando no es un lector y que nombran un path protegido.
4. **Cuerpos de heredoc** servidos a algo que no es lector, si `body_can_write` encuentra
   una primitiva de escritura.
5. **Destinos leídos adentro del parche**, para `git apply` / `git am` / `patch`.

Los tres defectos estaban en (3), (4) y en lo que (3) no veía:

- **`body_can_write` contaba `open(` como escritura por substring.** `json.load(open(p))`
  —leer— quedaba clasificado como escribir en `p`. Familia más grande de las medidas.
- **`strip_heredocs` resolvía el ejecutable de la LÍNEA entera.** En
  `mkdir -p d && cat > d/r.md <<MD` resolvía `mkdir`, no `cat`; el cuerpo del heredoc
  —la prosa de un informe— pasaba a leerse como programa, y cada path protegido que el
  informe mencionaba se convertía en destino. El mismo error corría al revés:
  `cat f && python3 <<PY` resolvía `cat`, así que un programa de verdad se archivaba como
  dato inerte. Ese lado costaba más.
- **`lift_substitutions` no levantaba `<(...)` ni `>(...)`.** El cuerpo nunca se evaluaba.

## Las dos listas de casos

Las 55 filas están en `tests/hooks/test_protected_config_guard_read_vs_write.py`. Resumen:

### No deben bloquear (22 casos)

| Caso | Estado antes | Motivo |
|---|---|---|
| `grep`, `cat`, `sed -n`, `head`, `wc -l`, `ls -la`, `find`, `git diff`, `git log --` | ya pasaba | palabra de comando lectora |
| `echo "hooks/_lib" > /tmp/nota.txt` | ya pasaba | menciona la ruta, escribe en otro lado |
| `n=$(wc -c < hooks/x.sh)` | ya pasaba | arreglado el 2026-08-18 |
| `diff <(cat hooks/x.sh) <(cat hooks/x.sh)` | ya pasaba | comando externo lector |
| `python3 - <<PY … json.load(open(SETTINGS)) … PY` | **bloqueaba** | `open(` contado como escritura |
| lo mismo con `open(p,'r')`, `'rb'`, `encoding='utf-8'` | **bloqueaba** | ídem |
| `mkdir -p d && cat > /tmp/r.md <<MD` con prosa que menciona `hooks/_lib` | **bloqueaba** | dueño del heredoc mal resuelto |
| `tee /tmp/r.md > /dev/null <<MD` con la misma prosa | **bloqueaba** | `tee` tratado como intérprete |

### Deben bloquear (30 casos)

`sed -i` (y `-i.bak`), `> archivo`, `>> archivo`, `cat protegido > protegido`, `cp`, `mv`,
`rm`, `tee`, `tee` con heredoc, `cat > protegido <<EOF`, lo mismo precedido de `mkdir &&`,
`chmod`, `truncate`, `awk -i inplace`, `yq -i`, `git apply`, `patch -p1 <`,
`bash -c "echo x > protegido"`, y siete formas de `open` que **sí** escriben:
`'w'`, `'a'`, `'r+'`, modo en variable, `mode='w'`, `os.open(..., os.O_WRONLY)`,
`Path(...).write_text(...)`.

Más los tres que **no** bloqueaban y ahora sí:

| Caso | Estado antes |
|---|---|
| `diff <(sed -i 's/a/b/' hooks/x.sh) /dev/null` | **pasaba** |
| `cat <(tee hooks/x.sh)` | **pasaba** |
| `cat /etc/hostname && python3 <<PY … open(p,'w') … PY` | **pasaba** |

## El arreglo

Tres cambios, los tres sobre propiedades verificables del comando, ninguno sobre una
adivinanza de intención.

**1. El heredoc pertenece al SEGMENTO, no a la línea** (`heredoc_terms_of`). Se resuelve
el ejecutable de cada segmento por separado y cada `<<` hereda el veredicto del suyo.
Corta para los dos lados: libera el informe escrito con `mkdir && cat >` y captura el
programa escondido detrás de `cat f && python3 <<PY`. Se agregó además
`HEREDOC_DATA_CONSUMERS = {tee, dd}`: los dos copian stdin a los archivos de sus propios
argumentos y ninguno lo interpreta jamás, así que su heredoc es dato. Ese conjunto se usa
**solo** para clasificar el cuerpo — los argumentos siguen juzgándose igual, y por eso
`tee hooks/y.sh <<EOF` sigue bloqueando.

**2. La sustitución de procesos se levanta como la de comandos** (`PROCSUB`). `<(...)` y
`>(...)` pasan a ser segmentos propios y se juzgan solos. Es puro cierre de agujero.

**3. `open(` se lee con su modo** (`_open_can_write`). Se saca `open(` de la lista de
primitivas y se analiza cada llamada: se extrae la lista de argumentos con conteo de
paréntesis y comillas, se parte en el nivel superior, y se busca el modo (posicional 2 o
kwarg `mode=`). Es lectura solo si no hay modo —el default de Python es `r`— o si el modo
es un literal formado únicamente por `r`, `b`, `t`, `U`. Todo lo demás es escritura: modo
con `w`, `a`, `x` o `+`, modo que es variable o expresión, flag de `os.open`, o llamada
cuyos paréntesis el escáner no puede balancear. Falla cerrado en cada rama.

Lo que **no** se hizo: no se sacó `hooks/_lib` de las rutas protegidas, no se agregó
ninguna excepción por nombre de binario, no se bajó nada a advertencia, ningún test
quedó `skip` ni `xfail`.

Restricciones del archivo respetadas: paréntesis balanceados y número par de comillas por
línea (el heredoc vive dentro de una sustitución de comando y `/bin/bash` 3.2 se pierde si
no), de ahí `chr(40)` en vez de un paréntesis suelto. Validado con la ruta absoluta:

```
$ /bin/bash --version | head -1
GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)
$ /bin/bash -n hooks/protected-config-write-guard.sh && echo OK
OK
```

Escritura en ruta protegida declarada: el arreglo se aplicó con
`COS_ALLOW_PROTECTED_CONFIG_WRITE=1`, queda la fila en
`.cognitive-os/metrics/protected-config-bypass.jsonl`.

## Prueba en las dos direcciones

El test acepta `COS_GUARD_UNDER_TEST`, así que el rojo se reproduce desde git sin
revertir nada:

```bash
mkdir -p /tmp/guard-prefix && ln -sfn "$PWD/hooks/_lib" /tmp/guard-prefix/_lib
git show d7a503bbd:hooks/protected-config-write-guard.sh > /tmp/guard-prefix/guard.sh
COS_GUARD_UNDER_TEST=/tmp/guard-prefix/guard.sh \
  .venv/bin/python3 -m pytest tests/hooks/test_protected_config_guard_read_vs_write.py -p no:randomly -q
```

**Rojo (hook de HEAD, sin el arreglo):**

```
FAILED …::test_read_only_work_is_not_blocked[heredoc-open-default-mode]
FAILED …::test_read_only_work_is_not_blocked[heredoc-open-mode-r]
FAILED …::test_read_only_work_is_not_blocked[heredoc-open-mode-rb]
FAILED …::test_read_only_work_is_not_blocked[heredoc-open-encoding-kwarg]
FAILED …::test_read_only_work_is_not_blocked[heredoc-report-after-mkdir]
FAILED …::test_read_only_work_is_not_blocked[heredoc-report-via-tee]
FAILED …::test_real_writes_to_protected_paths_stay_blocked[procsub-runs-sed-i]
FAILED …::test_real_writes_to_protected_paths_stay_blocked[procsub-runs-tee]
FAILED …::test_real_writes_to_protected_paths_stay_blocked[heredoc-owner-is-second-segment]
9 failed, 46 passed in 16.60s
```

Seis falsos positivos y tres falsos negativos, que son los que importan.

**Verde (con el arreglo):**

```
$ .venv/bin/python3 -m pytest tests/hooks/test_protected_config_guard_read_vs_write.py -p no:randomly -q
55 passed in 16.05s
```

**Sin regresión en la suite que ya existía:**

```
$ .venv/bin/python3 -m pytest tests/hooks/test_protected_config_write_guard.py -p no:randomly -q
212 passed in 47.53s
```

**Sobre los bloqueos reales del proyecto.** Se cosecharon de los transcripts los 88
comandos Bash únicos que el guard bloqueó (pares `tool_use`/`tool_result` con `is_error` y
el prefijo del harness), y se los volvió a pasar por el hook antes y después:

```
comandos históricos re-ejecutados:      88
  seguían bloqueando antes del arreglo: 79
  siguen bloqueando después:            68
  liberados por el arreglo:             11
  bloqueados de más por el arreglo:      0
```

Los 11 liberados son informes escritos con `cat >` o `tee` hacia `docs/`, y lecturas de
`.claude/settings.json` desde Python. Ninguno escribe en una ruta protegida.

**Latencia:** sin costo medible. 15 corridas sobre el mismo payload,
p50 295 ms → 214 ms, p95 395 ms → 336 ms; la diferencia es caché tibia, no una mejora.

## El canal de falsos positivos: ¿alguien lo usó?

No. Nunca.

```
$ wc -l .cognitive-os/metrics/governance-catches.jsonl
       0
$ ls -la .cognitive-os/metrics/governance-catches.jsonl
-rw-r--r--  1 …  0 Jun 17 20:11 …/governance-catches.jsonl
$ grep -c 'protected-config-write-guard' .cognitive-os/metrics/governance-catch-prompts.jsonl
     117
$ wc -l .cognitive-os/metrics/governance-catch-prompts.jsonl
     535
$ wc -l .cognitive-os/metrics/protected-config-bypass.jsonl
     571
```

El guard ofreció el canal **117 veces** para este hook solo (535 en total, todos los
hooks), repartidas en nueve días distintos entre el 2026-07-02 y hoy. El ledger donde
irían esas respuestas está en **cero filas desde el 17 de junio**, día en que se creó. En
el mismo período se otorgaron **571 aprobaciones** de escritura y se emitieron **1500**
intervenciones de este guard.

El consumidor existe y está escrito: `scripts/cos_governance_roi.py` lee
`governance-catches.jsonl` para calcular la relación fricción-vs-catch, y hasta trae una
recomendación enlatada que dice, textualmente, que hay que registrar los veredictos "so
friction-vs-catch ratio can distinguish correct blocks from false positives". Es decir: el
sistema sabe que le falta el dato, lo pide 117 veces, nadie contesta, y la recomendación
que emite es que alguien conteste.

Por eso el guard estuvo equivocado durante semanas sin enterarse. La señal se produjo, el
consumidor estaba escrito, y el circuito nunca se cerró — el mismo patrón que venimos
persiguiendo en toda la sesión. Dos cosas que lo explican y que no arreglé:

- El prompt trae `"default":"skip"`. La respuesta por omisión es no contestar.
- El texto que ve el agente arranca con "COS governance feedback **optional** (default
  skip)". Un canal opcional, ofrecido en el peor momento posible —justo cuando al agente
  le acaban de frenar el trabajo—, con la salida más barata marcada como default.

## Lo que NO hice y por qué

**`python3 -c "<programa>"` que solo lee sigue bloqueando.** Es la familia de falsos
positivos que queda, ~1 de cada 4 bloqueos sobre trabajo de lectura en los transcripts. Es
el mismo programa que en heredoc ahora pasa, y esa asimetría es fea. Arreglarla significa
mandar el argumento de `-c` por `body_can_write`, o sea confiar en una lista negra de
primitivas de escritura —lo que el propio autor del hook llamó "unwinnable"— a través de
una segunda sintaxis. Eso es una decisión sobre el canje falso-positivo / falso-negativo y
es del operador, no del agente que lo notó. Queda **fijado** en el test, en
`CONSERVATIVE_OVERBLOCKS`, con el motivo escrito y con un mensaje de assert que dice qué
hacer si algún día se resuelve: mover el caso a `READ_ONLY` y anotar la decisión. No está
`skip` ni `xfail` — es una aserción del contrato actual, para que el costo se vea.

**`cp hooks/x.sh /tmp/copia` sigue bloqueando**, aunque el path protegido sea el origen.
Se arregla de forma demostrable (`cp` escribe solo en el destino, o en el target de `-t`),
pero no está en la lista del encargo y cada narrowing de un guard de seguridad es
superficie nueva. Fijado en `CONSERVATIVE_OVERBLOCKS` junto con el anterior.

**Un script auxiliar con un path protegido en los argumentos sigue bloqueando.** Es el
fallo-cerrado funcionando: `/tmp/helper.sh 'hooks/…'` puede hacer cualquier cosa. Correcto
por diseño, fijado igual para que quede visible.

**No commiteé el cosechador de transcripts.** Lee `~/.claude/projects/…`, depende de la
máquina y del formato del harness. La evidencia durable del arreglo es el test más la
receta de `COS_GUARD_UNDER_TEST` de arriba, que se reconstruye desde git en tres comandos.

**No toqué el canal de falsos positivos.** El hallazgo está arriba con los números; qué
hacer con un canal opcional que nadie usó en 117 ofertas —hacerlo obligatorio, sacarlo, o
cambiar el default— es una decisión de gobierno, no un arreglo de parsing.
