# Poda lote 1 — gates de estante

**Fecha:** 2026-08-15
**Alcance:** los gates que el informe de arquitectura dio por no registrados.
**Resultado:** no se borró nada. El lote no tiene candidatos.

---

## 1. Veredicto

De los gates sin registrar: **0 borrados, 0 regresiones, 3 pendientes por diseño,
0 ambiguos** — porque el conteo de partida estaba mal. No hay 42 gates de
estante: hay **3 gates sin ningún ejecutor**, y los tres tienen una decisión
escrita que dice por qué no se cablean.

Comando:

```bash
.venv/bin/python scripts/audit_gate_registration.py
```

```
canonical hooks (symlink-resolved): 256   (aliases collapsed: 42)
  ambiguo       68   wired   58   unwired   10
  gate          69   wired   66   unwired    3
  instrument   119   wired  102   unwired   17

gates absent from .claude/settings.json : 35
gates with NO executor at all           : 3
```

La diferencia entre **35** y **3** es todo el informe: 32 gates que no están en
`.claude/settings.json` sí corren, por otras cuatro vías.

---

## 2. Las cinco superficies de registro

`.claude/settings.json` es un archivo **generado**. Medir "registrado" ahí y solo
ahí es medir la salida del proyector, no el cableado. Las superficies reales:

| Superficie | Qué es | ¿Ejecuta hoy? |
|---|---|---|
| `.claude/settings.json` / `.local` / `.codex/hooks.json` | lo que lee el harness | sí |
| **dispatcher** (`bash-hot-path-dispatcher.sh` y 10 más) | un hook registrado que abre en abanico a otros | sí |
| **consumer-install** (`cos_init.py::DEFAULT_HOOKS`, `generate-project-settings.sh::DEFAULT_HOOKS`, `packages/*/cos-package.yaml`) | lo que se copia y registra en cada proyecto externo | sí, en el consumidor |
| `templates/security-profiles/*.json` | lo aplica `set-security-profile.sh` | solo si el operador cambia de perfil |
| `cognitive-os.yaml` | registro que alimenta al proyector | declarativo |

La tercera es la que faltaba en todos los conteos previos. Un hook puede estar
ausente del `settings.json` propio y **shippearse activado a todos los
consumidores**.

---

## 3. Tabla por hook — los 3 gates sin ejecutor

| Hook | Clasificación | Evidencia | Commit que lo sacó |
|---|---|---|---|
| `agent-quota-redirect` | **PENDIENTE POR DISEÑO** | `manifests/hook-registration-classification.yaml` → `conditional_opt_in`: *"ADR-056 L2 blocks native Agent launches under quota pressure. Keep opt-in because it changes execution routing."* | nunca estuvo en `settings.json` |
| `pre-commit-gate` | **PENDIENTE POR DISEÑO** | manifiesto → `git_or_manual`: *"installed through git hooks, not Claude settings. Keep out of Claude settings."* Instalador propio: `scripts/install-pre-commit.sh` lo symlinkea a `.git/hooks/pre-commit` | nunca estuvo |
| `valkey-ensure` | **PENDIENTE POR DISEÑO** | manifiesto → `conditional_opt_in`: *"Only needed when ORCHESTRATOR_MODE=executor and Valkey is required."* Concuerda con `RULES-COMPACT.md` §7 (`agent-communication` Valkey OFF) | — |

Verificación:

```bash
.venv/bin/python -c "
import json
for e in json.load(open('manifests/hook-registration-classification.yaml'))['entries']:
    n=e['path'].split('/')[-1]
    if n in ('agent-quota-redirect.sh','pre-commit-gate.sh','valkey-ensure.sh'):
        print(n, '->', e['status'], '|', e['rationale'])"
```

**Ninguno es BORRAR**: los tres fallan el criterio "sin ADR ni decisión escrita".

---

## 4. Los tres nombres que citaba el encargo

| Hook | Lo que decía el encargo | Lo que mide el script |
|---|---|---|
| `destructive-rm-blocker` | gate de estante | `wiring=['dispatcher','cognitive-os.yaml']` — lo corre `bash-hot-path-dispatcher.sh:107` bajo `_is_fs_mutation` |
| `network-egress-guard` | gate de estante | `wiring=['dispatcher','profile','cognitive-os.yaml']` — `bash-hot-path-dispatcher.sh:103` |
| `secret-audit-pre-commit` | gate de estante | clasifica **ambiguo**, no gate; manifiesto → `conditional_opt_in` citando ADR-215 (*"may require optional scanner binaries"*) |

Los dos primeros salieron de `settings.json` en `60f29880` —
*"fix(observability): restore bash governance via tiered dispatcher"*— que es
exactamente el commit que los movió al dispatcher. Salir del `settings.json` era
el objetivo del cambio, no su efecto colateral.

---

## 5. Regresiones — la lista, y por qué está vacía

Se auditaron los dos commits que vaciaron el hot path, hook por hook: ¿alguno
quedó sin ejecutor después de la mudanza?

```bash
for c in a0b208a0b9c8c2e019af532d6d809b0c9278e630 \
         60f29880e0860f44ad85487261515157a538a1a7; do
  git show $c -- .claude/settings.json | grep '^-' \
    | grep -o -E 'hooks/[a-z0-9-]+\.sh' | sed 's|hooks/||;s|\.sh||'
done | sort -u   # 30 hooks
```

Cruzados contra el cableado actual: **30 de 30 re-alojados, 0 huérfanos.** La
refactorización del hot path fue limpia.

**No hay regresiones que restituir en este lote.**

### 5.1 `dod-gate` — la regresión que el encargo daba por confirmada

No lo es, pero tampoco está sano. Estado real:

```
dod-gate   wiring=['profile','cognitive-os.yaml','consumer-install']
           manifest=future
```

Está en `DEFAULT_HOOKS`: **se instala y registra en todo proyecto consumidor.**
Lo que se cayó es el `settings.json` de este repo, en `7ae80f54`
*"fix(validation): stabilize integration launch readiness"* (2026-05-10).

O sea: el SO le exige DoD a sus consumidores y no se lo exige a sí mismo. No es
pérdida silenciosa —el manifiesto lo tiene como `future` con next_action escrito—
pero es una asimetría self-host / consumidor que conviene que el operador mire.
Misma forma para `rate-limiter`, con el agravante de que `rules/rate-limiting.md`
afirma que no está activo sin aclarar que eso vale solo para el self-host.

**Ninguna de las dos se restituye acá**: registrar un gate lo pone a bloquear y
es decisión del operador.

---

## 6. Qué se borró

**Nada.** Conteo: **0 archivos**.

La autorización `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` quedó sin usar.

Verificación:

```bash
git show --stat HEAD -- hooks/    # sin entradas: el commit no toca hooks/
```

### Los cuatro que parecían BORRAR, y por qué no lo eran

El manifiesto marca cuatro hooks como `deprecated`, tres de ellos gates, cada uno
con la instrucción *"Archive after reference audit"*. Esa auditoría es la que se
hizo, y la respuesta fue no:

| Hook | Por qué no se borra |
|---|---|
| `agnix-lint` | `hooks/agnix-lint.sh` es un **symlink** a `packages/ecosystem-tools/hooks/`. Declarado en `cos-package.yaml` (`source:`), documentado en el README y en `rules/ecosystem-tools.md` del paquete |
| `clarification-interceptor` | symlink a `packages/quality-gates/`. Y está en `DEFAULT_HOOKS` de `cos_init.py:110` **y** `generate-project-settings.sh:151`: se instala en todo proyecto nuevo |
| `confidence-gate-llm` | symlink a `packages/cos-advisory-llm/`. `cos-package.yaml` lo declara con `source:` y `script:`; ADR-022 lo lista dos veces |
| `completeness-check-llm` | symlink a `packages/cos-advisory-llm/`, declarado en su `cos-package.yaml` (ambiguo, no gate — fuera del lote igual) |

Comando que lo cierra:

```bash
readlink hooks/agnix-lint.sh hooks/clarification-interceptor.sh \
         hooks/confidence-gate-llm.sh
git grep -n "clarification-interceptor" -- scripts/cos_init.py \
         scripts/generate-project-settings.sh
```

Borrar el symlink no borra el hook: deja el paquete declarando un `source:` que
ya no existe. Y en el caso de `clarification-interceptor`, rompería el instalador
por defecto.

**Contradicción viva, para el operador:** el manifiesto dice `deprecated` de tres
hooks que el instalador sigue shippeando. Una de las dos afirmaciones es falsa.
Es la deuda más accionable que dejó este lote.

---

## 7. Correcciones a las premisas del encargo

1. **"42 gates no registrados" — no.** Son **3** gates sin ejecutor. El 42 sale
   de medir solo contra `.claude/settings.json`, que es generado. Nota aparte: 42
   es también, exactamente, el total de hooks sin ejecutor sumando las tres
   clases (10 ambiguos + 3 gates + 17 instrumentos = 30... y 42 en la corrida
   previa a incorporar la superficie `consumer-install`). El número del informe de
   arquitectura es reproducible **si y solo si** se ignora el instalador.

2. **"42 symlinks" era el otro 42.** `audit-arq-hooks-2026-08-15.md:21` reporta
   42 symlinks, y `arq-contrato-gate-instrumento` reporta 42 gates sin registrar.
   Mi censo colapsa exactamente 42 alias. Vale verificar que no sea el mismo
   número contado dos veces con dos etiquetas.

3. **`destructive-rm-blocker` y `network-egress-guard` corren.** Los cita el
   encargo como ejemplos de gates muertos; los dos están en el dispatcher. Ya lo
   había advertido `judge3-primitivas-2026-08-15.md:288`, con 23 filas en
   `hook-health.jsonl` como prueba. El dato existía en el repo antes de este lote.

4. **`secret-audit-pre-commit` no es un gate**, es ambiguo por nombre (`-audit`),
   y su no-registro está motivado en ADR-215.

5. **`dod-gate` no es una regresión silenciosa** (§5.1): sigue shippeándose a los
   consumidores. Es una asimetría self-host.

6. **La taxonomía del encargo tiene un cuarto caso que no contempla.** "Estuvo
   registrado y no está" no implica regresión: puede ser **mudanza deliberada**
   (al dispatcher: 30 casos) o **depreciación decidida** (4 casos). El criterio
   que separa no es "¿estuvo alguna vez?" sino "¿hay un sucesor cableado?". Se
   verificó: `clarification-gate`, `confidence-gate` y `completeness-check` están
   los tres en `settings.json`, así que las depreciaciones son reales. El que no
   cierra es `agnix-lint`: su sucesor declarado, `architecture-compliance`, es un
   *instrumento* y solo está en `profile`.

7. **El gate de este lote ya tenía trampa puesta.** `scripts/check_hook_registration.py`
   sale **exit 0** — "257 hooks on disk, 72 fully registered, 185 intentionally
   absent"— porque `hooks/_lib/registration-allowlist.txt` tiene 185 entradas
   grandfathered de 2026-04-11. **152 de esas 185 ya están cableadas.** Es un
   colchón de 152 lugares: el ratchet dice "solo puede achicarse" y hoy acepta
   152 hooks sin registrar más de los que hay. Un supresor por encima de la
   realidad, exactamente el patrón de `gates-sin-trampa`.

   ```bash
   .venv/bin/python scripts/audit_gate_registration.py | grep cushion
   # allowlist entries that ARE wired (cushion): 152
   ```

8. **Un hook sin decisión escrita.** El contrato del manifiesto dice *"Every
   unregistered top-level hook must appear here with status, rationale, and
   next_action"*. `prompt-quality` (instrumento) no aparece. Es la única
   violación del contrato en las tres clases.

---

## 8. Recomendaciones, por orden

1. **Resolver la contradicción manifiesto ↔ instalador** (§6): tres hooks
   `deprecated` que `DEFAULT_HOOKS` y los `cos-package.yaml` siguen shippeando.
   Hasta que se resuelva, ningún lote de poda puede tocarlos.
2. **Bajar el allowlist de 185 a 33** (§7.7). Es mecánico y devuelve el gate a
   la realidad. El script ya emite la lista.
3. **Decidir la asimetría self-host / consumidor** de `dod-gate` y `rate-limiter`
   (§5.1). Decisión del operador: o se registran acá, o se documenta que el
   self-host corre con menos gates que sus consumidores.
4. **Corregir `rules/rate-limiting.md`**: afirma que el limitador no está activo,
   sin aclarar que va cableado en `DEFAULT_HOOKS` para todo consumidor.
5. **Dar de alta `prompt-quality` en el manifiesto** (§7.8).
6. **Revisar la depreciación de `agnix-lint`** (§7.6): el sucesor que declara no
   cubre lo mismo.

---

## 9. Salteado por territorio ajeno

Aparecieron en el censo como sin cablear y **no se tocaron** porque tienen dueño:

| Hook | Clase | Estado |
|---|---|---|
| `task-panel-sync` | instrumento | sin ejecutor, manifiesto `future` |
| `recap-sync` | instrumento | sin ejecutor, manifiesto `future` |

Los dos son instrumentos, así que quedaban fuera del lote de gates igual.

Tampoco se leyó ni modificó: `hooks/dispatch-gate.sh`, `session-init.sh`,
`destructive-git-blocker.sh`, `auto-verify.sh`, `completion-gate.sh`,
`claim-validator.sh`, `subagent-budget-enforcer.sh`, `skill-metrics-tracker.sh`,
`scripts/hook-timing-wrapper.sh`, `scripts/runtime_hook_reality.py`,
`templates/`, `rules/`.

`destructive-git-blocker` sí aparece en la tabla de §5 (30 re-alojados) porque
el chequeo es sobre la historia de `.claude/settings.json`, no sobre el archivo.

---

## 10. Evidencia ejecutable

`scripts/audit_gate_registration.py` — read-only, determinista, exit 0/1/2.

```bash
.venv/bin/python scripts/audit_gate_registration.py            # resumen
.venv/bin/python scripts/audit_gate_registration.py --history  # arqueología git
.venv/bin/python scripts/audit_gate_registration.py --json     # filas completas
```

Se diferencia de `scripts/check_hook_registration.py` en dos cosas: **no** honra
el allowlist para contar (reporta el cableado crudo y por separado si hay
decisión escrita), y suma la superficie `consumer-install`, que es la que faltaba.
