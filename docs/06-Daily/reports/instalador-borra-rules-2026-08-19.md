# El instalador copia 17 rules y borra 2 sin decir nada

**Fecha**: 2026-08-19 · **Scope**: OS · **Archivos**: `scripts/cos_init.py`,
`tests/integration/test_install_rules_manifest_parity.py`,
`docs/00-MOCs/entrypoints/getting-started.md`

## Resumen ejecutivo

- Confirmado y reproducido: `cos_init.py --default` en un directorio vacío deja
  **15 rules**, no las 17 que declara `manifests/primitive-install-boundary.yaml`.
  Faltan `model-routing.md` y `result-management.md`. Exit code 0, cero warnings.
- Causa: el **copiado** ya se deriva del manifest (`cos_init.py:1780`), pero el
  **filtro de efficiency-profile** usaba `COS_INIT_CORE_RULES`, una lista fija de
  16 nombres. Las dos rules se copian y ese filtro las borra.
- Arreglo: el filtro se deriva del mismo censo. `COS_INIT_CORE_RULES` se eliminó;
  no quedaron usos. El `--help` ahora deriva los tres números (decía "14").
- Test de efecto (no de intención): corre el instalador real y compara el disco
  contra el manifest. Con el bug **falla nombrando las dos rules**; con el arreglo pasa.
- 98 tests preexistentes de `cos_init` siguen en verde.
- Encontré una lista fija más de la misma clase: `scripts/cos-init-global.sh`
  (14 nombres, 4 víctimas). No la toqué.

## Correcciones a las premisas del encargo

1. **"agent-security.md está en la constante pero no en el manifest: entrada
   muerta, nunca llega"** — correcto pero incompleto: `agent-security.md` tampoco
   está en `DEFAULT_RULES` (el fallback de `cos_init.py:94`), así que en
   `--default` nunca se copia y la entrada nunca protegió nada. Sí tenía efecto en
   un camino que el encargo no menciona: `--full` con `cognitive-os.yaml`
   declarando `efficiency.profile: default` copia *todas* las rules y después
   filtra — ahí `agent-security.md` sobrevivía hoy y con mi cambio se borra. Es la
   conducta correcta (el manifest es el censo del perfil `default`, y su
   `purpose` dice "may project **only** primitives listed here"), pero es un
   cambio de comportamiento real, no una entrada inerte.

2. **"Verificá si `COS_INIT_CORE_RULES` se usa en más de un lugar"** — en Python
   se usaba en uno solo (`:977`). Pero existen **dos copias con otro nombre** que
   el encargo no anticipa, y una de ellas afirma por escrito un sincronismo que ya
   es falso:
   - `cmd/cos/internal/wizard/install.go:270` — `var coreRules` con **14** nombres
     y el comentario *"must stay in sync with CORE_RULES in hooks/self-install.sh
     and COS_INIT_CORE_RULES in scripts/cos-init.sh"*. `hooks/self-install.sh`
     CORE_RULES hoy tiene **2** entradas (`RULES-COMPACT.md`, `rate-limiting.md`):
     el sincronismo que el comentario promete no existe hace tiempo. Además cita
     `scripts/cos-init.sh`, que desde `da2534444` es un shim de una línea.
   - `scripts/cos-init-global.sh:50` — otra `CORE_RULES` de 14 (ver §Otras listas).

3. **"Rutas protegidas: el guard también bloquea leer esas rutas"** — no se
   reprodujo. `cat manifests/primitive-install-boundary.yaml` sin prefijo
   funcionó. Usé el prefijo igual sobre `hooks/self-install.sh` por precaución,
   pero la premisa "bloquea leer" no se verificó en esta sesión.

4. **El `--help` decía tres números mal, no uno.** El encargo señala "14 core
   rules"; la misma línea decía "10 curated skills, ~29 standard hooks" cuando el
   censo declara 8 y 44. Derivé los tres.

5. **Ya había un informe previo del hallazgo** (`listas-fijas-vs-censo-2026-08-19.md`,
   commiteado hoy) que describe el mismo defecto con el mismo número de línea. Este
   informe no lo descubre: lo reproduce, lo arregla y lo blinda con un test.

## Reproducción del defecto

Instalador corrido en un directorio vacío con el árbol en HEAD (`d7a503bbd`):

```bash
mkdir repro && cd repro && git init -q .
/…/luum-agent-os/.venv/bin/python3 /…/luum-agent-os/scripts/cos_init.py --default
```

```text
Cognitive OS initialized (default mode)
  Rules:  15 installed
  Hooks:  43 registered
  Skills: 8 available
```

```bash
ls .claude/rules/cos | sort
```

```text
RULES-COMPACT.md          error-learning.md         responsiveness.md
acceptance-criteria.md    license-policy.md         token-economy.md
adaptive-bypass.md        phase-aware-agents.md     trust-score.md
agent-quality.md          research-first-protocol.md
closed-loop-prompts.md    content-policy.md
credential-management.md  definition-of-done.md
```

15 archivos. **Ausentes**: `model-routing.md`, `result-management.md` — ambas
declaradas en `manifests/primitive-install-boundary.yaml >
profiles.default.primitives.rules` (17 entradas). Exit code `0`, ningún mensaje.

El desvío es *interno al propio instalador*: `cos_init.py:1780` arma la lista de
copiado con `_boundary_names(install_boundary, "rules", DEFAULT_RULES)` — o sea, el
manifest — y `:977` la filtraba contra `COS_INIT_CORE_RULES`. Las dos rules se
escriben en disco y se borran unos milisegundos después, en la misma corrida.

## Por qué existía el borrado

No es código muerto ni un accidente: es la única cosa que hace que el perfil
`default` sea realmente `default`. Nació en `58d7b8873` (`scripts/cos-init.sh`,
sección *"8b. Apply efficiency profile filtering"*) con este comentario:

> After rules are installed AND cognitive-os.yaml exists, apply profile filtering
> from cognitive-os.yaml. This mirrors the logic in self-install.sh so external
> projects get the same profile-aware rule restriction.

El orden importa: `cognitive-os.yaml` se escribe *después* de copiar las rules, y
puede pedir un perfil más chico que el flag de la línea de comandos (`--full` +
`efficiency.profile: default`). Sin el borrado, `--full` seguido de una config
`default` dejaría las 94 rules en contexto — que es exactamente lo que ADR-074 /
ADR-079 quieren evitar (~93.700 tokens contra un objetivo de ~3.500). El equivalente
en Go lo dice sin vueltas: *"This ensures that switching from full to standard
actually reduces the rule count."*

O sea: el borrado se queda. Lo que estaba mal era **contra qué lista borraba**.

## El arreglo

`scripts/cos_init.py`:

- Se elimina `COS_INIT_CORE_RULES` (16 nombres a mano). No quedan referencias:
  `grep -rn COS_INIT_CORE_RULES` solo devuelve docs y el comentario stale del Go.
- Nuevos helpers junto a `_boundary_names`:
  - `default_rule_names()` → stems del perfil `default` según el manifest, con
    `DEFAULT_RULES` como fallback solo si el YAML es ilegible.
  - `default_rule_files()` → el keep-set del filtro. Suma `RULES-COMPACT.md`
    incondicionalmente porque se instala fuera del loop del boundary
    (`cos_init.py:~1877`, índice compacto de ADR-074) y no debe caer ni por el
    camino de fallback.
  - `_default_mode_summary()` → la línea de `--help`, con skills/hooks/rules
    contados del censo.
- `_apply_efficiency_profile` filtra contra `default_rule_files()`.

La derivación se hace **adentro** del filtro con perfil `"--default"` fijo, no
recibiendo la lista de `main()`: bajo `--full` la variable `default_rules` de
`main()` cae al fallback (el manifest declara `primitives: all`, que no es un dict),
y el filtro, cuando corre, siempre tiene que aplicar el censo del perfil `default`.

Efecto (mismo comando de reproducción):

```text
  Rules:  17 installed
```

con `model-routing.md` y `result-management.md` presentes en los dos destinos
(`.claude/rules/cos/` y `.cognitive-os/rules/cos/`).

`--help`, antes y después:

```text
-  --default  10 curated skills, ~29 standard hooks, 14 core rules (~8K tokens/session)
+  --default  8 curated skills, 44 standard hooks, 17 core rules (~8K tokens/session)
```

Un nombre nuevo en `manifests/primitive-install-boundary.yaml` ahora se copia, se
conserva y se cuenta sin tocar `cos_init.py`.

## Prueba en las dos direcciones

`tests/integration/test_install_rules_manifest_parity.py`. Corre el instalador de
verdad en un `tmp_path` con `git init`, y compara los `.md` **en disco** contra el
manifest, en los dos sentidos (borradas y sobrantes). No lee ninguna constante del
instalador: leer la intención no puede detectar un filtro que la contradice.

**Con el bug** (`git show HEAD:scripts/cos_init.py > scripts/cos_init.py`):

```text
E   AssertionError: .claude/rules/cos: the installer copied these rules from the census
    and then deleted them — the consumer never sees them and gets no warning:
    ['model-routing.md', 'result-management.md']
E   AssertionError: .cognitive-os/rules/cos: … ['model-routing.md', 'result-management.md']
E   AssertionError: --help does not report the census count (17)
FAILED …::test_installed_rules_equal_the_census[.claude/rules/cos]
FAILED …::test_installed_rules_equal_the_census[.cognitive-os/rules/cos]
FAILED …::test_reported_rule_count_matches_disk
FAILED …::test_help_rule_count_is_derived_not_hardcoded
4 failed in 2.52s
```

**Con el arreglo**:

```text
$ .venv/bin/python3 -m pytest tests/integration/test_install_rules_manifest_parity.py -q
....                                                                     [100%]
4 passed in 2.47s
```

Sin regresiones en lo preexistente:

```text
$ .venv/bin/python3 -m pytest tests/unit/test_cos_init_py.py \
    tests/behavior/test_cos_init_parity_2_{1,2,3}.py \
    tests/contracts/test_cos_instance_profiles.py -q
98 passed in 13.52s
```

## Otras listas fijas en el camino de instalación

Una nueva, del mismo tipo y con víctimas nombradas:

| Lista | Ubicación | Censo que debería leer | Víctimas |
|---|---|---|---|
| `CORE_RULES` (14) | `scripts/cos-init-global.sh:50` | `manifests/primitive-install-boundary.yaml > profiles.default.primitives.rules` (17) | **`license-policy.md`, `research-first-protocol.md`, `model-routing.md`, `result-management.md`** nunca llegan a `~/.claude/rules/cos/`. Instala además `agent-security.md`, que no está en el censo. |

Su comentario dice *"Must match the CORE_RULES array in hooks/self-install.sh
exactly"* — `hooks/self-install.sh` CORE_RULES tiene hoy **2** entradas. La
afirmación de sincronismo es falsa y no hay nada que la chequee. Es el mismo
defecto silencioso pero en el install global: el operador cree tener el ruleset
universal y le faltan 4 reglas.

Y la copia en Go, ya listada en §Correcciones: `cmd/cos/internal/wizard/install.go:270`,
`coreRules` de 14, mismas 4 víctimas.

Ninguna de las dos la toqué: cambian *qué se instala* en caminos distintos
(install global, wizard Go) y eso es decisión del operador.

Las cuatro que ya reportó el informe previo (`settings-driver-claude-code.sh`,
`cognitive-os.yaml`, `portable_ai_overlay.py DEFAULT_HARNESSES`,
`check_hook_registration.py`) siguen sin tocar.

## Lo que NO hice y por qué

- **No agregué los dos nombres a mano** a la constante. Era el verde barato
  explícito: deja la lista igual de fija y el próximo elemento del manifest se
  pierde igual, otra vez en silencio.
- **No saqué el borrado.** Es lo único que hace que `--full` → `default` baje de
  verdad el conteo de rules (§Por qué existía el borrado).
- **No arreglé `cos-init-global.sh` ni el `coreRules` de Go.** Cambian qué se
  instala en otros caminos; van con decisión del operador. Quedan documentados
  arriba con sus víctimas.
- **No toqué `hooks/self-install.sh`** (ruta protegida): solo lo leí para
  desmentir los comentarios de sincronismo.
- **No commiteé ni pusheé.** Todo queda en el working tree.
- **Deuda de documentation-truth**: corregí el único doc que reproduce
  literalmente la línea del `--help` (`docs/00-MOCs/entrypoints/getting-started.md`).
  Siguen diciendo "14 core rules": `docs/07-Capabilities/root/agent-efficiency-strategy.md`,
  `docs/01-Build-Log/root/versioning-strategy.md`,
  `docs/05-Methodology/root/rules-consolidation-plan.md` (varias líneas),
  `docs/02-Decisions/adrs/ADR-093-simplify-profiles.md` y su `.synthesis.md`. No
  agregué el claim a `manifests/documentation-truth-claims.yaml` — es ruta
  protegida y el orquestador está commiteando en paralelo; queda como entrada
  explícita de deuda acá, que es la salida (b) que admite la disciplina de cierre.
