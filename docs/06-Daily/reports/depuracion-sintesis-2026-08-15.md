# Depuración — síntesis

> Estado: **síntesis, nada borrado.** El criterio quedó en ADR-342.
> Método: recontar antes de citar. Cada número de acá sale de un comando que
> está escrito al lado; los informes del día se usan como pista, no como fuente.
> Dos agentes seguían en vuelo al cierre — lo que dependa de ellos está marcado.

---

## Lo que abriste la sesión diciendo

Tres frases: *"es un gastadero de tokens"*, *"no hay gobernanza"*, *"no sé si
este repo tiene sentido"*. Las tres tienen respuesta con número, y ninguna es
la que esperabas.

### 1. "Es un gastadero de tokens"

Medio cierto, pero el gasto no está donde parece.

```
python3 -c "..."   # conteo por hook sobre .cognitive-os/metrics/hook-timing.jsonl
→ 46.396 filas, 156 hooks distintos, top-10 = 41,5% del total
python3 scripts/audit_gate_liveness.py | awk '...'
→ 72 gates cableados, 244 bloqueos en total
```

**46.396 invocaciones de hook produjeron 244 decisiones de bloqueo.** Una cada
190. Pero los hooks son bash: cuestan latencia e IO, no tokens. El token se
gasta arriba, en los agentes, y ahí el mejor rendimiento del sistema es un hook
mecánico — `result-truncator`, ~3,16 M de tokens ahorrados, un efecto cada 21
corridas.

La frase correcta no es "gastadero de tokens". Es **"gastadero de atención"**:
256 hooks de los cuales 189 se llaman como una clase que no tienen, y ocho
producen el 65% de todo lo que el sistema alguna vez impidió.

### 2. "No hay gobernanza"

Casi cierto, y ahora sabemos exactamente cuánta hay.

```
python3 scripts/audit_gate_liveness.py | head -12
→ live 8 · advisory-only 16 · untested 17 · unmeasured 18 · theatre 12 · telemetry-lying 1
```

Ocho gates vivos, con nombre y apellido: `destructive-git-blocker` (41),
`protected-config-write-guard` (49), `skill-router-bash-gate` (44),
`direct-main-guard` (13), `destructive-rm-blocker` (6), `provenance-scan` (3),
`lethal-trifecta-gate` (1), `untracked-work-preservation-guard` (1). **158 de
los 244 bloqueos.** Otros 66 son de `subagent-budget-enforcer`, y son todos
post-efecto: bloquean después de que la acción ocurrió. Los **63 gates
cableados restantes suman 20 bloqueos entre todos**.

Pero la corrección importa más que el número: **mucho de lo que parecía
gobernanza fallada nunca fue gobernanza.** 159 de los 256 hooks son
instrumentos por comportamiento — miden, no impiden — y buena parte de ellos
funciona bien. El defecto era el nombre, y el censo que clasificaba por el
nombre.

### 3. "No sé si este repo tiene sentido"

Acá la respuesta es que sí, pero **no por la capa que estabas mirando**.

Lo que produjo valor hoy no fue ningún hook. Fueron dos mecanismos del propio
repo: el encargo refutable y la verificación cruzada. La medida de cuánto
producen es incómoda y está en la sección siguiente: **de 19 cifras publicadas
hoy, 4 reprodujeron.** Las otras quince las cazó el repo contra sí mismo, casi
todas antes de que se actuara sobre ellas.

Un sistema que publica quince números malos en un día es malo. Un sistema que
los encuentra el mismo día, con un script que queda, es otra cosa.

---

## La reconciliación

Recontado al cierre. `✔` reproduce, `≠` no.

| # | Cifra publicada hoy | Recuento | | Por qué |
|---|---|---|---|---|
| 1 | teatro: 22 gates | 12 | ≠ | superada: censo por comportamiento |
| 2 | clase `ambiguo`: 68 hooks | la clase se abolió | ≠ | superada: `ambiguo` era un artefacto del nombre |
| 3 | 189 de 256 hooks mal nombrados | 189 / 256 | ✔ | — |
| 4 | 42 gates de estante | 3 | ≠ | refutada por el agente de poda |
| 5 | ~68.000 invocaciones de los cuatro ruidosos | 28.267 | ≠ | el encargo inflaba 2,4x |
| 6 | 21.046 invocaciones sin efecto | ~10.700 | ≠ | ídem, contado dos veces |
| 7 | 155 hallazgos | 8 | ≠ | refutada; no la reconté yo |
| 8 | `trust-score-validator`: 953 corridas | 36 (timing) / 41 (health) | ≠ | no reproducible en este checkout |
| 9 | `auto-verify`: 0 PASS en 55 corridas | 0 filas timing / 2 health | ≠ | no medible acá |
| 10 | `dod-gate`: 0 PASS, nunca bloqueó | 0 filas timing | ≠ | no medible acá |
| 11 | `subagent-budget-enforcer`: 12 `exit 2` | 95 → 66 | ≠ | superada dos veces el mismo día |
| 12 | cero guards sobre `apply_patch` en Codex | 10 Pre + 22 Post con `^apply_patch$` | ≠ | vencida: se arregló hoy |
| 13 | matchers `"prompt"` / `"shutdown"` en Codex | ausentes | ≠ | vencida: se arregló hoy |
| 14 | 8 campos fantasma / 2683 payloads | 9 / 2686 | ≠ | **provisional**, ver abajo |
| 15 | "el campo está bajo `tool_response`" | el campo no existe | ≠ | refutada |
| 16 | "sin consumidor vivo de opencode" | opencode 1.16.2 instalado | ≠ | refutada |
| 17 | `subagent-budget-enforcer` solo en `PostToolUse` | sigue así | ✔ | `grep -n subagent-budget .claude/settings.json` |
| 18 | opencode cuelga de `toolName === "agent"` | 3 sitios, sin `task` | ✔ | `grep -n toolName .opencode/plugins/cos-primitive-guard.js` |
| 19 | `trust-scores.jsonl` no existe | no existe | ✔ | `ls .cognitive-os/trust-scores.jsonl` |

**4 de 19.** Desglose de las quince: ocho **superadas** por un instrumento
mejor (el sistema funcionando), tres **refutadas** por falsas, dos **vencidas**
porque el arreglo entró el mismo día, dos **no medibles** en este checkout.

La distinción no es cosmética. Ocho de quince son la señal de que el método
converge; tres son error puro; dos son documentación que envejeció en horas —
y ésa es la razón por la que un informe con cifras necesita el comando al lado,
no la cifra sola.

---

## Lo que no se conectó, y conecta

Las tres tesis del día no son tres. Son **una tesis y dos versiones peores de
ella**, en orden de descubrimiento:

1. *La autoevaluación envejece mal.* Cierto, y un caso particular.
2. *No eran gates rotos, eran instrumentos con nombre de gate.* Cierto, y la
   razón por la que (1) contaba de más.
3. *Un control puede estar escrito, firmado, proyectado — y no existir.* Ésta
   contiene a las otras dos.

La forma final está en ADR-342: cuatro preguntas, cada una con su censo, y
ninguna se la contesta el control a sí mismo.

| | Pregunta | Censo |
|---|---|---|
| 1 | ¿El nombre que lo invoca existe en el host? | **no hay censo** — el hueco más grande que deja el ADR |
| 2 | ¿Corre donde todavía puede impedir? | `scripts/audit_gate_registration.py` |
| 3 | ¿Llega el campo que lee? | `scripts/audit_payload_field_contracts.py --canary` |
| 4 | ¿Se lo vio decidir? | `scripts/audit_gate_liveness.py` |

Y la autoevaluación cae sola: nunca puede contestar la 4 con autoridad, porque
el juez es la parte. No hay que prohibirla — hay que degradarla a instrumento.

---

## Donde estoy forzando la narrativa, y lo digo

Me pediste que avisara si cinco hilos que convergen suena sospechosamente
ordenado. **Suena, y en parte lo es.**

- **Tres de los cinco son uno solo.** Las tesis 1, 2 y 3 no son hallazgos
  independientes: son la misma medición mejorando. Presentarlas como
  "convergencia" les da un mérito que no tienen; es una sola pregunta que tardó
  un día en formularse bien.
- **El "verde barato" no converge con las otras — es otra cosa.** Las tres
  primeras hablan del *control*; ésta habla del *que arregla*. Son familias
  distintas y el único punto de contacto es que las dos se miden con el mismo
  censo. La puse en el ADR porque hace falta, no porque cierre el patrón.
- **Las cuatro formas de "escrito pero inexistente" no están igual de vivas.**
  Las formas 1 y 4 (nombre de herramienta, matcher descartado) se midieron sobre
  Codex y opencode, pero **la mitad de Codex se arregló hoy mismo**: los matchers
  `"prompt"`/`"shutdown"` ya no están y `apply_patch` quedó cubierto en las dos
  puntas. Decir "cuatro formas medidas hoy, todas vivas" sería falso. Lo vivo
  es: opencode sobre `toolName === "agent"` (forma 1), el enforcer en
  `PostToolUse` (forma 2), los campos fantasma (forma 3). La forma 4 es
  histórica y su valor es que el ADR la prevenga, no que esté abierta.
- **El quinto hilo lo escribieron los mismos que lo evalúan.** "El encargo
  refutable produjo más defectos que la capa de hooks" es plausible y las
  refutaciones son verificables una por una, pero el conteo comparado no está
  medido con el mismo rigor que el resto de este informe. Lo dejo como
  afirmación fuerte sin número, en vez de inventarle uno.

Lo que queda después de sacar el adorno sigue siendo suficiente: **una sola
ausencia, cuatro caras, tres de ellas abiertas hoy, y un criterio que las
cierra con cuatro comandos.**

---

## Provisional

Dos agentes en vuelo al cierre: el arreglo real de
`error-pipeline` / `error-learning` (detección por cambio de tipo, no por
`exit_code`) y el canario de campos fantasma convertido en gate con corpus
anonimizado.

**Lo único que pueden mover es la fila 14** (9 campos fantasma sobre 2686
payloads), y la esperable es que baje. La tesis no depende del número: la
pregunta 3 del criterio vale igual con 9, con 3 o con 0 — un 0 es el criterio
funcionando, no el criterio refutado.

También se movió el denominador mientras escribía esto: `hook-timing.jsonl`
pasó de 45.195 a 46.396 filas en el transcurso de la sesión. El censo mide un
sistema vivo; las cifras absolutas de invocaciones son de la ventana en que se
corrió el comando, no constantes.

---

## Qué sigue, en orden

1. **Construir el censo de la pregunta 1.** Es el único de los cuatro que no
   existe, y es el que hubiera cazado opencode, Codex y los matchers
   descartados sin necesidad de tres forenses manuales.
2. **`subagent-budget-enforcer`:** partir contar (Post) de impedir (Pre). El
   diseño está en `docs/06-Daily/reports/subagent-budget-enforcer-architecture-2026-08-15.md`;
   el commit `27191622d` es el documento, no la implementación — sigue
   registrado solo en `PostToolUse`.
3. **opencode:** `toolName === "agent"` → `task` en
   `.opencode/plugins/cos-primitive-guard.js`, y cubrir la escritura.
4. **El colchón del allowlist:** 185 entradas, 153 ya cableadas. 32 lugares
   libres bajo un número que se lee como "cubierto"
   (`python3 scripts/audit_gate_registration.py`).
5. **La poda**, que es tuya. Este informe no borra nada: dice qué se puede
   contar como cobertura y qué no.

---

## Comandos

```bash
python3 scripts/audit_gate_registration.py            # clase por comportamiento, cableado, allowlist
python3 scripts/audit_gate_liveness.py                # los 6 cuadrantes y los bloqueos
python3 scripts/audit_payload_field_contracts.py --canary   # campos fantasma contra payloads reales
python3 scripts/hook_behavior.py                      # clase de un hook, sin mirar el nombre
```
