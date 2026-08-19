# Ecosistemas de plugins y detección de superficie muerta: qué se puede copiar y qué no

**Fecha:** 2026-08-19
**Alcance:** investigación web (pytest/pluggy, VS Code, lazy.nvim, Homebrew, npm/PyPI, vulture/knip,
coverage.py, JaCoCo, Teamscale, SCARF de Meta, atuin/bash history) contra el problema local:
767 scripts y 35 plantillas sin señal de uso, skills con canal vivo y casi cero eventos.
**Estado:** cerrado como investigación. Deja un hallazgo bloqueante con fecha de vencimiento.

---

## Lo primero, porque tiene reloj

El análisis retroactivo desde transcripts **no es inviable, pero el corpus se está borrando solo
y ya perdió todo lo anterior a 30 días**.

Claude Code borra los `.jsonl` de sesión cuyo mtime sea anterior a `cleanupPeriodDays` (default 30)
al arrancar, sin aviso y sin recuperación
([docs de settings](https://docs.anthropic.com/claude/docs/claude-code/settings),
[issue 59248](https://github.com/anthropics/claude-code/issues/59248)).
Medido acá:

```bash
P=~/.claude/projects/$(pwd | sed 's/[/.]/-/g')   # el slug es la ruta con / y . vueltos -
ls -lt "$P"/*.jsonl | awk 'NR==1 || END {print}'  # extremos de la ventana
grep -r cleanupPeriodDays ~/.claude/settings.json .claude/settings.json 2>/dev/null || echo "sin setear"
```

Resultado: 22 archivos, 246 MB, el más viejo del **20-jul** y el más nuevo del **19-ago** —
treinta días clavados— y `cleanupPeriodDays` sin setear en ningún lado, o sea default.

Tres consecuencias que cambian el plan:

1. **Todo "0 usos" que salga de transcripts significa "sin señal en los últimos 30 días"**, jamás
   "nunca se usó". Un script de release, de patch o de cierre de sprint puede tener un período
   natural mayor que la ventana entera de observación.
2. **La medición no es repetible hacia atrás.** Lo que no se extraiga hoy no se puede volver a
   analizar mañana con otro criterio: el insumo ya no existe. Eso rompe la norma de evidencia
   ejecutable — el script quedaría, pero el input desaparece.
3. **La premisa "medir sin instrumentar nada" no se sostiene.** Hay una acción de instrumentación
   mínima e inaplazable antes de medir: fijar retención (`cleanupPeriodDays: 0`) y/o volcar un
   extracto append-only versionado. Todo día de demora es un día que se cae del extremo viejo.

Y hay un segundo defecto, específico de este caso y más traicionero que el anterior:
**la auditoría contamina su propio corpus**. Una sesión que audita scripts muertos hace
`ls scripts/`, `grep` por nombres, `cat` de los sospechosos — y deja en el transcript los 767
nombres. Cualquier conteo hecho con `grep -c "<nombre>"` sobre los `.jsonl` va a "encontrar uso"
justamente de los que se estaban por matar. La señal válida es **posición de ejecución**
(primer token del comando, o token siguiente a `bash`/`sh`/`python3`/`uv run`), nunca mención.

---

## Mecanismos, uno por uno

### 1. pytest / pluggy: separar "registrado" de "invocado"

pytest distingue explícitamente dos cosas que acá se están mezclando:

- **Registrado**: `pytest --trace-config` imprime los plugins activos y los `conftest.py` cargados;
  `-p no:NOMBRE` bloquea uno; `PYTEST_DISABLE_PLUGIN_AUTOLOAD` corta la carga por entry points
  ([docs](https://docs.pytest.org/en/stable/how-to/writing_plugins.html)).
- **Invocado**: eso no lo da el flag de config, lo da pluggy.
  `PluginManager.enable_tracing()` y sobre todo
  `add_hookcall_monitoring(before, after)` envuelven **todas** las llamadas a hooks con un par
  before/after; `pytest --debug` engancha eso y vuelca a `pytestdebug.log`
  ([pluggy](https://pluggy.readthedocs.io/en/latest/)).

**Aplica, y es el patrón más directamente transplantable:** una sola envoltura en el despachador
observa las N piezas. No hay que tocar los 767 scripts ni las 194 skills; hay que instrumentar
el punto por donde pasan. El corolario incómodo: lo que no pasa por un despachador (un script
invocado con `bash scripts/foo.sh` desde una sesión cualquiera) no tiene dónde colgarse, y ahí
el transcript es el único observador que existe.

### 2. VS Code: la declaración de activación es la instrumentación

`activationEvents` obliga a la extensión a declarar cuándo debe despertarse (`onCommand:`,
`onLanguage:`, `onStartupFinished`) y el host sabe si despertó
([docs](https://code.visualstudio.com/api/references/activation-events)). Nadie mide "uso" de una
extensión: se mide activación, que es lo que el host puede saber sin cooperación del plugin.

**Aplica** a skills y hooks (declaran disparador, pasan por un host).
**No aplica** a scripts sueltos. Y conviene mirar el otro lado: VS Code **no** tiene expiración
automática por falta de activación, y marcar una extensión como deprecada en el Marketplace
requiere escribirle al equipo de VS Code a mano
([discusión oficial](https://github.com/microsoft/vscode-discussions/discussions/1)). El
ecosistema de plugins más grande del mundo resuelve deprecación con un correo.

### 3. lazy.nvim: el loader sabe qué cargó

`:Lazy profile` da el desglose de qué plugin se cargó y cuánto tardó
([docs](https://lazy.folke.io/usage/profiling)). Misma idea que pluggy: el gestor es el que mide,
porque es el único que ve todo. Aplica como confirmación del patrón, no aporta nada nuevo.

### 4. Homebrew: la mejor política de expiración encontrada, y es numérica

Tres estados, no borrado directo: **deprecated → disabled → removed**, con DSL `deprecate!` /
`disable!` ([docs](https://docs.brew.sh/Deprecating-Disabling-and-Removing)). Y umbrales duros:

- fórmula con **más de 1000 instalaciones en 90 días** → no se deshabilita sin **6 meses** de
  deprecación previa;
- fórmula con **menos de 1000 en 90 días** → se puede deshabilitar de una;
- una API pública se deprecia si tiene "uso nulo o insignificante según analytics o búsqueda en
  el repositorio" — dos señales, no una;
- lo deshabilitado se remueve **automáticamente al año**.

**Aplica la forma, no los números.** Lo valioso es el estado intermedio: `disabled` no es silencio,
es un error con mensaje. Ese estado es el detector de falsos negativos — si alguien de verdad
necesitaba la pieza, aparece un error atribuible en vez de un hueco. Es la única forma barata de
convertir "no observado" en "efectivamente nadie lo usa".

### 5. SCARF (Meta): grafo estático + señales de runtime + fallback textual

El sistema que más se parece al problema.
([post de ingeniería](https://engineering.fb.com/2023/10/24/data-infrastructure/automating-dead-code-cleanup/),
[paper FSE 2023](https://dl.acm.org/doi/10.1145/3611643.3613871)):

- grafo de dependencias por lenguaje extraído de los compiladores, **aumentado con señales
  operativas**: uso de endpoints según logs, invocaciones de scripts, hooks de plantillas;
- **búsqueda textual (BigGrep) como red de seguridad**: prefieren falsos negativos a falsos
  positivos, explícitamente;
- revisión humana de los change requests, auto-merge solo en lenguajes de alta confianza, y los
  falsos positivos que caza el revisor se realimentan al análisis;
- escala: +100 millones de líneas borradas en +370.000 change requests; pasar a analizar el grafo
  completo dio ~50% más de código muerto detectado.

**Aplica la arquitectura de dos señales y el fallback textual.** Acá el "fallback textual" no es
red de seguridad, es la señal estática principal: la mitad de las referencias a scripts viven
dentro de markdown, YAML y `settings.json`, o sea en strings que ningún analizador de código ve.

### 6. Cobertura en producción: la respuesta real a "nunca vs no observado"

CQSE instala un profiler en producción y **graba durante varios meses, cuidando de cubrir los
intervalos importantes como el cierre de año**
([Teamscale](https://teamscale.com/blog/en/news/blog/does-anybody-use-this-feature)). No hay
truco estadístico: la respuesta a "¿nunca se usó?" es una ventana de observación declarada, larga,
y elegida para incluir los picos estacionales.

**Aplica como criterio de diseño y choca de frente con el hallazgo del principio:** con retención
de 30 días no se puede tener una ventana estacional. Primero se arregla la retención, después se
mide.

### 7. Estáticos (vulture, knip): sirven por su taxonomía de falsos positivos

- vulture avisa que se le escapa lo llamado por `getattr()`, clases instanciadas desde strings,
  módulos importados dinámicamente y overrides implícitos; recomienda whitelist y
  `--min-confidence 100` para lo garantizado ([repo](https://github.com/jendrikseipp/vulture)).
- knip documenta lo mismo del lado JS: imports dinámicos con template strings, convenciones de
  framework, archivos generados, entry points no reconocidos
  ([guía](https://knip.dev/guides/handling-issues)). En una evaluación sobre Angular, 22 de 36
  casos detectados y **14 de los hallazgos eran falsos positivos**
  ([Iterative](https://blog.iterative.engineering/2024/03/20/strengths-and-limitations-of-knip-for-unused-code-detection-in-angular/)).

Esto es exactamente lo que dice el skill `gates-sin-trampa`: **un hallazgo es una hipótesis**.
Un catálogo cuyas invocaciones son strings dentro de documentos es el peor caso posible para
análisis estático puro.

### 8. Descargas agregadas (npm, PyPI): no aplica

npm dice que sus números son "indicadores direccionales de popularidad, no números absolutos, y
definitivamente no la cantidad de usuarios"
([npm](https://blog.npmjs.org/post/92574016600/numeric-precision-matters-how-npm-download-counts-work.html)).
pypistats aclara que los mirrors enmascaran descargas de paquetes populares e inflan las de los
poco comunes, que la incertidumbre no es cuantificable, y que **el tráfico de CI/CD está incluido
en todas las métricas** ([FAQ](https://pypistats.org/faqs)).

Es la analogía de contar cuántas veces un script está listado en un catálogo: mide distribución,
no ejecución.

### 9. atuin vs `.bash_history`: el modelo de datos correcto

atuin guarda por comando: timestamp, duración, exit code, comando, **cwd**, sesión y host
([repo](https://github.com/atuinsh/atuin)). `.bash_history` pierde por diseño: se escribe recién
al salir la shell, `HISTCONTROL=ignorespace` descarta lo que empieza con espacio, `ignoredups`
descarta repeticiones, y dos shells concurrentes se pisan el archivo al cerrar
([forense de bash](https://mattcasmith.net/2022/02/22/bash-history-basics-behaviours-forensics)).

Buena noticia local, verificada: **los transcripts ya son de calidad atuin**. Cada registro trae
`cwd` y el comando literal:

```bash
P=~/.claude/projects/$(pwd | sed 's/[/.]/-/g')
grep -ho '"name":"Bash"' "$P"/*.jsonl | wc -l                 # 2885
grep -ho '"command":"[^"]*scripts/[^"]*"' "$P"/*.jsonl | wc -l # 742
grep -ho '"cwd":"[^"]*"' "$P"/*.jsonl | head -1
```

---

## Las cuatro preguntas, contestadas

### 1. ¿Alguien mide retroactivamente desde logs?

Sí, pero nadie mide **solo** desde logs. SCARF usa logs de endpoints y de invocación de scripts
para aumentar un grafo que ya existía; CQSE instala un profiler y **espera**. El retroactivo puro
sobre historial de shell no aparece en la literatura seria, y las razones son las de
`.bash_history`: el corpus no fue diseñado para eso.

Problemas de atribución que sí nos tocan, en orden de daño:

| Problema | Nos afecta | Por qué |
|---|---|---|
| Mención vs ejecución | **Sí, grave** | Auditar scripts deja los 767 nombres en el transcript. Contar por `grep` de nombre se autoconfirma. |
| `cd X && ./script`, rutas relativas | Parcial | El registro trae `cwd`, pero un `cd` embebido dentro del propio comando lo invalida. |
| Heredocs y `python3 -c` | Sí | Lógica ejecutada sin nombrar ningún archivo del catálogo. |
| Symlinks (`scripts/` ↔ `packages/*/scripts/`) | Sí | Un basename puede mapear a dos rutas; sin `readlink -f` se cuentan dos componentes donde hay uno. |
| Aliases y wrappers | Bajo | Los agentes escriben comandos completos, no aliases interactivos. |
| Pipes y `xargs` | Bajo | El script sigue apareciendo como token ejecutable. |

### 2. ¿Cómo distinguen "nunca se usó" de "no lo estamos observando"?

Nadie lo resuelve con una medición más fina. Lo resuelven con tres cosas combinadas:

1. **Ventana declarada y estacional** (CQSE: meses, incluyendo el cierre de año). La afirmación
   honesta no es "no se usa", es "sin señal en la ventana W bajo el canal C".
2. **Dos señales independientes** (Homebrew: analytics *o* búsqueda en el repo; SCARF: grafo *y*
   runtime *y* grep textual). Una sola señal nunca alcanza para borrar.
3. **Un estado intermedio reversible que genera ruido si alguien lo necesitaba** (Homebrew
   `disabled`, SCARF revierte si rompe). Esto convierte la ausencia de evidencia en evidencia:
   deshabilitar y esperar el error es más barato y más concluyente que medir mejor.

Traducido a matriz para nuestro caso, con dos señales:

| | Ejecutado en la ventana | No ejecutado |
|---|---|---|
| **Referenciado** (grep en settings/hooks/skills/docs) | vivo | **no observado** — puede ser baja frecuencia; candidato a `deprecated`, no a borrado |
| **No referenciado** | bug de catálogo: se ejecuta a mano y nadie lo documenta | candidato fuerte a `disabled` |

### 3. Políticas de expiración

- **Homebrew**: la más explícita y la única con umbrales publicados (arriba). Tres estados,
  remoción automática al año de `disabled`.
- **SCARF**: borra automáticamente, con revisión humana y mecanismos de reversión; los falsos
  positivos son insumo para mejorar el análisis, no motivo para frenar el proceso.
- **VS Code**: no hay política automática; deprecar requiere intervención manual del equipo.
- **npm/PyPI**: no deprecan por falta de uso; el paquete vive para siempre.

El patrón que se repite en los dos que sí funcionan: **nunca se pasa de "vivo" a "borrado" en un
solo paso**, y el paso intermedio siempre produce una señal observable.

### 4. Costo de latencia aceptado (números, no opiniones)

| Instrumentación | Overhead medido | Fuente |
|---|---|---|
| coverage.py con `sys.monitoring` (py3.12+) | "a menudo menor al 5%"; **no soporta dynamic contexts** | [Batchelder](https://nedbatchelder.com/blog/202312/coveragepy_with_sysmonitoring.html) |
| coverage.py con `sys.settrace` | varias veces mayor; es el modo que sí da contextos | [docs](https://coverage.readthedocs.io/en/latest/howitworks.html) |
| JaCoCo agent (instrumentación on-the-fly) | ~5-10%, peor con muchos métodos chicos | [FAQ](https://www.jacoco.org/jacoco/trunk/doc/faq.html) |
| Teamscale en producción | mide a nivel de **método**, no de línea, para bajar el costo | [Teamscale](https://teamscale.com/blog/en/news/blog/does-anybody-use-this-feature) |
| OpenTelemetry auto-instrumentación | 7-42% CPU y hasta 42% de latencia; 3,4-3,6% con batching y sampling; en Go, p99 de 10 ms a 15 ms | [OTel Java](https://opentelemetry.io/docs/zero-code/java/agent/performance/), [Coroot](https://coroot.com/blog/opentelemetry-for-go-measuring-the-overhead/) |

Lectura para nuestro caso: la industria tolera **5-10% en producción** y baja de nivel de
granularidad (método en vez de línea) antes que resignar la medición. Pero el porcentaje no es la
métrica correcta acá: los hooks del harness son sincrónicos y serializados, así que lo que importa
son **milisegundos por invocación**, y el presupuesto lo fija el hook más lento de la cadena, no
un porcentaje del proceso.

---

## Lo que NO se puede transplantar

- **Código de cualquiera de estas herramientas.** `manifests/external-tool-adoption-freeze.yaml`
  está `frozen: true` desde el 2026-05-11 por decisión comercial. Este informe describe
  mecanismos y doctrina pública; no propone adoptar ni portar implementaciones.
- **Los umbrales de Homebrew.** 1000 instalaciones en 90 días presupone millones de usuarios
  anónimos. Acá el n es 1. Con un solo operador no hay ley de grandes números: la diferencia
  entre 0 y 1 uso es una sesión, no una tendencia. Se copia la máquina de estados, no los números.
- **El grafo de SCARF.** Depende de compiladores que emiten dependencias reales por lenguaje. Acá
  buena parte de las aristas son nombres de archivo escritos dentro de markdown, YAML y JSON. El
  equivalente honesto de SCARF para nosotros no es el grafo: es el fallback textual, que ellos
  usan como red y nosotros tendríamos como señal principal.
- **coverage.py / JaCoCo sobre los scripts.** Miden funciones dentro de un proceso vivo y largo.
  Un script de shell lanzado por un agente es un proceso efímero: no hay dónde colgar un agente,
  y el arranque del profiler costaría más que el script. Sí aplicaría a `cos_lib/` si alguna vez
  se corre un proceso persistente.
- **La ventana estacional de CQSE, hoy.** "Varios meses incluyendo el cierre de año" es
  incompatible con retención de 30 días. Es una precondición, no una alternativa.
- **`activationEvents` para los 767 scripts.** Exige un host que controle la carga. Los scripts se
  invocan por bash arbitrario. Solo es aplicable a skills y hooks, que sí pasan por despachador —
  y ahí ya existe canal, que es justamente donde se ven 3 eventos.
- **vulture / knip / deadcode.** Ninguno lee markdown ni YAML. Sobre este repo reportarían muerto
  todo lo que se invoca por string desde documentación, que es la mayoría del catálogo.
- **Las descargas agregadas como modelo mental.** "Está listado en el catálogo" no es "se usó",
  igual que una descarga de npm no es un usuario.

---

## Fuentes

| # | Fuente | URL | Aporta |
|---|---|---|---|
| 1 | pytest — Writing plugins (oficial) | https://docs.pytest.org/en/stable/how-to/writing_plugins.html | `--trace-config`, `-p no:`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD`: registro ≠ invocación |
| 2 | pluggy (oficial) | https://pluggy.readthedocs.io/en/latest/ | `enable_tracing()`, `add_hookcall_monitoring(before, after)`: una envoltura observa todos los hooks |
| 3 | VS Code — Activation Events (oficial) | https://code.visualstudio.com/api/references/activation-events | La declaración de activación como instrumentación del host |
| 4 | VS Code — Deprecated extensions (discusión oficial) | https://github.com/microsoft/vscode-discussions/discussions/1 | No hay deprecación automática; es manual |
| 5 | lazy.nvim — Profiling (oficial) | https://lazy.folke.io/usage/profiling | `:Lazy profile`: el gestor mide qué cargó |
| 6 | Homebrew — Deprecating, Disabling and Removing (oficial) | https://docs.brew.sh/Deprecating-Disabling-and-Removing | Máquina de tres estados y umbrales 1000/90d, 6 meses, remoción al año |
| 7 | Meta — Automating dead code cleanup | https://engineering.fb.com/2023/10/24/data-infrastructure/automating-dead-code-cleanup/ | Grafo aumentado con logs; grep textual como red; 100M líneas |
| 8 | Meta — Dead Code Removal at Meta (FSE 2023) | https://dl.acm.org/doi/10.1145/3611643.3613871 | Paper del anterior |
| 9 | Teamscale/CQSE — Feature usage analysis | https://teamscale.com/blog/en/news/blog/does-anybody-use-this-feature | Ventana de meses con estacionalidad; medición a nivel de método |
| 10 | JaCoCo — FAQ (oficial) | https://www.jacoco.org/jacoco/trunk/doc/faq.html | Overhead del agente, inclusión/exclusión |
| 11 | coverage.py — How it works (oficial) | https://coverage.readthedocs.io/en/latest/howitworks.html | Cores `ctrace`/`pytrace`/`sysmon` |
| 12 | Batchelder — coverage.py con sys.monitoring | https://nedbatchelder.com/blog/202312/coveragepy_with_sysmonitoring.html | <5% de overhead, sin dynamic contexts |
| 13 | vulture (repo oficial) | https://github.com/jendrikseipp/vulture | Límites del estático: `getattr`, strings, imports dinámicos |
| 14 | knip — Handling issues (oficial) | https://knip.dev/guides/handling-issues | Falsos positivos por imports dinámicos y convenciones de framework |
| 15 | Iterative — Strengths and limitations of Knip | https://blog.iterative.engineering/2024/03/20/strengths-and-limitations-of-knip-for-unused-code-detection-in-angular/ | 22/36 detectados, 14 falsos positivos |
| 16 | npm — How download counts work | https://blog.npmjs.org/post/92574016600/numeric-precision-matters-how-npm-download-counts-work.html | "Direccional, no usuarios" |
| 17 | pypistats — FAQ | https://pypistats.org/faqs | Mirrors enmascaran/inflan; CI/CD incluido |
| 18 | atuin (repo oficial) | https://github.com/atuinsh/atuin | Modelo de datos de historial: cwd, exit code, duración, sesión |
| 19 | MattCASmith — bash history forensics | https://mattcasmith.net/2022/02/22/bash-history-basics-behaviours-forensics | Por qué `.bash_history` no sirve como corpus |
| 20 | Claude Code — settings (oficial) | https://docs.anthropic.com/claude/docs/claude-code/settings | `cleanupPeriodDays`, default 30 |
| 21 | anthropics/claude-code issue 59248 | https://github.com/anthropics/claude-code/issues/59248 | Borrado silencioso de transcripts, sin recuperación |
| 22 | OpenTelemetry — Java agent performance (oficial) | https://opentelemetry.io/docs/zero-code/java/agent/performance/ | Overhead de auto-instrumentación |
| 23 | Coroot — OTel para Go: midiendo el overhead | https://coroot.com/blog/opentelemetry-for-go-measuring-the-overhead/ | p99 de 10 ms a 15 ms |

---

## Correcciones a las premisas del encargo

1. **"766 scripts"** → `ls scripts/ | wc -l` da **767** entradas (incluye subdirectorios, no solo
   archivos ejecutables). El número correcto depende del criterio de conteo; el encargo no lo
   trae. Cualquier medición debería fijar el criterio antes que el número.
2. **"60 plantillas"** → `ls templates/ | wc -l` da **35**. El 60 solo cierra si se suman
   plantillas de `packages/*`; no pude reproducir 60 con un conteo simple del directorio raíz.
3. **"194 skills"** → `find . -name SKILL.md | wc -l` da **437**. La diferencia son skills de
   plugins externos y symlinks a `packages/*`. 194 puede ser el subconjunto propio, pero el
   encargo no dice cuál es el denominador, y esa ambigüedad es justamente la que produce
   auditorías que no se pueden replicar.
4. **"transcripts que ya registran cada comando ejecutado"** → cierto, y con `cwd` por registro,
   que es mejor de lo que esperaba. Pero **caducan a los 30 días por default y ya caducaron**:
   la ventana disponible hoy es 20-jul a 19-ago. Esta es la corrección que más cambia el plan.
5. **"medir uso pasado sin instrumentar nada"** → no se puede sostener. Antes de medir hay que
   fijar retención o volcar un extracto versionado; si no, la medición no es reproducible mañana,
   que es el requisito central de evidencia ejecutable.
6. **Cobertura de sub-agentes** → verificado que sí quedan registrados, en archivos de sesión
   propios (0 registros con `"isSidechain":true` en 22 archivos, y 267 lanzamientos de `Agent`;
   el uuid de esta misma sesión de sub-agente aparece como `.jsonl` propio en el directorio del
   proyecto). No asumir cobertura sin verificar esto en cada versión del harness: si cambiara,
   se perdería justo el tráfico donde más se invocan scripts.
7. **Existe un corpus alternativo que el encargo no menciona**: `.cognitive-os/*.jsonl` va del
   **8-may al 19-ago** (3,5 meses, contra 30 días de los transcripts), o sea tres veces más
   ventana. Contra: está en `.gitignore`, es local a esta máquina y registra otras cosas
   (cleanup, cola de trabajo, errores), no ejecución de scripts. Vale mirarlo antes de dar por
   único al corpus de transcripts.
