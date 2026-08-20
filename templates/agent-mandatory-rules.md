<!-- SCOPE: os-only -->

## MANDATORY PROJECT RULES (injected by subagent-context-injector)

These rules are automatically injected into every sub-agent's context via the SubagentStart hook. They are non-negotiable.

### The Brief Is Refutable

The numbers, paths, diagnoses and CONSTRAINTS in your assignment are HYPOTHESES.
Whoever wrote them — the orchestrator included — may have miscounted.

- Recount before you cite. Repeat a number from the brief and you own it.
- A premise that tells you NOT to do something needs more scrutiny than one that
  tells you to. A false "you should" leaves a wrong result someone catches; a
  false "you can't" leaves NO trace. Sharpest tell: a brief that also forbids the
  command that would check the limit.
- Constraints are environment claims — who owns these files, what you may write,
  what is registered — so "recount" never fires. Run the read-only command that
  would disprove the limit: ownership is `git status`, not recollection. If you
  truly cannot check, say so instead of quietly working around it.
- You may refute the orchestrator. That is the job, not insubordination.
- If a premise does not hold: report it and CONTINUE. Do not stop, do not ask for
  a new mandate, do not invent one.
- Your report MUST carry `## Corrections to the brief's premises`
  (`## Correcciones a las premisas del encargo`). ZERO corrections is suspicious.

### Filesystem: Symlinks
This project uses symlinks (42 of 256 `hooks/*.sh`, most of them to `packages/*/hooks/`). **`tests/` has ZERO symlinks** — that half of this sentence was false for months. Check before assuming: `ls -la <path>`.
- ALWAYS use `readlink -f <path>` before classifying any file as missing
- ALWAYS use `ls -la <path>` to verify symlinks before reporting absence
- Use `file_exists_strict()` from `hooks/_lib/file_checker.sh` for file checks
- NEVER report a file as 'missing' or 'ghost' without verifying with readlink -f
- Previous audits reported false 'missing' files due to naive checks — do NOT repeat this

### Auditing
- When counting components, resolve symlinks first — a symlink and its target are ONE component
- Cross-validate findings: if you find N 'missing' items, verify EACH ONE individually before reporting N
- Use /audit-integrity skill for standardized component audits

### Code Quality
- Do NOT create tests that only verify file existence — tests MUST execute code and verify behavior
- Do NOT add metadata fields to files unless code exists to consume them
- Do NOT add config flags unless code exists to read them

### Engram
- Save important discoveries to engram via mem_save before returning
- Search engram for prior context before starting work that might have been done before

### Performance
- Do NOT add `python3 -c` calls inside while-read loops (O(n) subprocess spawns)
- Consolidate multiple Python calls into a single script
- If adding a hook, estimate its latency impact

### Critical Agent-Instruction Rules (read before claiming done)

No hook enforces these for you. They live in `rules/`.

- `acceptance-criteria` — criterios medibles ANTES de empezar. Si no te los
  dieron, definilos y decilos en tu primera respuesta.
- `trust-score` — cerrá con TRUST_REPORT: evidencia, incertidumbres, qué debería
  chequear un humano. **Al menos una incertidumbre honesta.** "100% seguro" es
  una bandera roja.
- `adversarial-review` — si tu tarea es verificar, producí al menos un hallazgo
  con severidad. "Looks good" está prohibido.
- `definition-of-done` — clasificá complejidad antes de empezar; cumplí el DoD de
  ese nivel antes de decir listo.
- `phase-aware-agents` — fase `reconstruction`: reescribí lo que no cumple, no
  difieras como "future work".
- `agent-quality` — sin TODO/FIXME, sin stubs, sin código comentado.
- `responsiveness` — salida estructurada: arranque en una línea, marcas de
  progreso, listas de archivos, resultado.
- `agent-output-reading` — leé `<result>` primero, después Engram, después
  `cos_lib/agent_output_extractor.py`. **Nunca** el JSONL crudo.
- `model-directive` — si te dieron un modelo, usá exactamente ése.

Otras reglas SÍ están cableadas a hooks, pero **no memorices cuáles**: la lista
en prosa envejece y esta misma sección publicó durante meses que siete reglas no
estaban registradas cuando las ocho lo estaban. El registro es un hecho sobre
`.claude/settings.json`, no un hecho que uno recuerda. Preguntáselo al archivo:

```bash
.venv/bin/python3 scripts/audit_hook_registration.py    # exit 1 = hay un declarado inalcanzable
```

Y para un hook puntual, `grep -c '<hook>.sh' .claude/settings.json`. Cero no
siempre es un defecto: hay omisiones declaradas a propósito en
`manifests/hook-registration-classification.yaml` y en
`tests/contracts/EXCLUDED_HOOKS.txt`, que ese gate sí lee.
