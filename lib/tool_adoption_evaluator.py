# scope: both
"""Tool Adoption Evaluator — deep evaluation pipeline for external tools and repos.

Evaluates GitHub URLs for license compatibility, deployment weight, feature overlap,
UI components, and generates adoption recommendations (ADOPT/ADAPT/WATCH/SKIP).

Usage:
    from lib.tool_adoption_evaluator import ToolAdoptionEvaluator
    e = ToolAdoptionEvaluator()
    report = e.evaluate_url("https://github.com/owner/repo")
    print(e.format_evaluation_report(report))
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# License tables
# ---------------------------------------------------------------------------

_LICENSE_APPROVED = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0"}
_LICENSE_CAUTION = {"MPL-2.0", "LGPL-2.1", "LGPL-3.0", "GPL-2.0", "GPL-3.0", "Artistic-2.0"}
_LICENSE_BLOCKED = {"AGPL-3.0", "SSPL", "BSL-1.1", "ELv2", "Commons-Clause", "FSL-1.1"}


def _normalize_license(raw: str | None) -> str:
    """Normalise a license string to a canonical short identifier."""
    if not raw:
        return "Unknown"
    raw = raw.strip()
    mapping = {
        "mit": "MIT",
        "apache-2.0": "Apache-2.0",
        "apache 2.0": "Apache-2.0",
        "bsd-2-clause": "BSD-2-Clause",
        "bsd-3-clause": "BSD-3-Clause",
        "isc": "ISC",
        "cc0-1.0": "CC0-1.0",
        "mpl-2.0": "MPL-2.0",
        "lgpl-2.1": "LGPL-2.1",
        "lgpl-3.0": "LGPL-3.0",
        "gpl-2.0": "GPL-2.0",
        "gpl-3.0": "GPL-3.0",
        "agpl-3.0": "AGPL-3.0",
        "agpl": "AGPL-3.0",
        "sspl": "SSPL",
        "bsl-1.1": "BSL-1.1",
        "business source license": "BSL-1.1",
    }
    return mapping.get(raw.lower(), raw)


# ---------------------------------------------------------------------------
# URL / slug helpers
# ---------------------------------------------------------------------------

def _parse_github_slug(url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub URL, or None if not GitHub."""
    m = re.search(r"github\.com[/:]([^/]+)/([^/\s#?]+)", url)
    if not m:
        return None
    return m.group(1), m.group(2).removesuffix(".git")


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ToolAdoptionEvaluator:
    """Deep evaluation pipeline for external tools and repos."""

    def __init__(self, project_root: str = "."):
        self._root = Path(project_root)
        self._lib_dir = self._root / "lib"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_url(self, url: str) -> dict:
        """Full evaluation pipeline for a GitHub URL."""
        license_info = self.check_license(url)
        result: dict = {
            "url": url,
            "slug": None,
            "name": None,
            "description": None,
            "stars": None,
            "last_commit": None,
            "open_issues": None,
            "license": license_info,
            "deployment": None,
            "overlap": [],
            "ui": None,
            "recommendation": None,
        }

        parsed = _parse_github_slug(url)
        if parsed:
            owner, repo = parsed
            result["slug"] = f"{owner}/{repo}"
            result["name"] = repo

        # Short-circuit on BLOCKED license
        if license_info["verdict"] == "BLOCKED":
            result["recommendation"] = self.generate_recommendation(result)
            return result

        result["deployment"] = self.check_deployment_weight(url)
        result["overlap"] = self.detect_feature_overlap(url)
        result["ui"] = self.check_ui_components(url)
        result["recommendation"] = self.generate_recommendation(result)
        return result

    def check_license(self, repo_url: str) -> dict:
        """Auto-check license via gh CLI or README heuristics.

        Returns dict with license, verdict, reason, can_copy_code, can_copy_patterns.
        """
        parsed = _parse_github_slug(repo_url)
        license_name = "Unknown"
        source = "fallback"

        if parsed:
            owner, repo = parsed
            slug = f"{owner}/{repo}"
            raw = _run_gh(["repo", "view", slug, "--json", "licenseInfo"])
            if raw:
                try:
                    data = json.loads(raw)
                    spdx = (data.get("licenseInfo") or {}).get("spdxId") or ""
                    name_field = (data.get("licenseInfo") or {}).get("name") or ""
                    license_name = _normalize_license(spdx or name_field)
                    source = "gh-api"
                except (json.JSONDecodeError, AttributeError):
                    pass

        verdict, reason, can_copy_code, can_copy_patterns = _classify_license(license_name)
        return {
            "license": license_name,
            "verdict": verdict,
            "reason": reason,
            "can_copy_code": can_copy_code,
            "can_copy_patterns": can_copy_patterns,
            "source": source,
        }

    def check_deployment_weight(self, repo_url: str) -> dict:
        """Classify deployment requirements from repo file tree."""
        parsed = _parse_github_slug(repo_url)
        files: list[str] = []
        if parsed:
            owner, repo = parsed
            raw = _run_gh(["api", f"repos/{owner}/{repo}/git/trees/HEAD",
                           "--field", "recursive=1"])
            if raw:
                try:
                    data = json.loads(raw)
                    files = [t["path"] for t in data.get("tree", []) if t.get("type") == "blob"]
                except (json.JSONDecodeError, KeyError):
                    pass

        return _classify_deployment(files)

    def detect_feature_overlap(self, repo_url: str) -> list[dict]:
        """Compare repo features against our lib/ directory."""
        our_libs = _list_our_libs(self._lib_dir)
        parsed = _parse_github_slug(repo_url)
        their_features: list[str] = []

        if parsed:
            owner, repo = parsed
            raw = _run_gh(["api", f"repos/{owner}/{repo}/git/trees/HEAD"])
            if raw:
                try:
                    data = json.loads(raw)
                    their_features = [
                        Path(t["path"]).stem
                        for t in data.get("tree", [])
                        if t.get("type") == "blob" and t["path"].endswith(".py")
                    ]
                except (json.JSONDecodeError, KeyError):
                    pass

        return _compute_overlap(their_features, our_libs)

    def check_ui_components(self, repo_url: str) -> dict:
        """Detect UI components by inspecting repo file tree."""
        parsed = _parse_github_slug(repo_url)
        files: list[str] = []
        if parsed:
            owner, repo = parsed
            raw = _run_gh(["api", f"repos/{owner}/{repo}/git/trees/HEAD",
                           "--field", "recursive=1"])
            if raw:
                try:
                    data = json.loads(raw)
                    files = [t["path"] for t in data.get("tree", []) if t.get("type") == "blob"]
                except (json.JSONDecodeError, KeyError):
                    pass

        return _classify_ui(files)

    def generate_recommendation(self, evaluation: dict) -> dict:
        """Generate final ADOPT/ADAPT/WATCH/SKIP recommendation."""
        license_info = evaluation.get("license") or {}
        deployment = evaluation.get("deployment") or {}
        overlap = evaluation.get("overlap") or []

        verdict = "SKIP"
        confidence = 0.5
        actions: list[str] = []
        risks: list[str] = []
        effort = "unknown"

        if license_info.get("verdict") == "BLOCKED":
            verdict = "SKIP"
            confidence = 1.0
            actions.append("License is BLOCKED — do not use code. Patterns may be studied only.")
            risks.append(f"License: {license_info.get('license')} — {license_info.get('reason')}")
            effort = "none"
        else:
            pip_score = deployment.get("pip_first_score", 0.5)
            weight = deployment.get("weight", "unknown")
            exact_overlaps = [o for o in overlap if o.get("overlap_level") == "exact"]
            partial_overlaps = [o for o in overlap if o.get("overlap_level") == "partial"]

            if pip_score >= 0.8 and not exact_overlaps:
                verdict = "ADOPT"
                confidence = 0.85
                effort = "trivial"
                cmd = deployment.get("install_command") or "install"
                actions.append(f"Install directly: {cmd}")
                if license_info.get("can_copy_code"):
                    actions.append("Code can be used/copied freely")
            elif exact_overlaps:
                verdict = "ADAPT"
                confidence = 0.75
                effort = "moderate"
                actions.append("Compare their implementation with ours; adopt superior patterns")
                for eo in exact_overlaps:
                    actions.append(f"Compare: {eo['their_feature']} ↔ {eo['our_equivalent']}")
            elif weight in ("docker-heavy",):
                verdict = "WATCH"
                confidence = 0.70
                effort = "significant"
                actions.append("Monitor for lighter deployment option (pip/binary)")
                risks.append("Heavy Docker dependency — resource overhead")
            elif partial_overlaps:
                verdict = "ADAPT"
                confidence = 0.65
                effort = "moderate"
                actions.append("Extract novel features; skip duplicated ones")
            else:
                verdict = "ADOPT"
                confidence = 0.60
                effort = "moderate"
                actions.append("Evaluate further before integration")

            if license_info.get("verdict") == "CAUTION":
                risks.append(f"License {license_info.get('license')} — use with care")

        return {
            "verdict": verdict,
            "confidence": confidence,
            "actions": actions,
            "risks": risks,
            "estimated_effort": effort,
            "pip_first": deployment.get("pip_first_score", 0.0) >= 0.6,
        }

    def format_evaluation_report(self, evaluation: dict) -> str:
        """Return a human-readable evaluation report."""
        name = evaluation.get("name") or evaluation.get("url", "unknown")
        url = evaluation.get("url", "")
        lic = evaluation.get("license") or {}
        dep = evaluation.get("deployment") or {}
        ui = evaluation.get("ui") or {}
        rec = evaluation.get("recommendation") or {}
        overlap = evaluation.get("overlap") or []

        lines: list[str] = [
            f"=== TOOL EVALUATION: {name} ===",
            f"URL: {url}",
            f"License: {lic.get('license', 'Unknown')} ({lic.get('verdict', '?')})"
            + (f" — {lic.get('reason', '')}" if lic.get("reason") else ""),
            f"Deployment: {dep.get('weight', 'unknown')}"
            + (f" — {dep.get('install_command')}" if dep.get("install_command") else ""),
            f"pip-first score: {dep.get('pip_first_score', 0.0):.1f}/1.0",
            "",
        ]

        if overlap:
            lines.append("FEATURE OVERLAP:")
            for o in overlap:
                level = o.get("overlap_level", "none")
                icon = {"exact": "❌", "partial": "⚠️", "none": "✅"}.get(level, "  ")
                their = o.get("their_feature", "?")
                ours = o.get("our_equivalent")
                line = f"  {icon} {level.capitalize()}: {their}"
                if ours:
                    line += f" ↔ our {ours}"
                lines.append(line)
            lines.append("")

        lines.append("UI COMPONENTS:")
        if ui.get("has_ui"):
            lines.append(f"  Type: {ui.get('ui_type')} ({ui.get('ui_tech')})")
            lines.append(f"  Configurable: {ui.get('configurable')}")
            lines.append(f"  Integration effort: {ui.get('integration_effort')}")
        else:
            lines.append("  No UI components detected")
        lines.append("")

        lines.append(f"RECOMMENDATION: {rec.get('verdict', '?')} (confidence {rec.get('confidence', 0):.0%})")
        for action in rec.get("actions") or []:
            lines.append(f"  → {action}")
        for risk in rec.get("risks") or []:
            lines.append(f"  ⚠ Risk: {risk}")
        lines.append(f"  Effort: {rec.get('estimated_effort', 'unknown')}")
        lines.append(f"  pip-first install: {'yes' if rec.get('pip_first') else 'no'}")
        lines.append("===")
        return "\n".join(lines)

    def batch_evaluate(self, urls: list[str]) -> list[dict]:
        """Evaluate multiple URLs and rank by adoption value."""
        results = [self.evaluate_url(u) for u in urls]
        order = {"ADOPT": 0, "ADAPT": 1, "WATCH": 2, "SKIP": 3}
        results.sort(key=lambda r: (
            order.get((r.get("recommendation") or {}).get("verdict", "SKIP"), 9),
            -(r.get("recommendation") or {}).get("confidence", 0),
        ))
        return results


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _run_gh(args: list[str]) -> str | None:
    """Run a gh CLI command; return stdout or None on any failure."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _classify_license(name: str) -> tuple[str, str, bool, bool]:
    """Return (verdict, reason, can_copy_code, can_copy_patterns)."""
    if name in _LICENSE_APPROVED:
        return "APPROVED", "Permissive license — use freely", True, True
    if name in _LICENSE_CAUTION:
        return "CAUTION", "Copyleft — dynamic linking OK, review if bundling", False, True
    if name in _LICENSE_BLOCKED:
        return "BLOCKED", "Network/server copyleft — cannot use in SaaS", False, True
    if name == "Unknown":
        return "BLOCKED", "Unknown license — verify before use", False, False
    return "CAUTION", "Unrecognised license — manual review required", False, True


def _classify_deployment(files: list[str]) -> dict:
    """Infer deployment weight from file paths."""
    has_pyproject = any(f in ("pyproject.toml", "setup.py", "setup.cfg") for f in files)
    has_cargo = "Cargo.toml" in files
    has_go_mod = "go.mod" in files
    has_package_json = "package.json" in files
    has_dockerfile = any(f.lower().startswith("dockerfile") for f in files)
    compose_files = [f for f in files if "docker-compose" in f.lower() or "compose.yml" in f.lower() or "compose.yaml" in f.lower()]

    # Count docker-compose services heuristically (one compose file = ~3 services on avg)
    containers = len(compose_files) * 3

    if has_pyproject:
        return {
            "weight": "pip-install",
            "install_command": "pip install <package>",
            "containers_needed": 0,
            "estimated_ram_mb": 50,
            "pip_first_score": 1.0,
        }
    if has_cargo:
        return {
            "weight": "single-binary",
            "install_command": "cargo install <crate>",
            "containers_needed": 0,
            "estimated_ram_mb": 30,
            "pip_first_score": 0.8,
        }
    if has_go_mod:
        return {
            "weight": "single-binary",
            "install_command": "go install <module>@latest",
            "containers_needed": 0,
            "estimated_ram_mb": 30,
            "pip_first_score": 0.8,
        }
    if has_package_json and not has_dockerfile:
        return {
            "weight": "pip-install",
            "install_command": "npm install <package>",
            "containers_needed": 0,
            "estimated_ram_mb": 80,
            "pip_first_score": 0.9,
        }
    if compose_files and containers >= 5:
        return {
            "weight": "docker-heavy",
            "install_command": "docker compose up -d",
            "containers_needed": containers,
            "estimated_ram_mb": containers * 300,
            "pip_first_score": 0.0,
        }
    if has_dockerfile or compose_files:
        return {
            "weight": "docker-light",
            "install_command": "docker compose up -d",
            "containers_needed": max(1, containers),
            "estimated_ram_mb": max(1, containers) * 200,
            "pip_first_score": 0.2,
        }
    return {
        "weight": "unknown",
        "install_command": None,
        "containers_needed": 0,
        "estimated_ram_mb": 0,
        "pip_first_score": 0.5,
    }


def _list_our_libs(lib_dir: Path) -> dict[str, str]:
    """Return {stem: filename} for all .py files in lib/."""
    if not lib_dir.exists():
        return {}
    return {p.stem: p.name for p in lib_dir.glob("*.py") if p.stem != "__init__"}


def _compute_overlap(their_features: list[str], our_libs: dict[str, str]) -> list[dict]:
    """Compare feature stems; classify overlap level."""
    seen: set[str] = set()
    results: list[dict] = []
    for feat in their_features:
        if feat in seen or feat.startswith("_"):
            continue
        seen.add(feat)
        if feat in our_libs:
            level = "exact"
            ours = our_libs[feat]
            rec = "keep_ours"
        else:
            # Check partial: substring match either direction
            partial_match = next(
                (k for k in our_libs if feat in k or k in feat), None
            )
            if partial_match:
                level = "partial"
                ours = our_libs[partial_match]
                rec = "investigate"
            else:
                level = "none"
                ours = None
                rec = "adopt_theirs"

        results.append({
            "their_feature": feat,
            "our_equivalent": ours,
            "overlap_level": level,
            "recommendation": rec,
        })
    return results


def _classify_ui(files: list[str]) -> dict:
    """Detect UI type and tech from file list."""
    react = any(f.endswith((".jsx", ".tsx")) or "react" in f.lower() for f in files)
    vue = any(f.endswith(".vue") for f in files)
    html = any(f.endswith((".html", ".jinja", ".j2")) for f in files)
    tui = any("blessed" in f or "textual" in f or "urwid" in f or "curses" in f for f in files)
    cli_dash = any("rich" in f or "click" in f or "dashboard" in f.lower() for f in files)

    if react:
        return {"has_ui": True, "ui_type": "web", "ui_tech": "React",
                "configurable": True, "integration_effort": "moderate"}
    if vue:
        return {"has_ui": True, "ui_type": "web", "ui_tech": "Vue",
                "configurable": True, "integration_effort": "moderate"}
    if html:
        return {"has_ui": True, "ui_type": "web", "ui_tech": "HTML/Jinja",
                "configurable": True, "integration_effort": "trivial"}
    if tui:
        return {"has_ui": True, "ui_type": "tui", "ui_tech": "TUI",
                "configurable": True, "integration_effort": "moderate"}
    if cli_dash:
        return {"has_ui": True, "ui_type": "cli-dashboard", "ui_tech": "Rich/Click",
                "configurable": True, "integration_effort": "trivial"}
    return {"has_ui": False, "ui_type": None, "ui_tech": None,
            "configurable": False, "integration_effort": "none"}
