<!-- SCOPE: os-only -->
---
rule: encargo-refutable
status: active
scope: os-only
applies_to:
  - every sub-agent brief written by the orchestrator (Agent/Task/delegate)
  - every sub-agent reading its own assignment
related:
  - templates/agent-mandatory-rules.md
  - hooks/subagent-context-injector.sh
  - rules/anti-hallucination.md
  - rules/RULES-COMPACT.md
---

## Purpose

The numbers, counts, paths and diagnoses inside a sub-agent brief are hypotheses.
The agent must recount before citing them, has standing permission to refute the
premise of whoever assigned the work — orchestrator included — and reports the
correction without stopping.

# Encargo refutable — the brief is a hypothesis, not a fact

## 1. The failure mode

Session of 2026-08-15: five preparation briefs were fanned out. In **four of them**
the premise the orchestrator passed down was false — the wrong generator named, an
inflated percentage, "thirteen readers" that turned out to be twenty, a figure said
to be on a cover page that was not on the cover page.

None of those errors came from the agents. Every one of them was caught by an agent,
and caught for one reason: the brief said *prepare*, so the agents recounted before
they wrote. Had the same briefs said *execute*, four out of five would have applied
the orchestrator's arithmetic faithfully and produced tidy, wrong work.

The orchestrator is the single highest-volume source of premises in this system and
has no verification path of its own. An agent that treats the brief as ground truth
is not being obedient — it is removing the only check that exists.

## 2. Rule

1. **Recount before you cite.** Any number, count, file list or "X is broken" claim
   that arrives in a brief is a hypothesis. If you repeat it in your report, you own
   it — sourcing it to the brief is not a defence.
2. **Refutation is authorised, always.** You may contradict the premise of whoever
   assigned you the work, including the orchestrator and including the operator's
   framing as relayed to you. No permission needs to be requested first.
3. **Refute and continue.** A false premise is a finding, not a blocker. Report it,
   then carry out whatever part of the assignment still stands. Do not halt for
   confirmation, and do not invent a replacement mandate for yourself.
4. **The correction is a named section.** Every report carries
   `## Corrections to the brief's premises` (`## Correcciones a las premisas del
   encargo`). When everything checked out, the section states which figures were
   rechecked and confirmed — it is never omitted.
5. **Zero corrections is a smell.** A brief that produced no corrections at all is
   more likely to mean nothing was recounted than to mean the brief was flawless.
   Treat a clean run as a prompt to name what you verified, not as a success signal.

## 3. Scope of the refutation

Refutable: facts, counts, measurements, causal claims, file paths, "this is the file
that does X", prior agents' findings relayed through the brief.

Not refutable on this rule's authority: the operator's mandate about *what to build*
or *whether to build it*. Re-verify the state, not the decision — see
`rules/scope-creep-detection.md`. Disagreeing with a priority is escalation, not
refutation.

## 4. Delivery

The agent-facing form of this rule ships in `templates/agent-mandatory-rules.md`
under the heading `The Brief Is Refutable`, which `hooks/subagent-context-injector.sh`
reads and emits as `additionalContext` on `SubagentStart` — the one path in this repo
proven to place text in every sub-agent's context.

Placing the block anywhere else in `rules/` would make it unread: the bulk of the
corpus reaches no agent through any automatic mechanism. The template is first in the
composed context, so it also survives the injector's 10K truncation.

## 5. Verification

Verified as a fact about delivery, never by self-assessment. Asking an agent whether
it refuted anything measures its willingness to claim it did; a better model self-
reports more convincingly, not more accurately.

The executable check runs the real hook and asserts the block is present in the
`additionalContext` it emits, before the truncation point:

```bash
.venv/bin/python -m pytest tests/hooks/test_encargo_refutable_delivery.py -q
```

## 6. Por que `os-only` hoy, y que haria falta para que sea `both`

Medido el 2026-08-15 sobre las dos instalaciones consumidoras con telemetria real:

    ls <consumidor>/.cognitive-os/templates/cos/agent-mandatory-rules.md  -> no existe

El canal de entrega no viaja. El inyector se proyecta, el archivo que lee no, asi
que en un consumidor los subagentes no reciben este bloque — ni ninguno de los
otros del mismo template. Es la misma forma que dejo `cos-root` fuera de las
instalaciones: el lector se envia y lo leido no.

Declarar `both` seria afirmar una entrega que no ocurre. Para cambiarlo hace falta
que el instalador proyecte el template y que exista una prueba de portabilidad que
lo verifique **en el destino** — no una que cambie el directorio de trabajo y mida
el origen, que es el defecto documentado en `judge5-verde-barato-patron-2026-08-15.md`.
