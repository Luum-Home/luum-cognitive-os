# Aislamiento de agentes concurrentes sobre un checkout compartido

**Fecha:** 2026-08-19
**Alcance:** investigación externa (>=25 fuentes) + evidencia ejecutable local sobre semántica de git.
**Freeze de adopción vigente:** acá hay patrones y mecanismos, no propuestas de importar código.

---

## Resumen ejecutivo

1. **La regla más barata es una línea de prohibición: los sub-agentes no corren `git add` ni `git commit --amend` sin pathspec. Commitean con `git commit -m "..." -- <paths>`.** Verificado localmente: ese modo ignora el índice y lo deja intacto (E1), mientras que `--amend` sin pathspec barre el índice ajeno y mete archivos de otros en el commit (E2) — exactamente el incidente de hoy. Costo: una línea en `templates/agent-mandatory-rules.md` y, si se quiere diente, un `deny` en el hook de Bash.
2. **La segunda más barata: poner `isolation: worktree` en el frontmatter de los agentes de escritura.** Claude Code v1.32885.1 (el instalado) tiene aislamiento **con bloqueo real** — cuatro checks que rechazan la tool call, no la sugieren. Hoy **ningún** agente del repo lo declara (`grep -rn '^isolation:' .claude/agents agents` → 0 sobre 3 archivos).
3. **`GIT_INDEX_FILE` por agente es una trampa**, no una solución barata: sin `git read-tree HEAD` previo, el commit resultante **borra todos los archivos del árbol** (E5b: `D mine.txt`, `D theirs.txt`). No recomendarlo suelto.
4. **`git stash` es compartido entre worktrees** — verificado en este repo: main y un worktree de agente resuelven ambos a `.git/refs/stash`. Tres proyectos distintos (Claude Code, Copilot CLI, Orca) tienen el mismo bug abierto.
5. El aislamiento que ya existe no se usa porque es **texto en el prompt**, y el propio upstream concluyó que eso no alcanza: *"this needs a harness-level fix, not a prompt-level one"* (issue #76197, 2026-07-09).

---

## Correcciones a las premisas del encargo

1. **"15 worktrees vivos hoy" → son 13.** `git worktree list | wc -l` da 15, pero esa lista incluye el checkout principal y un worktree del scratchpad de esta sesión (`land/hooks-context-shape`). Los worktrees de agente son 13: `git worktree list | grep -c '.cos-agent-worktrees'` → `13`.

2. **"ADR-223 con worktrees por agente" es correcto, pero no es el ADR del *enforcement*.** ADR-223 se titula `Agent Lifecycle Reconstruction: Worktree-Per-Write-Agent`. El que promete forzar el cwd es **ADR-035 `Worktree CWD Enforcement: 3-Layer Defense`, con `implementation_status: partial`** — la propia ficha del ADR ya declara que no está entero. ADR-239 (`Isolated Worktree Default for Write Agents`, `implemented`) extiende a ADR-035/094/182/223/225.

3. **"el aislamiento es advisory" es cierto pero incompleto: existe un enforcer y está sin registrar.** `hooks/agent-bash-cwd-enforcer.sh` existe (10.683 bytes, modificado hoy) y hasta tiene un texto `BLOCKER WARNING: git command issued from WRONG DIRECTORY`, pero (a) `grep -c 'agent-bash-cwd-enforcer' .claude/settings.json` → `0`, no está registrado; y (b) sus dos `permissionDecision` son `"allow"`. O sea: aunque se registrara hoy, avisa, no bloquea. El único hook de worktree registrado es `session-start-worktree-nudge.sh` — "nudge", el nombre lo dice.

4. **"el índice de git también es compartido — un agente deja archivos staged" — cierto como mecanismo, pero el índice está limpio ahora.** `git diff --cached --name-only` al arrancar esta tarea devolvió vacío, con 30+ archivos modificados sin stagear. La condición de carrera existe; el estado actual no la muestra. Importa porque cualquier medición de "cuántos archivos ajenos hay staged" hecha ahora daría cero y se leería como "el problema no existe".

5. **La causa raíz declarada tiene una tercera pata que el encargo no nombra: la atribución por sesión, no por repo.** Al intentar reproducir el incidente en un repo descartable del scratchpad, `hooks/destructive-git-blocker` lo bloqueó con `op='git commit -qm base on main'`. Ese repo fue creado con `git init -b exp` y no tiene rama `main`: el hook clasificó por la rama de **la sesión**, no por el repo que el comando toca. Es la misma familia de error que el incidente — una operación de git atribuida al repo equivocado. Destrabado con el token documentado `# --allow-destructive --allow-main-branch`; ninguna escritura tocó el repo del proyecto.

6. **`git commit -- <paths>` no es la bala de plata que sugiere el encargo para `--amend`.** Sirve para el commit normal (E1) y también para el amend (E3: el índice ajeno sobrevive), pero `--amend` con pathspec **igual arrastra lo que el commit anterior ya tenía**. Si el commit que se está corrigiendo ya venía contaminado, el pathspec no lo limpia. La documentación de git lo dice: *"The recorded tree is prepared as usual (including the effect of the `-i` and `-o` options and explicit pathspec)"*.

---

## Los tres problemas y cómo los resuelve la comunidad

### 1. Scratchpad / directorio temporal compartido

El patrón dominante no es un mecanismo nuevo: es **no derivar el nombre del temporal de nada estable**. `mktemp -d` genera un directorio privado (`drwx------`) con nombre aleatorio; el colapso ocurre cuando el harness le da a todos los agentes hermanos **el mismo** directorio de sesión, que es exactamente lo que pasó hoy — el path del scratchpad es por sesión, no por agente.

Tres niveles, de más barato a más caro:

- **`TMPDIR` por agente.** `mktemp` respeta `$TMPDIR`; si el harness exporta un `TMPDIR` distinto por sub-agente, todo lo que use `mktemp`, `tempfile` de Python o `File::Temp` queda separado sin tocar una línea de código de agente. Es la vía más barata y la menos citada en la literatura de agentes, que salta directo a contenedores.
- **Sesión/terminal por agente.** `amux` le da a cada agente su propia sesión de tmux con acceso de filesystem configurable.
- **Sandbox del SO.** Codex CLI es el caso extremo y el único CLI mayor con sandbox por defecto: Seatbelt en macOS, Landlock + seccomp en Linux, tokens restringidos en Windows; `codex-rs/linux-sandbox/src/landlock.rs` da lectura universal y **escritura solo a directorios explícitamente whitelisteados**. Ahí el aislamiento no es advisory porque el agente físicamente no puede escribir afuera.

### 2. El índice de git compartido

Acá la comunidad se dividió en tres respuestas, y las tres están documentadas con fallas.

**(a) Worktree por agente — índice propio, resto compartido.** Verificado en este repo: el worktree de agente resuelve su índice a `.git/worktrees/<id>/index` mientras el principal usa `.git/index`, y ambos comparten `--git-common-dir`. La doc de git lo formaliza: *"In general, all pseudo refs are per-worktree and all refs starting with `refs/` are shared"*. El índice y HEAD quedan aislados; refs, config, hooks y stash **no**.

**(b) Índice explícito por proceso (`GIT_INDEX_FILE`).** Funciona pero tiene un filo. Medido (E4/E5b): dos `git add` con `GIT_INDEX_FILE` distintos no se pisan y el índice compartido queda intacto — pero un `git commit` desde un índice **no sembrado** produjo un commit cuyo árbol contiene **solo** el archivo agregado, borrando el resto (`A a.txt / D mine.txt / D theirs.txt`). Sembrándolo con `git read-tree HEAD` primero (E6), el diff vuelve a ser el correcto: `A c.txt`. La receta segura es de dos pasos, no de uno.

**(c) Prohibir el índice: `git commit -- <paths>`.** La doc de git es explícita — al listar archivos como argumentos *"the commit will ignore changes staged in the index, and instead record the current content of the listed files (which must already be known to Git)"*. Medido (E1): el commit de A contiene solo `mine.txt`, y `theirs.txt`, que el agente B había dejado staged, **sigue staged** después. Cero configuración, cero variables de entorno, cero infraestructura. Limitación real: los archivos deben ser ya conocidos por git — un archivo **nuevo** no se puede commitear así sin un `git add` previo.

Y la falla transversal que nadie resolvió del todo: el lock. El issue #55724 de claude-code (2026-05-03) lo mide: *"Tested with 13 parallel agents: 5 committed successfully, 8 failed due to lock contention"*, con el error `Unable to create '.git/index.lock': File exists`. La mitigación propuesta es reintento con backoff *"3-5 times with exponential backoff (200ms, 400ms, 800ms)"*, y la prioridad que el reporte le asigna no es esa sino la otra: *"Fix 2 is the most important — even if contention can't be fully eliminated, preserving uncommitted work prevents data loss."*

### 3. `--amend` y las operaciones que reconstruyen desde el índice

Medido. Ver la sección de operaciones inseguras más abajo: `--amend` sin pathspec es el caso reproducido, y no está solo.

---

## Por qué el aislamiento que ya existe no se usa

Tres razones, en orden de peso.

**1. Porque es texto, y el texto no obliga.** `hooks/agent-working-dir-inject.sh` declara en su propio encabezado que *"injects a WORKING DIR directive into every sub-agent's additionalContext"* y su salida es `hookSpecificOutput.additionalContext`. Eso es contexto, no permiso. El upstream llegó a la misma conclusión midiéndola: en el issue #76197 (2026-07-09), el cwd de un sub-agente con `isolation: "worktree"` *"can silently drift back to the main repo root across the agent's own later tool calls"*, y los commits *"land in the **main repo checkout** instead of the isolated worktree"* — **"despite prompt-level hardening telling the subagent to stay inside its worktree — meaning this needs a harness-level fix, not a prompt-level one"**. El repo está aplicando la estrategia que upstream ya descartó por medición.

**2. Porque el enforcement nativo existe y no está declarado.** La documentación oficial de Claude Code tiene una sección entera, "How Claude Code enforces isolation", que no describe sugerencias sino bloqueos: *"Claude Code blocks an `Edit`, `Write`, or `NotebookEdit` that targets a path in the main checkout"*; *"blocks a Bash, PowerShell, or Monitor command whose working directory resolves to the main checkout"*; *"blocks a Bash or Monitor command that redirects git into the main checkout"* — incluyendo vía `git -C`, `--git-dir`, `GIT_DIR`, `GIT_WORK_TREE` o un `cd` previo; y un cuarto check de forma de comando que *"You can't turn this check off"*. Ese mecanismo se activa poniendo `isolation: worktree` en el frontmatter del sub-agente. En este repo hay 3 archivos de agente y **ninguno** lo declara. El aislamiento no se usa, en parte, porque se construyó uno propio en vez de declarar el que ya venía.

**3. Porque incluso el nativo falla bajo concurrencia, y eso enseña la lección correcta.** El issue #83311 (2026-08-02) reporta que con 5 agentes concurrentes *"2 of 5 agents got correct isolated worktrees ... the other 3 exhibited the contamination"*: un commit de un agente cayó en la rama de otro, aparecieron *"`git stash` entries in the main repository"*, y *"The parent repo's uncommitted working-tree changes were stashed/reverted out from under the user by a child agent"*. La conclusión no es "el aislamiento no sirve" sino **"no apoyar la seguridad en una sola capa"**: si la disciplina de comandos (no `git add`, no `--amend` pelado) hubiera estado vigente, la contaminación de PR de ese reporte no habría podido ocurrir aunque el worktree fallara.

Corolario: la razón por la que un worktree "no aísla" cuando el agente puede ignorarlo es que **el worktree nunca fue una frontera**. Fletch lo dice sin vueltas (2026-07-30): *"A worktree was never a boundary. It is a second working directory attached to one `.git`, and everything interesting lives in that `.git`"* — y enumera qué se comparte: refs, config, `refs/stash` y, el peor, *"**Hooks** (`.git/hooks`), which is where a shared directory becomes arbitrary code execution"*. Su recomendación: *"worktree when a person is driving, clone when something else is. The cost is the same either way."*

---

## Las opciones ordenadas por costo

| # | Opción | Qué previene | Qué NO previene | Costo |
|---|--------|--------------|-----------------|-------|
| 1 | **Prohibir `git add` y `--amend` sin pathspec en sub-agentes; commitear con `git commit -m "..." -- <paths>`** | Arrastrar archivos staged por otro agente (E1); barrer el índice ajeno con `--amend` (E2). Cubre las dos causas raíz declaradas del incidente. | Archivos **nuevos** (no conocidos por git) no se pueden commitear sin `git add`; no previene contención de `index.lock`; no previene que dos agentes editen el mismo archivo. | **Mínimo.** Una línea en `templates/agent-mandatory-rules.md`. Con diente: un patrón `deny` en el hook de Bash — el repo ya tiene la maquinaria (`destructive-git-blocker`). |
| 2 | **Declarar `isolation: worktree` en el frontmatter de los agentes de escritura** | Edits, cwd de Bash y redirecciones de git hacia el checkout principal — bloqueadas por el harness, no por el prompt. | Es inconsistente bajo concurrencia alta (#83311: 3 de 5 fallaron); no aísla stash, refs, config ni hooks. | **Bajo.** Una línea de frontmatter por agente (3 archivos hoy). Ojo: cambia el cwd real de los agentes; hay que revisar los hooks que asumen el checkout principal. |
| 3 | **`TMPDIR` propio por agente** | Que un hermano pise el archivo temporal de otro — la causa raíz nº1 del incidente. Aplica automáticamente a `mktemp`, `tempfile`, `File::Temp`. | Nada de git: no toca índice, ni stash, ni refs. | **Bajo.** Exportar un `TMPDIR` derivado del id del agente en el hook que ya inyecta contexto. |
| 4 | **Reintento con backoff sobre `index.lock`** | La pérdida de trabajo por contención transitoria (8 de 13 agentes en #55724). | Nada de atribución cruzada: un commit que sale con los archivos equivocados sale igual, solo que al segundo intento. | **Bajo.** Wrapper de `git commit` con 3-5 reintentos (200/400/800 ms). |
| 5 | **`GIT_INDEX_FILE` por agente** | Colisión de `git add` entre agentes (E4). | **Introduce un riesgo peor si se usa mal**: sin `git read-tree HEAD` previo, el commit borra todo el árbol (E5b). | **Medio y con filo.** Siempre dos pasos: `read-tree` y después `add`. No recomendado si ya se aplicó la opción 1, que lo vuelve innecesario. |
| 6 | **Forzar el cwd del sub-agente (registrar + endurecer `agent-bash-cwd-enforcer.sh`)** | Que los comandos del agente corran en el checkout del operador. | El drift documentado en #76197 ocurre **sin `cd` explícito** del agente — un enforcer que inspecciona el texto del comando no lo ve. | **Medio.** El hook existe; hay que registrarlo y cambiar `permissionDecision: "allow"` por `"deny"`. Riesgo de falsos positivos alto (ver corrección nº5: el blocker de hoy clasificó por rama de sesión, no por repo destino). |
| 7 | **`git clone --shared` por agente en vez de worktree** | Todo lo del worktree **más** stash, refs, config y hooks compartidos. | Costo de sincronización de vuelta; el objeto store sigue compartido con `--shared` (borrar el clon con commits no mergeados pierde trabajo). | **Alto.** Cambia el ciclo de vida completo del agente. Es la recomendación de Fletch, con la medición de que *"The cost is the same either way"* en tiempo de creación. |
| 8 | **Contenedor por agente (container-use / Sculptor)** | Filesystem, red y servicios. Aislamiento real. | Nada gratis: setup de entorno por contenedor, `.env`, dependencias. | **Alto.** Infraestructura nueva. Bajo freeze de adopción, queda como referencia. |

**Recomendación:** 1 + 3 ahora (juntas cuestan dos líneas y cubren las dos causas raíz declaradas), 2 como siguiente paso, 4 si vuelve a aparecer `index.lock`. Las opciones 5 a 8 no se justifican hoy.

---

## Qué operaciones de git son inseguras bajo concurrencia

Clasificación con la evidencia que la sostiene. "Inseguro" = puede afectar el trabajo de otro agente/sesión sin avisar.

### Inseguras — reconstruyen desde el índice compartido

| Operación | Por qué | Evidencia |
|---|---|---|
| `git commit --amend` **sin** pathspec | Reconstruye el árbol desde el índice completo: mete todo lo que otro dejó staged y deja el índice vacío. | E2 medido: el commit pasó de `mine.txt` a `mine.txt` + `theirs.txt`; `git diff --cached` quedó vacío. Es el incidente. |
| `git commit` **sin** pathspec | Mismo mecanismo, sin la reescritura. | Doc de git: el modo con paths es el que *"ignore changes staged in the index"*; sin paths, commitea el índice. |
| `git commit -a` | Stagea todo lo modificado del árbol, incluidos los archivos de otro agente. | Corolario directo del anterior. |
| `git add` (cualquier forma) | Deja residuo en un índice que otro va a commitear. Además compite por `.git/index.lock`. | #55724: `Unable to create '.git/index.lock': File exists`, 8 de 13 agentes fallaron. |
| `git commit --include` / `-i` | *"Before making a commit out of staged contents so far, stage the contents of paths given on the command line as well"* — arrastra lo staged por definición. | Doc de git, verbatim. |

### Inseguras — tocan estado compartido entre worktrees

| Operación | Por qué |
|---|---|
| `git stash` / `git stash pop` / `git stash drop` | `refs/stash` es **una sola pila para todo el repo**. Verificado acá: main y worktree de agente resuelven ambos a `.git/refs/stash`. Confirmado como bug en tres productos: claude-code #83311, copilot-cli #1725 (2026-02-27), orca #13695. Un `pop` puede aplicar o descartar el stash de otro. |
| `git gc` / `git prune` | Opera sobre el object store compartido; afecta a todos los worktrees a la vez. |
| `git branch -f` / `git push --force` / update de refs | `refs/heads` es un namespace único para todos los worktrees. |
| `git checkout <branch>` / `git switch` | Cambia HEAD del worktree y reescribe el árbol; si el cwd derivó al checkout principal (#76197), reescribe el del operador. |
| `git reset --hard` | Idem, destructivo. #83311 reporta agentes *"fighting HEAD resets from concurrent background agents"*. |
| `git rebase` / `git rebase --onto` + force-push | Reescribe historia compartida. Ya prohibido por la norma `merge-sobre-rebase` del perfil. |
| Escribir en `.git/hooks` | Compartido: código arbitrario que corre en el próximo commit del operador (Fletch). |

### Seguras (o razonablemente seguras)

| Operación | Por qué |
|---|---|
| `git commit -m "..." -- <paths>` | Ignora el índice y lo deja intacto. **Medido (E1)**: `theirs.txt` seguía staged después del commit de A. |
| `git commit --amend -- <paths>` | El índice ajeno sobrevive (**E3 medido**). Cuidado: hereda el contenido del commit anterior. |
| Lecturas: `git status`, `git log`, `git diff`, `git show`, `git rev-parse`, `git worktree list` | No mutan. `git status` puede refrescar el índice, pero no cambia contenido staged. |
| `git worktree add` / `list` | Crea estado propio; `git worktree lock` protege contra el barrido concurrente (la doc oficial de Claude Code confirma que lo usa mientras el agente corre). |
| `GIT_INDEX_FILE=<propio> git read-tree HEAD && GIT_INDEX_FILE=<propio> git add ...` | Aislado — **pero solo con el `read-tree` primero** (E6). Sin él, destructivo (E5b). |

### Evidencia ejecutable

Reproducible en un repo descartable; no toca el repo del proyecto. Corrido con git 2.50.1 (Apple Git-155).

```bash
SB=$(mktemp -d); cd "$SB"
git init -q -b exp .; git config user.email t@t; git config user.name t
echo v1 > mine.txt; echo v1 > theirs.txt; git add .; git commit -qm base

# E1 — agente B deja theirs.txt staged; agente A commitea solo mine.txt
echo v2 > theirs.txt; git add theirs.txt
echo v2 > mine.txt
git commit -qm "A-solo-mine" -- mine.txt
git show --name-only --format= HEAD      # => mine.txt        (solo lo suyo)
git diff --cached --name-only            # => theirs.txt      (indice INTACTO)

# E2 — --amend SIN pathspec: reproduce el incidente
git commit -q --amend -m "A-amend-sin-pathspec"
git show --name-only --format= HEAD      # => mine.txt theirs.txt   (barrio el indice ajeno)
git diff --cached --name-only            # => (vacio)

# E5b — GIT_INDEX_FILE sin sembrar: destructivo
GIT_INDEX_FILE=.git/idx-A git add a.txt
GIT_INDEX_FILE=.git/idx-A git commit -qm x
git show --name-status --format= HEAD    # => A a.txt / D mine.txt / D theirs.txt

# E6 — GIT_INDEX_FILE sembrado: correcto
GIT_INDEX_FILE=.git/idx-C git read-tree HEAD
GIT_INDEX_FILE=.git/idx-C git add c.txt
GIT_INDEX_FILE=.git/idx-C git diff --cached --name-status   # => A c.txt
```

Comprobaciones sobre este repo (read-only):

```bash
git worktree list | grep -c '.cos-agent-worktrees'                 # => 13
grep -c 'agent-bash-cwd-enforcer' .claude/settings.json            # => 0
grep -rn '^isolation:' .claude/agents agents 2>/dev/null | wc -l   # => 0
git rev-parse --git-path refs/stash                                # => .git/refs/stash
git -C <worktree-de-agente> rev-parse --git-path refs/stash        # => .../.git/refs/stash  (compartido)
git -C <worktree-de-agente> rev-parse --git-path index             # => .../.git/worktrees/<id>/index  (propio)
```

---

## Fuentes

Marcadas **[2026]** las publicadas o reportadas en 2026. "verbatim" = contenido citado textual tras recuperar la página; "listado" = aparece en resultados de búsqueda y se usa solo como señal de existencia del proyecto/patrón, no como respaldo de una cita.

### Reportes de incidentes en harnesses (los más cercanos a nuestro caso)

1. **[2026]** anthropics/claude-code #55724 — *"Agent isolation: worktree — parallel agents lose work due to git lock contention + auto-cleanup"*, 2026-05-03. verbatim. https://github.com/anthropics/claude-code/issues/55724
2. **[2026]** anthropics/claude-code #76197 — *"Agent isolation:'worktree' cwd pin drifts back to main repo mid-run — git-mutating commands land in wrong repo"*, 2026-07-09. verbatim. https://github.com/anthropics/claude-code/issues/76197
3. **[2026]** anthropics/claude-code #83311 — *"Parallel isolation:"worktree" agents commit to each other's branches and mutate the main working tree (stash/HEAD), inconsistently across a batch"*, 2026-08-02. verbatim. https://github.com/anthropics/claude-code/issues/83311
4. **[2026]** github/copilot-cli #1725 — *"Copilot CLI uses global git stash in worktrees"*, 2026-02-27. verbatim. https://github.com/github/copilot-cli/issues/1725
5. **[2026]** stablyai/orca #13695 — *"git stash is shared across all worktrees of a repo — one agent's stash can destroy another Orca worktree's work"*. listado. https://github.com/stablyai/orca/issues/13695
6. **[2026]** driftsys/git-std #511 — *"pre-commit hook stash isolation collides with the shared worktree stash stack, aborting the commit and dropping staged changes"*. listado. https://github.com/driftsys/git-std/issues/511
7. **[2026]** anthropics/claude-code #42282 — *"[Bug] Sub-agents in worktrees cause persistent working directory drift"*. listado. https://github.com/anthropics/claude-code/issues/42282
8. **[2026]** anthropics/claude-code #31819 — subagentes forzados a `isolation: "worktree"` en directorios no-git. listado. https://github.com/anthropics/claude-code/issues/31819
9. **[2026]** anthropics/claude-code #34886 — *"Decouple subagents from mandatory worktree isolation"*. listado. https://github.com/anthropics/claude-code/issues/34886
10. **[2026]** anthropics/claude-code #31940 — pedido de `cwd` y `additionalDirectories` por subagente en el frontmatter. listado. https://github.com/anthropics/claude-code/issues/31940
11. **[2026]** anthropics/claude-code #50109 — *"Option to disable automatic worktree isolation in Claude Code Desktop"*. listado. https://github.com/anthropics/claude-code/issues/50109

### Documentación canónica

12. Git — `git-commit(1)`, git-scm.com. verbatim (`--only`/`-o`, `--include`/`-i`, `--amend`, semántica de pathspec). https://git-scm.com/docs/git-commit
13. Git — `git-worktree(1)`, secciones DETAILS y REFS. verbatim (`$GIT_COMMON_DIR`, refs compartidos, `git worktree lock`). https://git-scm.com/docs/git-worktree
14. **[2026]** Claude Code Docs — *"Run parallel sessions with worktrees"*, sección "How Claude Code enforces isolation" (cuatro checks bloqueantes) y "What worktrees share with the main checkout". verbatim. https://code.claude.com/docs/en/worktrees
15. Git — `git-add(1)`. listado. https://git-scm.com/docs/git-add
16. `git-commit(1)` manual page (kernel.org mirror). listado. https://www.kernel.org/pub/software/scm/git/docs/git-commit.html
17. mktemp — manual (`$TMPDIR`, `-d`, permisos `drwx------`). listado. https://www.mktemp.org/docs/mktemp.man/
18. Python — `tempfile` (respeta `TMPDIR`). listado. https://docs.python.org/3/library/tempfile.html
19. Perl — `File::Temp`. listado. https://perldoc.perl.org/File::Temp

### Análisis de la frontera de aislamiento

20. **[2026]** Fletch — *"Git worktrees are not an isolation boundary for coding agents"*, 2026-07-30. verbatim (`refs/stash`, `.git/hooks` como RCE, `clone --shared`). https://fletch.sh/blog/git-worktrees-vs-clones-for-ai-agents/
21. **[2026]** Zylos Research — *"Git Worktree Isolation Patterns for Parallel AI Agent Development"*, 2026-02-22. listado. https://zylos.ai/research/2026-02-22-git-worktree-parallel-ai-development/
22. **[2026]** Zylos Research — *"AI Agent Sandbox & Code Execution Isolation"*, 2026-02-21. listado. https://zylos.ai/research/2026-02-21-ai-agent-sandbox-execution-isolation/
23. **[2026]** Penligent — *"Git Worktrees Need Runtime Isolation for Parallel AI Agent Development"*. listado. https://www.penligent.ai/hackinglabs/git-worktrees-need-runtime-isolation-for-parallel-ai-agent-development/
24. **[2026]** Augment Code — *"How to Run a Multi-Agent Coding Workspace (2026)"*. listado. https://www.augmentcode.com/guides/how-to-run-a-multi-agent-coding-workspace
25. **[2026]** Augment Code — *"How to Use Git Worktrees for Parallel AI Agent Execution"*. listado. https://www.augmentcode.com/guides/git-worktrees-parallel-ai-agent-execution
26. **[2026]** MindStudio — *"Parallel Agentic Development With Git Worktrees: A Practical Playbook"*. listado. https://www.mindstudio.ai/blog/parallel-agentic-development-git-worktrees
27. **[2026]** arXiv 2605.15221 — *"Effective Harness Engineering for Algorithm Discovery with Coding Agents"*. listado. https://arxiv.org/pdf/2605.15221

### Sandboxes y aislamiento forzado por el SO/runtime

28. **[2026]** Codex Knowledge Base — *"Inside the Codex Sandbox: Platform-Specific Implementation on macOS, Linux and Windows"*, 2026-04-08 (Seatbelt / Landlock+seccomp / bubblewrap; write solo a directorios whitelisteados). listado. https://codex.danielvaughan.com/2026/04/08/codex-sandbox-platform-implementation/
29. **[2026]** Codex Knowledge Base — *"Agent Sandbox Comparison Matrix: Codex Seatbelt vs NVIDIA OpenShell vs Docker sbx"*, 2026-04-24. listado. https://codex.danielvaughan.com/2026/04/24/agent-sandbox-comparison-codex-seatbelt-openshell-docker-sbx/
30. **[2026]** Codex Knowledge Base — *"Docker Sandboxes for Codex CLI: MicroVM Isolation, the sbx CLI"*, 2026-04-13. listado. https://codex.danielvaughan.com/2026/04/13/docker-sandboxes-codex-cli-microvm-isolation/
31. openai/codex — Sandboxing Implementation (DeepWiki), `codex-rs/linux-sandbox/src/landlock.rs`. listado. https://deepwiki.com/openai/codex/5.6-sandboxing-implementation
32. dagger/container-use — README: *"Each agent gets a fresh container in its own git branch - run multiple agents without conflicts, experiment safely, discard failures instantly."* verbatim. https://github.com/dagger/container-use
33. InfoQ — cobertura del lanzamiento de container-use, 2025-08. listado. https://www.infoq.com/news/2025/08/container-use
34. **[2026]** Northflank — *"How to sandbox AI agents in 2026: MicroVMs, gVisor & isolation strategies"*. listado. https://northflank.com/blog/how-to-sandbox-ai-agents
35. **[2026]** Modal — *"Best Code Execution Sandboxes for Tool-Calling AI Agents in 2026"*. listado. https://modal.com/resources/best-code-execution-sandboxes-tool-calling-ai-agents
36. **[2026]** amux.io — *"AI Agent Sandboxing in 2026: 8 Isolation Technologies Compared"* (sesión de tmux por agente). listado. https://amux.io/guides/ai-agent-sandboxing/
37. **[2026]** Gist (wincent) — *"List of coding agent sandboxes"*, 2026-05. listado. https://gist.github.com/wincent/2752d8d97727577050c043e4ff9e386e
38. **[2026]** Firecrawl — *"AI Agent Sandbox: How to Safely Run Autonomous Agents in 2026"*. listado. https://www.firecrawl.dev/blog/ai-agent-sandbox
39. Pierce Freeman — *"A deep dive on agent sandboxes"*. listado. https://pierce.dev/notes/a-deep-dive-on-agent-sandboxes

### Orquestadores que implementan worktree/contenedor por agente

40. **[2026]** Augment Code — *"9 Open-Source Agent Orchestrators for AI Coding (2026)"* (Conductor, Crystal/Nimbalyst, Vibe Kanban, Claude Squad, Emdash, Baton). listado. https://www.augmentcode.com/tools/open-source-agent-orchestrators
41. **[2026]** Nimbalyst — *"Best Git Worktree Tools for AI Coding in 2026 (Compared)"* (Sculptor = Docker; Conductor y Crystal = worktree). listado. https://nimbalyst.com/blog/best-git-worktree-tools-ai-coding-2026/
42. **[2026]** Nimbalyst — *"Best Multi-Agent Coding Tools for Claude Code and Codex Users (2026)"*. listado. https://nimbalyst.com/blog/best-multi-agent-coding-tools-2026/
43. **[2026]** Munder Difflin — *"The Best Tools to Run Multiple Claude Code Agents (2026)"*. listado. https://munderdiffl.in/blog/best-claude-code-multi-agent-tools/

---

## Nota de método

Dos trampas que el encargo señalaba y cómo se manejaron acá:

- **Resumir un changelog inventa versiones.** Por eso las afirmaciones que sostienen una recomendación están citadas textual y marcadas "verbatim"; las fuentes "listado" nunca sostienen sola una conclusión.
- **"No encontrado" no es "no existe".** Antes de afirmar que ningún agente declara `isolation:`, se verificó que los directorios de agentes existen y contienen 3 archivos `.md` — el cero es un cero medido, no un directorio ausente. Lo mismo con `agent-bash-cwd-enforcer.sh`: el archivo existe (`ls -la`), lo que falta es el registro en `settings.json`.
