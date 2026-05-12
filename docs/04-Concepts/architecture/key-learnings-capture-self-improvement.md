# Key Learnings Capture and Self-Improvement Boundary

## Problem

Assistant responses often end with a `## Key Learnings` section. Before this
contract, those learnings were conversational structure only: useful to the
human, but not an operational Cognitive OS signal unless an agent manually wrote
them into an ADR, test, manifest, skill, rule, or other repository artifact.

That was a mismatch with the self-improvement claim. The SO already has error
learning, session learning, KPI triggers, governed improvement drafts, and skill
promotion gates. Key learnings should feed that governed loop without silently
rewriting runtime behavior.

## Decision

Key learnings are now captured as explicit evidence in:

```text
.cognitive-os/metrics/key-learnings.jsonl
```

The capture primitive is:

```bash
scripts/cos-key-learnings-capture --source assistant-final --json < response.md
```

The capture flow is intentionally conservative:

1. Parse only an explicit Markdown heading: `## Key Learnings`.
2. Extract numbered or bulleted items.
3. Classify each item by recommended durable artifact:
   - `test`
   - `script-or-hook`
   - `skill`
   - `manifest-or-contract`
   - `adr-or-plan`
   - `documentation`
4. Classify actionability as `candidate-improvement`, `evidence`, or
   `observation`.
5. Append deduplicated JSONL rows.
6. Feed `candidate-improvement` rows into
   `scripts/cos_governed_self_improvement.py suggest`.

## Non-goals

- Do not auto-edit rules, skills, hooks, scripts, or ADRs just because a key
  learning exists.
- Do not claim Engram persistence unless Engram tools are available in the
  active environment.
- Do not treat conversational text as stronger evidence than tests or repository
  artifacts.
- Do not bypass the governed draft/promote approval path.

## Operational Contract

A key learning becomes an SO improvement only after one of these happens:

1. It is captured into `key-learnings.jsonl`.
2. The governed self-improvement loop emits a signal.
3. A draft is created under `.cognitive-os/improvements/drafts/`.
4. Comparative evaluation proves the candidate draft performs better than the
   current/baseline primitive by the required delta, with no safety regressions.
5. A human or approved automation promotes the draft into a durable primitive.
6. Targeted tests validate the primitive.

This preserves the distinction between memory, evidence, and behavior:

| Layer | Example | Mutates behavior? |
|---|---|---:|
| Conversation | `## Key Learnings` in a chat response | No |
| Evidence | `.cognitive-os/metrics/key-learnings.jsonl` | No |
| Proposal | `.cognitive-os/improvements/drafts/<id>/` | No |
| Evaluation | `.cognitive-os/improvements/drafts/<id>/promotion-evaluation.json` | No |
| Primitive | rule, skill, hook, script, manifest, ADR, test | Yes, after review |

Promotion is blocked unless `scripts/cos_governed_self_improvement.py evaluate`
writes a passing baseline-vs-candidate comparison. Human approval alone is not
enough; the promoted candidate must show measured improvement and no recorded
safety regression.

## Verification

```bash
python3 -m pytest tests/unit/test_key_learning_capture.py -q
python3 -m pytest tests/unit/test_governed_self_improvement.py tests/behavior/test_governed_self_improvement_cli.py -q
```
