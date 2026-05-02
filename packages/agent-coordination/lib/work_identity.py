# SCOPE: both
"""Work-identity fingerprinting — ADR-116 P1.2.

Provides a stable ``fingerprint`` that identifies *equivalent work* across
sessions, independent of session ID, agent ID, or wall-clock time.

A fingerprint is ``sha256(normalized_description + "\x00" + sorted_outputs_joined)``
truncated to 16 hex characters.  That gives 64-bit collision resistance —
adequate for a cross-session deduplication primitive in a single codebase.

Typical call sequence
---------------------
1. ``fp = compute_fingerprint(description, expected_outputs)``
2. ``existing = find_existing_work(fp, repo_root)``
3. If ``existing`` is None, proceed; otherwise surface the conflict.
4. On commit: ``msg = embed_in_commit_msg(raw_msg, fp)``

All functions are pure / stateless except ``find_existing_work``, which reads
``.cognitive-os/tasks/active-claims.json`` and recent ``git log``.

Python 3.9+ compatible.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable, Optional

# Trailer key used in git commit messages
FINGERPRINT_TRAILER = "X-COS-Work-Fingerprint"

# Regex to extract the trailer from a commit message body
_TRAILER_RE = re.compile(
    r"^" + re.escape(FINGERPRINT_TRAILER) + r":\s*([0-9a-f]{16,64})",
    re.MULTILINE,
)

# Path within a repo root to the active-claims ledger (runtime file)
_ACTIVE_CLAIMS_REL = ".cognitive-os/tasks/active-claims.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Normalize free-form description text for stable hashing.

    Rules (mirrors ``_cos_normalize_task_text`` in hooks/_lib/task-identity.sh):
    - Lowercase
    - Collapse all whitespace (including newlines/tabs) to a single space
    - Strip leading/trailing whitespace
    """
    lowered = text.lower()
    collapsed = re.sub(r"\s+", " ", lowered)
    return collapsed.strip()


def _sort_outputs(outputs: Iterable[str]) -> list[str]:
    """Return a deterministically ordered list of output paths."""
    return sorted({o.strip() for o in outputs if o.strip()})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_fingerprint(description: str, outputs: Iterable[str]) -> str:
    """Compute a 16-hex-char work fingerprint.

    The fingerprint is stable: calling with the same *description* and
    *outputs* (regardless of order) always returns the same value.

    Args:
        description: Human-readable task description or task body text.
        outputs: Expected output file paths / artefact names produced by the
                 work.  Order does not matter; duplicates are deduplicated.

    Returns:
        16-character lowercase hex string (64-bit prefix of SHA-256).
    """
    normalized_desc = _normalize(description)
    sorted_out = _sort_outputs(outputs)
    # Null byte separator prevents length-extension confusion between parts
    payload = normalized_desc + "\x00" + "\x01".join(sorted_out)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest[:16]


def find_existing_work(fingerprint: str, repo_root: Path) -> Optional[dict]:
    """Search for existing work that matches *fingerprint*.

    Search order:
    1. ``.cognitive-os/tasks/active-claims.json`` — live claims in-progress.
    2. ``git log`` trailer scan — last 100 commits on any local ref.

    Args:
        fingerprint: 16-char hex fingerprint from :func:`compute_fingerprint`.
        repo_root: Absolute path to the git repository root.

    Returns:
        A dict describing the existing work on the first match, or ``None``
        if no match is found.

        Active-claim match keys:
            ``source``, ``task_id``, ``session_id``, ``claimed_at``,
            ``fingerprint``.

        Commit match keys:
            ``source``, ``commit_sha``, ``commit_subject``, ``fingerprint``.
    """
    # -- 1. Active-claims ledger ------------------------------------------
    claims_file = repo_root / _ACTIVE_CLAIMS_REL
    if claims_file.is_file():
        try:
            raw = claims_file.read_text(encoding="utf-8")
            claims = json.loads(raw) if raw.strip() else []
            if isinstance(claims, dict):
                # Accept both list and {task_id: claim_dict} shapes
                claims = list(claims.values())
            for claim in claims:
                if isinstance(claim, dict) and claim.get("fingerprint") == fingerprint:
                    return {
                        "source": "active-claims",
                        "task_id": claim.get("task_id"),
                        "session_id": claim.get("session_id"),
                        "claimed_at": claim.get("claimed_at"),
                        "fingerprint": fingerprint,
                    }
        except (json.JSONDecodeError, OSError):
            pass  # Corrupt / locked file — skip rather than hard-fail

    # -- 2. Recent git commits -------------------------------------------
    try:
        result = subprocess.run(
            [
                "git",
                "-C", str(repo_root),
                "log",
                "--format=%H%x00%s%x00%b%x00---COMMIT---",
                "-n", "100",
                "--all",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            for block in result.stdout.split("---COMMIT---"):
                block = block.strip()
                if not block:
                    continue
                parts = block.split("\x00", 2)
                if len(parts) < 3:
                    continue
                sha, subject, body = parts[0].strip(), parts[1].strip(), parts[2].strip()
                # Check both body (trailer section) and full message
                full_text = subject + "\n" + body
                match = _TRAILER_RE.search(full_text)
                if match and match.group(1) == fingerprint:
                    return {
                        "source": "git-log",
                        "commit_sha": sha,
                        "commit_subject": subject,
                        "fingerprint": fingerprint,
                    }
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass  # git not available or repo not initialized

    return None


def embed_in_commit_msg(message: str, fingerprint: str) -> str:
    """Append the fingerprint trailer to *message*.

    If the trailer is already present (idempotent), the existing value is
    replaced.  Ensures a single blank line separates the body from the
    trailers section (git convention).

    Args:
        message: Raw commit message (may or may not have a trailers section).
        fingerprint: 16-char hex string from :func:`compute_fingerprint`.

    Returns:
        Updated commit message string with ``X-COS-Work-Fingerprint: <fp>``
        appended.
    """
    trailer_line = f"{FINGERPRINT_TRAILER}: {fingerprint}"

    # Remove any pre-existing fingerprint trailer (idempotent)
    cleaned = _TRAILER_RE.sub("", message).rstrip()

    # Ensure there is exactly one blank line before the trailer block.
    # If the message already ends with a trailer-like line (no blank line
    # prefix needed), still add the separator to keep git happy.
    return cleaned + "\n\n" + trailer_line + "\n"


def parse_fingerprint_from_msg(message: str) -> Optional[str]:
    """Extract the fingerprint value from a commit message, or return None."""
    match = _TRAILER_RE.search(message)
    return match.group(1) if match else None
