# El audit de retención ahora chequea el techo global

**Fecha:** 2026-08-18
**Alcance:** `scripts/state_retention_audit.py`, `manifests/state-retention.yaml`,
`tests/contracts/test_ram_ceiling.py`, `tests/unit/test_state_retention_audit.py`

## El defecto

El audit chequeaba cada superficie contra **su** tope y nunca las sumaba. Con 14
superficies todas adentro de su límite, reportaba `findings=0` sin importar cuánto
pesara el árbol entero. El manifiesto ya tenía escrito el razonamiento —"a 20-entry
pool silently permits ~800 MiB against the 400 MiB .cognitive-os ceiling"— pero
ninguna línea de código lo implementaba.

## Uso real por superficie

Medido con bloques asignados (`st_blocks*512`), que es lo que cuenta `du -sk`:

```bash
.venv/bin/python scripts/state_retention_audit.py --json --no-metrics \
  | .venv/bin/python -c 'import json,sys; r=[x for x in json.load(sys.stdin)["surfaces"] if x["kind"]=="budget"][0]; print(json.dumps(r,indent=2))'
```

| Superficie | Entradas | MiB | Tope propio |
|---|---:|---:|---|
| auto-pre-agent-stashes | n/a (git) | 0.0 | sin tope de bytes |
| task-claims-ledger | 1 | 0.0 | sin tope de bytes |
| active-tasks-ledger | 1 | 0.0 | sin tope de bytes |
| agent-bus-directories | 14 | 0.1 | sin tope de bytes |
| metrics-jsonl | 122 | 53.8 | `max_count: unbounded-with-rotation` |
| performance-ledger-artifacts | 1 | 0.7 | sin tope de bytes |
| performance-ledger-latest-report | 0 | 0.0 | sin tope de bytes |
| copy-only-checkpoints | 4 | 83.5 | `max_total_mib: 120` |
| auto-pre-agent-snapshot-dirs | 5 | 41.8 | `max_total_mib: 80` |
| quality-duplicate-reports | 2 | 1.3 | sin tope de bytes |
| run-flight-recorder-traces | 0 | 0.0 | sin tope de bytes |
| run-flight-recorder-latest-report | 0 | 0.0 | sin tope de bytes |
| runtime-locks | 6 | 0.0 | sin tope de bytes |
| preserve-worktrees | n/a (git) | 0.0 | sin tope de bytes |
| **suma de superficies registradas** | | **181.2** | |
| **bytes sin superficie registrada** | | **208.8** | |
| **`.cognitive-os` completo** | | **390.0** | techo 400 |

Contraste: `du -sm .cognitive-os` → `390`. `du -sk` → `398636` KiB = 389.3 MiB.

Dato que decide el diseño: **12 de las 14 superficies no declaran tope de bytes**.
"Cada superficie está dentro de su tope" suena a control y no lo es — de esas 12,
`metrics-jsonl` está literalmente declarada `unbounded-with-rotation`. Los topes
por superficie nunca pudieron sumar un límite.

## De dónde sale el techo y dónde vive ahora

**Antes:** el número 400 estaba hardcodeado en `tests/contracts/test_ram_ceiling.py`
(`COS_VITALS_DISK_CEILING_MIB`, default `"400"`), y el manifiesto lo repetía en
prosa. Dos copias.

**Ahora:** vive en `manifests/state-retention.yaml`, bloque `global_budget`:

```yaml
global_budget:
  path: .cognitive-os
  max_total_mib: 400
  max_unregistered_mib: 210
  env_override: COS_VITALS_DISK_CEILING_MIB
  measurement: allocated-blocks
```

`test_ram_ceiling.py` ahora lee `global_budget.max_total_mib` del manifiesto en vez
de hardcodearlo, y `COS_VITALS_DISK_CEILING_MIB` sigue siendo el override que mueve
a los dos consumidores a la vez. El manifiesto es el lugar correcto y no el test
porque quien enforza el número ahora son dos cosas (el audit y el test), y ninguna
de las dos puede ser fuente de la otra.

### Unidad de medida: no es un detalle

El techo se asserta sobre `du -sk`, o sea **bloques asignados**. El audit ya tenía
`path_bytes()`, que suma **tamaño aparente** (`st_size`). Sobre este árbol la
diferencia es 350.1 vs 389.3 MiB — **39 MiB, casi el 10% del techo**. Medir el total
con `path_bytes` habría hecho que el audit diera verde sobre el mismo commit en que
el gate da rojo. Por eso el chequeo global usa `allocated_bytes()` (`st_blocks*512`).

Deuda que dejo nombrada, no arreglada: los `max_total_mib` **por superficie** siguen
midiéndose en tamaño aparente. Cambiar `path_bytes` movería hallazgos existentes de
otras superficies y es una decisión aparte.

## Qué cuenta y qué no para el total

Cuenta **todo `.cognitive-os`**, no la suma de las superficies registradas.

Sumar solo las registradas habría sido el verde barato más difícil de ver: da
**181.2 MiB contra un techo de 400**, o sea verde permanente, mientras el árbol real
está en 390. La mitad del techo se gasta en estado que ningún reaper reclama.

Las superficies `git:refs/stash` y `git:worktree` no aportan bytes de disco: no
tienen path en el árbol.

Los 208.8 MiB fuera de superficie registrada son un hallazgo aparte —
`global-unregistered-bytes`, WARN, con tope propio `max_unregistered_mib: 210`.
Las áreas más pesadas:

```
46.6 MiB  .cognitive-os/artifacts/aci
39.3 MiB  .cognitive-os/tasks/control-plane-remediation.jsonl
23.6 MiB  .cognitive-os/reports/test-runs
14.5 MiB  .cognitive-os/external-source-cache/gentle-ai
11.0 MiB  .cognitive-os/metrics/.archive
```

El 210 es un ratchet puesto sobre la realidad medida (208.8), no un colchón: tiene
~1 MiB de aire y **va a disparar en días**. Eso es a propósito. La respuesta correcta
cuando dispare es registrar esas superficies y bajar el número, no subirlo — y el
motivo de cualquier movimiento va escrito en el `rationale` del bloque. Si el
operador prefiere no tener ese ratchet, se saca `max_unregistered_mib` del manifiesto
y el chequeo se apaga solo; el número de atribución (`unregistered_mib`) se sigue
reportando igual como dato.

## Qué dice el hallazgo cuando no hay a quién culpar

`global-budget-exceeded`, nivel BLOCK, mismo formato que los demás y contado en
`summary.finding_count` (no es una segunda clase de hallazgo). Cuando ninguna
superficie viola su propio tope, `attributable_surfaces` viene vacío y el mensaje lo
dice sin rodeos: *"tree over the global ceiling while every registered surface is
inside its own cap: no single surface is at fault, so this is a manifest-level
decision"*. Ofrece las dos salidas reales, y la primera viene con la advertencia
puesta adentro del texto:

1. reconciliar la retención por superficie contra el uso **medido** — bajarle el tope
   a una superficie por debajo de lo que usa no reclama nada, solo le deja trabajo
   real de borrado al próximo reaper;
2. subir `global_budget.max_total_mib` con el motivo escrito en su `rationale`.

El chequeo global corre solo en el audit completo. Con `--surface`, `--auto-safe` o
`--repair-before-block` se salta: esos modos seleccionan subconjuntos para reparar, y
un BLOCK del árbol entero levantado desde un path de reparación haría fallar un
preflight que no puede reparar.

## La prueba contra el código viejo

Árbol sintético en `tmp_path`: dos superficies de 1.5 MiB cada una, tope propio 2 MiB
cada una (adentro), techo global 2 MiB (el total de 3.0 lo excede). Mismo manifiesto,
mismo árbol, los dos scripts:

```bash
SP="$(mktemp -d)"; git show HEAD:scripts/state_retention_audit.py > "$SP/old_audit.py"
# (fixture y corrida: ver tests/unit/test_state_retention_audit.py::_budget_tree)
OLD (HEAD)           findings=0 exit=0
NEW (working tree)   findings=1 exit=2
```

Tests agregados en `tests/unit/test_state_retention_audit.py`:

- `test_global_budget_flags_tree_over_ceiling_when_every_surface_is_within_cap` —
  el caso del defecto: todas adentro, total excedido, `findings=1`, y asserta que
  las filas por superficie siguen limpias (o sea que el hallazgo es del total).
- `test_global_budget_silent_when_tree_is_under_ceiling` — el reverso, `findings=0`.
- `test_global_budget_reports_bytes_no_registered_surface_owns`
- `test_global_budget_ceiling_comes_from_the_manifest_not_the_script`
- `test_repo_manifest_declares_the_global_budget_the_ram_ceiling_test_reads`

Ninguno toca `.cognitive-os` real: todo se monta en `tmp_path`.

```bash
.venv/bin/python -m pytest tests/unit/test_state_retention_audit.py tests/contracts/test_ram_ceiling.py -p no:cacheprovider -q
```

## Qué del encargo era falso

**El total no está excedido.** El encargo abre con `.cognitive-os total: 414 MiB` y
"hoy da verde con el total excedido". Medido hoy: **390.0 MiB** (`du -sm` → 390,
`du -sk` → 389.3). El propio encargo anticipa ~387 por los ~27 MiB reclamados, así
que el 414 es de antes de esa reclamación, pero conviene dejarlo dicho: **no pude
reproducir una violación real del techo**, y el audit nuevo reporta `findings=0`
sobre el árbol real, correctamente. El defecto —no había suma— era real igual, y se
prueba con el árbol sintético.

**`manifests/state-retention.yaml` no es config protegida.** El encargo dice "puede
ser config protegida" y da el token de aprobación. No hizo falta: los globs de
`manifests/protected-config-write-policy.yaml` cubren `manifests/*security*.yaml` y
`manifests/credential-safe-scripts.yaml`, no éste. Verificado leyendo la policy, y
las escrituras pasaron sin token y sin entrada nueva en el ledger de bypass.

**"El techo vive en el test" era cierto pero incompleto.** El test se contradecía a
sí mismo: el docstring decía `COS_VITALS_DISK_CEILING_MIB default 200` mientras el
código usaba `"400"`. Arreglado de paso al mover el número. Queda pendiente el paso
que pide la norma de session-close: agregar el claim correspondiente a
`manifests/documentation-truth-claims.yaml` — no lo toqué porque hay tres agentes
activos y ese manifiesto está fuera del alcance que me dieron.

**"Cada superficie está dentro de su tope" mide menos de lo que suena.** Solo 2 de
14 superficies declaran tope de bytes. Para las otras 12 la frase es vacía: estar
dentro de un `max_count` no dice nada sobre disco, y `metrics-jsonl` (53.8 MiB, la
segunda más pesada) está declarada `unbounded-with-rotation`.

**El cuarto verde barato, que el encargo no listó:** sumar las superficies
registradas parece la lectura natural de "sumar el uso real", y da 181 MiB contra
400 — verde para siempre, sin medir el manifiesto contra sí mismo, así que no cae en
el segundo verde barato que sí estaba listado. Pero deja 208 MiB invisibles.
