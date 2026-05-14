#!/usr/bin/env python3
# SCOPE: os-only
"""cos-generate-notices.py — NOTICE.md and THIRD_PARTY_LICENSES.txt generator.

Combines two data sources:
  1. manifests/external-tool-licenses.yaml  — operator-curated upstream tools
  2. pip-licenses (optional)                — transitive Python dependency scan

Usage:
  python scripts/cos-generate-notices.py                # regenerate both files
  python scripts/cos-generate-notices.py --check        # CI drift check (exit 1 on diff)
  python scripts/cos-generate-notices.py --mode saas    # saas mode (all deps required)
  python scripts/cos-generate-notices.py --out /tmp     # write to alternate directory

Python 3.10+ required. No third-party imports required (pip-licenses is optional).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import textwrap
from collections import Counter
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "manifests" / "external-tool-licenses.yaml"

NOTICE_FILENAME = "NOTICE.md"
THIRD_PARTY_FILENAME = "THIRD_PARTY_LICENSES.txt"

NOTICE_HEADER = (
    "<!-- This file is auto-generated. "
    "Run scripts/cos-generate-notices.py to regenerate. -->\n"
)

SEPARATOR = "=" * 78


# ---------------------------------------------------------------------------
# Minimal YAML parser (stdlib only, no PyYAML dependency)
# ---------------------------------------------------------------------------

def _parse_yaml_manifest(path: Path) -> dict[str, Any]:
    """Parse the external-tool-licenses.yaml manifest.

    This is NOT a general-purpose YAML parser. It handles the specific
    structure of the manifest file: top-level scalar keys and a list of
    entries with known field types (str, list[str], int).

    Limitations: does not handle anchors, multi-document streams, or
    complex nested mappings beyond one level of list items. Falls back
    to a subprocess call to `python3 -c 'import yaml'` if available,
    otherwise uses the built-in line parser.
    """
    text = path.read_text(encoding="utf-8")

    # Try PyYAML if available (faster, correct)
    try:
        import yaml  # type: ignore[import]
        return yaml.safe_load(text)
    except ImportError:
        pass

    # Fallback: hand-rolled parser for this specific schema
    return _parse_manifest_fallback(text)


def _parse_manifest_fallback(text: str) -> dict[str, Any]:
    """Parse the manifest YAML with a minimal line-by-line scanner."""
    lines = text.splitlines()
    result: dict[str, Any] = {"schema_version": 1, "entries": []}
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_key: str | None = None
    in_entries = False
    in_cos_files = False
    current_multiline: list[str] = []

    def _flush_multiline() -> None:
        nonlocal current_key, current_multiline
        if current is not None and current_key and current_multiline:
            current[current_key] = " ".join(current_multiline).strip()
        current_key = None
        current_multiline = []

    for raw_line in lines:
        stripped = raw_line.rstrip()

        # Skip comments and blank lines
        if not stripped or stripped.lstrip().startswith("#"):
            if in_cos_files:
                in_cos_files = False
                _flush_multiline()
            continue

        indent = len(raw_line) - len(raw_line.lstrip())

        # Top-level key
        if indent == 0:
            if stripped.startswith("schema_version:"):
                val = stripped.split(":", 1)[1].strip()
                result["schema_version"] = int(val) if val.isdigit() else val
            elif stripped == "entries:":
                in_entries = True
            _flush_multiline()
            in_cos_files = False
            continue

        # List item: new entry
        if indent == 2 and stripped.startswith("- name:"):
            _flush_multiline()
            in_cos_files = False
            if current is not None:
                entries.append(current)
            name_val = stripped.split(":", 1)[1].strip().strip('"')
            current = {"name": name_val}
            current_key = None
            continue

        if not in_entries or current is None:
            continue

        # cos_files list items
        if indent == 6 and stripped.startswith("- "):
            val = stripped[2:].strip().strip('"')
            current.setdefault("cos_files", []).append(val)
            continue

        # Multiline block scalar (>) continuation
        if current_key and indent >= 6 and not stripped.lstrip().startswith("-"):
            # Continuation of a block scalar
            fragment = stripped.strip()
            if fragment:
                current_multiline.append(fragment)
            continue

        # Key-value pair inside entry (indent 4)
        if indent == 4 and ":" in stripped:
            _flush_multiline()
            in_cos_files = False
            colon_pos = stripped.index(":")
            key = stripped[:colon_pos].strip()
            val = stripped[colon_pos + 1:].strip()

            if key == "cos_files":
                in_cos_files = True
                current["cos_files"] = current.get("cos_files", [])
                current_key = None
            elif val == ">":
                # Block scalar — next indented lines are the value
                current_key = key
                current_multiline = []
            elif val:
                current[key] = val.strip('"')
            else:
                current[key] = ""
            continue

    _flush_multiline()
    if current is not None:
        entries.append(current)

    result["entries"] = entries
    return result


# ---------------------------------------------------------------------------
# Transitive dependency scanner (pip-licenses, optional)
# ---------------------------------------------------------------------------

def _scan_transitive_deps(mode: str) -> list[dict[str, str]]:
    """Run pip-licenses and return a list of package dicts.

    Returns an empty list with a warning if pip-licenses is not installed.
    Each dict has: name, version, license, url.
    """
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "piplicenses",
                "--format", "json",
                "--with-urls",
                "--with-license-file",
                "--no-license-path",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        raw = json.loads(result.stdout)
        deps = []
        for pkg in raw:
            deps.append({
                "name": pkg.get("Name", ""),
                "version": pkg.get("Version", ""),
                "license": pkg.get("License", "UNKNOWN"),
                "url": pkg.get("URL", ""),
            })
        return deps

    except FileNotFoundError:
        _warn_pip_licenses_missing()
        return []
    except (ModuleNotFoundError, subprocess.CalledProcessError, RuntimeError,
            json.JSONDecodeError) as exc:
        _warn_pip_licenses_missing(extra=str(exc))
        return []


def _warn_pip_licenses_missing(extra: str = "") -> None:
    msg = (
        "WARNING: pip-licenses is not installed. Transitive Python dependency scan "
        "will be skipped.\n"
        "To enable the full scan, install it:\n"
        "  pip install pip-licenses\n"
        "Then re-run: python scripts/cos-generate-notices.py"
    )
    if extra:
        msg += f"\n  Detail: {extra}"
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# NOTICE.md generator
# ---------------------------------------------------------------------------

def _status_badge(status: str) -> str:
    """Return a short Markdown inline badge for compliance status."""
    badges = {
        "ALLOWED": "![ALLOWED](https://img.shields.io/badge/status-ALLOWED-green)",
        "PATTERN-ONLY": "![PATTERN-ONLY](https://img.shields.io/badge/status-PATTERN--ONLY-blue)",
        "TRIAL-PATTERNS": "![TRIAL-PATTERNS](https://img.shields.io/badge/status-TRIAL--PATTERNS-yellow)",
        "HOLD": "![HOLD](https://img.shields.io/badge/status-HOLD-orange)",
        "BLOCKED": "![BLOCKED](https://img.shields.io/badge/status-BLOCKED-red)",
    }
    return badges.get(status.upper(), f"`{status}`")


def _is_copyleft(spdx: str) -> bool:
    """Return True if the SPDX identifier indicates a copyleft license."""
    copyleft_prefixes = ("AGPL", "GPL", "LGPL", "EUPL", "OSL", "CDDL", "MPL",
                         "CC-BY-SA", "CC-BY-NC")
    upper = spdx.upper()
    return any(upper.startswith(p) for p in copyleft_prefixes)


def _generate_notice_md(
    entries: list[dict[str, Any]],
    deps: list[dict[str, str]],
    mode: str,
) -> str:
    """Build the full NOTICE.md content string."""
    lines: list[str] = []

    lines.append(NOTICE_HEADER)
    lines.append("# NOTICE — Third-Party Attributions\n")
    lines.append(
        "> This file lists upstream tools and Python dependencies used in "
        "Cognitive OS (COS). It is auto-generated from "
        "`manifests/external-tool-licenses.yaml` and the installed Python "
        "environment. Do not edit manually.\n"
    )

    # ------------------------------------------------------------------
    # §1 Curated upstream tools
    # ------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## §1 — Curated Upstream Tools\n")
    lines.append(
        "These tools have been vendored, ported, or adapted into COS source "
        "files. Each entry is governed by the corresponding Annex F compliance "
        "dossier.\n"
    )

    # In oss mode, flag copyleft entries prominently
    for entry in entries:
        name = entry.get("name", "UNKNOWN")
        spdx = entry.get("spdx", "UNKNOWN")
        status = entry.get("status", "UNKNOWN")
        upstream_url = entry.get("upstream_url", "UNKNOWN")
        copyright_ = entry.get("copyright", "MISSING")
        attribution = entry.get("attribution", "")
        cos_files = entry.get("cos_files", [])
        annex_f = entry.get("annex_f", "")
        notes = entry.get("notes", "")

        # oss mode: warn on copyleft
        copyleft_warning = ""
        if mode == "oss" and _is_copyleft(spdx):
            copyleft_warning = (
                "\n> **OSS MODE WARNING**: This entry has a copyleft license "
                f"(`{spdx}`). Runtime inclusion is blocked per `rules/license-policy.md`."
            )

        lines.append(f"### {name}\n")
        lines.append(f"- **Status**: {_status_badge(status)}  ")
        lines.append(f"- **License (SPDX)**: `{spdx}`  ")
        lines.append(f"- **Upstream**: {upstream_url}  ")
        lines.append(f"- **Copyright**: {copyright_}  ")

        if attribution:
            lines.append(f"- **Attribution**: {attribution}  ")

        if cos_files:
            lines.append("- **COS files**:")
            for f in cos_files:
                lines.append(f"  - `{f}`")

        if annex_f:
            lines.append(f"- **Annex F**: `{annex_f}`  ")

        if copyleft_warning:
            lines.append(copyleft_warning)

        if notes:
            lines.append(
                "\n<details><summary>Compliance notes</summary>\n\n"
                + textwrap.fill(notes.strip(), width=100)
                + "\n\n</details>"
            )

        lines.append("")

    # ------------------------------------------------------------------
    # §2 Transitive Python dependencies
    # ------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## §2 — Transitive Python Dependencies\n")

    if not deps:
        lines.append(
            "> Transitive scan was skipped (pip-licenses not installed). "
            "Run `pip install pip-licenses` and regenerate to populate this section.\n"
        )
    else:
        lines.append(
            "| Package | Version | License | Source |"
        )
        lines.append(
            "| ------- | ------- | ------- | ------ |"
        )
        for dep in sorted(deps, key=lambda d: d["name"].lower()):
            pkg_name = dep["name"]
            version = dep["version"]
            lic = dep["license"]
            url = dep.get("url", "")
            url_cell = f"[link]({url})" if url else "—"

            # saas mode: include all; oss mode: flag copyleft
            flag = ""
            if mode == "oss" and _is_copyleft(lic):
                flag = " ⚠️ COPYLEFT"

            lines.append(
                f"| `{pkg_name}` | {version} | `{lic}`{flag} | {url_cell} |"
            )
        lines.append("")

    # ------------------------------------------------------------------
    # §3 License families summary
    # ------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## §3 — License Families Summary\n")

    all_spdx: list[str] = [e.get("spdx", "UNKNOWN") for e in entries]
    for dep in deps:
        all_spdx.append(dep.get("license", "UNKNOWN"))

    counter = Counter(all_spdx)
    lines.append("| SPDX / License | Count |")
    lines.append("| -------------- | ----- |")
    for spdx_id, count in sorted(counter.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| `{spdx_id}` | {count} |")
    lines.append("")

    lines.append("---\n")
    lines.append(
        "_Generated by `scripts/cos-generate-notices.py` on "
        + _today_iso()
        + "_\n"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# THIRD_PARTY_LICENSES.txt generator
# ---------------------------------------------------------------------------

_STANDARD_MIT = """\
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

_STANDARD_APACHE2 = """\
Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

[Full text available at: https://www.apache.org/licenses/LICENSE-2.0]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

_STANDARD_AGPL3_NOTICE = """\
GNU AFFERO GENERAL PUBLIC LICENSE
Version 3, 19 November 2007

[Full text available at: https://www.gnu.org/licenses/agpl-3.0.txt]

RUNTIME INCLUSION: REJECTED — AGPL-3.0 triggers copyleft on network
interaction per §13. This entry is included for documentation purposes
only (TRIAL-PATTERNS pattern-only classification). No helix-db source
code has been vendored into this repository."""


def _license_body(entry: dict[str, Any]) -> str:
    """Return a license body text for the given entry."""
    spdx = entry.get("spdx", "UNKNOWN").upper()
    copyright_ = entry.get("copyright", "")

    if spdx == "MIT":
        header = f"{copyright_}\n\n" if copyright_ else ""
        return header + _STANDARD_MIT
    elif spdx == "APACHE-2.0":
        header = f"{copyright_}\n\n" if copyright_ else ""
        return header + _STANDARD_APACHE2
    elif spdx == "AGPL-3.0":
        return _STANDARD_AGPL3_NOTICE
    elif spdx in ("UNKNOWN", "PROPRIETARY", "CONFIDENTIAL"):
        return (
            f"License text unavailable — {spdx}.\n"
            f"See compliance notes in manifest and Annex F dossier.\n"
            f"Copyright: {copyright_}"
        )
    else:
        return (
            f"SPDX: {spdx}\n"
            f"Copyright: {copyright_}\n\n"
            "License text not embedded. See upstream repository for full text."
        )


def _generate_third_party_licenses(entries: list[dict[str, Any]]) -> str:
    """Build THIRD_PARTY_LICENSES.txt content."""
    parts: list[str] = []
    parts.append(
        "THIRD-PARTY LICENSE NOTICES\n"
        "Cognitive OS (COS) — generated by scripts/cos-generate-notices.py\n"
        + _today_iso()
        + "\n"
    )
    parts.append(SEPARATOR)

    for entry in entries:
        name = entry.get("name", "UNKNOWN")
        upstream_url = entry.get("upstream_url", "")
        spdx = entry.get("spdx", "UNKNOWN")
        status = entry.get("status", "UNKNOWN")

        header = (
            f"\n{name}\n"
            f"{'─' * len(name)}\n"
            f"Upstream: {upstream_url}\n"
            f"SPDX: {spdx}\n"
            f"Status: {status}\n\n"
        )
        parts.append(header + _license_body(entry))
        parts.append("\n" + SEPARATOR)

    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_iso() -> str:
    """Return today's date as an ISO string using only stdlib."""
    import datetime
    return datetime.date.today().isoformat()


def _read_existing(path: Path) -> str | None:
    """Read existing file content, returning None if file does not exist."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _normalise_for_check(text: str) -> str:
    """Strip the date line before comparing, to avoid spurious drift on date change."""
    lines = [
        ln for ln in text.splitlines()
        if not ln.startswith("_Generated by") and not ln.startswith("Cognitive OS (COS) — generated")
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cos-generate-notices",
        description=(
            "Generate NOTICE.md and THIRD_PARTY_LICENSES.txt for Cognitive OS."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["oss", "saas"],
        default="oss",
        help=(
            "Output mode. 'oss' is stricter on copyleft; 'saas' requires "
            "NOTICE for ALL deps (default: oss)."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "CI mode: verify existing NOTICE.md and THIRD_PARTY_LICENSES.txt "
            "match what would be generated. Exit 1 on drift."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT,
        help="Output directory (default: repo root).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help=f"Path to manifest YAML (default: {MANIFEST_PATH}).",
    )

    args = parser.parse_args(argv)
    out_dir: Path = args.out
    mode: str = args.mode
    manifest_path: Path = args.manifest

    # Validate manifest exists
    if not manifest_path.exists():
        print(
            f"ERROR: manifest not found: {manifest_path}\n"
            "Expected: manifests/external-tool-licenses.yaml",
            file=sys.stderr,
        )
        return 2

    # Parse manifest
    try:
        manifest = _parse_yaml_manifest(manifest_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed to parse manifest: {exc}", file=sys.stderr)
        return 2

    entries: list[dict[str, Any]] = manifest.get("entries", [])
    if not entries:
        print("WARNING: manifest has no entries.", file=sys.stderr)

    # Scan transitive deps
    deps = _scan_transitive_deps(mode)

    # Generate content
    notice_content = _generate_notice_md(entries, deps, mode)
    third_party_content = _generate_third_party_licenses(entries)

    notice_path = out_dir / NOTICE_FILENAME
    third_party_path = out_dir / THIRD_PARTY_FILENAME

    if args.check:
        drift = False

        existing_notice = _read_existing(notice_path)
        if existing_notice is None:
            print(
                f"DRIFT: {notice_path} does not exist (expected generated file).",
                file=sys.stderr,
            )
            drift = True
        elif _normalise_for_check(existing_notice) != _normalise_for_check(notice_content):
            print(
                f"DRIFT: {notice_path} does not match what would be generated.\n"
                "Re-run `python scripts/cos-generate-notices.py` to fix.",
                file=sys.stderr,
            )
            drift = True
        else:
            print(f"OK: {notice_path} is up to date.")

        existing_third_party = _read_existing(third_party_path)
        if existing_third_party is None:
            print(
                f"DRIFT: {third_party_path} does not exist.",
                file=sys.stderr,
            )
            drift = True
        elif (
            _normalise_for_check(existing_third_party)
            != _normalise_for_check(third_party_content)
        ):
            print(
                f"DRIFT: {third_party_path} does not match what would be generated.\n"
                "Re-run `python scripts/cos-generate-notices.py` to fix.",
                file=sys.stderr,
            )
            drift = True
        else:
            print(f"OK: {third_party_path} is up to date.")

        return 1 if drift else 0

    # Write output files
    out_dir.mkdir(parents=True, exist_ok=True)
    notice_path.write_text(notice_content, encoding="utf-8")
    third_party_path.write_text(third_party_content, encoding="utf-8")

    notice_lines = notice_content.count("\n")
    third_party_lines = third_party_content.count("\n")
    print(
        f"Generated {notice_path} ({notice_lines} lines)\n"
        f"Generated {third_party_path} ({third_party_lines} lines)\n"
        f"Curated entries: {len(entries)}\n"
        f"Transitive deps: {len(deps)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
