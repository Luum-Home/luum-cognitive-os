# Carga cognitiva de la documentación — 2026-08-15

> Encargo: bajar el abrumamiento de `docs/`, no su tamaño. Tres frentes:
> puertas de entrada, los 190 PoCs, y duplicación en `04-Concepts`.
> Todo número de acá abajo viene con el comando que lo produjo.

## Resumen

- **Punto 1 (puertas): hecho y commiteado** (`958845a18`). Tres puertas de
  instalación que se contradecían entre sí quedaron en una. Ninguna se borró.
- **Punto 2 (PoCs): la premisa del encargo es mayormente falsa.** 188 de 190 ya
  están protegidos en código, y 136 no son PoCs sino evaluaciones de repos
  ajenos: nunca "se convierten" en nada. Sí hay un hallazgo real: 10 veredictos
  ADOPT sin ADR.
- **Punto 3 (`04-Concepts`): la premisa también es falsa.** El bulto real es 275,
  no 378, y la duplicación medida es de **un** par confirmado, no de un patrón.
- **Correcciones al encargo: 6.** Están al final, en su propia sección.

---

## Punto 1 — Una sola puerta

### Lo que había

Nueve archivos, no ocho. `quickstart.md` faltaba en el encargo.

```bash
ls docs/00-MOCs/entrypoints/*.md | wc -l    # 9
```

Y en la raíz del repo hay otros dos con **el mismo nombre y distinto contenido**:
`README.md` (215 líneas, landing público) y `AGENTS.md` (229 líneas, reglas del
proyecto), contra `entrypoints/README.md` (960) y `entrypoints/AGENTS.md` (95).
Once superficies de entrada en total.

### ¿Competían?

El encargo pedía explícitamente reportar si **no** competían. Compiten, y la
evidencia es más fuerte que "se parecen": **se contradicen**.

| Puerta | Comando de instalación que daba |
|---|---|
| `quickstart.md` | `git clone .../luum-home/luum-agent-os` + `scripts/cos-init.sh` |
| `getting-started-quick.md` | `curl .../Luum-Home/luum-cognitive-os/.../install-cos.sh` |
| `getting-started.md` | `curl .../luum-home/luum-cognitive-os/.../install.sh` |

El remoto real:

```bash
git remote -v          # git@github.com:Luum-Home/luum-cognitive-os.git
```

Dos defectos duros en `quickstart.md`, la puerta más corta y por eso la más
probable de seguir:

1. Clonaba `luum-agent-os`, que no es el nombre del remoto. El clon no resolvía.
2. Ofrecía `cos-init.sh --full` / `--minimal` / `--standard`. Esos flags no
   existen:
   ```bash
   grep -nE 'minimal|standard|full' scripts/cos-init.sh   # sin salida
   ```

O sea: el problema no era solo que hubiera tres puertas, sino que la más barata
de leer estaba rota.

### Qué contenía cada una, y qué quedó

| Puerta | Contenido propio | Qué quedó |
|---|---|---|
| `getting-started.md` (605 l) | Prerequisitos, instalación, coexistencia con `.claude/`, primer run, primer pipeline SDD, tests, notificaciones, otros IDEs, self-repair, Docker headless | **La puerta única.** Absorbió lo de las otras dos |
| `getting-started-quick.md` (98 l) | Instalación en 30s, `cos new --template`, `cos init`, tabla "You say / COS does", comandos esenciales, claves de `cognitive-os.yaml` | Todo preservado en la sección *Fast path*. El archivo quedó como redirect |
| `quickstart.md` (56 l) | `upgrade.sh`, `uninstall.sh`, el patrón de clon único, matriz sin-Docker | `upgrade`/`uninstall` preservados en *Upgrade and uninstall*. La matriz **no se copió: la de `getting-started.md` ya era un superconjunto** (incluye la fila del CLI `cos`). El archivo quedó como redirect, y explicita por qué perdió sus comandos |
| `INDEX.md` (352 l) | Índice de 18 categorías + sección *Entry Points* | Se queda. Se le agregó una tabla que rutea las nueve puertas **por pregunta del lector** |
| `AGENTS.md` (95 l) | Tabla tarea→doc, glosario, lista *What NOT to Read* | Se queda. Lector distinto y bien definido: un agente ruteando |
| raíz `AGENTS.md` (229 l) | Tabla de arquitectura, vocabulario | Se queda. Distinto del anterior pese al nombre |
| raíz `README.md` (215 l) | Pitch, badges, lista "Cognitive OS is NOT" | Se queda. Es el landing público |
| `overview.md` (343 l) | Diagrama de arquitectura, inventario de primitivas, data flow, MAPE-K | Se queda |
| `faq.md` (350 l) | 10 secciones en forma de pregunta | Se queda |
| `HOW-TO-USE-COS.md` (228 l) | Auto-construcción, `cos-skill`, usar COS en otros proyectos | Se queda |
| `README.md` entrypoints (960 l / 115 KB) | Arquitectura de largo plazo, capas futuras, specs YAML | Se queda, **marcado en el índice como material de diseño, no camino de adopción** |

**No se creó ningún archivo nuevo.** El "verde barato" de este lote era escribir
una novena puerta; se evitó porque `INDEX.md` ya tenía una sección *Entry Points*
y ya nombraba a `getting-started.md` como la puerta de instalación —
`quickstart.md` y `getting-started-quick.md` ni figuraban. El índice ya había
decidido; los archivos no se habían enterado.

### Por qué redirects y no borrado

```bash
git grep -l 'entrypoints/quickstart.md'          | wc -l   # 13
git grep -l 'entrypoints/getting-started-quick.md' | wc -l # 12
```

25 documentos apuntan a esos dos. Borrarlos recreaba exactamente los enlaces
rotos que se arreglaron hoy.

### Verificación de enlaces, antes y después

Enlaces relativos salientes que no resuelven, sobre los 4 archivos tocados:

```bash
# reproducible: compara HEAD contra el working tree
cd docs/00-MOCs/entrypoints
for f in getting-started.md quickstart.md getting-started-quick.md INDEX.md; do
  grep -oE '\]\([^)]+\)' "$f" | sed 's/](//;s/)$//' \
  | while read -r l; do case "$l" in http*|\#*) continue;; esac
      t="${l%%#*}"; [ -n "$t" ] && [ ! -e "$t" ] && echo "BROKEN $f -> $l"; done
done | wc -l
```

| | Enlaces salientes rotos |
|---|---|
| En `HEAD` (antes) | **57** |
| Después del commit | **55** |

Cero rotos por este cambio; dos reparados. Los 55 que quedan son **preexistentes
y casi todos de `INDEX.md`**: enlaces planos (`adrs/`, `hooks.md`,
`runbooks/`) que asumen el layout anterior a la reorganización en carpetas
numeradas. **Es un hallazgo abierto**: el documento que existe para orientar es
el que más enlaces muertos tiene. No lo arreglé — es volumen aparte y toca
rutas de otro agente.

Las nueve anclas nuevas (`#fast-path-one-minute`, `#use-it`, etc.) se
verificaron una por una contra los encabezados reales del destino: 9/9 resuelven.

### Corrección de paso

`INDEX.md` declaraba `Docs | 1 209 files, including 1 140 markdown files`.
Medido: **1 955 archivos, 1 852 markdown** (1 433 sin contar los 419
`*.synthesis.md` generados). Corregido en el mismo commit.

---

## Punto 2 — Los 190 PoCs

### El veredicto: la pregunta del encargo no aplica a la mayoría

```bash
find docs/03-PoCs -name '*.md' | wc -l              # 190
find docs/03-PoCs/research -name '*.md' | wc -l     # 188
```

**188 de 190 ya están protegidos en código**, no por convención:

```
cos_lib/delete_intent.py:20-25
PROTECTED_PREFIXES = ("docs/03-PoCs/research/", "docs/06-Daily/reports/", ...)
```

El operador ya decidió esto y está escrito. Los 2 restantes son
`root/research-log.md` y `proposals/doctrine-amendment-*.md`.

Y la composición desarma la premisa:

| Subdirectorio | Archivos | Qué es |
|---|---|---|
| `research/repo-scout/deep` | 73 | Evaluación profunda de repos **externos** |
| `research/repo-scout/monitor-followup` | 43 | Seguimiento de esos repos |
| `research/repo-scout` | 20 | Clusters del landscape externo |
| `research/orchestration-gaps` | 13 | Gaps de orquestación |
| `research` (raíz) | 39 | Investigación por tema/herramienta |
| `root` + `proposals` | 2 | Log y enmienda de doctrina |

**136 de 190 son reconocimiento sobre repositorios ajenos.** No son experimentos
propios que "prosperaron o no": son el registro de qué se evaluó y qué se
descartó. Su clase epistémica es la de `06-Daily/reports` — que el propio encargo
declara intocable. Preguntarles "¿te convertiste en código?" es la pregunta
equivocada; la respuesta correcta para casi todos es "nunca fue el punto".

Además ya están indexados: `docs/03-PoCs/research/INDEX.md` (generado
2026-05-07) navega los 190 por sección. La carga cognitiva de este corpus ya
tenía dueño.

### Dónde sí hay un hallazgo: veredictos ADOPT sin ADR

Los repo-scout traen frontmatter legible por máquina:

```bash
grep -rhoE '^deep_verdict: *[A-Za-z-]+' docs/03-PoCs/research/repo-scout/ \
  | sed 's/^deep_verdict: *//' | sort | uniq -c
#   18 ADOPT
#    4 TRIAL
```

Cruzando cada ADOPT contra el ADR que cita, y verificando que ese ADR exista:

```bash
grep -rlE '^deep_verdict: *ADOPT' docs/03-PoCs/research/repo-scout/ | while read f; do
  adr=$(grep -oE 'ADR-[0-9]{3}' "$f" | head -1)
  if [ -n "$adr" ] && ls docs/02-Decisions/adrs/${adr}-*.md >/dev/null 2>&1
    then echo "CONVERTED $(basename $f) -> $adr"; else echo "NO-ADR-LINK $(basename $f)"; fi
done
```

| Estado | Cuenta | Detalle |
|---|---|---|
| **Convertido** | 8 | ADR-049 ×4, ADR-033 ×2, ADR-139 ×1, y `simonw/llm` → ADR-049 |
| **Indeterminado** (ADOPT sin ADR) | 10 | `aider`, `LightRAG`, `HippoRAG`, `SWE-agent`, `dspy`, `graphiti`, `gepa`, `crawl4ai`, `mempalace`, `agents.md` |
| **Sin veredicto legible** | 168 | No tienen campo `deep_verdict` |

Los 10 indeterminados son el único trabajo accionable del punto 2: son
decisiones "adoptar" que nunca aterrizaron en un ADR. **No propongo borrarlos** —
propongo el camino contrario, que es el que pedía el encargo: marcarlos. Un
ADOPT de hace tres meses sin ADR o se convierte en decisión o se dice que no
prosperó.

**No toqué nada acá.** El corpus está protegido en código y la acción correcta
(abrir ADRs o marcar "no prosperó") es una decisión del operador, no una edición.

---

## Punto 3 — Duplicación en `04-Concepts`

### El bulto real es 275, no 378

```bash
find docs/04-Concepts -name '*.md' | wc -l                    # 378
find docs/04-Concepts -name '*.synthesis.md' | wc -l          # 103
```

103 son `*.synthesis.md`, que `cos_lib/context_injector.py` sirve **en lugar** del
`.md` hermano. No son duplicados y no se tocan. El bulto trabajable es **275**.

Recuento completo del territorio:

| Carpeta | Total | Synthesis | Real |
|---|---|---|---|
| 02-Decisions | 510 | 150 | 360 |
| 06-Daily | 385 | 0 | 385 |
| 04-Concepts | 378 | 103 | **275** |
| 03-PoCs | 190 | 0 | 190 |
| 09-Quality | 143 | 71 | 72 |
| 08-References | 95 | 47 | 48 |
| 05-Methodology | 86 | 38 | 48 |
| 07-Capabilities | 21 | 10 | 11 |
| 01-Build-Log | 18 | 0 | 18 |
| 00-MOCs | 17 | 0 | 17 |
| 99-Archive | 8 | 0 | 8 |
| **Total** | **1 852** | **419** | **1 433** |

### La duplicación medida: mucho menos de lo esperado

Títulos H1 repetidos entre los 275:

```bash
find docs/04-Concepts -name '*.md' ! -name '*.synthesis.md' \
  | while read f; do grep -m1 '^# ' "$f"; done | sort | uniq -c | sort -rn | awk '$1>1'
#   3 Moved
#   2 OS vs Project Separation
```

Los tres "Moved" son stubs de redirect ya existentes (`harness-adoption-gap/ADR-00*.md`)
— o sea, consolidación **ya hecha** por alguien más, bien hecha.

Basenames repetidos:

| Par | Tamaños | Lectura |
|---|---|---|
| `patterns/cross-harness-authoring.md` vs `architecture/cross-harness-authoring.md` | 18 l vs 211 l | El de 18 líneas es puntero, no duplicado. **Coincidencia, no deuda** |
| `patterns/os-vs-project.md` vs `root/os-vs-project-separation.md` | 79 l vs 138 l | Mismo H1, tamaños distintos. **Candidato** |
| `patterns/dogfooding.md` vs `root/dogfooding.md` | 78 l vs 81 l | Tamaño casi igual, H1 casi igual. **El candidato más claro** |
| `README.md` ×3 | — | Uno por subdirectorio. Coincidencia estructural |

**Conclusión medida: 2 candidatos reales de consolidación sobre 275 archivos.**
El encargo describía `04-Concepts` como "varios documentos cubriendo el mismo
concepto porque cada uno se escribió sin ver los otros". Eso no es lo que muestra
la medición. Hay un patrón `patterns/X.md` ↔ `root/X.md`, pero es de **dos casos**,
no sistémico.

No consolidé ninguno: son dos, el presupuesto se fue en el punto 1 (que era la
prioridad indicada), y **la medición era el entregable admitido** para este punto.
Aplicando el criterio del encargo — *¿un cambio en uno debería obligar a tocar el
otro?* — los dos pares de `dogfooding` y `os-vs-project` dicen que sí, y son deuda
real; `cross-harness-authoring` dice que no, y es coincidencia.

---

## Correcciones a las premisas del encargo

Seis, todas verificadas:

1. **"ocho puertas de entrada"** → son **nueve** en `entrypoints/`. Faltaba
   `quickstart.md`. Y hay dos más en la raíz del repo (`README.md`, `AGENTS.md`)
   con nombre repetido y contenido distinto: **once superficies**.
2. **"Tres son variantes de cómo empezar"** → son tres, pero el problema no era la
   redundancia sino la **contradicción**: tres comandos de instalación distintos,
   uno con URL de clon que no resuelve y flags que no existen.
3. **"04-Concepts 378 — el bulto"** → el bulto real es **275**; 103 son synthesis
   que no se tocan.
4. **"03-PoCs 190 — el bulto"** → **188 ya están protegidos en código**
   (`cos_lib/delete_intent.py:20-25`), y **136 son evaluaciones de repos externos**,
   no PoCs propios. La pregunta "¿se convirtió en algo del repo?" no les aplica.
   Además ya tienen índice propio desde 2026-05-07.
5. **"buscá duplicación y superposición en 04-Concepts"** → medida: **2 candidatos
   reales sobre 275**. La premisa de duplicación extendida no se sostiene.
6. **"el índice que existe para reducir la carga cognitiva es él mismo una decisión
   de ocho opciones"** → parcialmente falso. `INDEX.md` **ya ruteaba por pregunta**
   y **ya nombraba una sola puerta de instalación**. El índice estaba bien; los
   archivos que no figuraban en él eran el problema.

### Lo que el encargo acertó

- Que el problema es humano y no de tokens. Confirmado: los 419 synthesis, que son
  el 23% de los archivos, ni siquiera los lee un humano.
- Que consolidar borrando contenido único sería el fracaso. Por eso la matriz
  sin-Docker de `quickstart.md` se verificó como subconjunto **antes** de no
  copiarla.
- Que había que verificar enlaces antes y después. Fue lo que permitió afirmar
  57 → 55 en vez de "no rompí nada".

---

## Hallazgos abiertos (no accionados)

| # | Hallazgo | Por qué no lo toqué |
|---|---|---|
| 1 | **55 enlaces salientes rotos**, casi todos en `INDEX.md`, por el layout previo a las carpetas numeradas | Preexistente y de volumen; toca rutas de todo `docs/` |
| 2 | **10 veredictos ADOPT sin ADR** en repo-scout | Corpus protegido en código; abrir ADR o marcar "no prosperó" es decisión del operador |
| 3 | **`patterns/dogfooding.md` ↔ `root/dogfooding.md`** y **`patterns/os-vs-project.md` ↔ `root/os-vs-project-separation.md`** | Deuda real de consolidación, 2 pares; sin presupuesto |
| 4 | `entrypoints/README.md` son 115 KB / 960 líneas de arquitectura futura bajo el nombre más invitador del directorio | Lo marqué en el índice como material de diseño; renombrarlo mueve 71 referencias |

---

## Cambios aplicados

Un commit, con paths explícitos (`git commit --only -- <paths>`):

```
958845a18 docs(entrypoints): collapse three install doors into one, routed by reader question
  docs/00-MOCs/entrypoints/getting-started.md        (+ fast path, + upgrade/uninstall, + tabla por pregunta)
  docs/00-MOCs/entrypoints/getting-started-quick.md  (-> redirect, contenido preservado arriba)
  docs/00-MOCs/entrypoints/quickstart.md             (-> redirect, + por qué perdió sus comandos)
  docs/00-MOCs/entrypoints/INDEX.md                  (+ ruteo de las 9 puertas, conteo corregido)
```

Cero archivos creados. Cero archivos borrados. Cero enlaces rotos nuevos.
