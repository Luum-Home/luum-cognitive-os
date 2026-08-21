# SCOPE: os-only
"""Gate: every ref-key cited in the always-loaded index must be REACHABLE.

`rules/RULES-COMPACT.md` is one of only two rule files projected into every
session. Its `[`ref-key`]` notation promises "full rules loaded on trigger" --
i.e. that the key names something a reader (or `/rules-expand`) can actually
open. For months that promise went unchecked, and 11 keys pointed at no
`rules/<key>.md` at all. Nothing turned red, because nothing was looking.

This is the thing that looks.

A cited key is REACHABLE if it resolves to `rules/<key>.md`. Keys that do not
must appear in DECLARED_UNREACHABLE with a written reason -- a dangling key
with a recorded decision is debt; a dangling key without one is a lie in the
file every session reads.

Counterfactual (run 2026-08-20, both branches recorded in
docs/06-Daily/reports/las-ciento-veinticuatro-reglas-inalcanzables-2026-08-20.md):
injecting a citation of a nonexistent key makes this test FAIL; removing it
makes it PASS again. A gate that cannot be made to fail is not a gate.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
INDEX = REPO / "rules" / "RULES-COMPACT.md"
RULES_DIR = REPO / "rules"

_REF_KEY = re.compile(r"\[`([A-Za-z][A-Za-z0-9_.\-]{0,80})`\]")

# Keys cited by the index that resolve to no rules/<key>.md, each with the
# decision recorded. Shrinking this dict is the ratchet; growing it needs a
# reason written here, not a silent append.
DECLARED_UNREACHABLE = {
    "cognitive-os-changes": "concept doc at docs/04-Concepts/patterns/; cite as "
                            "a link, not a loadable ref-key (option C)",
    "component-classification": "concept doc at docs/04-Concepts/patterns/",
    "component-reality-check": "is a SKILL, not a rule; ref-key notation "
                               "promises a loadable rule body",
    "cost-predictor": "is a SKILL, not a rule",
    "dogfood-score": "is a SKILL, not a rule",
    "dogfooding": "concept doc at docs/04-Concepts/patterns/ (and /root/)",
    "ecosystem-tools": "NOT a ghost: packages/ecosystem-tools/rules/"
                       "ecosystem-tools.md (29KB) and docs/04-Concepts/patterns/"
                       "ecosystem-tools.md (31KB) both exist. It is a package "
                       "reference doc, declared non-behavioural in "
                       "hooks/self-install.sh:EXCLUDED_RULES, so it is "
                       "deliberately absent from rules/ -- unreachable by "
                       "ref-key, not missing (corrected 2026-08-21)",
    "library-selection": "concept doc at docs/04-Concepts/patterns/",
    "os-vs-project": "concept doc at docs/04-Concepts/patterns/",
    "plan-first": "concept doc at docs/04-Concepts/patterns/",
    "stash-mutation-reversibility": "concept doc at docs/04-Concepts/patterns/",
}


def cited_keys() -> set:
    return set(_REF_KEY.findall(INDEX.read_text(encoding="utf-8")))


def unreachable(keys: set) -> set:
    return {k for k in keys if not (RULES_DIR / f"{k}.md").is_file()}


def test_probe_actually_finds_keys():
    """Positive control: a zero here would mean a broken regex, not a clean index."""
    keys = cited_keys()
    assert len(keys) > 100, f"only {len(keys)} ref-keys parsed — probe is broken"
    assert "trust-score" in keys, "known-good key missing — probe is broken"


def test_no_undeclared_unreachable_ref_keys():
    """The gate. A cited key must resolve, or carry a written reason."""
    undeclared = sorted(unreachable(cited_keys()) - set(DECLARED_UNREACHABLE))
    assert not undeclared, (
        "RULES-COMPACT.md cites ref-keys that resolve to no rules/<key>.md and "
        "are not declared:\n  " + "\n  ".join(undeclared) +
        "\n\nEither point the key at a real rule, stop citing it as a ref-key, "
        "or add it to DECLARED_UNREACHABLE with the reason.")


def test_declared_unreachable_has_no_stale_entries():
    """A suppressor that suppresses nothing is a bug — it fakes a decision."""
    keys = cited_keys()
    stale = sorted(k for k in DECLARED_UNREACHABLE
                   if k in keys and (RULES_DIR / f"{k}.md").is_file())
    assert not stale, (
        f"declared unreachable but now resolves — remove from the list: {stale}")
    orphan = sorted(k for k in DECLARED_UNREACHABLE if k not in keys)
    assert not orphan, (
        f"declared unreachable but no longer cited by the index: {orphan}")


def test_every_declaration_carries_a_reason():
    thin = sorted(k for k, v in DECLARED_UNREACHABLE.items() if len(v) < 15)
    assert not thin, f"declarations without a usable reason: {thin}"
