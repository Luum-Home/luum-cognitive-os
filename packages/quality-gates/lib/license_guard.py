# scope: both
"""License Auto-Guard -- Enforce license policy on dependencies.

Checks licenses against blocked/caution lists, auto-blocks in
content policy, and scans existing references in the codebase.

Author: luum
Python 3.9+ compatible.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---- License classifications ----

BLOCKED_LICENSES: Dict[str, str] = {
    "AGPL-3.0": "Network copyleft -- forces open-sourcing all SaaS code",
    "AGPL-3.0-only": "Network copyleft -- forces open-sourcing all SaaS code",
    "AGPL-3.0-or-later": "Network copyleft -- forces open-sourcing all SaaS code",
    "SSPL-1.0": "Server-side copyleft -- blocks SaaS deployment entirely",
    "SSPL": "Server-side copyleft -- blocks SaaS deployment entirely",
    "CC-BY-NC-4.0": "Non-commercial restriction -- incompatible with commercial use",
    "CC-BY-NC-3.0": "Non-commercial restriction -- incompatible with commercial use",
    "CC-BY-NC-SA-4.0": "Non-commercial + share-alike -- incompatible with commercial use",
    "BSL-1.1": "Business source -- cannot compete with vendor",
    "BUSL-1.1": "Business source -- cannot compete with vendor",
    "ELv2": "Elastic License -- cannot offer as managed service",
    "Elastic-2.0": "Elastic License -- cannot offer as managed service",
    "Commons-Clause": "Cannot sell the software as a service",
    "FSL-1.0": "Functional Source License -- commercial restrictions",
    "FSL-1.1": "Functional Source License -- commercial restrictions",
}

CAUTION_LICENSES: Dict[str, str] = {
    "GPL-2.0": "Viral copyleft -- derivative works must be GPL",
    "GPL-2.0-only": "Viral copyleft -- derivative works must be GPL",
    "GPL-2.0-or-later": "Viral copyleft -- derivative works must be GPL",
    "GPL-3.0": "Viral copyleft -- derivative works must be GPL",
    "GPL-3.0-only": "Viral copyleft -- derivative works must be GPL",
    "GPL-3.0-or-later": "Viral copyleft -- derivative works must be GPL",
    "LGPL-2.1": "Dynamic linking only -- do not modify or statically link",
    "LGPL-2.1-only": "Dynamic linking only -- do not modify or statically link",
    "LGPL-3.0": "Dynamic linking only -- do not modify or statically link",
    "LGPL-3.0-only": "Dynamic linking only -- do not modify or statically link",
    "MPL-2.0": "File-level copyleft -- changes to MPL files must be open-sourced",
}

SAFE_LICENSES: Dict[str, str] = {
    "MIT": "Permissive -- no restrictions",
    "Apache-2.0": "Permissive -- maintain NOTICE + indicate changes",
    "BSD-2-Clause": "Permissive -- maintain copyright",
    "BSD-3-Clause": "Permissive -- maintain copyright",
    "ISC": "Permissive -- no restrictions",
    "CC0-1.0": "Public domain -- no restrictions",
    "Unlicense": "Public domain -- no restrictions",
    "0BSD": "Permissive -- no restrictions",
}


@dataclass
class LicenseCheckResult:
    """Result of a license check."""

    tool_name: str
    license_id: str
    status: str  # "safe", "caution", "blocked", "unknown"
    reason: str
    action_required: str


def check_license(tool_name: str, license_id: str) -> LicenseCheckResult:
    """Check a single tool's license against the policy.

    Returns a ``LicenseCheckResult`` with status and recommended action.
    """
    normalized = license_id.strip()

    if normalized in BLOCKED_LICENSES:
        return LicenseCheckResult(
            tool_name=tool_name,
            license_id=normalized,
            status="blocked",
            reason=BLOCKED_LICENSES[normalized],
            action_required="REJECT -- do not use this dependency",
        )

    if normalized in CAUTION_LICENSES:
        return LicenseCheckResult(
            tool_name=tool_name,
            license_id=normalized,
            status="caution",
            reason=CAUTION_LICENSES[normalized],
            action_required="Review usage carefully -- dynamic linking only for LGPL, no modifications for MPL",
        )

    if normalized in SAFE_LICENSES:
        return LicenseCheckResult(
            tool_name=tool_name,
            license_id=normalized,
            status="safe",
            reason=SAFE_LICENSES[normalized],
            action_required="None -- safe to use",
        )

    return LicenseCheckResult(
        tool_name=tool_name,
        license_id=normalized,
        status="unknown",
        reason=f"License '{normalized}' not in known lists -- treat as caution",
        action_required="Manual review required -- verify license terms before adoption",
    )


def auto_block_in_content_policy(
    tool_name: str,
    license_id: str,
    policy_path: str = ".cognitive-os/content-policy.yaml",
) -> bool:
    """Add a blocked tool to content-policy.yaml.

    Returns True if the entry was added, False if it already existed or
    the license is not blocked.
    """
    result = check_license(tool_name, license_id)
    if result.status != "blocked":
        return False

    path = Path(policy_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_content = ""
    if path.exists():
        existing_content = path.read_text()

    # Check for duplicates
    if tool_name in existing_content:
        return False

    entry = (
        f"\n# Auto-blocked by license_guard: {license_id}\n"
        f"- tool: {tool_name}\n"
        f"  license: {license_id}\n"
        f"  reason: {result.reason}\n"
        f"  blocked_at: {datetime.now(timezone.utc).isoformat()}\n"
    )

    with open(path, "a") as fh:
        fh.write(entry)

    return True


def check_and_enforce(
    tool_name: str,
    license_id: str,
    policy_path: str = ".cognitive-os/content-policy.yaml",
    log_path: str = ".cognitive-os/metrics/license-checks.jsonl",
) -> LicenseCheckResult:
    """Full flow: check license, auto-block if needed, log result."""
    result = check_license(tool_name, license_id)

    if result.status == "blocked":
        auto_block_in_content_policy(tool_name, license_id, policy_path)

    # Log the check
    log = Path(log_path)
    log.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "license": license_id,
        "status": result.status,
        "reason": result.reason,
    }
    with open(log, "a") as fh:
        fh.write(json.dumps(entry) + "\n")

    return result


def format_license_report(results: List[LicenseCheckResult]) -> str:
    """Format a user-visible report from multiple license check results."""
    lines: List[str] = []
    lines.append("## License Check Report")
    lines.append("")

    blocked = [r for r in results if r.status == "blocked"]
    caution = [r for r in results if r.status == "caution"]
    unknown = [r for r in results if r.status == "unknown"]
    safe = [r for r in results if r.status == "safe"]

    if blocked:
        lines.append(f"### BLOCKED ({len(blocked)})")
        for r in blocked:
            lines.append(f"- **{r.tool_name}** ({r.license_id}): {r.reason}")
        lines.append("")

    if caution:
        lines.append(f"### CAUTION ({len(caution)})")
        for r in caution:
            lines.append(f"- **{r.tool_name}** ({r.license_id}): {r.reason}")
        lines.append("")

    if unknown:
        lines.append(f"### UNKNOWN ({len(unknown)})")
        for r in unknown:
            lines.append(f"- **{r.tool_name}** ({r.license_id}): {r.reason}")
        lines.append("")

    if safe:
        lines.append(f"### SAFE ({len(safe)})")
        for r in safe:
            lines.append(f"- **{r.tool_name}** ({r.license_id})")
        lines.append("")

    lines.append(f"**Total**: {len(results)} checked | "
                 f"{len(blocked)} blocked | {len(caution)} caution | "
                 f"{len(unknown)} unknown | {len(safe)} safe")

    return "\n".join(lines)


def scan_existing_references(
    project_dir: str = ".",
    extensions: Optional[List[str]] = None,
) -> List[LicenseCheckResult]:
    """Scan codebase for references to blocked license tools.

    Searches for SPDX identifiers of blocked licenses in common config
    and documentation files.
    """
    if extensions is None:
        extensions = [".yaml", ".yml", ".json", ".md", ".toml", ".txt"]

    blocked_ids = set(BLOCKED_LICENSES.keys())
    # Build a pattern that matches any blocked SPDX ID
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(lid) for lid in sorted(blocked_ids)) + r")\b",
        re.IGNORECASE,
    )

    findings: List[LicenseCheckResult] = []
    root = Path(project_dir)

    for ext in extensions:
        for filepath in root.rglob(f"*{ext}"):
            # Skip hidden directories and node_modules
            parts = filepath.parts
            if any(p.startswith(".") and p not in (".", "..") for p in parts):
                continue
            if "node_modules" in parts or "vendor" in parts:
                continue
            try:
                content = filepath.read_text(errors="ignore")
            except OSError:
                continue
            for match in pattern.finditer(content):
                license_id = match.group(1)
                findings.append(
                    LicenseCheckResult(
                        tool_name=str(filepath.relative_to(root)),
                        license_id=license_id,
                        status="blocked",
                        reason=BLOCKED_LICENSES.get(license_id, "Blocked license found in file"),
                        action_required=f"Review reference in {filepath}",
                    )
                )

    return findings
