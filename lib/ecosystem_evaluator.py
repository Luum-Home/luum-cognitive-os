# SCOPE: os-only
"""Ecosystem Evaluator — monitors plugins and evaluated tools for adoption opportunities.

Tracks:
- Plugin submodules (.claude/plugins/*) for new commits with adoption interest
- Tools in ecosystem-tools.md with status EVALUATE/WATCH for staleness
- Reinvention risk by comparing plugin file names to our lib/ files
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone


class EcosystemEvaluator:
    """Monitors plugins and evaluated tools for adoption opportunities."""

    INTEREST_KEYWORDS = re.compile(
        r"\b(feat|feature|new|add|implement|breaking|refactor|improve)\b", re.IGNORECASE
    )
    STALE_DAYS = 30
    STALE_SECONDS = STALE_DAYS * 86400

    def __init__(self, project_root: str = ".") -> None:
        self.root = Path(project_root).resolve()
        self.plugins_dir = self.root / ".claude" / "plugins"
        self.ecosystem_md = (
            self.root
            / "packages"
            / "ecosystem-tools"
            / "rules"
            / "ecosystem-tools.md"
        )
        self.metrics_dir = self.root / ".cognitive-os" / "metrics"
        self.timestamp_file = self.metrics_dir / "ecosystem-eval-last-run"

    # ------------------------------------------------------------------
    # Plugin checks
    # ------------------------------------------------------------------

    def check_plugin_updates(self) -> list[dict]:
        """Check each plugin submodule for new commits since last check."""
        if not self.plugins_dir.exists():
            return []

        results = []
        for plugin_path in sorted(self.plugins_dir.iterdir()):
            if not plugin_path.is_dir():
                continue
            if not (plugin_path / ".git").exists() and not (plugin_path / "HEAD").exists():
                # Not a git repo — skip
                continue
            info = self._check_single_plugin(plugin_path)
            results.append(info)
        return results

    def _check_single_plugin(self, plugin_path: Path) -> dict:
        name = plugin_path.name
        highlights: list[str] = []
        new_commits = 0
        adoption_candidates: list[str] = []

        try:
            # Fetch silently; ignore errors (offline, no remote, etc.)
            subprocess.run(
                ["git", "-C", str(plugin_path), "fetch", "--quiet"],
                timeout=10,
                capture_output=True,
            )

            # Try common default branch names
            for branch in ("origin/main", "origin/master"):
                result = subprocess.run(
                    ["git", "-C", str(plugin_path), "log", "--oneline", f"HEAD..{branch}"],
                    timeout=5,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
                    new_commits = len(lines)
                    for line in lines:
                        if self.INTEREST_KEYWORDS.search(line):
                            highlights.append(line)
                            # Extract the message part (after hash)
                            parts = line.split(" ", 1)
                            if len(parts) > 1:
                                adoption_candidates.append(parts[1])
                    break
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        return {
            "plugin": name,
            "path": str(plugin_path),
            "new_commits": new_commits,
            "highlights": highlights[:10],  # cap
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "adoption_candidates": adoption_candidates[:5],
        }

    # ------------------------------------------------------------------
    # Evaluated tools check
    # ------------------------------------------------------------------

    def check_evaluated_tools(self) -> list[dict]:
        """Read ecosystem-tools.md for EVALUATE/WATCH status tools."""
        if not self.ecosystem_md.exists():
            return []

        content = self.ecosystem_md.read_text(encoding="utf-8", errors="replace")
        return self._parse_tool_statuses(content)

    def _parse_tool_statuses(self, content: str) -> list[dict]:
        # Match lines like: | **Status** | **EVALUATE** — note… |
        # or: Status | **EVALUATE** or Status: EVALUATE
        status_pattern = re.compile(
            r"^\|\s*Status\s*\|\s*\*\*([A-Z]+)\*\*",
            re.MULTILINE,
        )
        # Also match inline status lines like: | Status | **ADOPT** |
        inline_pattern = re.compile(
            r"\*\*Status\*\*\s*[—–-]\s*\*\*([A-Z]+)\*\*"
        )

        # Extract tool blocks: a ### header followed by a table
        tool_block_pattern = re.compile(
            r"###\s+(.+?)\n(.*?)(?=###|\Z)", re.DOTALL
        )

        tools = []
        now_ts = time.time()

        for match in tool_block_pattern.finditer(content):
            tool_name = match.group(1).strip()
            block = match.group(2)

            # Find status in this block
            status = None
            for pat in (status_pattern, inline_pattern):
                m = pat.search(block)
                if m:
                    status = m.group(1).upper()
                    break

            if status not in ("EVALUATE", "WATCH"):
                continue

            # Try to find GitHub URL
            github_url = None
            url_match = re.search(r"https://github\.com/[\w./-]+", block)
            if url_match:
                github_url = url_match.group(0).rstrip(")")

            # We don't store last_evaluated dates in the file, so use timestamp file
            # heuristic: if the file itself was modified recently, treat as fresh
            last_evaluated = None
            days_since = 999
            try:
                mtime = self.ecosystem_md.stat().st_mtime
                days_since = int((now_ts - mtime) / 86400)
                last_evaluated = datetime.fromtimestamp(mtime, tz=timezone.utc).date().isoformat()
            except OSError:
                pass

            is_stale = days_since > self.STALE_DAYS

            if is_stale:
                recommendation = "re-evaluate"
            elif status == "EVALUATE":
                recommendation = "actively evaluating"
            else:
                recommendation = "still watching"

            tools.append(
                {
                    "name": tool_name,
                    "status": status,
                    "github_url": github_url,
                    "last_evaluated": last_evaluated,
                    "days_since_eval": days_since,
                    "is_stale": is_stale,
                    "recommendation": recommendation,
                }
            )

        return tools

    # ------------------------------------------------------------------
    # Reinvention risk
    # ------------------------------------------------------------------

    def check_reinvention_risk(self) -> list[dict]:
        """Cross-reference our libs with plugin files to detect reinvention."""
        if not self.plugins_dir.exists():
            return []

        our_libs = self._collect_lib_stems()
        risks: list[dict] = []

        for plugin_path in sorted(self.plugins_dir.iterdir()):
            if not plugin_path.is_dir():
                continue
            for plugin_file in plugin_path.rglob("*.py"):
                stem = plugin_file.stem.lower()
                for our_lib in our_libs:
                    similarity = self._compute_similarity(our_lib, stem)
                    if similarity:
                        risks.append(
                            {
                                "our_lib": f"lib/{our_lib}.py",
                                "plugin_file": str(plugin_file.relative_to(self.root)),
                                "plugin": plugin_path.name,
                                "similarity": similarity,
                            }
                        )
        return risks

    def _collect_lib_stems(self) -> list[str]:
        lib_dir = self.root / "lib"
        if not lib_dir.exists():
            return []
        return [
            p.stem.lower()
            for p in lib_dir.glob("*.py")
            if not p.stem.startswith("_")
        ]

    def _compute_similarity(self, our: str, theirs: str) -> str | None:
        if our == theirs:
            return "name_match"
        # Check word overlap (split by underscore)
        our_words = set(our.split("_"))
        their_words = set(theirs.split("_"))
        shared = our_words & their_words
        if len(shared) >= 2 and len(shared) >= min(len(our_words), len(their_words)) * 0.6:
            return "purpose_overlap"
        return None

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def generate_evaluation_report(self) -> dict:
        """Full report combining all checks."""
        return {
            "plugins": self.check_plugin_updates(),
            "tools": self.check_evaluated_tools(),
            "reinvention": self.check_reinvention_risk(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def format_report(self, report: dict) -> str:
        lines = ["=== ECOSYSTEM EVALUATION ===", ""]

        # Plugins
        plugins = report.get("plugins", [])
        lines.append("PLUGINS:")
        if not plugins:
            lines.append("  (no plugin submodules found)")
        else:
            for p in plugins:
                count = p["new_commits"]
                label = f"{count} new commits" if count else "up to date"
                lines.append(f"  {p['plugin']}: {label}")
                for h in p["highlights"][:3]:
                    lines.append(f"    NEW {h}")
        lines.append("")

        # Stale tools
        tools = report.get("tools", [])
        stale = [t for t in tools if t.get("is_stale")]
        fresh = [t for t in tools if not t.get("is_stale")]
        lines.append("EVALUATED TOOLS:")
        if not tools:
            lines.append("  (ecosystem-tools.md not found or no EVALUATE/WATCH entries)")
        else:
            if stale:
                lines.append("  STALE (>30 days):")
                for t in stale:
                    lines.append(
                        f"    STALE {t['name']} — {t['days_since_eval']} days ({t['status']})"
                    )
            if fresh:
                lines.append("  Fresh:")
                for t in fresh:
                    lines.append(
                        f"    OK {t['name']} — {t['days_since_eval']} days ({t['status']}, {t['recommendation']})"
                    )
        lines.append("")

        # Reinvention risk
        reinvention = report.get("reinvention", [])
        lines.append("REINVENTION RISK:")
        if not reinvention:
            lines.append("  (none detected)")
        else:
            for r in reinvention[:10]:
                lines.append(
                    f"  WARN {r['our_lib']} <-> {r['plugin_file']} [{r['similarity']}]"
                )
        lines.append("")
        lines.append("===")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Timestamp persistence
    # ------------------------------------------------------------------

    def save_check_timestamp(self) -> None:
        """Save last check timestamp to metrics file."""
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp_file.write_text(str(int(time.time())))
