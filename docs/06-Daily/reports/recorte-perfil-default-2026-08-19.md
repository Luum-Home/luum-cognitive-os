<!-- SCOPE: os-only -->
# Recorte del perfil `default` — cuatro hooks fuera del hot path

> Fecha: 2026-08-19 · Alcance: `cognitive-os.yaml`, `scripts/_lib/settings-driver-claude-code.sh`,
> `templates/security-profiles/{minimal,standard,paranoid}.json`, `scripts/apply-efficiency-profile.sh`.
> No se borró ningún hook: los cuatro siguen proyectados en `full`.
> Toda cifra de este informe sale de los comandos del `## Antes y después, medido`.

## Resumen ejecutivo

- Salieron **4 hooks** del perfil `default`, todos del camino sincrónico por tool call:
  `tool-sequence-capture`, `aci-observation-capture`, `rate-limit-drain`,
  `post-git-orphan-notifier`. Los cuatro siguen encendidos en `full`.
- **Procesos por tool call (hooks sincrónicos, los que el operador espera):**
  **Bash 19 → 15** (−21 %) · **Edit 28 → 26** · **Read 14 → 12** (−14 %).
  Comandos de hook proyectados en total: **162 → 158**.
- Sobre 283.094 filas del wrapper de timing, los cuatro suman **17.186 s**, el
  **15,0 %** de todo el tiempo de hook sincrónico del sistema.
- **Lo que pierde el operador en `default`:** propuestas automáticas de skills
  nuevas, el corpus ACI, y el aviso automático de commits huérfanos tras un
  rebase/reset (la detección sigue disponible a pedido).
- **No saqué ninguna guarda de daño irreversible.** `destructive-git-blocker`,
  `destructive-rm-blocker`, `secret-detector` y `protected-config-write-guard`
  siguen igual.
- **`quality-duplicates` NO es el 85 % del `Stop` que sufre el operador: ya está
  `async: true`.** Ver sección propia — la recomendación cambia de sentido.

## Correcciones a las premisas del encargo

1. **`quality-duplicates` ya corre `async: true`, así que no bloquea el `Stop`.**
   El encargo dice «23 hooks / 276 s, y el 85 % es quality-duplicates (243 s por
   corrida)». Los 235 s de media por corrida se confirman (318 corridas,
   74.722 s). Lo que no se sostiene es que sean fricción *percibida*: en
   `.claude/settings.json` la entrada lleva `"async": true`, igual que otros 8 de
   los 23 hooks de `Stop`. El operador espera **14 hooks sincrónicos**, no 23, y
   `quality-duplicates` no está entre ellos. Su costo es **carga de máquina**, no
   espera — que con la máquina en load 100-180 no es poca cosa, pero es otro
   problema y se arregla distinto.
2. **`hook-health.jsonl` no sirve para afirmar «este hook nunca corrió»: lo emite
   cada hook por su cuenta y la mayoría no lo emite.** `cosd-auth-guard`,
   `lethal-trifecta-gate`, `session-heartbeat`, `aci-observation-capture`,
   `rate-limit-drain` y otros tienen **0 filas en 92.650**, y sin embargo el
   wrapper (`hook-timing.jsonl`, 283.094 filas) los muestra con 9.500-12.400
   corridas cada uno. Todas mis decisiones de recorte usan `hook-timing`, que lo
   emite el wrapper y por eso es completo. Si algún censo previo concluyó
   «actividad cero» leyendo `hook-health`, esa conclusión hay que rehacerla.
3. **Los moldes no son cuatro: son cinco.** Además de `cognitive-os.yaml`, las tres
   plantillas y el driver en bash, `scripts/apply-efficiency-profile.sh` tiene
   **dos superficies hardcodeadas** que describen el perfil: la lista de sanidad de
   ~120 hooks (líneas 186-208) y los `echo` del resumen (líneas 279-280). Las dos
   quedaban mintiendo tras el recorte. Las corregí; sin eso, el arreglo eran cuatro
   moldes de cinco.
4. **Las tres plantillas registran `rate-limiter.sh` y ninguna registra su drain;
   el driver hace exactamente lo contrario.** En `default` el driver proyecta
   `rate-limit-drain` sin productor (`grep -c 'rate-limiter' .claude/settings.json`
   = 0, consistente con `rules/rate-limiting.md`); las plantillas proyectan el
   limitador sin drenaje, o sea trabajo encolado que nadie saca —
   `.cognitive-os/rate-limit-queue.jsonl` tiene 82 filas paradas. Es el defecto que
   el encargo describe, pero al revés de como lo esperaba: no es que un molde tenga
   el arreglo y los otros no, es que **los moldes se contradicen entre sí**.
   Alineé el par: `minimal`/`standard` sin ninguno de los dos, `paranoid` con los
   dos, driver `full` con los dos.
5. **`rules/rate-limiting.md` dice que el limitador «no está registrado» y eso vale
   solo para el `settings.json` generado.** Está registrado en las tres plantillas,
   así que cualquier corrida de `set-security-profile.sh` lo encendía. Tras este
   cambio la afirmación de la regla pasa a ser cierta también para `minimal` y
   `standard`. Queda pendiente decidir `paranoid`.
6. **`protected-config-write-guard` falla en falso sobre comandos de solo lectura.**
   El encargo lo cuenta como fricción (1.678 bloqueos / 14 %) pero lo trata como
   costo de la protección. En esta tarea me bloqueó **3 veces, las 3 sobre lecturas**:
   un `grep -rl` que solo nombraba `hooks/` en el patrón y dos `python3 -c` que solo
   hacían `json.load('.claude/settings.json')`. El guard mira el texto del comando,
   no si escribe. No lo saqué —protege de daño real— pero el 14 % no es el precio de
   la protección: buena parte es un parser que confunde leer con escribir.
7. **No pude usar el número «~22 procesos por tool call» como está.** Es un promedio
   sobre todos los tipos de tool call, y mezcla sincrónicos con asincrónicos. Lo
   recontá por tipo de herramienta y separando sync de async, que es lo que el
   operador siente: Bash 21 totales / **19 sincrónicos**. Ese es el número contra el
   que mido.

## Qué salió y qué pierde el operador

| Hook | Evento | Corridas | Tiempo total | ms/corrida | Qué pierde `default` |
|---|---|---|---|---|---|
| `tool-sequence-capture` | PostToolUse `*` | 11.847 | 5.220,1 s | 441 | `tool-sequences.jsonl` deja de crecer. Su único consumidor es `cos_lib/skill_synthesizer.py`, que propone skills nuevas a partir de secuencias repetidas. Se pierde esa propuesta automática. Comodidad, no protección. |
| `post-git-orphan-notifier` | PostToolUse `Bash` | 9.550 | 4.570,6 s | 479 | El aviso **automático** de commits huérfanos tras un rebase/reset. La detección sigue: `scripts/orphan_commit_scan.py` lee el reflog y `git fsck --unreachable` directo, no depende del JSONL del hook. Pasa de automático a a-pedido. |
| `rate-limit-drain` | PostToolUse `Bash` | 9.550 | 4.128,1 s | 432 | **Nada.** Drena la cola que llena `rate-limiter.sh`, que el driver proyecta solo en `full`. En `default` su productor está apagado: pagaba 432 ms por cada Bash para mirar una cola que nadie escribe. |
| `aci-observation-capture` | PostToolUse `*` | 11.846 | 3.267,1 s | 276 | El corpus ACI de `.cognitive-os/artifacts/aci` deja de crecer. Fuera de `hooks/`, la única mención en el repo es `manifests/state-retention.yaml`, que es una política de retención — dice cuánto guardarlo, no lo lee. Sin consumidor programático. |

Criterio de orden: los cuatro **corren en cada tool call** y **ninguno interrumpe**
(cero bloqueos, cero pedidos de confirmación). Entran justo en la categoría que el
encargo pone al final de la lista de valor: observan y escriben a un archivo.
`rate-limit-drain` es más fuerte que eso: ni siquiera observa algo que exista.

## Qué NO saqué y por qué

- **`protected-config-write-guard`, `secret-detector`, `destructive-rm-blocker`,
  `destructive-git-blocker`.** Protegen de daño irreversible. `destructive-git-blocker`
  bloquea de verdad (144 `exit 2` medidos). Sacarlos baja el número y saca la
  protección: es `full` invertido, no un recorte.
- **`bash-hot-path-dispatcher`** (10.027 corridas, 16.167 s, el segundo costo del
  sistema). Es caro, pero es el que enruta a los bloqueadores destructivos y ya es
  condicional: solo abre el abanico de 29 hijos cuando el comando es `git commit`,
  `rm`, etc. Sacarlo apaga toda la batería de guardas.
- **`result-truncator`** (9.513 corridas). Protege el contexto del operador de una
  salida gigante. Beneficio directo y visible.
- **`error-learning`** (298 ms). Barato y es el insumo del auto-repair.
- **`context-watchdog`, `subagent-budget-enforcer`, `private-mode-metrics-gate`,
  `rate-limit-detector`.** Los cuatro tienen consumidor vivo o son guardas de
  presupuesto/privacidad. Anoto que `subagent-budget-enforcer` corre en **cada** tool
  call (11.807 corridas, 4.590 s) para hacer cumplir un presupuesto de sub-agentes:
  parece que debería estar en el matcher `Agent`, no en `*`. No lo toqué — es un
  cambio de comportamiento, no un recorte de perfil, y merece su propio ticket.
- **`audit-id-enricher`** (9.722 corridas, 2.860 s). Es el siguiente candidato: solo
  enriquece `cost-events.jsonl`. Existe `scripts/backfill_cost_events.py`, que por el
  nombre reconstruiría lo perdido, pero **no lo corrí**, y no saco algo apoyándome en
  una recuperabilidad que no verifiqué. Queda nombrado, no cortado.

## quality-duplicates: la recomendación aparte

**Recomendación: no lo saques del `Stop`; apagale el trabajo, no el disparo — y
antes de eso, arreglá el ratchet o borrá el artefacto.**

Los hechos, recontados:

- **235 s de media por corrida** (318 corridas, 74.722 s acumulados). La cifra del
  encargo (243 s) se confirma dentro del ruido.
- **Es el 39,6 % de TODO el tiempo de hook medido** del sistema — más de lo que decía
  el encargo.
- **Pero corre `async: true`.** No es la espera del operador al cerrar sesión; es un
  proceso detached que sigue comiendo la máquina después. Con load 100-180, 235 s de
  CPU detached por cada `Stop` es una causa plausible de la saturación que infla todas
  las demás mediciones — incluido este mismo informe.
- Sus 245.704 hallazgos van a `latest.json`/`latest.md`, **gitignoreados y sin lector
  programático**, con el ratchet en `missing-baseline`.

Por qué **no** lo saqué por mi cuenta, más allá de que el encargo lo pidiera: sacarlo
del perfil no cambia lo que siente el operador (ya no lo espera) y sí apaga la única
señal de duplicación que existe. El costo real es de máquina, y el arreglo proporcional
es distinto: o el ratchet pasa a tener baseline y alguien lee la salida —y entonces los
235 s compran algo—, o no lo lee nadie y lo que sobra es el **trabajo**, no el hook.
Bajo `gates-sin-trampa`, un ratchet en `missing-baseline` es un supresor que no suprime
nada: hoy es gate por sensación, no por medición. **Decisión del operador**, en este
orden: (1) ¿alguien va a leer `latest.md`? Si no → borrar el artefacto y el hook juntos.
Si sí → (2) fijar baseline y meter la salida en algún flujo que la consuma; y (3) en
cualquiera de los dos casos, acotar el escaneo, porque 235 s por `Stop` en detached es
lo que está compitiendo con el trabajo del operador por la CPU.

## Antes y después, medido

**Bajo qué carga:** la máquina estuvo en load 100-180 durante toda la sesión. Por eso
**no reporto milisegundos de reloj como mejora**: reporto conteo de hooks por evento,
que es determinista y no depende de la carga. Los tiempos acumulados que sí cito salen
de 283.094 filas históricas del wrapper, no de un cronómetro de hoy.

Comando (mismo antes y después, sobre `.claude/settings.json` regenerado):

```bash
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python3 -c "
import json
d=json.load(open('.claude/settings.json'))
def fires(mt,t): return True if mt in ('','*') else t in mt.split('|')
print('TOTAL hook commands:', sum(len(g['hooks']) for gs in d['hooks'].values() for g in gs))
for tool in ['Bash','Edit','Read']:
    sy=asy=0
    for ev in ['PreToolUse','PostToolUse']:
        for g in d['hooks'][ev]:
            if not fires(g.get('matcher',''),tool): continue
            for h in g['hooks']:
                asy+=1 if h.get('async') else 0; sy+=0 if h.get('async') else 1
    print(f'{tool}: SYNC={sy} ASYNC={asy} TOTAL={sy+asy}')"
```

| Métrica | Antes | Después | Δ |
|---|---|---|---|
| Comandos de hook proyectados | 162 | **158** | −4 |
| **Bash — hooks sincrónicos** | **19** | **15** | **−4 (−21 %)** |
| Bash — total (sync+async) | 21 | 17 | −4 |
| **Edit — hooks sincrónicos** | **28** | **26** | **−2 (−7 %)** |
| Edit — total | 34 | 32 | −2 |
| **Read — hooks sincrónicos** | **14** | **12** | **−2 (−14 %)** |
| `Stop` — hooks sincrónicos | 14 | 14 | 0 (no toqué `Stop`) |

Tiempo acumulado eliminado, sobre 283.094 filas de `hook-timing.jsonl` (vivo + 9
rotados de `.cognitive-os/metrics/.archive/`):

```bash
.venv/bin/python3 - <<'PY'
import json,glob,gzip,collections
files=['.cognitive-os/metrics/hook-timing.jsonl']+sorted(glob.glob('.cognitive-os/metrics/.archive/hook-timing-*'))
CUT={'tool-sequence-capture','aci-observation-capture','rate-limit-drain','post-git-orphan-notifier'}
tot=qd=0.0; cut=collections.Counter(); runs=collections.Counter()
for f in files:
    op=gzip.open if f.endswith('.gz') else open
    for l in op(f,'rt',errors='replace'):
        try: r=json.loads(l)
        except: continue
        h=(r.get('hook') or '').split('/')[-1]; d=float(r.get('duration_ms') or 0); tot+=d
        if h=='quality-duplicates': qd+=d
        if h in CUT: cut[h]+=d; runs[h]+=1
s=sum(cut.values())
print(f"total {tot/1000:,.0f} s | quality-duplicates(async) {qd/1000:,.0f} s | sync {(tot-qd)/1000:,.0f} s")
print(f"removido {s/1000:,.0f} s = {s/(tot-qd)*100:.1f}% del tiempo sincronico")
for k,v in cut.most_common(): print(f"  {k:30s} {runs[k]:6d} {v/1000:8.1f}s {v/runs[k]:4.0f}ms")
PY
```

Resultado: **17.186 s removidos = 15,0 %** del tiempo de hook sincrónico
(114.311 s excluyendo `quality-duplicates`, que es async).

Gates:

```
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 bash scripts/apply-efficiency-profile.sh default
  -> Applied profile 'default': 158 hook commands in settings.json
.venv/bin/python3 scripts/hook_quality_audit.py --check
  -> hook-quality: OK (200 hooks, 200 syntax checks)
/bin/bash -n scripts/_lib/settings-driver-claude-code.sh   -> OK (bash 3.2.57)
/bin/bash -n scripts/apply-efficiency-profile.sh           -> OK (bash 3.2.57)
```

**Ruido preexistente que NO introduje y NO arreglé:** la lista de sanidad de
`apply-efficiency-profile.sh` emite ~19 `Warning: expected hook ... missing from
settings.json` en cada corrida de `default`. Son hooks que se alcanzan **por el
dispatcher**, no por `settings.json` (`destructive-git-blocker`, `direct-main-guard`,
`conflict-marker-guard`, …), y el chequeo es un `grep` sobre `settings.json` que no
sabe del dispatcher. Es un aviso que no se puede satisfacer, o sea ruido permanente.
Sí saqué de esa lista los 3 que yo mismo dejé de proyectar, para no **agregar** ruido.
Arreglar el chequeo entero es otro trabajo.

## Los cuatro moldes, verificados

Cinco superficies, no cuatro (ver corrección 3). Estado tras el cambio:

| # | Molde | Qué se tocó | Verificación |
|---|---|---|---|
| 1 | `cognitive-os.yaml` | `efficiency.profiles.default.description`: el conteo decía «~29 standard hooks», ahora dice 158 comandos proyectados / 15 sincrónicos por Bash | `grep -n 'trimmed 2026-08-19' cognitive-os.yaml` |
| 2 | `scripts/_lib/settings-driver-claude-code.sh` | `post_all` y `post_bash` pasan a tener rama `if [ "$PROFILE" = "full" ]` — los 4 hooks se proyectan solo en `full` | `/bin/bash -n` OK; el `settings.json` regenerado no contiene ninguno de los 4 |
| 3 | `templates/security-profiles/minimal.json` | −4 entradas: `rate-limiter`, `post-git-orphan-notifier`, `tool-sequence-capture`, `aci-observation-capture` | 117 → 113 comandos |
| 4 | `templates/security-profiles/standard.json` | las mismas −4 | 155 → 151 comandos |
| 5 | `templates/security-profiles/paranoid.json` | **+1**: `rate-limit-drain` en `PostToolUse:Bash`, para emparejar el `rate-limiter` que ya registraba y que quedaba sin drenaje | 171 → 172 comandos |

Comando que prueba que **ningún** molde de nivel `default` volvió a inyectar los 4:

```bash
for f in .claude/settings.json templates/security-profiles/minimal.json templates/security-profiles/standard.json; do
  printf '%-52s ' "$f"
  COS_ALLOW_PROTECTED_CONFIG_WRITE=1 grep -c -E 'tool-sequence-capture|aci-observation-capture|rate-limit-drain|post-git-orphan-notifier|rate-limiter\.sh' "$f"
done
```

Debe dar `0` en las tres. `paranoid.json` y el driver bajo `PROFILE=full` deben dar
distinto de cero: ahí los cuatro siguen vivos, que es el punto — esto es un recorte de
perfil, no un borrado.

## Anexo — el gate que mi propio cambio puso en rojo

`tests/contracts/test_orphan_hooks.py::test_no_orphan_hooks` falló por mi cambio,
con los **3** hooks que saqué (el cuarto, `aci-observation-capture.sh`, ya estaba
contemplado). Causa: el test define «registrado» como *aparece en
`.claude/settings.json`*, o sea **solo la proyección `default`**. Con esa
definición, cualquier hook que exista únicamente en `full` es huérfano por
construcción — no porque esté muerto.

No lo tapé moviendo un baseline. Usé la opción (b) que el propio test ofrece,
`tests/contracts/EXCLUDED_HOOKS.txt`, con la categoría y el motivo escritos, y hay
**precedente exacto en el mismo archivo**: `aci-observation-capture.sh` ya figuraba
como `CONDITIONAL: ... not projected into default .claude/settings.json for this
profile`. Los tres nuevos usan la misma categoría y dicen dónde sí se proyectan.
Verificado: `7 passed`.

**Lo que queda abierto (no es verde barato, es deuda declarada):** el test no sabe
leer la rama `PROFILE=full` del driver ni las plantillas, así que cada hook que
pase a ser full-only va a necesitar una línea a mano en el whitelist. Enseñarle al
test a resolver las dos proyecciones lo arreglaría de raíz y dejaría de pedir
excepciones. Es un cambio en el test, no en el perfil, y no lo hice acá.

**Otros 5 fallos de `tests/contracts/` (853 passed, 6 failed, 780 s):**
`test_p95_hook_latency`, `test_portable_ai_completion` (`assert 864 == 862`),
`test_portable_ai_overlay`, `test_primitive_harness_partial_ratchets`,
`test_ram_ceiling` (disco). **No establecí baseline previo al cambio**, así que no
puedo afirmar que sean preexistentes; lo que sí verifiqué es que ninguno de los
cuatro hooks ni las rutas de moldes aparecen en las 780 s de salida
(`grep -c -E 'tool-sequence-capture|aci-observation-capture|rate-limit-drain|post-git-orphan-notifier|security-profiles|settings-driver'` = **0**).
Los dos `portable_ai` cuentan artefactos generados y hay dos agentes más escribiendo
en este mismo worktree. **Es lo primero que debería mirar una persona.**
