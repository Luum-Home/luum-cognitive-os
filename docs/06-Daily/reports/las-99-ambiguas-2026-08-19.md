<!-- SCOPE: os-only -->
# Las 99 ambiguas del censo de kill-switches

**Medición**: 2026-08-19 (la sesión cruzó la medianoche; el nombre conserva la
fecha del censo).
**Instrumento**: `scripts/audit_killswitch_activation.py`.
**Gate**: `tests/contracts/test_killswitch_activation_is_executable.py`.

## Resumen ejecutivo

`python3 scripts/audit_killswitch_activation.py`, antes y después:

| | población | mentira | honesto | incompleto | ambiguo | declaración | cita | código |
|---|---|---|---|---|---|---|---|---|
| antes | 142 | 0 | 22 | — | **99** | — | — | 21 |
| después | 143 | 0 | 27 | 16 | **0** | 77 | 2 | 21 |

De dónde salió cada movimiento (`--json` antes y después, comparado por
`archivo+variable+texto`):

- **77 ambiguas → `declaración`**: comentarios de encabezado que nombran el switch
  y ninguna vía. No son ofertas: nadie las lee estando bloqueado. Van a `blind`
  con motivo escrito, no a un desenlace.
- **16 ambiguas → `incompleto`**: texto *emitido* que nombra la variable sin vía.
  Se cuentan: es deuda visible, no ceguera.
- **6 ambiguas → `honesto`**, y las seis se separan en dos causas distintas:
  **2 por corrección del instrumento** (los mensajes de `destructive-git-blocker`
  ya ofrecían `--allow-destructive` / `--allow-branch-switch`, que el hook sí lee
  del comando; el clasificador no conocía esa vía) y **4 por migración del texto**
  (`branch-ownership-lock`, `direct-main-guard` ×3).
- **1 honesta → `cita`**: `symlink-mutation-guard.sh:35` no ofrecía nada, describía
  la forma rota. Estaba en el lado correcto por casualidad.

Ninguna ambigua se volvió honesta por ensanchar qué cuenta como honesto: las dos
del `--flag` exigen la misma compensación que el prefijo leído del texto (el
literal tiene que aparecer en código del hook junto a un comparador), y hay una
fixture de control con el flag *sin* compensación que debe dar `incompleto`.

## Correcciones a las premisas del encargo

1. **«144 ocurrencias · 24 medibles» es falso.** El censo en `HEAD` al empezar daba
   **142 / 22** (99 ambiguas, 21 código). El 99 sí era correcto. Comando:
   `python3 scripts/audit_killswitch_activation.py`.
2. **Faltaba una quinta vía ejecutable.** El encargo lista cuatro. Hay una más, y
   ya estaba en producción: un **token en el comando que no es una variable**
   (`--allow-destructive`, `--allow-branch-switch`), que `destructive-git-blocker`
   busca en el texto (`hooks/destructive-git-blocker.sh:820,833`). Dos de las 99
   «ambiguas» eran mensajes honestos ofreciendo justamente eso.
3. **`bypass.env` no es «la vía accionable a mitad de sesión» en general.** El
   resolvedor lee del archivo **solo `COS_BYPASS`**
   (`hooks/_lib/bypass-resolver.sh:26`). Todo bypass que además exija una variable
   compañera —`COS_DIRECT_MAIN_BYPASS_REASON`, `COS_SKILL_BYPASS_REASON`,
   `COS_SUBAGENT_BUDGET_BYPASS_REASON`— **no tiene ninguna vía a mitad de sesión**:
   la razón se lee del entorno. Está anotado en el cheatsheet y en el mensaje de
   `direct-main-guard`.
4. **El commit quedó bloqueado por deuda ajena.** `scope-marker-portability-gate`
   escanea **todo el índice**, y otra sesión tiene `scripts/audit_hook_registration.py`
   staged sin prueba de portabilidad (`git diff --cached --name-only`). Su bypass,
   `COS_ALLOW_UNPROVEN_SCOPE_BOTH=1`, se lee **solo del entorno**
   (`hooks/scope-marker-portability-gate.sh:215`): a mitad de sesión no hay forma de
   activarlo. Es exactamente el defecto que este censo mide, ocurriéndole al
   auditor. La ocurrencia está clasificada `incompleto` en el censo.

## Por qué eran ambiguas: la taxonomía

La categoría `ambiguo` mezclaba dos poblaciones que no tienen el mismo lector, y
ése era todo el problema. El clasificador preguntaba «¿el texto nombra una vía?» y
no preguntaba **«¿quién lo lee, y está bloqueado ahora?»**.

- Un **comentario** lo lee quien abre el archivo. Nombrar el switch ahí es
  inventario. No es una salida que alguien pueda intentar tomar y fallar.
- Un **`echo`/`printf`/heredoc** lo lee quien está trabado en ese instante. Nombrar
  la variable sin decir dónde ponerla lo deja igual de trabado.

La misma frase, en los dos lugares, no vale lo mismo. `_message_lines()` ahora
devuelve dos conjuntos en vez de uno, y de ahí salen `declaración` (77) e
`incompleto` (16): 93 de las 99 se disuelven por esa sola distinción. Las otras 6
eran errores del instrumento o texto que había que arreglar.

## Oferta vs cita de una oferta

`hooks/destructive-git-blocker.sh` tenía este comentario:

> «El literal viejo no se cita: `scripts/audit_killswitch_activation.py` no puede
> distinguir una oferta de la cita de una oferta, y cuenta de más a propósito.»

O sea: el código se escribió peor —una explicación que no puede nombrar lo que
explica— para no confundir a la herramienta. Eso es el instrumento mandando sobre
el código, y era la ganancia más grande disponible.

El criterio nuevo, y su límite:

- Un **comentario** que muestra la forma rota **dentro de un bloque de comentarios
  que dice que no llega** (`no llega`, `no funciona`, `ofrecía antes`, `never
  reaches`…) es `cita`, no oferta.
- La ventana es el **bloque contiguo de `#`**, no un radio fijo: un radio se comería
  el `echo` de al lado y le regalaría la absolución del vecino.
- El marcador **no vale en texto emitido**. Un mensaje que dice «esto no funciona»
  al lado de la forma rota se lo sigue mostrando a alguien trabado. Sin ese límite,
  `cita` sería un supresor universal: cualquiera apagaría el rojo agregando cuatro
  palabras. Hay un test dedicado
  (`test_la_cita_no_absuelve_un_mensaje_emitido`) que lo mantiene cerrado.

Fixtures nuevas, en pares para que la distinción esté probada en las dos
direcciones: `_OFERTA_EN_COMENTARIO` y `_CITA_EN_COMENTARIO` llevan **el mismo
literal roto** y deben dar `mentira` y `cita` respectivamente; `_HONESTO_FLAG` y
`_FLAG_SIN_COMPENSACION` llevan el mismo `--allow-demo` y deben dar `honesto` e
`incompleto`; `_INCOMPLETO` y `_DECLARACION` llevan el mismo texto en `echo` y en
comentario. El comentario del hook ya no evita el literal, y el censo lo ve como
`cita` (`hooks/destructive-git-blocker.sh:994`).

## El cheatsheet

Los **tres** ejemplos eran la forma de prefijo, no solo la línea 39 que marcaba el
encargo:

```
COS_BYPASS=branch_switch bash -lc 'git switch release/prepare'
COS_BYPASS=push_collision git push --force-with-lease
COS_BYPASS=commit_guard git commit -m 'fix: emergency scoped change'
```

Ninguna llega: `cos_bypass_allows` lee el entorno y `.cognitive-os/runtime/bypass.env`,
nunca el texto del comando. La página está reescrita alrededor de la pregunta que
de verdad decide —**¿estás bloqueado ahora o no?**— con la forma rota conservada
como contraejemplo explícito. Se agregó, además, la advertencia sobre las claves
con `*_REASON` compañera, que no tienen vía a mitad de sesión.

Gate nuevo, por ruta y no por censo: `test_ningun_doc_ofrece_cos_bypass_como_prefijo`
recorre `docs/**` y `rules/**`. Probado por mutación: un `.md` con la forma de
prefijo lo pone en rojo, y sin él vuelve a verde.

**Decisión sobre ampliar el clasificador a documentos: no.** El motivo, escrito
para que el alcance angosto no se lea como cobertura: el veredicto de una oferta
necesita el par *mensaje + hook que debería honrarlo*, y un `.md` no nombra a su
hook. Ampliar el censo mezclaría dos poblaciones con criterios distintos. La
familia que **sí** es decidible sin ese par —el prefijo con `COS_BYPASS=`, inerte
contra todos los hooks— se gatea por ruta, que es la respuesta proporcionada: una
regla de una línea en vez de un segundo censo.

**Deuda declarada**: `ADR-241` (líneas 120, 122) y `ADR-243` (línea 117) tienen la
misma forma de prefijo. Están **dentro** del gate y listadas en
`_PREFIJO_EN_DOCS_PENDIENTE`, con `test_la_deuda_de_docs_no_tiene_asientos_fantasma`
impidiendo que el asiento sobreviva a su ocurrencia. No las corregí porque un ADR
es un **registro de decisión** y reescribir su ejemplo es decisión de quien lo
firmó, no un arreglo de paso. Reproducir:
`grep -rnE 'COS_BYPASS=[a-z_,]+[ \t]+[a-z./]' docs/ rules/ --include='*.md'`.

## Las que siguen ambiguas, y por qué cada una

**Ninguna queda en `ambiguo`** — hay un test que lo verifica
(`test_ninguna_ocurrencia_queda_sin_decidir`). Lo que queda sin resolver está
*decidido y nombrado*, en dos formas:

- **`declaración` (77, en `blind`)** — comentarios de encabezado del tipo
  `# Killswitch: DISABLE_HOOK_X=1`. Motivo: no son ofertas. El instrumento no las
  juzga porque no hay nada que juzgar: nadie queda trabado leyendo un comentario.
- **`incompleto` (16, contado)** — mensajes emitidos que nombran la variable y
  ninguna vía. Motivo: la vía existe (export antes del lanzamiento) pero el
  mensaje no la dice, así que quien está trabado no la tiene. Deuda real y
  visible, no ceguera. La lista completa sale de
  `python3 scripts/audit_killswitch_activation.py --json | jq -r '.[]|select(.verdict=="incompleto")|"\(.file):\(.line)"'`.
  Encabezan la lista `token-budget-monitor.sh:124`, `network-egress-guard.sh:31`,
  `edit-lock-pre-tool.sh:94` y `scope-marker-portability-gate.sh:298` — esta última
  es la que me bloqueó a mí.
- **Imprecisión conocida dentro de `incompleto`**: `destructive-git-blocker.sh:930`
  es un **aviso posterior** («allowed … via VAR=1»), no una oferta: nadie está
  bloqueado cuando se imprime. El instrumento no distingue tiempo verbal y la
  cuenta como incompleta. Cuenta de más, no de menos, y queda dicho acá en vez de
  resuelto con un heurístico frágil de prosa.

## Lo que NO hice y por qué

- **No migré las 16 `incompleto`.** Son ~13 hooks y dos sesiones más están
  escribiendo en este checkout. Migré las **4** donde el arreglo era exacto y
  verificable (el hook sourcea el resolvedor ADR-241, así que sabía qué vía ofrecer
  sin inventarla). El resto queda como deuda **contada**, con su lista reproducible
  — que es estrictamente mejor que antes, cuando estaba en «no sé».
- **No toqué los ADR.** Ver arriba: declarados, gateados, no corregidos.
- **No agrandé `KNOWN_UNREACHABLE_KILLSWITCHES`.** Sigue vacío; `mentira` sigue en 0
  y los 31 tests pasan (eran 20).
- **No usé `COS_ALLOW_UNPROVEN_SCOPE_BOTH`** para saltear el gate que me bloqueó:
  no es activable a mitad de sesión, y aunque lo fuera, apagar el rojo de la deuda
  de otro es exactamente el verde barato.
