# Anti-overfit Constraints

- The target must not read files under `private/`.
- The target must not special-case exact private case IDs.
- Improvements must generalize through category rules, not string equality against
  the expected labels file.
- Feedback may propose changes, but must not apply them without the approval gate.
