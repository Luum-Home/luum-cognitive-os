# Stash Mutation Reversibility Pattern

The `stash-mutation-reversibility` rule key captures ADR-117's stash safety
contract: stash operations must be named, applied by name rather than `pop`,
logged to `stash-ops.jsonl`, budget bounded, and lock coordinated.
