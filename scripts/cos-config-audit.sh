#!/usr/bin/env python3
"""
cos-config-audit.sh — Aspirational-vs-Real Config Validator for Cognitive OS

PURPOSE:
    Reads cognitive-os.yaml and checks each declared runtime section against the actual
    codebase implementation. Detects "aspirational drift": config promises behaviour that
    is not wired or implemented.

USAGE:
    bash scripts/cos-config-audit.sh [--json]
    python3 scripts/cos-config-audit.sh [--json]

OUTPUT:
    [IMPL|PARTIAL|ASPIR] section.name — reason
    Summary: N implemented, M partial, K aspirational.

EXIT CODE:
    Always 0 (advisory tool, never blocks CI).

ADDING A NEW CONTRACT:
    Add a dict to the CONTRACTS list below:
        {
            "section": "runtime.my_feature",
            "description": "one-line description of what it promises",
            "check": lambda root: ("IMPL"|"PARTIAL"|"ASPIR", "reason string"),
        }
    The check callable receives the repo root Path and returns (status, reason).
    Status must be one of: "IMPL", "PARTIAL", "ASPIR".

MACHINE-READABLE:
    --json  Writes a JSON array to stdout. Each element:
            {"section": str, "status": str, "reason": str}
"""

import sys
import os
import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate repo root — works whether invoked as `bash cos-config-audit.sh` or
# directly as `python3 scripts/cos-config-audit.sh`.
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPT_DIR.parent


def _exists(*parts) -> bool:
    """Return True if any of the given relative paths exist under REPO_ROOT."""
    return any((REPO_ROOT / p).exists() for p in parts)


def _grep(pattern: str, *rel_dirs, include_glob: str = "*.sh") -> list[str]:
    """
    Return list of file paths (relative to REPO_ROOT) that match *pattern*
    under *rel_dirs*.  Pure-Python — no subprocess needed.
    """
    import fnmatch
    results = []
    for rel_dir in rel_dirs:
        base = REPO_ROOT / rel_dir
        if not base.exists():
            continue
        for path in base.rglob(include_glob):
            try:
                text = path.read_text(errors="replace")
                if re.search(pattern, text):
                    results.append(str(path.relative_to(REPO_ROOT)))
            except (OSError, PermissionError):
                pass
    return results


def _settings_commands() -> list[str]:
    """Return all hook command strings from .claude/settings.json."""
    settings_path = REPO_ROOT / ".claude" / "settings.json"
    if not settings_path.exists():
        return []
    try:
        data = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    cmds = []
    hooks_block = data.get("hooks", {})
    # settings.json format: {"hooks": {"EventName": [{"matcher": ..., "hooks": [...]}]}}
    if isinstance(hooks_block, dict):
        for _event, entries in hooks_block.items():
            for entry in (entries or []):
                if isinstance(entry, dict):
                    for h in entry.get("hooks", []):
                        if isinstance(h, dict) and "command" in h:
                            cmds.append(h["command"])
    return cmds


# ---------------------------------------------------------------------------
# Contract definitions — data-driven, one dict per contract.
# ---------------------------------------------------------------------------

def _check_session_watchdog(root: Path):
    lib_ok = _exists("lib/session_watchdog_lib.py")
    script_ok = _exists("scripts/so-session-watchdog.py")
    if not lib_ok:
        return ("ASPIR", "lib/session_watchdog_lib.py missing — no implementation")
    if not script_ok:
        return ("ASPIR", "lib exists but scripts/so-session-watchdog.py missing")
    # Singleton launcher hook (ADR-047 Phase A auto-start) is the canonical
    # auto-start mechanism. Fall back to launchd/systemd/Makefile or any
    # hook referencing so-session-watchdog for backwards compatibility.
    launcher_hook = root / "hooks" / "session-watchdog-launcher.sh"
    if launcher_hook.exists():
        return (
            "IMPL",
            "lib + script present; auto-start wired via hooks/session-watchdog-launcher.sh",
        )
    autostart = (
        list((root / "launchd").glob("*watchdog*"))
        + list((root / "systemd").glob("*watchdog*"))
        + list(root.glob("*.plist"))
        + _grep(r"so-session-watchdog", "hooks", include_glob="*.sh")
        + _grep(r"so-session-watchdog", ".", include_glob="Makefile")
    )
    if autostart:
        return ("IMPL", f"lib + script present; auto-start wired via {autostart[0]}")
    return (
        "PARTIAL",
        "lib/session_watchdog_lib.py + scripts/so-session-watchdog.py exist "
        "but no auto-start found (no hook launch, no launchd/systemd/Makefile target)",
    )


def _check_ttft_watchdog(root: Path):
    hooks = list((root / "hooks").glob("ttft-watchdog*.sh")) if (root / "hooks").exists() else []
    if hooks:
        return ("IMPL", f"hook found: {hooks[0].name}")
    return (
        "ASPIR",
        "no hooks/ttft-watchdog-*.sh found; "
        "cognitive-os.yaml runtime.ttft_watchdog.enabled=false confirms Phase B scope",
    )


def _check_engram_mcp(root: Path):
    candidates = [
        "scripts/engram-mcp-wrapper.sh",
        "hooks/engram-mcp-wrapper.sh",
        "scripts/engram-mcp-semaphore.sh",
    ]
    if _exists(*candidates):
        which = next(p for p in candidates if (root / p).exists())
        return ("IMPL", f"wrapper found: {which}")
    # Check for semaphore-based engram wrapper in shell scripts (exclude this audit file itself)
    matches = [
        m for m in _grep(r"engram.*semaphore|semaphore.*engram|engram-mcp", "scripts", include_glob="*.sh")
        if not m.endswith("cos-config-audit.sh")
    ]
    if matches:
        return ("PARTIAL", f"engram semaphore logic found in {matches[0]} but dedicated wrapper absent")
    return (
        "ASPIR",
        "no engram-mcp-wrapper.sh or semaphore logic found; "
        "cognitive-os.yaml runtime.engram_mcp.wrapper_enabled=false confirms Phase A scope",
    )


def _check_reaper(root: Path):
    script_ok = _exists("scripts/so-reaper.sh")
    hook_ok = _exists("hooks/reaper-daemon-launcher.sh")
    if not script_ok and not hook_ok:
        return ("ASPIR", "neither scripts/so-reaper.sh nor hooks/reaper-daemon-launcher.sh exists")
    # Check settings.json registration
    cmds = _settings_commands()
    registered = any("reaper-daemon-launcher" in c for c in cmds)
    parts = []
    if script_ok:
        parts.append("scripts/so-reaper.sh")
    if hook_ok:
        parts.append("hooks/reaper-daemon-launcher.sh")
    if registered:
        return ("IMPL", f"{', '.join(parts)} present and reaper-daemon-launcher registered in settings.json")
    if hook_ok:
        return ("PARTIAL", f"{', '.join(parts)} exist but reaper-daemon-launcher NOT found in settings.json")
    return ("PARTIAL", f"scripts/so-reaper.sh exists but hooks/reaper-daemon-launcher.sh absent")


def _check_killswitch(root: Path):
    # killswitch_check.sh should be sourced by >= 1 hook
    matches = _grep(r"killswitch_check", "hooks", include_glob="*.sh")
    if len(matches) >= 1:
        return (
            "IMPL",
            f"{len(matches)} hook(s) source killswitch_check.sh "
            f"(e.g. {Path(matches[0]).name})",
        )
    # Check _lib directly
    lib_exists = _exists("hooks/_lib/killswitch_check.sh")
    if lib_exists:
        return ("PARTIAL", "hooks/_lib/killswitch_check.sh exists but no hook sources it")
    return ("ASPIR", "hooks/_lib/killswitch_check.sh not found")


def _check_efficiency_profile(root: Path):
    script_ok = _exists("scripts/apply-efficiency-profile.sh")
    if not script_ok:
        return ("ASPIR", "scripts/apply-efficiency-profile.sh does not exist")
    # Verify it reads efficiency.profile from cognitive-os.yaml
    matches = _grep(r"efficiency|profile", "scripts", include_glob="apply-efficiency-profile.sh")
    if matches:
        return ("IMPL", "scripts/apply-efficiency-profile.sh exists and references efficiency/profile")
    return ("PARTIAL", "scripts/apply-efficiency-profile.sh exists but no efficiency/profile reference found in it")


def _check_project_phase(root: Path):
    hook_ok = _exists("hooks/inject-phase-context.sh")
    if not hook_ok:
        return ("ASPIR", "hooks/inject-phase-context.sh does not exist")
    # Verify the hook actually reads the yaml
    matches = _grep(r"cognitive.os\.yaml|project\.phase|PHASE", "hooks", include_glob="inject-phase-context.sh")
    if matches:
        return ("IMPL", "hooks/inject-phase-context.sh exists and reads project.phase from cognitive-os.yaml")
    return ("PARTIAL", "hooks/inject-phase-context.sh exists but no yaml/phase read detected")


def _check_resources_budget(root: Path):
    monitor_ok = _exists("hooks/token-budget-monitor.sh")
    lib_ok = _exists("lib/budget_calculator.py")
    if monitor_ok and lib_ok:
        # Confirm monitor is registered in settings.json
        cmds = _settings_commands()
        registered = any("token-budget-monitor" in c for c in cmds)
        if registered:
            return ("IMPL", "hooks/token-budget-monitor.sh + lib/budget_calculator.py present; hook registered in settings.json")
        return ("PARTIAL", "hook + lib exist but token-budget-monitor NOT registered in settings.json")
    if monitor_ok or lib_ok:
        which = "hooks/token-budget-monitor.sh" if monitor_ok else "lib/budget_calculator.py"
        return ("PARTIAL", f"only {which} found; both expected for full implementation")
    return ("ASPIR", "neither hooks/token-budget-monitor.sh nor lib/budget_calculator.py found")


def _check_settings_freshness(root: Path):
    """
    Verify .claude/settings.json is an up-to-date output of the current
    scripts/apply-efficiency-profile.sh. The downstream-drift scenario:
    cos-update.sh copies a new apply-efficiency-profile.sh (adding a hook
    registration) but doesn't re-run it — settings.json stays stale and the
    new hook never fires.

    Status logic:
      * script missing         → ASPIR (can't track what doesn't exist)
      * settings.json missing  → ASPIR (nothing to check against)
      * SHA file missing but
        settings.json exists   → PARTIAL (first-run or manually generated;
                                           no baseline recorded yet)
      * SHAs match             → IMPL   (settings.json regenerated against
                                           the current script)
      * SHAs differ            → ASPIR  (script changed since last regen —
                                           settings.json is stale)
    """
    script_path = root / "scripts" / "apply-efficiency-profile.sh"
    settings_path = root / ".claude" / "settings.json"
    sha_path = root / ".cognitive-os" / "state" / "apply-efficiency-profile.sha"

    if not script_path.exists():
        return ("ASPIR", "scripts/apply-efficiency-profile.sh missing — cannot track freshness")
    if not settings_path.exists():
        return ("ASPIR", ".claude/settings.json missing — run scripts/apply-efficiency-profile.sh")

    # Compute current script SHA
    import hashlib
    try:
        current_sha = hashlib.sha256(script_path.read_bytes()).hexdigest()
    except OSError as exc:
        return ("ASPIR", f"failed to hash apply-efficiency-profile.sh: {exc}")

    if not sha_path.exists():
        return (
            "PARTIAL",
            "settings.json present but no profile SHA tracked (first-run or manually generated); "
            "run `bash scripts/apply-efficiency-profile.sh <profile>` to record baseline",
        )

    try:
        tracked_sha = sha_path.read_text().strip()
    except OSError as exc:
        return ("ASPIR", f"failed to read tracked SHA: {exc}")

    if tracked_sha == current_sha:
        return ("IMPL", f"settings.json in sync with apply-efficiency-profile.sh (sha={current_sha[:8]})")

    return (
        "ASPIR",
        f"apply-efficiency-profile.sh changed (tracked={tracked_sha[:8]}, current={current_sha[:8]}) "
        f"since last regen — run `bash scripts/apply-efficiency-profile.sh <profile>`",
    )


def _check_docker_container_freshness(root: Path):
    """
    Verify running cognitive-os-* containers match the image pin in
    docker-compose.cognitive-os.yml. Drift scenario: someone updates the
    pinned sha in compose but the old container keeps running because
    `docker compose up -d` was not invoked with --force-recreate; the
    container persists indefinitely with stale image and can crash-loop
    if the old entrypoint was removed upstream.

    Status logic:
      * compose file missing          → ASPIR
      * docker CLI missing            → PARTIAL (can't check, but compose exists)
      * no cognitive-os-* containers  → PARTIAL (service stack not running)
      * all running match their pin   → IMPL
      * at least one drift            → ASPIR with drift list

    Real incident that motivated this (2026-04-21): cognitive-os-langfuse-worker
    kept crash-looping with `./worker/entrypoint.sh: No such file or directory`.
    Compose was pinned to sha 0e7a6d86 (new), container ran sha 50674bb0 (old).
    Recreating with --force-recreate fixed it.
    """
    import re
    import subprocess

    compose_path = root / "docker-compose.cognitive-os.yml"
    if not compose_path.exists():
        return ("ASPIR", "docker-compose.cognitive-os.yml missing")

    # Find docker binary (OrbStack installs it in a non-standard location).
    docker = None
    for candidate in (
        "/opt/homebrew/bin/docker",
        "/usr/local/bin/docker",
        "/Applications/OrbStack.app/Contents/Resources/bin/docker",
    ):
        if Path(candidate).exists():
            docker = candidate
            break
    if docker is None:
        # subprocess.which would need `which` on PATH, fall back to PATH lookup
        from shutil import which
        docker = which("docker")
    if docker is None:
        return ("PARTIAL", "docker CLI not found — cannot verify container freshness")

    # Parse compose for `image:` lines that reference pinned digests.
    # Match blocks like:
    #   image: foo/bar:tag@sha256:abcdef...
    # We only care about pinned (@sha256:) images; others are floating and
    # can't be drift-checked.
    compose_text = compose_path.read_text()
    pin_re = re.compile(
        r"^\s*image:\s*([^\s#@]+)@sha256:([0-9a-f]{64})",
        re.MULTILINE,
    )
    pins = {}  # image_name -> sha256
    for m in pin_re.finditer(compose_text):
        pins[m.group(1)] = m.group(2)

    if not pins:
        return ("PARTIAL", "no @sha256 pinned images in compose — nothing to verify")

    # List running containers with name prefix cognitive-os-
    try:
        proc = subprocess.run(
            [docker, "ps", "--filter", "name=cognitive-os-", "--format", "{{.Names}}\t{{.Image}}"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        return ("PARTIAL", f"docker ps failed: {exc}")
    if proc.returncode != 0:
        return ("PARTIAL", f"docker ps returned {proc.returncode}: {proc.stderr.strip()[:80]}")

    running = []  # list of (name, image_ref_or_sha)
    for line in proc.stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            running.append((parts[0], parts[1]))

    if not running:
        return ("PARTIAL", "no cognitive-os-* containers running — stack not started")

    # For each running container, compare the MANIFEST DIGEST of its source
    # image to the pin. Important distinction:
    #   - `.Image`         = image CONFIG ID (sha of the config blob; not the digest)
    #   - `.Config.Image`  = the image REFERENCE the container was created from,
    #                         including the @sha256:... manifest digest if pinned
    # Comparing .Image against the pin is ALWAYS a mismatch because they are
    # different hash schemes of the same image. Use Config.Image.
    drifts = []
    verified = 0
    for name, image_ref in running:
        try:
            insp = subprocess.run(
                [docker, "inspect", "--format", "{{.Config.Image}}", name],
                capture_output=True, text=True, timeout=5,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
        if insp.returncode != 0:
            continue
        config_image = insp.stdout.strip()

        # Find matching pin by image base name
        base = image_ref.split("@", 1)[0]
        pinned_sha = pins.get(base)
        if pinned_sha is None:
            continue

        verified += 1
        # If Config.Image contains the pinned digest, fresh. Otherwise drift.
        if pinned_sha not in config_image:
            # Running ref MAY have its own digest or be tagged; extract what we can
            running_digest = ""
            if "@sha256:" in config_image:
                running_digest = config_image.split("@sha256:", 1)[1][:8]
            drifts.append(
                f"{name} (pin={pinned_sha[:8]}, running={running_digest or 'no-digest'})"
            )

    if verified == 0:
        return ("PARTIAL", "no running containers have pinned-sha images to verify")
    if drifts:
        return (
            "ASPIR",
            f"{len(drifts)} container(s) running stale image: {'; '.join(drifts)} — "
            "run `docker compose -f docker-compose.cognitive-os.yml up -d --force-recreate <service>`",
        )
    return ("IMPL", f"{verified} cognitive-os container(s) match pinned images")


def _check_orchestration(root: Path):
    # Check that referenced hooks in orchestration section exist
    # Known key hook: agent-working-dir-inject.sh
    inject_ok = _exists("hooks/agent-working-dir-inject.sh")
    if not inject_ok:
        return ("ASPIR", "hooks/agent-working-dir-inject.sh missing")
    cmds = _settings_commands()
    registered = any("agent-working-dir-inject" in c for c in cmds)
    if registered:
        return ("IMPL", "hooks/agent-working-dir-inject.sh exists and registered in settings.json")
    return ("PARTIAL", "hooks/agent-working-dir-inject.sh exists but NOT registered in settings.json")


CONTRACTS = [
    {
        "section": "runtime.session_watchdog",
        "description": "Session watchdog daemon that detects idle/stale sessions",
        "check": _check_session_watchdog,
    },
    {
        "section": "runtime.ttft_watchdog",
        "description": "Time-to-first-token watchdog hook (Phase B scope)",
        "check": _check_ttft_watchdog,
    },
    {
        "section": "runtime.engram_mcp",
        "description": "Semaphore-based Engram MCP wrapper for concurrency control",
        "check": _check_engram_mcp,
    },
    {
        "section": "runtime.reaper",
        "description": "Process reaper that cleans up orphan agent processes",
        "check": _check_reaper,
    },
    {
        "section": "runtime.killswitch_respected",
        "description": "Hooks respect killswitch flag to disable non-critical work",
        "check": _check_killswitch,
    },
    {
        "section": "efficiency.profile",
        "description": "Efficiency profile controls which hooks are registered",
        "check": _check_efficiency_profile,
    },
    {
        "section": "project.phase",
        "description": "Project phase injected into agent context by hook",
        "check": _check_project_phase,
    },
    {
        "section": "resources.budget",
        "description": "Budget enforcement via token-budget-monitor and budget_calculator",
        "check": _check_resources_budget,
    },
    {
        "section": "orchestration",
        "description": "Orchestration hooks (agent-working-dir-inject etc.) wired and registered",
        "check": _check_orchestration,
    },
    {
        # Cross-file contract (not a single cognitive-os.yaml key), so it
        # lives under the synthetic `meta.*` namespace. Such sections do not
        # carry a `# STATUS:` annotation in cognitive-os.yaml — the audit
        # coherence logic exempts `meta.*` from the "UNANNOTATED" flag.
        "section": "meta.settings_freshness",
        "description": "settings.json is the current output of apply-efficiency-profile.sh",
        "check": _check_settings_freshness,
    },
    {
        # Another meta.* cross-file contract: docker container images must
        # match compose.yml pins. Prevents the stale-container/crash-loop
        # scenario (see _check_docker_container_freshness docstring).
        "section": "meta.docker_container_freshness",
        "description": "running cognitive-os-* containers use the images pinned in docker-compose.cognitive-os.yml",
        "check": _check_docker_container_freshness,
    },
]

STATUS_LABEL = {
    "IMPL": "IMPL",
    "PARTIAL": "PARTIAL",
    "ASPIR": "ASPIR",
}

# Map between annotation vocabulary (user-facing words in YAML comments) and
# the validator's internal status codes.
ANNOTATION_TO_STATUS = {
    "implemented": "IMPL",
    "partial": "PARTIAL",
    "aspirational": "ASPIR",
}


def parse_status_annotations(yaml_path: Path) -> dict[str, str]:
    """
    Parse `# STATUS: <value>` comments in cognitive-os.yaml and map them to
    contract section paths. Returns dict mapping "section.name" -> "IMPL"|"PARTIAL"|"ASPIR".

    Association rule:
      - The annotation applies to the nearest following YAML key (within 3 non-blank lines)
      - Nested keys are resolved to dotted paths based on indentation
      - Special form `# STATUS: X (some.section)` binds to the explicit section name
    """
    if not yaml_path.exists():
        return {}
    try:
        lines = yaml_path.read_text().splitlines()
    except (OSError, PermissionError):
        return {}

    annotations: dict[str, str] = {}
    # Stack of (indent_level, key) tracking the YAML nesting path
    nesting: list[tuple[int, str]] = []
    # Pending annotations: list of (status, explicit_target_or_none)
    pending: list[tuple[str, str | None]] = []

    status_re = re.compile(r"^\s*#\s*STATUS:\s*(\w+)(?:\s*\(([^)]+)\))?\s*$", re.IGNORECASE)
    key_re = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:")

    for line in lines:
        # Skip blank lines — pending annotations carry through
        if not line.strip():
            continue

        m_status = status_re.match(line)
        if m_status:
            word = m_status.group(1).lower()
            explicit = m_status.group(2)
            status = ANNOTATION_TO_STATUS.get(word)
            if status:
                pending.append((status, explicit))
            continue

        # Other comment lines (not STATUS) reset nothing
        if line.lstrip().startswith("#"):
            continue

        m_key = key_re.match(line)
        if not m_key:
            # Non-key content — drop pending (they must bind to next key)
            # But only drop if we've consumed them; otherwise keep one more chance
            continue

        indent = len(m_key.group(1))
        key = m_key.group(2)
        # Maintain nesting stack based on indentation
        while nesting and nesting[-1][0] >= indent:
            nesting.pop()
        nesting.append((indent, key))
        dotted = ".".join(k for _, k in nesting)

        # Bind pending annotations
        if pending:
            for status, explicit in pending:
                target = explicit if explicit else dotted
                annotations[target] = status
            pending = []

    return annotations

ANSI = {
    "IMPL": "\033[32m",      # green
    "PARTIAL": "\033[33m",   # yellow
    "ASPIR": "\033[31m",     # red
    "RESET": "\033[0m",
}


def _colorize(status: str, text: str, use_color: bool) -> str:
    if not use_color:
        return text
    return f"{ANSI.get(status, '')}{text}{ANSI['RESET']}"


def run_audit(use_color: bool = True) -> list[dict]:
    annotations = parse_status_annotations(REPO_ROOT / "cognitive-os.yaml")
    results = []
    for contract in CONTRACTS:
        section = contract["section"]
        try:
            status, reason = contract["check"](REPO_ROOT)
        except Exception as exc:  # noqa: BLE001
            status, reason = "ASPIR", f"check raised exception: {exc}"
        entry = {"section": section, "status": status, "reason": reason}
        annotated = annotations.get(section)
        entry["annotation"] = annotated  # may be None
        # `meta.*` sections are cross-file contracts (not single yaml keys), so
        # they're exempt from the `# STATUS:` annotation requirement. Treat
        # them as coherent by design.
        if section.startswith("meta."):
            entry["coherence"] = "OK"
        elif annotated is None:
            entry["coherence"] = "UNANNOTATED"
        elif annotated != status:
            entry["coherence"] = "DRIFT"
        else:
            entry["coherence"] = "OK"
        results.append(entry)
    return results


def format_text(results: list[dict], use_color: bool = True) -> str:
    lines = []
    for r in results:
        coherence = r.get("coherence", "OK")
        if coherence == "DRIFT":
            label_text = "[ DRIFT ]"
            label = _colorize("ASPIR", label_text, use_color)
            ann = r.get("annotation") or "?"
            suffix = f" (annotation={ann}, actual={r['status']})"
            lines.append(f"{label} {r['section']} — {r['reason']}{suffix}")
        else:
            label = _colorize(r["status"], f"[{r['status']:^7}]", use_color)
            unann = " [unannotated]" if coherence == "UNANNOTATED" else ""
            lines.append(f"{label} {r['section']} — {r['reason']}{unann}")
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("IMPL", "PARTIAL", "ASPIR")}
    drift_count = sum(1 for r in results if r.get("coherence") == "DRIFT")
    unann_count = sum(1 for r in results if r.get("coherence") == "UNANNOTATED")
    lines.append("")
    lines.append(
        f"Summary: {counts['IMPL']} implemented, "
        f"{counts['PARTIAL']} partial, "
        f"{counts['ASPIR']} aspirational."
    )
    if drift_count or unann_count:
        lines.append(
            f"Coherence: {drift_count} drift, {unann_count} unannotated."
        )
    return "\n".join(lines)


def main():
    want_json = "--json" in sys.argv
    strict = "--strict" in sys.argv
    use_color = sys.stdout.isatty() and not want_json

    results = run_audit(use_color=use_color)

    if want_json:
        print(json.dumps(results, indent=2))
    else:
        print(format_text(results, use_color=use_color))

    if strict and any(r.get("coherence") == "DRIFT" for r in results):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
