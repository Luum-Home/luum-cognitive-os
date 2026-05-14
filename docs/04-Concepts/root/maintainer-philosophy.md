# Maintainer Philosophy

> Context for contributors about how the original maintainer thinks,
> and why the system has the shape it does.
> Not rules to follow — evidence for why certain decisions look the way they do.

## The Four Instincts

### 1. Symptom vs Root Cause

The most reliable signal that a fix is wrong is that it changes the form of the
problem without changing the cause.

A concrete example from this codebase: skill routing was language-dependent because
it used regex patterns with human-language keywords. The first fix replaced those
patterns with multilingual example phrases (`intent_examples`). The form changed
— regex strings became YAML lists. The cause did not — the system still depended
on hardcoded natural-language strings.

The fix was rejected not because it failed tests, but because it failed the
question: *does this resolve the cause, or does it relocate the symptom?*

The correct fix was embeddings against the skill `description` field — a field that
is already language-agnostic by nature. No new strings in any language. The semantic
matching handles the translation. ADR-296 documents this decision.

This pattern repeats across the codebase. ADRs that were rejected typically failed
the same test: they addressed the observable behavior without touching the
underlying invariant.

### 2. Diagnostic Before Fix

The `language_dependence_audit.py` was written before any fix was proposed.
The audit scanned routing patterns, extracted literals, scored structural risk,
and produced a ranked list of findings. Only after that was the fix designed.

This order matters. A fix designed without a diagnostic tends to address the
most visible cases and miss the structural cause. A diagnostic first reveals
the full scope, the distribution of the problem, and — importantly — whether
the proposed fix would actually close it.

The `cos-language-dependence-audit` script now runs as a regression gate in CI.
The diagnostic became the test. That is only possible because the diagnostic
was built as a first-class artifact, not as a throwaway investigation step.

The pattern generalizes: before changing behavior, build the measurement. Before
fixing a bug, build the detector. The detector outlasts the fix.

### 3. Empirical Over Intuitive

ADR-300 was rejected after benchmarking, not before.

The routing benchmark harness (ADR-298) ran multilingual-e5-large, BGE-M3, and
other candidates against a corpus of real prompts in multiple languages. The
winner was selected by measured precision, not by reputation or theoretical
properties. The margin was +14 points average — enough to make the decision
unambiguous.

ADR-300 Phase 2 introduced a more aggressive approach. It was also benchmarked.
It did not outperform the baseline. It was rejected with a documented reason,
and the baseline was retained.

The cost of building the benchmark harness was real. The benefit is that every
future routing decision has a measurement infrastructure to validate against.
Intuition is fast but uncalibrated. Benchmarks are slow once and fast forever.

### 4. Rejection as Craft

Building is visible. Rejection is not. The commit history records what was
accepted — it does not record what was proposed and rejected before reaching
the codebase.

The ability to reject a working solution because it is structurally wrong is
harder to develop than the ability to build working solutions. It requires
holding the invariant in mind while evaluating the implementation, and being
willing to redo work that already passes tests.

In practice this means: when an agent produces output that works but is wrong,
the maintainer stops the implementation, names the structural problem precisely,
and restates the constraint before delegating again. The second delegation
produces a different design, not a corrected version of the first.

This is why the OS has the shape it does. Many primitives that could have been
simpler exist in their current form because simpler versions were built and
rejected.

## Why This Matters for Contributors

If you are contributing to this codebase, these instincts explain decisions
that might otherwise look over-engineered or unnecessarily strict.

The benchmark harness is not over-engineering — it is the infrastructure that
makes routing decisions defensible. The language audit is not bureaucracy — it
is the regression gate that ensures routing improvements do not silently
reintroduce the problem they fixed. The rejected ADRs are not failures — they
are the boundary that defines what the accepted ADRs are not.

When you encounter a decision that seems stricter than necessary, look for the
incident or the pattern that motivated it. It is almost always there, either in
the ADR corpus or in the build log sessions.

## The Underlying Principle

Every one of these instincts reduces to the same thing: **prefer correctness
over the appearance of correctness**.

A working test suite, a passing CI, and a merged PR are evidence that the
implementation looks correct. They are not evidence that the implementation
is correct. The gap between those two things is where the maintainer's
attention lives.

The OS itself embodies this: trust reports, claim gates, verification loops,
and adversarial review exist because the system does not trust its own outputs
by default. That skepticism toward surface behavior — and the insistence on
structural evidence — came from somewhere.

## See Also

- [`developer-as-orchestrator.md`](developer-as-orchestrator.md) — how one developer operates at this scale
- [`design-philosophy.md`](design-philosophy.md) — the organism analogy and 12 biological systems
- [`self-building-protocol.md`](self-building-protocol.md) — mandatory self-usage rules
- [`docs/02-Decisions/adrs/ADR-132`](../../../docs/02-Decisions/adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md) — solo-swarm vs multi-maintainer strategic decision
