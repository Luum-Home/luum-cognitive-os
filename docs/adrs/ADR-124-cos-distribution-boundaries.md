# ADR-124: COS Distribution Boundaries — Core, Team, Maintainer, Lab

## Status

Proposed — 2026-05-02

## Context

The operational-stability discussion in ADR-123 identified that Cognitive OS is
valuable but unevenly valuable across contexts. The full SO is appropriate for
heavy multi-agent operation, but it is too much friction for a solo developer or
a small project using a single Claude Code session.

A later clarification adds an important distinction: **headcount is not the risk
model**. A solo maintainer running Claude Code and Codex, multiple concurrent
sessions, multiple sub-agents, and multiple consumer projects has a Strict-class
concurrency problem even though the team size is one. For that persona, control,
governance, and determinism primitives are not optional overhead; they are the
operating envelope that keeps the work from escaping human control.

A senior/architect review captured the product tension clearly:

- for one developer and one small project, native harness primitives plus a few
  safety hooks are enough;
- for teams with occasional parallel sessions, the useful subset is roughly the
  multi-session safety primitives;
- for a startup running many agents across IDEs, the full SO is justified
  because one silent-damage incident costs more than the overhead;
- meta-infrastructure such as primitive harvesting, aspirational audits,
  dogfood scoring, deep scorecards, and extensive ADR formalism is useful for
  SO maintainers, but should not be in the default user path.

The adoption risk is therefore packaging, not capability. If Cognitive OS is
presented as an all-or-nothing framework, users pay the overhead before seeing
value. If it is presented as modular agent-safety primitives, teams can adopt the
parts that match their risk.

## Decision

Split Cognitive OS into distribution tiers. The repository may continue to
contain all layers, but runtime projection, default profiles, docs, and install
flows must distinguish them.

### Distribution tiers

| Tier | Audience | Default stance | Contents |
|---|---|---|---|
| `core` | Solo devs, small projects, single harness session | Minimal, low-friction safety | claim verification, concurrent-write guard, stash auto-reapply, session branches, FS/session reaper, branch/worktree closure, protected landing/status/repair basics |
| `team` | 3–5 developers or occasional parallel agent sessions | Coordination without heavy meta | `core` plus task claims, resource leases, derived-artifact gate, validation lanes, lightweight decision docs, small swarm tests |
| `maintainer` | Teams maintaining Cognitive OS or other agent platforms; also solo maintainers operating multi-IDE/multi-agent swarms | Full governance for platform work | `team` plus ADR contracts, hook quality, capability coverage, primitive coverage, scorecards, release/audit contracts |
| `lab` | Research/experimentation | Opt-in, never default | primitive harvester, aspirational audit experiments, dogfood scoring, meta-evaluation, large chaos N=50, experimental dashboards |

### Boundary rules

1. Default installs and first-run docs MUST start with `core`.
2. Solo operators MUST be classified by concurrency/blast radius, not headcount;
   a solo multi-IDE swarm may start at `maintainer`/Strict.
3. Meta-primitives MUST NOT run in `core` unless explicitly requested.
4. Every hook, skill, script, and doctor SHOULD eventually declare
   `distribution: core | team | maintainer | lab`.
5. Profiles (`lean`, `standard`, `strict`) remain risk modes; distribution tiers
   define which primitives are present at all.
6. Product messaging should sell modular primitives first, not the entire SO.
7. Maintainer/lab tooling can stay in-repo, but it must be clearly labeled as
   maintainer tooling and excluded from default projection.

## Consequences

- The SO becomes easier to adopt incrementally.
- Friction decreases because small projects stop loading platform-maintainer
  governance by default.
- Documentation must separate user runtime primitives from SO-maintainer
  meta-infrastructure.
- Hook projection and efficiency profiles need distribution awareness.
- Some current docs and skills will need reclassification.
- The repository remains comprehensive, but the installed/runtime surface becomes
  narrower and more honest.

## Alternatives rejected

- **Keep the SO as one monolithic framework**: rejected because it makes users
  pay meta-infrastructure overhead before they need it.
- **Remove maintainer/lab tooling from the repo**: rejected because those tools
  are useful for building and auditing the SO; they should be tiered, not lost.
- **Use only profiles to solve this**: rejected because profiles tune strictness,
  but do not answer whether a primitive should be installed/projected at all.
- **Rely on documentation warnings**: rejected because agents and operators need
  runtime/projected boundaries, not just prose.

## Verification

Initial verification is documentation-level; implementation phases are tracked in
`.cognitive-os/plans/architecture/operational-stability-friction-reduction.md`.

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
python3 -m pytest tests/audit/test_adr_locations.py -q
```

Future enforcement:

```bash
python3 -m pytest tests/audit/test_distribution_metadata.py -q
python3 -m pytest tests/contracts/test_core_distribution_projection.py -q
python3 -m pytest tests/behavior/test_core_install_is_low_friction.py -q
```
