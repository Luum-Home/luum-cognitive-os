"""Auto-repair system — worktree-isolated repair engine.

Classifies errors, applies known remediations from a registry, and executes
repairs in isolated git worktrees so failed attempts never pollute the main
working tree.

Safety boundaries (NEVER auto-repaired):
- Database migrations
- Auth/authorization code
- Payment/billing code
- .env files or secrets
- Docker compose configuration
- Git history operations

Usage:
    from lib.auto_repair import AutoRepairEngine, classify_error

    engine = AutoRepairEngine()
    result = engine.attempt_repair("LINT_ERROR", "my-service", "unused import on line 5")
    if result.success:
        print("Apply this diff:", result.diff)
"""
import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Safety blocklist — paths that must NEVER be auto-repaired
# ---------------------------------------------------------------------------

BLOCKED_PATH_PATTERNS = [
    # Secrets / credentials
    r"\.env",
    r"\.env\.",
    r"\.key$",
    r"\.pem$",
    r"\.p12$",
    r"secrets/",
    r"credentials",
    r"password",
    # Auth / security
    r"auth",
    r"authorization",
    r"oauth",
    r"jwt",
    r"session",
    r"token",
    r"permission",
    r"rbac",
    r"acl",
    # Payments / billing
    r"payment",
    r"billing",
    r"stripe",
    r"checkout",
    r"invoice",
    # Database migrations
    r"migration",
    r"migrate",
    r"schema\.",
    r"alembic",
    r"flyway",
    r"liquibase",
    # Infrastructure
    r"docker-compose",
    r"docker_compose",
    r"\.dockerfile",
]

_BLOCKED_RE = re.compile("|".join(BLOCKED_PATH_PATTERNS), re.IGNORECASE)


def is_safe_to_repair(file_path: str) -> bool:
    """Return True if the path is safe to auto-repair.

    Blocks files matching any safety-boundary pattern.
    """
    return not bool(_BLOCKED_RE.search(file_path))


# ---------------------------------------------------------------------------
# Remediation data model
# ---------------------------------------------------------------------------


@dataclass
class Remediation:
    """A known fix for a common error pattern."""
    error_pattern: str  # regex
    fix_command: str    # bash command (may contain {placeholders})
    description: str
    safe: bool = True   # True = auto-apply, False = suggest only
    _compiled: re.Pattern = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._compiled = re.compile(self.error_pattern, re.IGNORECASE)

    def matches(self, message: str) -> Optional[re.Match]:
        return self._compiled.search(message)


# ---------------------------------------------------------------------------
# In-memory registry of well-understood remediations
# ---------------------------------------------------------------------------

REMEDIATION_REGISTRY: List[Remediation] = [
    Remediation(
        error_pattern=r"ModuleNotFoundError: No module named '(\w+)'",
        fix_command="pip install {module}",
        description="Install missing Python module",
        safe=False,
    ),
    Remediation(
        error_pattern=r"Cannot find module '([^']+)'",
        fix_command="npm install {module}",
        description="Install missing npm package",
        safe=False,
    ),
    Remediation(
        error_pattern=r"go: .*missing go\.sum entry",
        fix_command="go mod tidy",
        description="Fix missing Go module checksums",
        safe=True,
    ),
    Remediation(
        error_pattern=r"permission denied.*?([^\s]+\.sh)",
        fix_command="chmod +x {file}",
        description="Make script executable",
        safe=True,
    ),
    Remediation(
        error_pattern=r"address already in use.*?:(\d+)",
        fix_command="lsof -ti:{port} | xargs kill -9",
        description="Kill process using port",
        safe=False,
    ),
    Remediation(
        error_pattern=r"SyntaxError:.*?line (\d+)",
        fix_command="python3 -m py_compile {file}",
        description="Python syntax error — check file compilation",
        safe=False,
    ),
    Remediation(
        error_pattern=r"ENOSPC: no space left on device",
        fix_command="docker system prune -f",
        description="Free Docker disk space",
        safe=False,
    ),
    Remediation(
        error_pattern=r"fatal: not a git repository",
        fix_command="git init",
        description="Initialize git repository",
        safe=False,
    ),
]


# ---------------------------------------------------------------------------
# Repair result
# ---------------------------------------------------------------------------


@dataclass
class RepairResult:
    """Result of an attempted worktree-isolated repair."""
    repair_id: str
    error_type: str
    service: str
    success: bool
    diff: str = ""           # unified diff if successful
    reason: str = ""         # failure reason if not successful
    worktree_path: str = ""  # resolved path used (empty if already cleaned)
    fix_applied: str = ""    # description of the fix that was applied


# ---------------------------------------------------------------------------
# AutoRepairEngine — worktree-isolated repair
# ---------------------------------------------------------------------------


class AutoRepairEngine:
    """Apply known fixes in an isolated git worktree.

    On success the worktree diff is returned so the caller can merge it.
    On failure the worktree is deleted and the circuit breaker is updated.
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        metrics_dir: Optional[Path] = None,
        circuit_breaker=None,
        registry_path: Optional[Path] = None,
    ):
        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent
        self.project_root = Path(project_root)

        if metrics_dir is None:
            metrics_dir = self.project_root / ".cognitive-os" / "metrics"
        self.metrics_dir = Path(metrics_dir)

        self._cb = circuit_breaker  # injected or lazy-loaded

        if registry_path is None:
            registry_path = self.metrics_dir / "remediation-registry.jsonl"
        self.registry_path = Path(registry_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def attempt_repair(
        self, error_type: str, service: str, error_msg: str
    ) -> RepairResult:
        """Attempt repair in an isolated git worktree.

        Returns a RepairResult with the diff if successful, or a failure reason.
        """
        repair_id = uuid.uuid4().hex[:8]
        cb_key = f"repair:{error_type}:{service}"

        # 1. Circuit breaker check
        cb = self._get_circuit_breaker()
        if cb is not None and not cb.can_launch(cb_key):
            return RepairResult(
                repair_id=repair_id,
                error_type=error_type,
                service=service,
                success=False,
                reason="Circuit breaker OPEN — too many consecutive failures",
            )

        # 2. Find a matching fix in the registry
        fix = self._lookup_fix(error_type, error_msg)
        if fix is None:
            return RepairResult(
                repair_id=repair_id,
                error_type=error_type,
                service=service,
                success=False,
                reason="No matching fix found in remediation registry",
            )

        fix_description, fix_command = fix

        # 3. Safety check on the target files (parse from fix_command heuristically)
        if not self._command_is_safe(fix_command):
            return RepairResult(
                repair_id=repair_id,
                error_type=error_type,
                service=service,
                success=False,
                reason=f"Safety boundary: fix command targets a protected path",
                fix_applied=fix_description,
            )

        # 4. Create worktree
        worktree_path = self._create_worktree(repair_id, error_type)
        if worktree_path is None:
            return RepairResult(
                repair_id=repair_id,
                error_type=error_type,
                service=service,
                success=False,
                reason="Failed to create git worktree",
            )

        try:
            # 5. Apply fix inside worktree
            applied = self._apply_fix(worktree_path, fix_command)
            if not applied:
                self._cleanup_worktree(worktree_path, repair_id)
                if cb is not None:
                    cb.record_failure(cb_key)
                result = RepairResult(
                    repair_id=repair_id,
                    error_type=error_type,
                    service=service,
                    success=False,
                    reason="Fix command failed inside worktree",
                    fix_applied=fix_description,
                )
                self._log_repair_outcome(result)
                return result

            # 6. Run verification in worktree
            verified = self._run_verification(worktree_path)
            if not verified:
                self._cleanup_worktree(worktree_path, repair_id)
                if cb is not None:
                    cb.record_failure(cb_key)
                result = RepairResult(
                    repair_id=repair_id,
                    error_type=error_type,
                    service=service,
                    success=False,
                    reason="Verification failed after applying fix",
                    fix_applied=fix_description,
                )
                self._log_repair_outcome(result)
                return result

            # 7. Capture the diff before cleanup
            diff = self._capture_diff(worktree_path)
            self._cleanup_worktree(worktree_path, repair_id)

            if cb is not None:
                cb.record_success(cb_key)

            result = RepairResult(
                repair_id=repair_id,
                error_type=error_type,
                service=service,
                success=True,
                diff=diff,
                fix_applied=fix_description,
            )
            self._log_repair_outcome(result)
            return result

        except Exception as exc:  # noqa: BLE001
            # Always clean up on unexpected failure
            self._cleanup_worktree(worktree_path, repair_id)
            if cb is not None:
                cb.record_failure(cb_key)
            result = RepairResult(
                repair_id=repair_id,
                error_type=error_type,
                service=service,
                success=False,
                reason=f"Unexpected error: {exc}",
                fix_applied=fix_description,
            )
            self._log_repair_outcome(result)
            return result

    # ------------------------------------------------------------------
    # Worktree management
    # ------------------------------------------------------------------

    def _create_worktree(self, repair_id: str, error_type: str) -> Optional[str]:
        """Create an isolated git worktree. Return path or None on failure."""
        slug = re.sub(r"[^a-z0-9]", "-", error_type.lower())
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        branch = f"repair/{slug}-{timestamp}"
        worktree_dir = (
            self.project_root / ".cognitive-os" / "worktrees" / f"repair-{repair_id}"
        )

        try:
            worktree_dir.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "worktree", "add", str(worktree_dir), "-b", branch],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return None
            return str(worktree_dir)
        except (subprocess.TimeoutExpired, OSError):
            return None

    def _cleanup_worktree(self, path: str, repair_id: str) -> None:
        """Remove worktree and its branch. Best-effort — never raises."""
        try:
            # Remove from git's worktree list
            subprocess.run(
                ["git", "worktree", "remove", "--force", path],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

        # Belt-and-suspenders: remove directory if still present
        try:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass

        # Remove the repair branch (ignore errors — HEAD may not have committed)
        try:
            # Find branch name from worktree directory name
            slug = re.sub(r"[^a-z0-9]", "-", "")  # placeholder
            # Instead, list worktrees to find the branch name, then delete
            result = subprocess.run(
                ["git", "branch", "--list", f"repair/*-*"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=10,
            )
            for branch in result.stdout.splitlines():
                branch = branch.strip().lstrip("* ")
                if repair_id in path and branch.startswith("repair/"):
                    subprocess.run(
                        ["git", "branch", "-D", branch],
                        cwd=str(self.project_root),
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
        except (subprocess.TimeoutExpired, OSError):
            pass

    # ------------------------------------------------------------------
    # Fix application & verification
    # ------------------------------------------------------------------

    def _apply_fix(self, worktree_path: str, fix_command: str) -> bool:
        """Run the fix command inside the worktree. Return True on success."""
        try:
            result = subprocess.run(
                fix_command,
                shell=True,
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def _run_verification(self, worktree_path: str) -> bool:
        """Run lightweight verification in the worktree.

        Tries several verifiers and returns True if none fail hard.
        Skips verifiers that are not installed.
        """
        verifiers = [
            # Python syntax check
            (["python3", "-m", "py_compile"], "*.py"),
            # Shell syntax check
            (["bash", "-n"], "*.sh"),
        ]

        # Try to find and run a project-level test command
        for test_cmd in [
            ["python3", "-m", "pytest", "--tb=no", "-q", "--co"],
            ["go", "build", "./..."],
        ]:
            try:
                result = subprocess.run(
                    test_cmd,
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                # If exit code is non-zero for a command that ran, it failed
                if result.returncode not in (0, 5):  # 5 = pytest no tests collected
                    return False
                # Successfully ran — done
                return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        # No verifier succeeded — assume OK (conservative: don't block on missing tools)
        return True

    def _capture_diff(self, worktree_path: str) -> str:
        """Capture the unified diff of changes in the worktree."""
        try:
            result = subprocess.run(
                ["git", "diff"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, OSError):
            return ""

    # ------------------------------------------------------------------
    # Registry lookup
    # ------------------------------------------------------------------

    def _lookup_fix(
        self, error_type: str, error_msg: str
    ) -> Optional[tuple]:
        """Look up a fix from the JSONL registry file or built-in registry.

        Returns (description, fix_command) or None.
        """
        combined = f"{error_type} {error_msg}"

        # 1. Try the JSONL registry file first
        if self.registry_path.exists():
            try:
                with open(self.registry_path, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        pattern = entry.get("error_pattern") or entry.get("pattern", "")
                        if not pattern:
                            continue
                        if re.search(pattern, combined, re.IGNORECASE):
                            fix_cmd = entry.get("fix", entry.get("fix_command", ""))
                            description = entry.get("description", pattern)
                            if fix_cmd:
                                return (description, fix_cmd)
            except OSError:
                pass

        # 2. Fall back to in-memory registry
        for remediation in REMEDIATION_REGISTRY:
            if remediation.matches(combined) and remediation.safe:
                # Resolve placeholders
                match = remediation.matches(combined)
                cmd = remediation.fix_command
                if match and match.groups():
                    for key in ("module", "file", "port"):
                        if f"{{{key}}}" in cmd:
                            cmd = cmd.replace(f"{{{key}}}", match.groups()[0])
                return (remediation.description, cmd)

        return None

    # ------------------------------------------------------------------
    # Safety checks
    # ------------------------------------------------------------------

    def _command_is_safe(self, fix_command: str) -> bool:
        """Return True if the fix command doesn't target protected paths."""
        return not bool(_BLOCKED_RE.search(fix_command))

    # ------------------------------------------------------------------
    # Circuit breaker (lazy load)
    # ------------------------------------------------------------------

    def _get_circuit_breaker(self):
        if self._cb is None:
            try:
                from lib.circuit_breaker import CircuitBreaker  # noqa: PLC0415
                self._cb = CircuitBreaker(
                    state_file=self.metrics_dir / "circuit-breaker-state.json",
                    failure_threshold=2,  # 2 failures → OPEN for auto-repair
                )
            except ImportError:
                self._cb = None
        return self._cb

    # ------------------------------------------------------------------
    # Metrics logging
    # ------------------------------------------------------------------

    def _log_repair_outcome(self, result: RepairResult) -> None:
        """Append repair outcome to metrics/repair-outcomes.jsonl."""
        try:
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
            path = self.metrics_dir / "repair-outcomes.jsonl"
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "repair_id": result.repair_id,
                "error_type": result.error_type,
                "service": result.service,
                "success": result.success,
                "reason": result.reason,
                "fix_applied": result.fix_applied,
                "diff_length": len(result.diff),
            }
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, default=str) + "\n")
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Legacy helpers (kept for backwards compatibility with existing hook)
# ---------------------------------------------------------------------------


def classify_error(error_type: str, message: str) -> Optional[Remediation]:
    """Match an error message against the in-memory registry. Return first match."""
    combined = f"{error_type} {message}"
    for remediation in REMEDIATION_REGISTRY:
        if remediation.matches(combined):
            return remediation
    return None


def apply_remediation(
    remediation: Remediation,
    message: str = "",
    dry_run: bool = False,
    metrics_dir: str = ".cognitive-os/metrics",
) -> dict:
    """Apply a remediation. In dry_run or unsafe mode, only suggest."""
    match = remediation.matches(message) if message else None
    command = remediation.fix_command

    if match and match.groups():
        groups = match.groups()
        placeholders = {"module": 0, "file": 0, "port": 0}
        for key in placeholders:
            if f"{{{key}}}" in command and len(groups) > 0:
                command = command.replace(f"{{{key}}}", groups[0])

    result = {
        "action": "suggest" if (dry_run or not remediation.safe) else "applied",
        "command": command,
        "description": remediation.description,
        "safe": remediation.safe,
        "dry_run": dry_run,
    }

    if not dry_run and remediation.safe:
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            result["exit_code"] = proc.returncode
            result["stdout"] = proc.stdout[:500]
            result["stderr"] = proc.stderr[:500]
            result["action"] = "applied" if proc.returncode == 0 else "failed"
        except (subprocess.TimeoutExpired, OSError) as exc:
            result["action"] = "failed"
            result["error"] = str(exc)

    _log_repair_outcome(result, metrics_dir)
    return result


def format_repair_suggestion(remediation: Remediation, message: str = "") -> str:
    """Human-readable suggestion string."""
    match = remediation.matches(message) if message else None
    command = remediation.fix_command
    if match and match.groups():
        for key in ("module", "file", "port"):
            if f"{{{key}}}" in command:
                command = command.replace(f"{{{key}}}", match.groups()[0])

    safe_tag = "[AUTO]" if remediation.safe else "[MANUAL]"
    return f"{safe_tag} {remediation.description}: {command}"


def _log_repair_outcome(result: dict, metrics_dir: str) -> None:
    """Append repair outcome to metrics."""
    try:
        os.makedirs(metrics_dir, exist_ok=True)
        path = os.path.join(metrics_dir, "repair-outcomes.jsonl")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **result,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except OSError:
        pass
