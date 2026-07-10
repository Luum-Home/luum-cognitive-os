# SCOPE: os-only
"""Skill Registry Runtime Drift Detector.

Compares on-disk SHA-256 hashes of skill files against the hashes recorded in
skills/REGISTRY.lock. Runs at SessionStart to surface mutations before any
agent tool invocations execute.

Policy (COS_SKILL_DRIFT_POLICY):
  warn   — log drifted skills to stderr and audit trail, exit 0 (default)
  block  — exit non-zero when drift is detected

Performance:
  mtime-keyed cache at .cognitive-os/state/skill-hash-cache.json avoids
  re-hashing files whose modification time has not changed. Target: <50ms
  for 175 skills on a warm cache.

Audit trail:
  Drift events appended to .cognitive-os/metrics/skill-drift.jsonl (NDJSON).

Killswitch:
  COS_DISABLE_SKILL_DRIFT_DETECTOR=1 — skip all checks, exit 0 immediately.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class DriftEvent:
    """A single skill file whose on-disk hash differs from the locked hash."""

    skill: str          # relative path, e.g. "skills/add-hook/SKILL.md"
    expected: str       # SHA-256 hex from REGISTRY.lock
    actual: str         # SHA-256 hex computed from disk
    policy: str         # "warn" | "block"
    ts: str             # ISO-8601 UTC timestamp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file using streaming reads (handles large files)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_registry(lock_path: Path) -> dict[str, str]:
    """Parse REGISTRY.lock YAML and return {relative_path: sha256}."""
    if not lock_path.exists():
        return {}
    try:
        raw = yaml.safe_load(lock_path.read_text(encoding="utf-8")) or {}
        entries: list[dict] = raw.get("skills", [])
        return {e["path"]: e["sha256"] for e in entries if "path" in e and "sha256" in e}
    except (OSError, yaml.YAMLError, TypeError):
        return {}


def _load_cache(cache_path: Path) -> dict[str, dict]:
    """Load the mtime cache. Returns {} on any error."""
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache_path: Path, cache: dict[str, dict]) -> None:
    """Atomically write the mtime cache."""
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=cache_path.parent,
            delete=False,
            suffix=".tmp",
        ) as f:
            json.dump(cache, f, indent=2)
            tmp_path = f.name
        os.replace(tmp_path, cache_path)
    except OSError:
        pass  # Cache write failure is non-fatal


def _append_drift_event(audit_path: Path, event: DriftEvent) -> None:
    """Append a drift event to the NDJSON audit trail."""
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")
    except OSError:
        pass  # Audit write failure is non-fatal


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class SkillDriftDetector:
    """Detect runtime drift between skill files and REGISTRY.lock hashes."""

    def __init__(
        self,
        lock_path: Optional[Path] = None,
        skills_root: Optional[Path] = None,
        project_root: Optional[Path] = None,
    ) -> None:
        root = project_root or Path.cwd()
        self.lock_path: Path = lock_path or root / "skills" / "REGISTRY.lock"
        self.skills_root: Path = skills_root or root / "skills"
        self.cache_path: Path = root / ".cognitive-os" / "state" / "skill-hash-cache.json"
        self.audit_path: Path = root / ".cognitive-os" / "metrics" / "skill-drift.jsonl"
        self.policy: str = os.environ.get("COS_SKILL_DRIFT_POLICY", "warn").strip().lower()
        self._registry: Optional[dict[str, str]] = None
        self._cache: Optional[dict[str, dict]] = None

    def _get_registry(self) -> dict[str, str]:
        if self._registry is None:
            self._registry = _load_registry(self.lock_path)
        return self._registry

    def _get_cache(self) -> dict[str, dict]:
        if self._cache is None:
            self._cache = _load_cache(self.cache_path)
        return self._cache

    def is_skill_locked(self, skill_id: str) -> bool:
        """Return True if the skill path exists in REGISTRY.lock."""
        return skill_id in self._get_registry()

    def verify_single(self, skill_path: Path) -> bool:
        """Return True if skill_path hash matches REGISTRY.lock. False on mismatch or missing."""
        registry = self._get_registry()
        # Normalise to relative path string matching the lock format
        try:
            rel = str(skill_path.relative_to(self.lock_path.parent.parent))
        except ValueError:
            rel = str(skill_path)
        expected = registry.get(rel)
        if expected is None:
            return False  # Not in lock — considered unverified
        if not skill_path.exists():
            return False
        actual = _sha256_file(skill_path)
        return actual == expected

    def _hash_with_cache(self, rel_path: str, abs_path: Path) -> str:
        """Return SHA-256 for abs_path, using mtime cache to avoid re-hashing."""
        cache = self._get_cache()
        try:
            mtime = abs_path.stat().st_mtime
        except OSError:
            return ""
        entry = cache.get(rel_path)
        if entry and entry.get("mtime") == mtime:
            return entry["sha256"]
        # Cache miss — recompute
        digest = _sha256_file(abs_path)
        cache[rel_path] = {"mtime": mtime, "sha256": digest}
        return digest

    def detect_drift(self) -> list[DriftEvent]:
        """Compare all locked skill hashes against disk. Returns list of drift events."""
        registry = self._get_registry()
        events: list[DriftEvent] = []
        ts = _utc_now()
        project_root = self.lock_path.parent.parent  # skills/ parent = project root

        for rel_path, expected_hash in registry.items():
            abs_path = project_root / rel_path
            if not abs_path.exists():
                # File removed after promotion — treat as drift
                event = DriftEvent(
                    skill=rel_path,
                    expected=expected_hash,
                    actual="<missing>",
                    policy=self.policy,
                    ts=ts,
                )
                events.append(event)
                _append_drift_event(self.audit_path, event)
                continue

            actual_hash = self._hash_with_cache(rel_path, abs_path)
            if actual_hash != expected_hash:
                event = DriftEvent(
                    skill=rel_path,
                    expected=expected_hash,
                    actual=actual_hash,
                    policy=self.policy,
                    ts=ts,
                )
                events.append(event)
                _append_drift_event(self.audit_path, event)

        # Persist updated cache
        if self._cache is not None:
            _save_cache(self.cache_path, self._cache)

        return events


# ---------------------------------------------------------------------------
# CLI entry point (called from the shell hook)
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the SessionStart hook."""
    if os.environ.get("COS_DISABLE_SKILL_DRIFT_DETECTOR"):
        sys.exit(0)

    detector = SkillDriftDetector()
    try:
        events = detector.detect_drift()
    except Exception as exc:  # noqa: BLE001
        print(f"[skill-drift-detector] ERROR: {exc}", file=sys.stderr)
        sys.exit(0)  # Non-fatal — never block session start on detector error

    if not events:
        sys.exit(0)

    policy = os.environ.get("COS_SKILL_DRIFT_POLICY", "warn").strip().lower()
    print(
        f"[skill-drift-detector] {len(events)} drifted skill(s) detected:",
        file=sys.stderr,
    )
    for ev in events:
        print(f"  {ev.skill}: expected={ev.expected[:12]}… actual={ev.actual[:12]}…", file=sys.stderr)

    if policy == "block":
        print(
            "[skill-drift-detector] Policy=block — session start blocked. "
            "Fix drift or set COS_SKILL_DRIFT_POLICY=warn to continue.",
            file=sys.stderr,
        )
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
