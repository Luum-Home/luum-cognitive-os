# Forense: la superficie de registro de un hook

Fecha: 2026-08-20 · Alcance: censo estático (grep, YAML, git). No se corrió
ninguna suite. Todo número de este informe trae el comando que lo produce.

Instrumento nuevo que deja este trabajo: `scripts/hook_surface_census.py`.

## Resumen ejecutivo

Hay **15 superficies** donde un hook puede o debe estar nombrado: 1 de
declaración (`cognitive-os.yaml`), 6 de proyección (driver de CC, los tres
artefactos por arnés, el dispatcher, los perfiles de seguridad), 4 de política
(policy de proyección, matriz de capacidades, schemas por arnés, presupuesto de
vitalidad), 3 de "no registrado a propósito" y 1 de resumen para humanos.
**Once se mantienen a mano.**

La deriva concreta hoy: `hook_projection_drift_audit.py` reporta **5 entradas
perdidas** en Claude (el techo declarado en `manifests/harness-hook-projection-policy.yaml`
es `max_lost_entries: 1`). El censo por superficie muestra que **ninguna de las
cinco es realmente indeclarada**: cuatro están gateadas por `PROFILE=full` en
código shell del driver y la quinta —`publication-safety.sh`, el "caso vivo" del
encargo— está declarada desde 2026-05-04 en
`manifests/hook-registration-classification.yaml` con status, rationale y
next_action. El gate mide sus propios puntos ciegos.

Costo real de agregar un hook, medido sobre `e11719383`: **6 archivos de registro
tocados a mano**, y aun así los artefactos de codex y opencode quedaron sin los
dos hooks en HEAD.

Por qué el driver de Claude Code no lee el yaml: **nunca lo leyó**. Nació así en
`387c9fc56` (2026-04-30), en el mismo commit que implementó ADR-064 y cuyo
mensaje afirma "Reads harness.hooks". No hay decisión escrita: hay una
afirmación falsa desde el día uno.

## Correcciones a las premisas del encargo

1. **"~200 entradas nombrando ~190 scripts, y ~184 aparecen en el driver"** —
   recontado hoy: **202 entradas, 192 scripts distintos, 6 ausentes del código
   del driver** (o sea 186 presentes). Los números de la cabecera del driver
   eran correctos el 2026-08-19 y ya se movieron; la cabecera es una foto, no un
   contador.

   ```
   .venv/bin/python -c "
   import yaml,pathlib,re
   h=(yaml.safe_load(open('cognitive-os.yaml')) or {}).get('harness',{}).get('hooks',{})
   scripts={v['script'] for v in h.values() if isinstance(v,dict) and v.get('script')}
   code='\n'.join(l for l in pathlib.Path('scripts/_lib/settings-driver-claude-code.sh').read_text().splitlines() if not re.match(r'\s*#',l))
   print(len(h), len(scripts), [s for s in sorted(scripts) if s not in code])"
   # 202 192 ['hooks/auto-refine.sh','hooks/auto-verify.sh','hooks/concurrent-write-guard-codex-proxy.sh','hooks/dod-gate.sh','hooks/publication-safety.sh','hooks/task-completed.sh']
   ```

2. **"los drivers de bare, codex y opencode sí leen el yaml (6, 5 y 15
   referencias)"** — la lectura es cierta; el 15 no. Ocurrencias reales:
   bare 6, codex 5, opencode 6. Y de esas, las que están fuera de comentarios
   son 3, 2 y 3: el resto es documentación.

   ```
   for f in bare codex opencode claude-code; do printf "%s: " "$f"; \
     grep -o "cognitive-os.yaml" scripts/_lib/settings-driver-$f.sh | wc -l; done
   # bare: 6  codex: 5  opencode: 6  claude-code: 10
   grep -vE '^\s*#' scripts/_lib/settings-driver-claude-code.sh | grep -c "cognitive-os.yaml"
   # 1  (un test de existencia de archivo para ubicar PROJECT_DIR, no una lectura del registro)
   ```

   El driver de Claude Code menciona el yaml **10 veces, más que cualquier
   hermano**, y no lo lee ni una. La densidad de menciones no mide lectura.

3. **"al menos seis mecanismos de omisión"** — son **siete**, y el séptimo es el
   que hoy rompe el ratchet: el condicional `if [ "$PROFILE" = "full" ]` escrito
   en shell adentro del driver. Hay tres (`grep -n 'PROFILE" = "full"'` → líneas
   301, 408, 445); el de la 301 gatea un grupo que el policy manifest sí declara,
   los de 408 y 445 no los declara nadie. Ningún gate puede leer un `if` de bash.

4. **"`publication-safety.sh` está declarado con `scope: both` sin opt-out y no
   corre"** — la primera mitad es cierta y la segunda también, pero la
   conclusión que se le colgó ("nada declara por qué") es falsa. Está en
   `manifests/hook-registration-classification.yaml` desde 2026-05-04:
   `status: conditional_opt_in`, con rationale y next_action. El gate que "ya lo
   detecta" lo detecta porque no lee ese manifest.

5. **"cinco superficies / seis mecanismos… tres cifras distintas y ninguna se
   sostuvo entera"** — la razón de fondo no es que alguien contó mal: es que
   **cada instrumento cuenta una cosa distinta y ninguno compara con el otro**.
   El drift audit cuenta ENTRADAS del yaml; el classifier cuenta ARCHIVOS en
   disco; el driver-literal cuenta LITERALES de shell. 6, 5 y 13 son las tres
   respuestas correctas a tres preguntas distintas.

6. **El encargo dice que el instrumento es opcional ("si construís uno").** Lo
   construí porque sin él no se podía cerrar la pregunta 2: las dos auditorías
   existentes se contradicen sobre las mismas cinco entradas y ninguna es
   árbitro de la otra.

## Las superficies, una por una: quién escribe, quién lee, qué pasa si falta

Comando que produce la fila "quién lee" de cada una:
`git grep -ln "<superficie>" -- scripts lib cos_lib hooks tests packages manifests`

| # | Superficie | Escribe | Lee | Si falta |
|---|---|---|---|---|
| 1 | `cognitive-os.yaml > harness.hooks` | humano | drivers bare/codex/opencode (`yaml.safe_load`), ≥6 auditorías | el hook no llega a codex/opencode/bare; en Claude **no pasa nada**: el driver no la lee |
| 2 | `scripts/_lib/settings-driver-claude-code.sh` | humano (235 literales `"hooks/…"`) | `scripts/apply-efficiency-profile.sh` | el hook **nunca corre en Claude Code**, aunque esté en el yaml |
| 3 | `.claude/settings.json` | generado por (2) | runtime de Claude Code, `test_orphan_hooks.py`, `derived_artifact_gate.py` | no corre |
| 4 | `.codex/hooks.json` | generado por driver codex desde (1) | arnés codex | no corre en codex |
| 5 | `.opencode/cos-hooks.json` | generado por driver opencode desde (1) | opencode vía `experimental.cognitive_os_hooks` | no corre en opencode |
| 6 | `hooks/bash-hot-path-dispatcher.sh` | humano | entrada única de PreToolUse:Bash en (3) | 27 hooks dependen de esta lista y de nada más |
| 7 | `templates/security-profiles/{minimal,standard,paranoid}.json` | humano | `hooks/self-install.sh`, `scripts/audit_gate_registration.py`, `scripts/audit_killswitch_activation.py` | el perfil de seguridad no lo instala |
| 8 | `manifests/harness-hook-projection-policy.yaml` | humano | `hook_projection_drift_audit.py`, `hook_surface_classifier.py`, `scripts/cos-patch-release` | se pierde el contrato anti-deriva del hot path y el ratchet |
| 9 | `manifests/harness-driver-capabilities.yaml` | humano | drivers bare/opencode, `harness_parity_audit.py`, `hook_projection_drift_audit.py` | una ausencia legítima por límite del arnés pasa a contarse como pérdida |
| 10 | `manifests/{claude-code,codex,opencode}-hooks-schema.yaml` | humano | `test_claude_code_hooks_schema_conformance.py`, `proof-event-cadence-gate.sh`, `cos_init.py` | el evento/payload no tiene contrato verificable |
| 11 | `tests/contracts/EXCLUDED_HOOKS.txt` (125 entradas) | humano | `test_orphan_hooks.py`, `hook_registration_audit.py`, `aspirational_audit.py`, `hook_surface_classifier.py` | un hook no registrado rompe el test de huérfanos |
| 12 | `hooks/_lib/registration-allowlist.txt` (179) | humano | `hook_surface_classifier.py` (ratchet) | sube el ratchet de no clasificados |
| 13 | `manifests/hook-registration-classification.yaml` (106) | humano | ≥10 lectores: `audit_gate_registration.py`, `check_hook_registration.py`, `runtime_hook_reality.py`, `primitive-coherence-audit.py`, `hook_surface_classifier.py`, tests | queda un hook sin status/rationale/next_action |
| 14 | `manifests/hook-vitality-budget.yaml` | humano | `scripts/hook_vitality_audit.py` | el hook no tiene presupuesto de latencia |
| 15 | bloque `echo` de `scripts/apply-efficiency-profile.sh` | humano | **solo personas** | el resumen que ve el operador miente por omisión |

**Superficies que nadie lee programáticamente: una** (la 15). No es deuda
gratis: es el texto que el operador toma como inventario cuando aplica un
perfil, y se actualiza a mano en el mismo commit que las demás.

**El caso raro es el 2.** Es la única superficie *hand-written* que es fuente de
verdad de un artefacto generado, en un repo donde las otras tres proyecciones se
derivan de (1). No es una superficie más: es la que hace que (1) sea, para
Claude, un documento.

## La deriva de hoy, con la lista

```
COS_ALLOW_PROTECTED_CONFIG_WRITE= .venv/bin/python scripts/hook_projection_drift_audit.py --json
# claude   189 projected /  8 by-design / 5 LOST
# codex    130 projected / 72 by-design / 0 LOST
# opencode  70 projected /132 by-design / 0 LOST
```

Las cinco, y lo que las nombra (`scripts/hook_surface_census.py`):

| Entrada | yaml | driver (código) | settings.json | dispatcher | perfiles seg. | ledgers |
|---|---|---|---|---|---|---|
| `aci-observation-capture.sh` | sí | sí (`PROFILE=full`) | no | no | sí | allowlist, EXCLUDED |
| `tool-sequence-capture.sh` | sí | sí (`PROFILE=full`) | no | no | sí | allowlist, EXCLUDED |
| `rate-limit-drain.sh` | sí | sí (`PROFILE=full`) | no | no | sí | allowlist, EXCLUDED |
| `post-git-orphan-notifier.sh` | sí | sí (`PROFILE=full`) | no | no | sí | EXCLUDED |
| `publication-safety.sh` | sí | **solo en un comentario** | no | no | no | classification |

Entonces la deriva **real** es esta, y es otra que la que el gate reporta:

- **0 hooks sin ninguna declaración.** Las cinco tienen razón escrita en algún
  lado. El ratchet `max_lost_entries: 1` está en rojo (5 > 1) por un cambio en
  la *forma* de declarar, no por deuda nueva.
- **4 hooks declarados en una superficie que ningún gate lee**: el condicional
  `PROFILE=full` en shell del driver (ADR-093, trim del 2026-08-19, commit
  `376976744`). El drift audit sabe leer `profiles:` del yaml —tres entradas lo
  usan— pero no sabe leer un `if` de bash.
- **1 hook declarado en una superficie que ese gate tampoco lee**
  (`hook-registration-classification.yaml`), y que además el classifier "ve"
  por el motivo equivocado.

La deriva **entre las dos auditorías** es 5/5: sobre las mismas cinco entradas,
`hook_projection_drift_audit.py` dice `lost` y `hook_surface_classifier.py` dice
`profile_gated`. Para `publication-safety.sh` el classifier acierta por error: lo
marca `profile_gated` porque su chequeo `name in driver` corre sobre el texto
crudo del driver, y el único lugar donde ese nombre aparece ahí es **la cabecera
que documenta su ausencia**. Es exactamente la trampa que el drift audit
documenta en su propio docstring, viva en el instrumento hermano.

Deriva entre HEAD y el árbol de trabajo, medida sobre los dos hooks de ayer:

```
for f in .codex/hooks.json .opencode/cos-hooks.json .claude/settings.json; do \
  printf "%-26s HEAD=%s worktree=%s\n" "$f" \
  "$(git show HEAD:$f | grep -c lineage)" "$(grep -c lineage $f)"; done
# .codex/hooks.json          HEAD=0 worktree=2
# .opencode/cos-hooks.json   HEAD=0 worktree=4
# .claude/settings.json      HEAD=2 worktree=2
```

En HEAD, `session-lineage-record` y `lineage-relaunch-gate` **no existen para
codex ni para opencode**. Se pusieron al día recién cuando alguien volvió a
correr los drivers, y ese cambio hoy está sin commitear.

## El costo real de agregar un hook, seguido sobre un caso

Caso: `e11719383` (2026-08-19), dos hooks nuevos —`session-lineage-record.sh` y
`lineage-relaunch-gate.sh`—.

```
git show --stat e11719383
```

De los 16 archivos, **6 son superficie de registro y los 6 se editaron a mano**:

1. `cognitive-os.yaml` (+15) — la declaración.
2. `scripts/_lib/settings-driver-claude-code.sh` (+2) — la proyección real de CC.
3. `.claude/settings.json` (+8) — el artefacto generado, commiteado.
4. `templates/security-profiles/standard.json` (+8).
5. `templates/security-profiles/paranoid.json` (+8).
6. `scripts/apply-efficiency-profile.sh` (+4/-2) — dos líneas de `echo`, o sea
   documentación que se edita como si fuera código.

Lo que **no** se tocó y hoy se nota:

- `.codex/hooks.json` y `.opencode/cos-hooks.json`: se derivan del yaml, pero
  alguien tiene que correr el driver y commitear el resultado. No pasó en ese
  commit.
- `manifests/hook-vitality-budget.yaml`: sin presupuesto de latencia para los
  dos hooks nuevos.
- `.ai/primitives/hooks/` y `manifests/agentic-primitive-registry.lock.yaml`:
  `ls .ai/primitives/hooks/ | grep -i lineage` no devuelve nada y
  `grep -c lineage-relaunch-gate manifests/agentic-primitive-registry.lock.yaml`
  devuelve 0.

Ningún ledger hizo falta (los dos quedaron registrados), así que este caso es el
**camino barato**: 6 archivos. Un hook que se agrega y *no* se registra en el
perfil activo cuesta más, porque entra a 1–3 ledgers con razón escrita en cada
uno.

El mensaje de ese commit lo dice sin vueltas: *"Registrado en cognitive-os.yaml
y proyectado a mano en el driver de Claude Code, que contra lo que dice ADR-064
no lee el yaml"*. El costo está documentado por quien lo pagó.

## Mecanismos de omisión: cuáles se pisan

Siete mecanismos. Uso hoy, medido sobre el yaml y los ledgers:

| Mecanismo | Uso hoy | Quién lo lee |
|---|---|---|
| `default_projection: false` | 4 entradas (+2 con `true`, que es el default explícito) | drift audit, classifier, `derived_artifact_gate.py`, `hook_registration_audit.py` |
| `claude_projection: false` | 4 entradas | los mismos |
| `codex_projection` | 4 entradas, **ninguna booleana**: `'gap'`, `'partial'` | leído con `is False`, así que hoy no omite nada |
| `opencode_projection` | **0 entradas**; la clave existe solo en `PROJECTION_FLAG` del audit | nadie la escribe |
| `projection_note` | 3 entradas | classifier y `hook_registration_audit.py` |
| `profiles: [...]` en el yaml | 4 entradas | drift audit |
| `if [ "$PROFILE" = "full" ]` en el driver | 3 condicionales (301, 408, 445); los de 408/445 gatean los 4 hooks perdidos | **ningún gate** |

**Se pisan, con caso:**

- **`claude_projection: false` sobre `default_projection: false`.**
  `auto-refine.sh`, `auto-verify.sh` y `dod-gate.sh` llevan las dos banderas y el
  mismo `projection_note`. `default_projection: false` ya apaga los tres arneses;
  la bandera por arnés no cambia el resultado para Claude en ninguna de las tres.
  Es el caso literal de dos mecanismos cubriendo lo mismo.
- **`profiles: [full]` del yaml vs `if [ "$PROFILE" = "full" ]` del driver.**
  Expresan la misma idea —"este hook solo va en tal perfil"— y conviven: 4
  entradas usan la primera, 4 hooks la segunda. La diferencia no es semántica,
  es de visibilidad: la del yaml la lee el gate, la del driver no la lee nadie.
  Si hay que borrar una, sobra la del driver, no la del yaml.
- **Los tres ledgers de "no registrado a propósito".** Overlap medido
  (`scripts/hook_surface_census.py`): allowlist 179, classification 106,
  EXCLUDED 125, **70 hooks en los tres a la vez**; allowlist∩EXCLUDED = 105.
  Setenta hooks tienen tres razones escritas por separado, que se actualizan por
  separado y envejecen por separado.

**No son redundantes, cubren algo que ningún otro cubre:**

- `EXCLUDED_HOOKS.txt` es el único que cubre `hooks/_lib/*.sh`: de sus 13
  entradas exclusivas, 12 son LIBRARY (`cache.sh`, `common.sh`, `file_checker.sh`,
  `safe-jsonl.sh`, `timing.sh`…), fragmentos que se sourcean y jamás serán "hooks
  registrados". Un ledger de *no-hooks*. La treceava es
  `post-git-orphan-notifier.sh`, o sea uno de los cinco "perdidos" cuya única
  razón escrita vive acá.
- `hook-registration-classification.yaml` es el único con contrato de
  `next_action`, o sea el único que distingue "no va nunca" de "todavía no". 25
  entradas exclusivas suyas, entre ellas `bash-hot-path-dispatcher.sh` y
  `agent-bash-cwd-enforcer.sh`.
- `registration-allowlist.txt` es el único con forma de ratchet declarada (solo
  puede achicarse). 70 entradas exclusivas.
- La matriz de capacidades (#9) es la única que explica ausencias que **no son
  decisiones**: 42 entradas de codex se pierden porque el matcher `Agent` no
  tiene traducción, y eso no es una omisión que alguien eligió.

## Por qué el driver no lee el yaml: lo que dice el historial

No hay decisión escrita. Hay una afirmación falsa desde el primer commit.

```
git log --oneline -S"CONFIG_FILE" -- scripts/_lib/settings-driver-claude-code.sh
# c888aa1ba 2026-08-19 docs(driver): que la cabecera diga lo que el driver hace
# 387c9fc56 2026-04-30 feat(adr-064): implement P0 Tasks 1-3 — canonical hook registry + settings drivers

git show 387c9fc56:scripts/_lib/settings-driver-claude-code.sh | grep -n CONFIG_FILE
# 38:CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"      (única ocurrencia)
```

En el commit que **implementa** ADR-064, el driver de Claude Code asigna
`CONFIG_FILE` y no lo usa nunca: el archivo tiene 384 líneas y esa es la única
aparición. El mensaje del mismo commit dice, sobre la Task 2:

> Task 2: scripts/_lib/settings-driver-claude-code.sh
> - Reads harness.hooks, projects to .claude/settings.json

Nunca lo leyó. El driver de codex, escrito en ese mismo commit como Task 3,
tampoco leía el yaml todavía —`grep yaml.safe_load` en su versión de ese commit
no devuelve nada—, así que el 2026-04-30 los dos eran literales; la diferencia es
que codex después aprendió a leerlo y Claude Code no. Entre medio, 113 commits
tocaron este archivo (`git log --follow --oneline | wc -l`), cada uno agregando
literales a mano.

Conclusión: **no fue una decisión, fue una asignación muerta que se leyó como
implementación durante 111 días.** La documentación se corrigió el 2026-08-19
(`c888aa1ba`), el código no. Y esto importa para cualquier propuesta de
unificar: no hay un motivo técnico documentado que defender ni derribar. Hay una
migración que nunca se hizo y una cabecera que decía que sí.

Lo que sí hay que mirar antes de unificar —y es la parte que el "unificar todo
en el yaml" se saltea— es que **el driver expresa hoy cosas que el yaml no sabe
expresar**: el condicional de perfil en shell (4 hooks), el orden dentro de cada
grupo, y el flag `async` que la cabecera del propio driver advierte que en el
yaml no se lee (líneas 271-272). Unificar sin darle al yaml esas tres
capacidades no reduce superficies: mueve la deuda de lugar.

## Lo que NO hice y por qué

- **No unifiqué nada.** El encargo lo prohíbe y, además, hay tres capacidades del
  driver que el yaml no expresa: sin resolverlas, la unificación pierde
  información.
- **No arreglé el drift audit** para que lea `hook-registration-classification.yaml`
  ni el condicional del driver. Es una reparación con consecuencia en un ratchet
  (`max_lost_entries`), y bajarlo o subirlo es decisión del operador. Además el
  gate vive en `tests/red_team/portability/`, fuera de mi alcance por atribución.
- **No toqué el ratchet en rojo.** Hoy `max_lost_entries: 1` contra 5 medidos.
  Moverlo sería el verde barato exacto que la norma prohíbe: el número creció por
  una forma de declarar que el gate no sabe leer, no porque se hayan perdido
  cuatro hooks.
- **No corrí ninguna suite.** Máquina cargada; todo el informe sale de grep,
  `yaml.safe_load`, `git log/show` y las dos auditorías read-only existentes.
- **No medí telemetría** (`--with-telemetry`): `hook-timing.jsonl` rota a
  `.cognitive-os/metrics/.archive/` y un conteo del archivo vivo no es historia.
- **No verifiqué el arnés bare** más allá de que lee el yaml: no tiene artefacto
  de hooks propio en el censo y su driver no aparece en `HARNESSES` del drift
  audit.
