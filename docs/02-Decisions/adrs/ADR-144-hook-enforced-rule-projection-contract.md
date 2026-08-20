---

adr: 144
title: Hook-Enforced Rule Projection Contract
status: accepted
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - cognitive-os.yaml
  - scripts/_lib/settings-driver-claude-code.sh
  - scripts/_lib/settings-driver-codex.sh
  - scripts/apply-efficiency-profile.sh
  - hooks/self-install.sh
  - hooks/skill-router-bash-gate.sh
  - tests/audit/test_hook_enforced_exclusions.py
  - tests/behavior/test_skill_router_bash_gate.py
  - docs/09-Quality/manual-tests/hook-enforced-rule-projection.md
tier: maintainer
tags: [hooks, rules, projection, validation, startup]
---

# ADR-144: Hook-Enforced Rule Projection Contract

## Status

Accepted. Hook-enforced rule exclusions are now a projection contract, not a prose convention.

## Context

Cognitive OS reduces startup/context load by excluding many full rule files from
agent context in `hooks/self-install.sh:EXCLUDED_RULES`. The intended contract is:

1. `RULES-COMPACT.md` keeps a compact reference to the rule;
2. the full rule body is not injected at session start;
3. a registered hook enforces the mechanical part of the rule.

A wiring audit found a dangerous fourth state: some rules were excluded as
"hook-enforced" while their hooks existed on disk but were not projected into
`.claude/settings.json`. This made the startup diet look successful while the
runtime enforcement was absent. Examples included scope proportionality,
scope-creep detection, token-budget monitoring, consequence evaluation,
auto-skill generation, assumption tracking, and prompt quality.

The project also has multiple projection layers:

- `cognitive-os.yaml > harness.hooks` is the canonical registry for portable
  harness projection;
- `scripts/_lib/settings-driver-claude-code.sh` generates `.claude/settings.json`;
- `scripts/_lib/settings-driver-codex.sh` generates `.codex/hooks.json` for the
  subset Codex can emit;
- `scripts/apply-efficiency-profile.sh` invokes the drivers;
- downstream installs use the same profile/projection machinery.

Therefore directly editing generated settings would fix only the self-hosted
checkout and would leave consumer projects vulnerable to the same drift.

## Decision

A rule may be listed in `EXCLUDED_RULES` with a `# → hook.sh` enforcement claim
only if all of the following are true:

1. every referenced hook file exists;
2. every referenced Claude/Codex-compatible hook is present in
   `cognitive-os.yaml > harness.hooks`;
3. the hook is projected by the active profile into the relevant harness settings;
4. if a rule is intentionally not hook-enforced, the comment must say
   `agent-instruction-only` or otherwise avoid a `# → hook.sh` claim.

We also add a PreToolUse Bash gate, `hooks/skill-router-bash-gate.sh`, for the
highest-ROI bypass class found during the audit: direct dependency/toolchain
upgrades. Direct upgrade commands such as `brew upgrade`, `pip install --upgrade`,
`uv sync --upgrade`, and equivalent package-manager upgrades must go through
`/deps-update` / `scripts/deps-update.sh` unless explicitly overridden with
`COS_ALLOW_SKILL_BYPASS=1`.

## Consequences

- Startup remains lean: rules can still be excluded from context when hooks are real.
- Missing hook projection now fails an audit test instead of relying on manual review.
- Self-hosted and consumer-project settings are fixed at the canonical projection
  layer, not by hand-editing generated settings files.
- Some additional maintainer hooks run in the hot path. This is accepted because
  the selected hooks are directly tied to rules already advertised as enforced.
- Codex receives only the supported Bash subset; non-Bash Agent/Edit/Write hooks
  remain represented in the canonical registry and Claude projection until Codex
  supports those events.

## Operational Guide

### What changes for the operator

Before this ADR, a rule listed in `hooks/self-install.sh:EXCLUDED_RULES`
with a `# → hook.sh` comment could claim hook enforcement while the hook
was never projected into `.claude/settings.json`. The startup diet looked
successful; the runtime enforcement was absent.

After this ADR:

- A rule may only claim `# → hook.sh` enforcement if:
  1. the hook file exists on disk;
  2. the hook is registered in `cognitive-os.yaml > harness.hooks`;
  3. the hook is projected by the active profile into the harness
     settings.
- `tests/audit/test_hook_enforced_exclusions.py` fails CI if any
  `EXCLUDED_RULES` entry claims hook enforcement for an unprojected hook.
- The projection is fixed at the canonical layer
  (`scripts/_lib/settings-driver-claude-code.sh`,
  `scripts/_lib/settings-driver-codex.sh`), not by hand-editing
  generated settings files. Consumer projects that run
  `scripts/apply-efficiency-profile.sh` get the corrected projection
  automatically.
- A new PreToolUse Bash gate (`hooks/skill-router-bash-gate.sh`) blocks
  direct dependency/toolchain upgrades (`brew upgrade`, `pip install
  --upgrade`, etc.) unless routed through `/deps-update` or
  `COS_ALLOW_SKILL_BYPASS=1`.

### Terminologia: que significa "enforced" en este ADR, y que NO

**Enmienda del 2026-08-20.** La decision de este ADR es correcta y no cambia. Lo que
se agrega es la definicion de la palabra, porque su ausencia costo una jornada.

En este contrato, **"hook-enforced" significa "el hook esta CABLEADO"** -- proyectado
al registro del arnes y alcanzable. **NO significa "el hook BLOQUEA".** La seccion
"Does not answer" de mas abajo ya lo decia, pero lo decia como una exclusion de
alcance, no como una definicion, y nadie leyo la exclusion antes de hacer la
inferencia.

**Como se descubrio.** El 2026-08-20 se audito `EXCLUDED_RULES` bajo la premisa de que
"un hook la hace cumplir" significaba bloqueo. Se verifico desde la fuente de cada
hook citado -- no desde un artefacto derivado -- y aparecieron ONCE citas donde el
hook no tiene ninguna ruta de bloqueo:

    exit2=0  deny=0  permissionDecision=0   auto-rollback-trigger      272 corridas
    exit2=0  deny=0  permissionDecision=0   git-context-capture        394
    exit2=0  deny=0  permissionDecision=0   consequence-evaluator      272
    exit2=0  deny=0  permissionDecision=0   auto-checkpoint         13.275
    exit2=0  deny=0                         blast-radius               274

Las once **CUMPLEN este contrato**: los hooks estan cableados. Lo que fallaba no era
el codigo ni las exclusiones: era que el lector -- humano y agente -- infiere
"bloquea" de la palabra "enforced", y nada lo desmentia en el lugar donde mira.

`blast-radius.md` es el caso mas claro: su propia linea 5 dice "Advisory only (exit 0)
-- does NOT block", y aun asi se lo citaba como enforcement. El archivo se
contradecia con su propia cita y nadie lo noto durante meses.

**Consecuencia practica para quien escriba una exclusion nueva.** Un comentario del
tipo `# -> hook.sh` afirma PROYECCION, no gobierno. Si el comportamiento tiene que
quedar gobernado de verdad, hace falta una de estas tres y hay que elegirla por
escrito:

  1. el hook gana una ruta de bloqueo (`exit 2`, `"deny"`, o `permissionDecision:
     "deny"`), y un test que la ejercite con payload real -- no basta con que exista
     en la fuente
  2. la regla se queda en el contexto del agente y se gobierna por prosa
  3. se acepta explicitamente que ese comportamiento NO esta gobernado, con motivo
     escrito

Lo que dejo de ser aceptable es la cuarta opcion, que era la de facto: excluir la
regla del contexto citando un hook que solo observa. Ahi no llega la regla NI obliga
el hook, y ademas la pregunta queda cerrada, que es peor que dejarla abierta.

**Nota sobre el gate de este ADR.** `tests/audit/test_hook_enforced_exclusions.py`
verifica las tres condiciones estructurales del contrato y por eso pasaba en verde
con las once citas falsas vivas. No es un bug del test: es fiel al contrato. Su
docstring, en cambio, prometia prevenir que una regla quedara "not enforced
anywhere", que es una promesa que este contrato nunca hizo.

### What this answers (and what it doesn't)

**Answers:**
- "Is rule X actually enforced at runtime?" — Check
  `hooks/self-install.sh:EXCLUDED_RULES` for the rule's comment. If
  it says `# → hook.sh`, run:
  ```bash
  bash scripts/_lib/settings-driver-claude-code.sh --check
  ```
  and verify the hook appears in `.claude/settings.json`.
- "Why is `brew upgrade` / `pip install --upgrade` blocked?" —
  `hooks/skill-router-bash-gate.sh` enforces routing through
  `/deps-update`. Use `COS_ALLOW_SKILL_BYPASS=1` for one-off overrides.
- "Which hooks are projected for Claude vs. Codex?" — Codex receives
  only the supported Bash subset. Non-Bash hooks are present in the
  canonical registry and Claude projection but absent from Codex until
  Codex supports those events.

**Does not answer:**
- Whether the hook logic itself is correct. The contract verifies
  projection (hook is wired); hook behavior correctness is covered by
  the hook's own tests.
- Whether a new hook added after this ADR is automatically projected.
  New hooks must be added to `cognitive-os.yaml > harness.hooks` and
  the appropriate settings driver; the audit test will catch the gap
  if the rule claims enforcement before projection is complete.

### Daily operational pattern

1. Adding a new hook that enforces a rule:
   a. Add hook file to `hooks/`.
   b. Register in `cognitive-os.yaml > harness.hooks`.
   c. Re-run `scripts/apply-efficiency-profile.sh`.
   d. Add the rule to `EXCLUDED_RULES` with `# → new-hook.sh`.
   e. Run `python3 -m pytest tests/audit/test_hook_enforced_exclusions.py -q`
      to verify the chain.
2. Checking current projection state:
   ```bash
   bash scripts/_lib/settings-driver-claude-code.sh --check
   bash scripts/_lib/settings-driver-codex.sh --check
   ```
3. Temporarily allowing a direct upgrade:
   `COS_ALLOW_SKILL_BYPASS=1 pip install --upgrade foo`
   (bypasses the skill-router bash gate for this invocation).

### Reading guide for cold readers

If you encounter ADR-144 cold and are unsure whether a specific rule is
hook-enforced:

1. Open `hooks/self-install.sh` and search for `EXCLUDED_RULES`.
2. Find the rule in the list. If it has `# → hook.sh`, the hook name
   is the enforcement mechanism.
3. Verify the hook is projected:
   `grep <hook-name> .claude/settings.json`
4. If the grep returns nothing, the projection is missing and the
   audit test should be failing. File a bug or run
   `scripts/apply-efficiency-profile.sh` to regenerate.
5. Rules without `# →` comments are excluded as
   `agent-instruction-only` — they rely on the orchestrator reading
   the compact rule reference, not on a mechanical hook.

## Alternatives rejected

| Alternative | Rejected because |
|---|---|
| Register all 72 unregistered hooks | Too much latency/noise; violates the profile model. |
| Remove all listed rules from `EXCLUDED_RULES` | Restores context load and loses the startup diet benefit. |
| Patch only `.claude/settings.json` | Generated artifact drift; downstream projects remain broken. |
| Leave as manual discipline | This already failed; tests claimed coverage while exemptions hid the gap. |

## Verification

Automatic:

```bash
python3 -m pytest tests/audit/test_hook_enforced_exclusions.py tests/behavior/test_skill_router_bash_gate.py -q
python3 -m pytest tests/behavior/test_self_install.py tests/integration/test_project_settings_generation.py -q
bash scripts/_lib/settings-driver-claude-code.sh --check
bash scripts/_lib/settings-driver-codex.sh --check
```

Manual:

See `docs/09-Quality/manual-tests/hook-enforced-rule-projection.md`.
