# skill-router-prompt-suggest: TimeoutExpired en dos tests

Fecha: 2026-08-18
Archivos: `hooks/skill-router-prompt-suggest.sh`, `cos_lib/skill_router.py`,
`tests/unit/test_skill_router_prompt_suggest_hook.py`
Evidencia reproducible: `scripts/measure_skill_router_cost.py`

## Veredicto en una línea

No se colgaba: era lento de verdad, y encima la máquina estaba a load 724.
El hook gastaba ~0.9 s de CPU en cada prompt del usuario porque parseaba el
frontmatter de cada SKILL.md tres veces. Se memoizó la lectura+parseo y la
CPU bajó a ~0.39 s; los cinco tests pasan.

## ¿Colgado o lento? — CPU medida aparte del wall

Primera medición, con el hook sin tocar, invocado igual que el test:

```
exits_zero(PASA)                wall=7.89s cpu=1.13s ratio=0.14 rc=0
emits_additional_context(FALLA) wall=9.45s cpu=1.16s ratio=0.12 rc=0
writes_suggestion_log(FALLA)    wall=7.38s cpu=1.07s ratio=0.15 rc=0
low_confidence(PASA)            wall=6.86s cpu=1.05s ratio=0.15 rc=0
```

Los cuatro **terminan** (`rc=0`), ninguno se cuelga. Los dos que fallaban son
simplemente los que quedaban del otro lado de los 10 s del `timeout=` del test.
Nótese que los que "pasan" estaban a 6.9 y 7.9 s: los cinco estaban al borde,
no había dos casos especiales.

El ratio 0.12-0.15 parecía espera de I/O. **No lo era.** El control lo decide:

```
$ .venv/bin/python -c 'spin puro de 3 s'
spin: wall=3.00s cpu=0.64s
$ uptime
load averages: 724.02 741.82 748.22    # sobre 12 cores
$ /usr/bin/time -l ...
4.31 real  0.92 user  0.09 sys
33 voluntary context switches / 2332 involuntary
```

Un bucle que no hace más que quemar CPU también reportaba ratio 0.21. O sea:
el proceso no esperaba nada, **no lo dejaban correr**. `involuntary` 70x mayor
que `voluntary` es la firma de preempción, no de bloqueo en I/O.

Comando para repetir todo esto, incluida la calibración:

```bash
.venv/bin/python scripts/measure_skill_router_cost.py
```

Imprime primero `CPU share of one core`, que avisa si el wall está inflado.

## ¿Código o invocación? — código

El costo estaba en el constructor, no en el matching:

```
import SkillRouter   wall=0.02s cpu=0.02s
SkillRouter()        wall=6.96s cpu=1.08s     <-- acá
best_match           wall=0.00s cpu=0.00s
```

Dentro del constructor, `_build_default_routing_table` era el 100 % del costo
(`_parse_catalog` 0.00 s, `_detect_skill_md_paths` 0.14 s,
`_load_profile_projected_skills` 0.00 s). Y adentro de ése, cProfile mostró
**1049 llamadas a `yaml.safe_load` para 427 archivos**: cada SKILL.md se leía
del disco y se parseaba tres veces, una por `_parse_routing_patterns_block`,
otra por `_parse_routing_intents_block` y otra por `_parse_frontmatter` para
sacar `name`/`invoke`.

Eso es deuda real, no coincidencia: los tres consumidores necesitan el mismo
bloque de frontmatter del mismo archivo, y un cambio en el formato obliga a
tocar los tres. Se unifica.

## El arreglo

`cos_lib/skill_router.py`:

- `_parse_frontmatter_ex(text) -> (dict, yaml_backed)` — misma lógica que
  `_parse_frontmatter`, pero informa si PyYAML llegó a parsear. Hace falta
  porque el parser mínimo de fallback no sabe representar listas de mappings
  (`routing_patterns`), y en ese caso hay que caer al escaneo por regex como
  antes. `_parse_frontmatter(text) -> dict` queda como wrapper: los tests de
  contrato la importan con esa firma.
- `_read_skill_md_cached(path)` — devuelve `(text, frontmatter, yaml_backed)`
  memoizado por `(st_mtime_ns, st_size)`. Un SKILL.md editado mientras el
  proceso vive se vuelve a leer.
- Los tres consumidores pasan a usarla.

`hooks/skill-router-prompt-suggest.sh`: sólo el comentario de cabecera, que
declaraba un presupuesto falso (ver abajo).

**No se tocó el test.** El `timeout=10` sigue en 10 s.

### Equivalencia: la salida no cambió

Antes y después se serializó la tabla de ruteo entera (208 entradas: nombre,
comando de invocación, patrones compilados con su confianza, intents,
templates) y se comparó por md5:

```
before  48a3d7d8f12892f6ae45f7b1efa0fe64
after   48a3d7d8f12892f6ae45f7b1efa0fe64
```

Idéntico, y estable en tres corridas de cada lado.

### Números

| | antes | después |
|---|---|---|
| `yaml.safe_load` por build | 1049 | 427 |
| CPU de la tabla de ruteo | 0.90 s | 0.39 s |
| CPU del hook completo | ~1.10 s | ~0.50 s |
| wall del hook (load ~700) | 7.4-9.5 s | 0.80-0.92 s |
| memoria del cache | — | 2.2 MiB de texto, RSS 31 MiB |

### Tests

```
$ .venv/bin/python -m pytest tests/unit/test_skill_router_prompt_suggest_hook.py -p no:randomly -q
5 passed in 3.93s

$ .venv/bin/python -m pytest $(grep -rln skill_router tests --include='*.py') -p no:randomly -q
214 passed, 5 skipped in 38.38s
```

Con línea de resumen, no sesión abortada.

## ¿Se cuelga en producción? No, pero costaba caro

El hook **está registrado** (`grep -c skill-router-prompt-suggest
.claude/settings.json` → 1) y dispara de verdad.

- `.cognitive-os/metrics/skill-suggestion.jsonl`: **425 líneas**. Esa línea se
  escribe al final del bloque Python, así que 425 disparos = 425 terminados.
  Cero cuelgues.
- `.cognitive-os/metrics/hook-timing.jsonl`, 29 muestras con duración:
  **p50 1767 ms, p95 11315 ms, máx 12053 ms, 22 de 29 por encima de 1 s.**

Con un presupuesto declarado de `<150ms` en su propia cabecera. La mediana
estaba 12x por encima; el p95, 75x. Ese comentario se corrigió con los números
medidos en vez de dejarlo mintiendo.

## Las dos hipótesis del encargo

**1. Espera de entrada (stdin).** Descartada. El test manda
`input=json.dumps({"prompt": prompt})` y `subprocess.run` cierra el pipe al
terminar de escribir; `read_stdin_json` recibe EOF. La prueba directa es que
el hook **termina** con `rc=0` en las cuatro corridas y escribe su log — un
proceso trabado en `poll()` sobre fd 0 no llega a escribir nada.

**2. Espera de filesystem / `fseventsd`.** Descartada como *causa*. `fseventsd`
estaba efectivamente al 62 % en el momento de medir, pero es otro síntoma de la
misma sobrecarga. Lo que la descarta es el control: el spin puro de CPU, que no
toca el filesystem, sufrió exactamente la misma penalización (ratio 0.21), y
`/usr/bin/time` mostró 33 context switches voluntarios contra 2332
involuntarios. Bloqueo en filesystem daría lo inverso.

## El verde barato que no se tomó

- Subir el `timeout=10`. Habría escondido un hook con p50 de 1.7 s corriendo en
  cada prompt.
- `skip` / `xfail`.
- Mandarle un payload mínimo que corte antes de construir el `SkillRouter`: el
  test pasaría sin ejercitar el único camino caro que tiene el hook.

Lo que se hizo fue bajar el trabajo real a la mitad, con la salida verificada
idéntica.

## Deuda que queda

El hook sigue en ~0.5 s de CPU por prompt, lejos de los 150 ms que declaraba.
El piso ahora es un `yaml.safe_load` por SKILL.md (427). Bajar de ahí pide un
cache persistente de la tabla de ruteo entre procesos, con invalidación por
checksum del árbol — hay una pieza parecida en memoria en `_RouterCache`, pero
no sirve porque el hook arranca un proceso nuevo cada vez. Queda anotado, no
resuelto, y el presupuesto en la cabecera del hook ahora dice la verdad.

## Correcciones a las premisas del encargo

1. **"Sobreviven al aislamiento, así que no es carga de máquina" — falso, y era
   la premisa central.** Aislar el *test* no aísla la *máquina*. El load average
   estaba en **724 sobre 12 cores** mientras se reintentaba, y un spin de CPU
   puro medido en el mismo momento sólo conseguía 0.21 de un core. La carga era
   causa necesaria: con la misma carga, después del arreglo, los tests pasan.

2. **"Dos tests fallan" — los cinco estaban al borde.** Los que pasaban tardaban
   6.9 y 7.9 s contra un tope de 10 s. No había nada particular en los dos
   señalados más allá de estar del otro lado de la línea; tratarlos como dos
   casos especiales llevaba a buscar una diferencia que no existe.

3. **La sospecha sobre `additionalContext` no aplica.** El hook ya emite la
   forma anidada correcta (`hookSpecificOutput.additionalContext`,
   líneas 100-109) y el test ya la verifica así (líneas 88-89). No hay forma
   plana en juego. El encargo mismo decía que no lo asumiera, y en efecto no era.

4. **Ambas hipótesis del encargo eran falsas** (ver arriba). Ninguna era espera:
   era CPU real más inanición de scheduler.

5. **El nombre del hook en el encargo era correcto**, pero conviene registrar
   que `hooks/skill-router-prompt-suggest.sh` es archivo regular, no symlink
   (`readlink -f` devuelve el mismo path).

6. **"`hooks/**` es config protegida" — cierto, y más amplio de lo que sugería
   el encargo.** El guard bloquea por *mención del path en el comando*, no sólo
   por escritura: un `bash -x hooks/...` puramente de lectura, para tracear,
   también quedó bloqueado y necesitó el prefijo. Vale saberlo antes de asumir
   que sólo aplica al editar.

7. **`timeout(1) no existe en esta máquina** (`command not found` en zsh). Para
   acotar corridas hay que usar otra cosa; no es GNU coreutils.
