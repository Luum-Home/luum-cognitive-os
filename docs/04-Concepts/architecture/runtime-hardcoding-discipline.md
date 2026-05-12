# Runtime Hardcoding Discipline

> Product discipline for keeping the central runtime small, portable, and resistant to subsystem sprawl.

## Purpose

Cognitive OS should age as a durable product, not as a bundle of every subsystem the repository can imagine. Central runtime paths must protect the product promise: make coding agents more governable, verifiable, and portable in real repositories.

That means core bootstrap, dispatch, settings, and runtime state paths must not silently promote dashboards, squads, manager agents, or other non-core systems as default product requirements.

## Rule

Protected runtime files may reference non-core subsystems only when the reference is one of these:

- A compatibility driver boundary.
- A documented legacy exception with a removal plan.
- A self-hosting projection exception that is not presented as the product wedge.
- A test fixture that is outside the protected runtime list.

New non-core references in protected runtime files must fail contract validation until they are either removed or explicitly documented in the runtime hardcoding allowlist.

## Protected Runtime Paths

The first enforcement slice watches the files that most directly shape user-facing bootstrap and execution behavior:

- `hooks/self-install.sh`
- `hooks/session-init.sh`
- `install.sh`
- `lib/config_loader.py`
- `lib/dispatch.py`
- `lib/paths.py`
- `lib/record_completion.py`
- `scripts/_lib/settings-driver.sh`
- `scripts/cos-init.sh`
- `scripts/generate-project-settings.sh`

This list is intentionally small. It should expand only when the contract can remain useful rather than noisy.

## Current Exceptions

The current repository still has two important exception families:

- `scripts/cos-init.sh` still installs dashboard-oriented skills in the default skill set. This is legacy onboarding behavior from the earlier “many visible systems” phase. It must either move behind an extension profile or be replaced with product-core defaults.
- `hooks/self-install.sh` still syncs `squads` and `agents` into `.cognitive-os/` during self-hosting. This preserves existing self-hosting behavior, but squads and agent-organization assets remain experimental unless promoted through proof paths.

These exceptions are tracked in `manifests/runtime-hardcoding-allowlist.yaml` and enforced by `tests/contracts/test_runtime_hardcoding.py`.

## Step-By-Step Remediation Plan

1. Add an explicit allowlist and contract test for protected runtime paths.
2. Stop adding new dashboard, squad, or agent-organization references to protected runtime files by default.
3. Move dashboard-oriented default skills into an explicit extension/profile selection path.
4. Gate `squads` and `agents` self-hosting sync behind an explicit self-hosting or experimental projection option.
5. Expand protected runtime scanning to additional CLI and installer paths after the first exception families are removed.

## Success Criteria

- A new central runtime reference to dashboards, squads, or agent-organization assets fails a contract test unless it is documented with a reason and remediation path.
- Product docs continue to describe dashboards, squads, and agent organization as extensions or experimental surfaces, not the minimum product wedge.
- The default install path can remain useful without teaching users that optional subsystems are required to understand Cognitive OS.

