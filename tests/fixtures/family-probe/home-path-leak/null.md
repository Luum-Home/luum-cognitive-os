# Null control

Content with nothing for this family to react to. Every candidate must ignore it.

A candidate that reacts here is reacting to being invoked — a usage error on an
argv shape it does not accept, a missing manifest, an unrelated policy — not to
the content. Without this fixture such a candidate reacts to both real fixtures
and gets reported as DEFECTIVE, which is how a conformance probe fills up with
false positives and stops being read.

Deliberately boring: a relative path (`scripts/family_conformance_probe.py`), a
container path (`/opt/app/bin`), and a plain sentence.
