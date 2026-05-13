# SCOPE: os-only
# scope: both
"""Skill Router — Auto-select skills from conversation context.

Matches user messages to the most appropriate Cognitive OS skill using
pattern-based intent detection. Supports English and Spanish.

The router reads CATALOG.md to know which skills exist and uses a routing
table of (pattern, skill, confidence) tuples to score matches.

Usage:
    from lib.skill_router import SkillRouter

    router = SkillRouter()
    match = router.best_match("investigá este repo")
    if match:
        print(match.invoke_command)  # "/repo-forensics"
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class SkillMatch:
    """A matched skill with confidence and reasoning."""

    skill_name: str
    confidence: float  # 0.0 to 1.0
    reason: str  # why this skill matched
    invoke_command: str  # e.g., "/repo-forensics"

    def __str__(self) -> str:
        return f"{self.invoke_command} (confidence={self.confidence:.2f}): {self.reason}"


@dataclass(frozen=True)
class RoutingIntent:
    """Language-agnostic natural-language routing intent."""

    intent: str
    description: str
    confidence: float = 0.80


@dataclass
class _RoutingEntry:
    """Internal routing table entry."""

    patterns: List[Tuple[re.Pattern, float]]  # (compiled regex, base confidence)
    skill_name: str
    invoke_command: str
    fallback_command: Optional[str]
    reason_template: str
    intents: List[RoutingIntent] = field(default_factory=list)


def _compile(patterns: List[Tuple[str, float]]) -> List[Tuple[re.Pattern, float]]:
    """Compile regex patterns with IGNORECASE."""
    return [(re.compile(p, re.IGNORECASE), w) for p, w in patterns]


_AUTO_ROLLBACK_META_CONTEXT_RE = re.compile(
    r"("
    r"(router|skill\s*router|agente|agent|suggest|sugiri[oó]|sugerencia|suggestion|hint)"
    r".{0,80}(/?auto[- ]?rollback)"
    r"|(/?auto[- ]?rollback).{0,80}"
    r"(router|skill\s*router|agente|agent|suggest|sugiri[oó]|sugerencia|suggestion|hint)"
    r"|("
    r"por\s+qu[eé]|why|qu[eé]\s+dispara|what\s+triggers|me\s+asusta|scary|preocupa|worr"
    r").{0,120}(/?auto[- ]?rollback)"
    r"|(ignoro|ignore|ignored|rechaz|reject).{0,80}(/?auto[- ]?rollback)"
    r")",
    re.IGNORECASE,
)


def _is_auto_rollback_meta_reference(text: str) -> bool:
    """Return True when auto-rollback is mentioned as critique/risk, not intent."""
    return bool(_AUTO_ROLLBACK_META_CONTEXT_RE.search(text))


_ROUTER_NEGATIVE_CONTEXT_RE = re.compile(
    r"("
    r"router|skill\s*router|suggest(?:ed|ion)?|sugiri[oó]|sugerencia|hint|"
    r"dogfood\s+evidence|evidence\s+#\d+|falso\s+positivo|false\s+positive|"
    r"mal\s+calibrad[oa]|miscalibrat\w*|badly\s+calibrated|"
    r"ignoro|ignored?|rechaz\w*|reject\w*|"
    r"por\s+qu[eé]|why|qu[eé]\s+dispara|what\s+triggers|"
    r"me\s+asusta|scary|me\s+preocupa|worr(?:y|ied|ies)"
    r")",
    re.IGNORECASE,
)


def _command_or_skill_mentioned(text: str, entry: "_RoutingEntry") -> bool:
    """Return True when *text* explicitly names the candidate route.

    This intentionally checks explicit command/skill mentions, not arbitrary
    routing patterns. The negative-context guard should reject "the router
    suggested /phoenix-trace-ui" but must not suppress normal prompts merely
    because they contain broad words like "research" or "debug".
    """
    names = {
        entry.skill_name,
        entry.invoke_command.lstrip("/"),
    }
    if entry.fallback_command:
        names.add(entry.fallback_command.lstrip("/"))
    for name in names:
        escaped = re.escape(name)
        if re.search(rf"(?<![\w/-])/?{escaped}(?![\w/-])", text, re.IGNORECASE):
            return True
    return False


def _is_router_negative_context(text: str, entry: "_RoutingEntry") -> bool:
    """Return True when a route is mentioned as critique/evidence, not intent."""
    return bool(_ROUTER_NEGATIVE_CONTEXT_RE.search(text)) and _command_or_skill_mentioned(text, entry)


# ---------------------------------------------------------------------------
# URL detectors (special-cased, not pure regex on the whole message)
# ---------------------------------------------------------------------------

_GITHUB_URL_RE = re.compile(
    r"https?://github\.com/[\w.\-]+/[\w.\-]+", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Frontmatter-derived routing loader (ADR-174)
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> Dict[str, Any]:
    """Extract YAML frontmatter between the first two '---' lines.

    Returns an empty dict if frontmatter is absent or unparseable.
    Avoids a hard dependency on PyYAML — uses a minimal inline parser
    sufficient for the simple key: value / list structures used in SKILL.md.
    Falls back to PyYAML if available for full correctness.
    """
    lines = text.splitlines()
    # Skip optional HTML comment (<!-- SCOPE: ... -->) before frontmatter
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---":
            start = i
            break
        if stripped.startswith("<!--") or stripped == "":
            continue
        # Non-comment, non-empty, non-dashes before first --- → no frontmatter
        return {}

    if start >= len(lines) or lines[start].strip() != "---":
        return {}

    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break

    if end is None:
        return {}

    yaml_block = "\n".join(lines[start + 1:end])
    try:
        import yaml  # type: ignore[import]
        return yaml.safe_load(yaml_block) or {}
    except Exception:
        pass

    # Minimal fallback parser: handles flat key: value and simple lists
    result: Dict[str, Any] = {}
    current_key: Optional[str] = None
    current_list: Optional[List[Any]] = None

    for line in yaml_block.splitlines():
        if not line or line.startswith("#"):
            continue
        # List item under current key
        if line.startswith("  - ") or line.startswith("- "):
            item_str = line.lstrip("- ").strip()
            if current_list is not None:
                # Sub-mapping item (e.g. routing_patterns entries)
                item: Dict[str, Any] = {}
                for part in item_str.split(","):
                    part = part.strip()
                    if ":" in part:
                        k, v = part.split(":", 1)
                        item[k.strip()] = v.strip().strip('"').strip("'")
                current_list.append(item)
            continue
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "" or value == "|" or value == ">":
                # Start of block scalar or list — skip for minimal parser
                current_key = key
                current_list = None
                result[key] = ""
            else:
                result[key] = value.strip('"').strip("'")
                current_key = key
                current_list = None
        elif line.startswith("  ") and current_key:
            # Continuation of block scalar
            existing = result.get(current_key, "")
            result[current_key] = (existing + " " + line.strip()).strip()

    return result


def _parse_routing_patterns_block(skill_md_path: Path) -> Optional[List[Tuple[str, float]]]:
    """Read a SKILL.md and extract routing_patterns if present.

    Returns a list of (pattern_str, confidence) or None if not defined.
    Never raises — returns None on any parse error.
    """
    try:
        text = skill_md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    # Fast path: skip files that don't even mention routing_patterns
    if "routing_patterns" not in text:
        return None

    # Use PyYAML for accurate parsing when available
    try:
        import yaml  # type: ignore[import]
        lines = text.splitlines()
        start = None
        for i, line in enumerate(lines):
            if line.strip() == "---":
                start = i
                break
            if line.strip().startswith("<!--") or line.strip() == "":
                continue
            break
        if start is None:
            return None
        end = None
        for i in range(start + 1, len(lines)):
            if lines[i].strip() == "---":
                end = i
                break
        if end is None:
            return None
        yaml_block = "\n".join(lines[start + 1:end])
        data = yaml.safe_load(yaml_block) or {}
        raw = data.get("routing_patterns")
        if not raw or not isinstance(raw, list):
            return None
        result = []
        for entry in raw:
            if isinstance(entry, dict):
                pat = entry.get("pattern", "")
                conf = float(entry.get("confidence", 0.80))
                if pat:
                    result.append((str(pat), conf))
        return result if result else None
    except Exception:
        pass

    # Minimal regex-based fallback for when PyYAML is unavailable
    import re as _re
    block_match = _re.search(
        r"routing_patterns:\s*\n((?:[ \t]+-.*\n?)+)", text
    )
    if not block_match:
        return None
    block = block_match.group(1)
    results = []
    for line in block.splitlines():
        line = line.strip().lstrip("- ").strip()
        pat_m = _re.search(r'pattern:\s*["\']?(.+?)["\']?\s*$', line)
        conf_m = _re.search(r'confidence:\s*([0-9.]+)', line)
        if pat_m:
            pat = pat_m.group(1).strip()
            conf = float(conf_m.group(1)) if conf_m else 0.80
            results.append((pat, conf))
    return results if results else None


def _parse_routing_intents_block(skill_md_path: Path) -> Optional[List[RoutingIntent]]:
    """Read a SKILL.md and extract routing_intents if present.

    ``routing_intents`` are semantic descriptions of user intent. They are not
    regexes and are intended to be evaluated by the semantic fallback layer.
    """
    try:
        text = skill_md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if "routing_intents" not in text:
        return None
    fm = _parse_frontmatter(text)
    raw = fm.get("routing_intents")
    if not raw or not isinstance(raw, list):
        return None
    result: List[RoutingIntent] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        intent = str(entry.get("intent") or "").strip()
        description = str(entry.get("description") or "").strip()
        if not intent or not description:
            continue
        try:
            confidence = float(entry.get("confidence", 0.80))
        except (TypeError, ValueError):
            confidence = 0.80
        result.append(RoutingIntent(intent=intent, description=description, confidence=confidence))
    return result if result else None


def _skill_md_to_routing_entry(skill_md: Path) -> Optional[_RoutingEntry]:
    """Convert a SKILL.md with routing metadata into a _RoutingEntry.

    Returns None if the file has neither routing_patterns nor routing_intents.
    """
    patterns_raw = _parse_routing_patterns_block(skill_md) or []
    intents = _parse_routing_intents_block(skill_md) or []
    if not patterns_raw and not intents:
        return None

    # Determine skill name: prefer frontmatter 'name', fallback to directory name
    skill_name = skill_md.parent.name
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        fm = _parse_frontmatter(text)
        if fm.get("name"):
            skill_name = str(fm["name"]).strip()
        invoke_cmd = fm.get("invoke", f"/{skill_name}")
    except Exception:
        invoke_cmd = f"/{skill_name}"

    try:
        compiled = _compile(patterns_raw)
    except re.error as exc:
        print(
            f"[skill_router] WARNING: bad routing pattern in {skill_md}: {exc}",
            file=sys.stderr,
        )
        return None

    return _RoutingEntry(
        patterns=compiled,
        skill_name=skill_name,
        invoke_command=str(invoke_cmd),
        fallback_command=None,
        reason_template=f"Auto-routed via {skill_name} frontmatter",
        intents=intents,
    )


def _load_routing_from_frontmatter(skills_root: Path) -> List[_RoutingEntry]:
    """Scan skill directories under *skills_root* and build routing entries.

    Searches:
      <skills_root>/*/SKILL.md
      <skills_root>/packages/*/skills/*/SKILL.md
      <skills_root>/.cognitive-os/skills/*/SKILL.md

    Skills with either ``routing_patterns:`` or ``routing_intents:`` frontmatter are included.
    Regex patterns remain compatibility aliases; routing_intents carry semantic intent.
    """
    entries: List[_RoutingEntry] = []
    seen: Set[str] = set()  # deduplicate by skill_name

    search_roots = [
        skills_root / "skills",
        skills_root / ".cognitive-os" / "skills",
    ]
    # Also search packages/*/skills/
    packages_dir = skills_root / "packages"
    if packages_dir.is_dir():
        for pkg in packages_dir.iterdir():
            pkg_skills = pkg / "skills"
            if pkg_skills.is_dir():
                search_roots.append(pkg_skills)

    for root in search_roots:
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            entry = _skill_md_to_routing_entry(skill_md)
            if entry and entry.skill_name not in seen:
                entries.append(entry)
                seen.add(entry.skill_name)

    return entries


def _detect_skill_md_paths(project_root: Path) -> Dict[str, Path]:
    """Return a mapping of skill_name -> SKILL.md path for all skills on disk."""
    result: Dict[str, Path] = {}
    search_roots = [
        project_root / "skills",
        project_root / ".cognitive-os" / "skills",
    ]
    packages_dir = project_root / "packages"
    if packages_dir.is_dir():
        for pkg in packages_dir.iterdir():
            pkg_skills = pkg / "skills"
            if pkg_skills.is_dir():
                search_roots.append(pkg_skills)

    for root in search_roots:
        if not root.is_dir():
            continue
        for skill_md in root.glob("*/SKILL.md"):
            name = skill_md.parent.name
            if name not in result:
                result[name] = skill_md
    return result


_PROFILE_ALIASES: Dict[str, str] = {
    "core": "lean",
    "default": "lean",
    "team": "standard",
    "default+team-extensions": "standard",
    "core+team": "standard",
    "full": "strict",
    "core+team+maintainer": "strict",
    "opt-in": "lab",
}


def _canonical_profile(profile: Optional[str]) -> Optional[str]:
    """Normalize installation/profile aliases used by COS manifests."""
    if not profile:
        return None
    normalized = profile.strip().lower()
    return _PROFILE_ALIASES.get(normalized, normalized)


def _load_profile_projected_skills(project_root: Path, profile: Optional[str]) -> Optional[Set[str]]:
    """Return the skill names projected for a routing profile, if declared.

    The profile manifest is intentionally separate from routing patterns: it
    answers "what should be visible in this install/runtime surface?" while
    SKILL.md frontmatter answers "how should this skill be detected?".
    """
    canonical = _canonical_profile(profile)
    if not canonical:
        return None
    manifest = project_root / "manifests" / "skill-routing-coverage.yaml"
    if not manifest.exists():
        return None
    try:
        import yaml  # type: ignore[import]
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    profile_data = (
        data.get("profile_routing", {})
        .get("profiles", {})
        .get(canonical, {})
    )
    projected = profile_data.get("projected_skills")
    if not isinstance(projected, list):
        return None
    return {str(item) for item in projected}


def _skill_md_checksum(project_root: Path) -> str:
    """Return a stable checksum for all first-party SKILL.md files."""
    digest = hashlib.sha256()
    for name, path in sorted(_detect_skill_md_paths(project_root).items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError:
            continue
        digest.update(b"\0")
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Routing table definition
# ---------------------------------------------------------------------------

def _build_default_routing_table(project_root: Optional[Path] = None) -> List[_RoutingEntry]:
    """Build the full routing table, merging frontmatter-derived and hand-coded entries.

    Strategy (ADR-174):
      1. Load frontmatter-derived entries from SKILL.md ``routing_patterns:`` blocks.
      2. Merge with hand-coded fallback entries (backward-compat for unmigrated skills).
      3. Frontmatter wins on conflict (same skill_name).
      4. Detect orphan hand-coded entries (no SKILL.md on disk) and warn to stderr.
    """
    # Locate project root relative to this file unless a service/project runtime supplies one.
    if project_root is None:
        _lib_dir = Path(__file__).resolve().parent
        _project_root = _lib_dir.parent
    else:
        _project_root = project_root.resolve()

    # Step 1: Load frontmatter-derived entries
    _fm_entries = _load_routing_from_frontmatter(_project_root)
    _fm_skill_names: Set[str] = {e.skill_name for e in _fm_entries}

    # Step 2: Load disk skill index for orphan detection
    _disk_skills = _detect_skill_md_paths(_project_root)

    # Step 3: Load hand-coded entries, warn on orphans, skip if frontmatter present
    _hand_coded = _build_hand_coded_routing_table()
    _merged: List[_RoutingEntry] = list(_fm_entries)
    for entry in _hand_coded:
        if entry.skill_name in _fm_skill_names:
            # Frontmatter entry takes precedence; skip hand-coded
            continue
        if entry.skill_name not in _disk_skills:
            # Orphan: hand-coded entry with no SKILL.md on disk
            # Known orphans as of ADR-174: "context-analysis", "traceability-check"
            # (plus any meta-commands like "sdd-new" that intentionally have no dir)
            _META_COMMANDS = {"sdd-new"}
            if entry.skill_name not in _META_COMMANDS:
                print(
                    f"[skill_router] WARNING: orphan routing entry '{entry.skill_name}' "
                    f"— no SKILL.md found on disk. See ADR-174 migration plan.",
                    file=sys.stderr,
                )
        _merged.append(entry)

    return _merged


def _build_hand_coded_routing_table() -> List[_RoutingEntry]:
    """Build the full routing table covering all major skills."""

    return [
        # --- Repository analysis ---
        _RoutingEntry(
            patterns=_compile([
                (r"https?://github\.com/[\w.\-]+/[\w.\-]+", 0.95),
                (r"\brepo[- ]?forensics\b", 0.95),
                (r"\b(analiz[áa]\w*|analy[sz]e)\s+(this|the|ese?|este?)?\s*repo", 0.90),
                (r"\binvestig[áa]\w*\s+(this|the|ese?|este?)?\s*repo", 0.90),
                (r"\bclone\s+and\s+(scan|analy)", 0.85),
            ]),
            skill_name="repo-forensics",
            invoke_command="/repo-forensics",
            fallback_command="/repo-scout",
            reason_template="Repository analysis detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\beval[- ]?repo\b", 0.95),
                (r"\brepo[- ]?scout\b", 0.95),
                (r"\b(evalua[rt]\w*|evaluate)\s+(this|the|ese?|este?)?\s*repo", 0.85),
                (r"\btech\s*radar\b", 0.80),
            ]),
            skill_name="repo-scout",
            invoke_command="/repo-scout",
            fallback_command=None,
            reason_template="Repository scouting/evaluation detected",
        ),

        # --- Bug fixing ---
        _RoutingEntry(
            patterns=_compile([
                (r"\b(fix|arregl[áa]\w*|repar[áa]\w*|corregir?)\s+.{0,30}\bbug\b", 0.90),
                (r"\b(fix|arregl[áa]\w*|repar[áa]\w*)\s+(the|el|la|this|ese?|este?)?\s*(error|fallo|falla|issue|problema|broken)", 0.88),
                (r"\bplan[- ]?bug\b", 0.95),
                (r"\bbug\s+(fix|report|found)\b", 0.85),
                (r"\b(hay|there'?s|found)\s+(un|a|an)?\s*(bug|error|fallo)\b", 0.80),
            ]),
            skill_name="plan-bug",
            invoke_command="/plan-bug",
            fallback_command="/systematic-debugging",
            reason_template="Bug fix workflow detected",
        ),

        # --- Debugging ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bdebug\w*\b", 0.85),
                (r"\b(no funciona|doesn'?t work|not working|broken)\b", 0.80),
                (r"\bsystematic[- ]?debug\b", 0.95),
                (r"\b(por qu[ée]|why)\s+(falla|fails|doesn'?t|no)\b", 0.80),
                (r"\b(root cause|causa ra[ií]z)\b", 0.85),
            ]),
            skill_name="systematic-debugging",
            invoke_command="/systematic-debugging",
            fallback_command=None,
            reason_template="Debugging workflow detected",
        ),

        # --- New feature / SDD ---
        _RoutingEntry(
            patterns=_compile([
                (r"\b(new feature|add feature|implement feature|nueva funcionalidad|agregar funcionalidad)\b", 0.88),
                (r"\b(necesito|I need to|quiero)\s+(agregar|add|implement|crear|create)\b", 0.85),
                (r"\bsdd[- ]?new\b", 0.95),
                (r"\b(design|dise[ñn][áa]\w*)\s+(a|an|un|una)?\s*(new|nuev[oa])\b", 0.80),
                (r"\b(build|construir?|arm[áa]\w*|armemos)\s+(a|an|un|una)?\s*(new|nuev[oa])?\s*(service|module|endpoint|api|feature|m[oó]dulo|servicio)", 0.85),
                (r"\b(build|construir?)\s+a\s+new\s+\w+\s+(service|module|endpoint)", 0.85),
            ]),
            skill_name="sdd-new",
            invoke_command="/sdd-new",
            fallback_command="/plan-feature",
            reason_template="New feature implementation detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bplan[- ]?feature\b", 0.95),
                (r"\b(plan|planifiq\w*|planear)\s+(the|la|el)?\s*(feature|funcionalidad|implementaci[oó]n)", 0.85),
            ]),
            skill_name="plan-feature",
            invoke_command="/plan-feature",
            fallback_command=None,
            reason_template="Feature planning detected",
        ),

        # --- Testing ---
        _RoutingEntry(
            patterns=_compile([
                (r"\b(run|corr[eé]\w*|ejecut[áa]\w*|lanz[áa]\w*)\s+(the|los|las|all)?\s*test", 0.95),
                (r"\brun[- ]?tests?\b", 0.95),
                (r"\b(test|tests)\s+(pass|fail|run|suite|result)", 0.80),
                (r"\bpytest\b", 0.80),
                (r"\b(go test|yarn test|npm test)\b", 0.85),
            ]),
            skill_name="run-tests",
            invoke_command="/run-tests",
            fallback_command=None,
            reason_template="Test execution detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\b(write|escrib[ií]\w*|agreg[áa]\w*|add)\s+(the|los|las)?\s*tests?\b", 0.85),
                (r"\btdd\b", 0.85),
                (r"\btest[- ]?driven\b", 0.90),
                (r"\bred[- ]?green[- ]?refactor\b", 0.95),
            ]),
            skill_name="test-driven-development",
            invoke_command="/test-driven-development",
            fallback_command=None,
            reason_template="Test-driven development detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bcoverage\b", 0.80),
                (r"\b(cobertura|coverage)\s+(report|reporte|check)\b", 0.90),
            ]),
            skill_name="coverage-enforcement",
            invoke_command="/coverage-report",
            fallback_command=None,
            reason_template="Coverage report detected",
        ),

        # --- Security ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bsecurity[- ]?audit\b", 0.95),
                (r"\b(audit[áa]\w*|revis[áa]\w*|revisar?)\s+(la\s+)?seguridad\b", 0.90),
                (r"\b(security|seguridad)\s+(scan|check|review|audit|revisi[oó]n)\b", 0.90),
                (r"\bseguridad\s+(del|de)\s+", 0.80),
                (r"\b(vulnerabilit|vulnerabilidad)\w*\b", 0.80),
            ]),
            skill_name="security-audit",
            invoke_command="/security-audit",
            fallback_command="/pentest-self",
            reason_template="Security audit detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bpentest\b", 0.90),
                (r"\bpenetration\s+test", 0.90),
                (r"\bself[- ]?pentest\b", 0.95),
            ]),
            skill_name="pentest-self",
            invoke_command="/pentest-self",
            fallback_command=None,
            reason_template="Penetration testing detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bred[- ]?team\b", 0.90),
                (r"\bprompt\s*injection\s*(test|scan)", 0.85),
                (r"\bjailbreak\s+test\b", 0.85),
            ]),
            skill_name="red-team",
            invoke_command="/red-team",
            fallback_command="/vulnerability-scan",
            reason_template="Red team testing detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bvulnerabilit\w+\s+(scan|test|check)\b", 0.85),
                (r"\bvulnerability[- ]?scan\b", 0.95),
                (r"\bgarak\b", 0.90),
            ]),
            skill_name="vulnerability-scan",
            invoke_command="/vulnerability-scan",
            fallback_command=None,
            reason_template="Vulnerability scanning detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bsemgrep\b", 0.95),
                (r"\bsast\s+(scan|check)\b", 0.85),
                (r"\bstatic\s+analysis\b", 0.80),
            ]),
            skill_name="semgrep-scan",
            invoke_command="/semgrep-scan",
            fallback_command=None,
            reason_template="SAST scanning detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bsecret[- ]?audit\b", 0.95),
                (r"\b(scan|check|revisar?)\s+(for\s+)?(secrets?|credentials?|claves?|credenciales?)\b", 0.85),
            ]),
            skill_name="secret-audit",
            invoke_command="/secret-audit",
            fallback_command=None,
            reason_template="Secret audit detected",
        ),

        # --- KPIs / Metrics / Performance ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bkpis?\b", 0.90),
                (r"\bagent[- ]?kpis?\b", 0.95),
                (r"\b(m[eé]tricas?|metrics?)\s+(de\s+)?(agent|agente)", 0.85),
                (r"\b(health|salud)\s+(dashboard|check|report)\b", 0.80),
                (r"\b(agent|agente)\s+(health|performance|rendimiento)\b", 0.85),
            ]),
            skill_name="agent-kpis",
            invoke_command="/agent-kpis",
            fallback_command="/model-optimizer",
            reason_template="Agent KPI reporting detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bmodel[- ]?optimi[sz]\w*\b", 0.95),
                (r"\b(optimi[sz]\w*|mejorar)\s+(the\s+)?model\s*routing\b", 0.85),
                (r"\bmodel\s+routing\b", 0.80),
            ]),
            skill_name="model-optimizer",
            invoke_command="/model-optimizer",
            fallback_command=None,
            reason_template="Model optimization detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\btrust[- ]?audit\b", 0.95),
                (r"\btrust\s+score\s+(audit|analysis|review)\b", 0.85),
            ]),
            skill_name="trust-audit",
            invoke_command="/trust-audit",
            fallback_command=None,
            reason_template="Trust audit detected",
        ),
        # --- Research ---
        _RoutingEntry(
            patterns=_compile([
                (r"\b(deep[- ]?research|investigaci[oó]n\s+profunda)\b", 0.95),
                (r"\b(research|investigar?|investig[áa]\w*)\b", 0.80),
                (r"\b(investig[áa]\w*|research)\s+(this|the|esto|este|ese?)\b", 0.85),
            ]),
            skill_name="deep-research",
            invoke_command="/deep-research",
            fallback_command="/tool-discovery",
            reason_template="Research task detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\btool[- ]?discovery\b", 0.95),
                (r"\b(find|discover|buscar?|encontr[áa]\w*)\s+(new\s+)?(tools?|herramientas?)\b", 0.85),
                (r"\bgithub\s+scan\b", 0.80),
            ]),
            skill_name="tool-discovery",
            invoke_command="/tool-discovery",
            fallback_command=None,
            reason_template="Tool discovery detected",
        ),

        # --- Skill management ---
        _RoutingEntry(
            patterns=_compile([
                (r"\b(create|crear?|generar?)\s+(a\s+|un\s+|una\s+)?skill\b", 0.95),
                (r"\bskill[- ]?creator\b", 0.95),
                (r"\b(new|nuev[oa])\s+skill\b", 0.90),
            ]),
            skill_name="skill-creator",
            invoke_command="/skill-creator",
            fallback_command=None,
            reason_template="Skill creation detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\b(optimize|optimizar?|mejorar)\s+(the\s+|la\s+|el\s+)?skill\b", 0.90),
                (r"\boptimize[- ]?skill\b", 0.95),
            ]),
            skill_name="optimize-skill",
            invoke_command="/optimize-skill",
            fallback_command=None,
            reason_template="Skill optimization detected",
        ),

        # --- Release ---
        _RoutingEntry(
            patterns=_compile([
                (r"\b(release|releas\w*|versi[oó]n|version)\b", 0.80),
                (r"\brelease[- ]?os\b", 0.95),
                (r"\b(tag|bump|publicar?)\s+(a\s+|un\s+|una\s+)?(new\s+|nuev[oa]\s+)?(release|version|versi[oó]n)\b", 0.90),
            ]),
            skill_name="release-os",
            invoke_command="/release-os",
            fallback_command=None,
            reason_template="Release workflow detected",
        ),

        # --- Scout / Exploration ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bscout\b", 0.90),
                (r"\b(explor[áa]\w*|explore)\s+(el\s+|the\s+)?(c[oó]digo|code|codebase)", 0.85),
                (r"\breconnaissance\b", 0.85),
                (r"\b(terrain|terreno)\s+(map|mapa)\b", 0.80),
            ]),
            skill_name="scout",
            invoke_command="/scout",
            fallback_command="/sdd-explore",
            reason_template="Codebase reconnaissance detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bsdd[- ]?explore\b", 0.95),
                (r"\bfeasibility\b", 0.75),
            ]),
            skill_name="sdd-explore",
            invoke_command="/sdd-explore",
            fallback_command=None,
            reason_template="SDD exploration detected",
        ),

        # --- Reverse engineering ---
        _RoutingEntry(
            patterns=_compile([
                (r"\breverse[- ]?engineer\b", 0.95),
                (r"\b(understand|comprehend|entender|comprender)\s+(the\s+|el\s+|la\s+)?(internal\s+)?((config|configuration)\s+schema|schema|structure|architecture|api|config|source|esquema|estructura|arquitectura|fuente)", 0.80),
                (r"\b(how\s+does|c[oó]mo\s+funciona)\s+.{0,30}\s+(work|funciona)\b", 0.75),
                (r"\b(internals?|source\s+code)\s+(of|del?|de\s+la)", 0.80),
                (r"\bdecipher\b", 0.80),
            ]),
            skill_name="reverse-engineer",
            invoke_command="/reverse-engineer",
            fallback_command="/repo-forensics",
            reason_template="Reverse engineering / internal schema understanding detected",
        ),

        # --- Documentation ---
        _RoutingEntry(
            patterns=_compile([
                (r"\b(document[áa]\w*|documentar?|docs?)\s+(the|la|el|this|ese?|este?)?\s*(feature|funcionalidad|endpoint|api|module|m[oó]dulo)", 0.85),
                (r"\bdocument[- ]?feature\b", 0.95),
                (r"\b(write|generar?|create)\s+(the|la|el)?\s*(docs?|documentation|documentaci[oó]n)\b", 0.85),
            ]),
            skill_name="document-feature",
            invoke_command="/document-feature",
            fallback_command="/doc-sync",
            reason_template="Documentation generation detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bdoc[- ]?sync\b", 0.95),
                (r"\bstale\s+docs?\b", 0.85),
                (r"\b(sync|actualizar?)\s+(the|la|el)?\s*(docs?|documentaci[oó]n)\b", 0.80),
            ]),
            skill_name="doc-sync",
            invoke_command="/doc-sync",
            fallback_command=None,
            reason_template="Documentation sync detected",
        ),

        # --- Code review ---
        _RoutingEntry(
            patterns=_compile([
                (r"\b(review|revis[áa]\w*|revisar)\s+(the|el|la|my|mi|this|ese?|este?)?\s*(code|c[oó]digo|changes?|cambios?|pr|pull\s*request)", 0.85),
                (r"\bself[- ]?review\b", 0.95),
                (r"\bcode\s+review\b", 0.85),
            ]),
            skill_name="self-review",
            invoke_command="/self-review",
            fallback_command="/sdd-verify",
            reason_template="Code review detected",
        ),

        # --- Stress test ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bstress[- ]?test\b", 0.95),
                (r"\bagent[- ]?stress\b", 0.90),
                (r"\b(degradaci[oó]n|degradation)\b", 0.80),
                (r"\bcognitive\s+load\s+test\b", 0.85),
            ]),
            skill_name="agent-stress-test",
            invoke_command="/agent-stress-test",
            fallback_command=None,
            reason_template="Agent stress testing detected",
        ),

        # --- Library recommendation ---
        _RoutingEntry(
            patterns=_compile([
                (r"\brecommend[- ]?librar\w*\b", 0.95),
                (r"\b(qu[eé]\s+librer[ií]a|which\s+library|what\s+library)\b", 0.90),
                (r"\b(suggest|recomendar?|suger\w*)\s+(a\s+|un\s+|una\s+)?(library|librer[ií]a|package|paquete)\b", 0.85),
            ]),
            skill_name="recommend-library",
            invoke_command="/recommend-library",
            fallback_command=None,
            reason_template="Library recommendation detected",
        ),

        # --- Estimation ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bplanning[- ]?poker\b", 0.95),
                (r"\b(estimate|estimar?|estimaci[oó]n)\s+(the\s+|la\s+)?(cost|task|effort|costo|tarea|esfuerzo)", 0.85),
                (r"\b(cu[áa]nto\s+(va\s+a\s+)?cost|how\s+much\s+will\s+(this|it)\s+cost)\b", 0.85),
            ]),
            skill_name="planning-poker",
            invoke_command="/planning-poker",
            fallback_command="/cost-predict",
            reason_template="Estimation / planning poker detected",
        ),
        # --- Status ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bcognitive[- ]?os[- ]?status\b", 0.95),
                (r"\b(cos|cognitive\s+os)\s+status\b", 0.90),
                (r"\b(c[oó]mo\s+viene|how'?s?\s+(the\s+)?(system|os|cognitive))\b", 0.75),
                (r"\b(health\s+check|estado\s+del\s+sistema)\b", 0.80),
            ]),
            skill_name="cognitive-os-status",
            invoke_command="/cognitive-os-status",
            fallback_command=None,
            reason_template="System status check detected",
        ),

        # --- Sprint ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bsprint\b", 0.80),
                (r"\bsprint\s+(plan|status|retro|review)\b", 0.90),
            ]),
            skill_name="sprint",
            invoke_command="/sprint",
            fallback_command=None,
            reason_template="Sprint management detected",
        ),

        # --- SRE / Infrastructure ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bsre[- ]?agent\b", 0.95),
                (r"\b(monitor|monitorear?)\s+(the\s+|los\s+)?(services?|servicios?|containers?|contenedores?)\b", 0.80),
                (r"\b(docker|container|contenedor)\s+(is\s+)?(down|ca[ií]do|failing|fallando)\b", 0.85),
                (r"\binfrastructure\s+(issue|problem|error)\b", 0.80),
            ]),
            skill_name="sre-agent",
            invoke_command="/sre-agent",
            fallback_command=None,
            reason_template="SRE / infrastructure monitoring detected",
        ),

        # --- Error analysis ---
        _RoutingEntry(
            patterns=_compile([
                (r"\berror[- ]?analy[sz]\w*\b", 0.95),
                (r"\b(analy[sz]e|analizar?)\s+(the\s+|los\s+)?(errors?|errores?|failures?|fallos?)\b", 0.85),
                (r"\berror\s+patterns?\b", 0.80),
            ]),
            skill_name="error-analyzer",
            invoke_command="/error-analyzer",
            fallback_command=None,
            reason_template="Error analysis detected",
        ),

        # --- Impact analysis ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bimpact[- ]?analysis\b", 0.95),
                (r"\bblast\s+radius\b", 0.85),
                (r"\b(what\s+will\s+break|qu[eé]\s+se\s+rompe)\b", 0.80),
            ]),
            skill_name="impact-analysis",
            invoke_command="/impact-analysis",
            fallback_command=None,
            reason_template="Impact analysis detected",
        ),

        # --- Issue pipeline ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bissue[- ]?to[- ]?pr\b", 0.95),
                (r"\b(issue|github\s+issue)\s+#?\d+", 0.80),
                (r"\b(take|grab|work\s+on|resolver)\s+(the\s+|el\s+)?(issue|ticket)\b", 0.80),
            ]),
            skill_name="issue-pipeline",
            invoke_command="/issue-to-pr",
            fallback_command=None,
            reason_template="Issue-to-PR pipeline detected",
        ),

        # --- Contract drift ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bcontract[- ]?drift\b", 0.95),
                (r"\b(openapi|swagger)\s+(drift|mismatch|check)\b", 0.85),
                (r"\bapi\s+contract\b", 0.75),
            ]),
            skill_name="contract-drift",
            invoke_command="/contract-drift",
            fallback_command=None,
            reason_template="API contract drift detection",
        ),

        # --- Resource governor ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bresource[- ]?governor\b", 0.95),
                (r"\bbudget\s+(check|status|report|review)\b", 0.80),
                (r"\b(cu[áa]nto\s+(gast[eé]|spent)|how\s+much\s+(did\s+we\s+)?spend)\b", 0.80),
            ]),
            skill_name="resource-governor",
            invoke_command="/resource-governor",
            fallback_command=None,
            reason_template="Resource governance detected",
        ),

        # --- Self-improve ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bself[- ]?improv\w*\b", 0.95),
                (r"\b(improve|mejorar)\s+(the\s+|el\s+)?(system|sistema|cognitive\s*os|cos)\b", 0.80),
            ]),
            skill_name="self-improve",
            invoke_command="/self-improve",
            fallback_command=None,
            reason_template="Self-improvement protocol detected",
        ),

        # --- Retrospective ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bretrospective\b", 0.90),
                (r"\bretro\b", 0.75),
                (r"\bsquad[- ]?report\b", 0.90),
            ]),
            skill_name="retrospective",
            invoke_command="/retrospective",
            fallback_command="/squad-report",
            reason_template="Retrospective / squad review detected",
        ),

        # --- Singularity ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bsingularity\b", 0.95),
                (r"\bautonomous\s+(loop|control|monitor)\b", 0.80),
                (r"\bmape[- ]?k\b", 0.85),
            ]),
            skill_name="singularity",
            invoke_command="/singularity",
            fallback_command=None,
            reason_template="Singularity autonomous loop detected",
        ),

        # --- Readiness check ---
        _RoutingEntry(
            patterns=_compile([
                (r"\breadiness[- ]?check\b", 0.95),
                (r"\b(ready|listo)\s+(to|para)\s+(implement|code|aplicar|apply)\b", 0.80),
            ]),
            skill_name="readiness-check",
            invoke_command="/readiness-check",
            fallback_command=None,
            reason_template="Implementation readiness check detected",
        ),

        # --- DoD check ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bdod[- ]?check\b", 0.95),
                (r"\bdefinition\s+of\s+done\b", 0.85),
            ]),
            skill_name="dod-check",
            invoke_command="/dod-check",
            fallback_command=None,
            reason_template="Definition of Done check detected",
        ),

        # --- Confidence check ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bconfidence[- ]?check\b", 0.95),
                (r"\b(readiness|confianza)\s+assessment\b", 0.80),
            ]),
            skill_name="confidence-check",
            invoke_command="/confidence-check",
            fallback_command=None,
            reason_template="Confidence assessment detected",
        ),

        # --- Web crawler ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bweb[- ]?crawl\w*\b", 0.95),
                (r"\b(fetch|crawl|scrape)\s+(the\s+|la\s+)?(web\s*page|p[áa]gina|url|site|sitio)\b", 0.80),
            ]),
            skill_name="web-crawler",
            invoke_command="/web-crawler",
            fallback_command=None,
            reason_template="Web crawling detected",
        ),

        # --- Audit website ---
        _RoutingEntry(
            patterns=_compile([
                (r"\baudit[- ]?website\b", 0.95),
                (r"\b(seo|performance|accessibility)\s+audit\b", 0.80),
                (r"\b(audit[áa]\w*|auditar?)\s+(the\s+|el\s+|la\s+)?(website|sitio|p[áa]gina)\b", 0.85),
            ]),
            skill_name="audit-website",
            invoke_command="/audit-website",
            fallback_command=None,
            reason_template="Website audit detected",
        ),

        # --- COS init ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bcognitive[- ]?os[- ]?init\b", 0.95),
                (r"\b(init|initializ\w*|inicializar?)\s+(cognitive\s+os|cos)\b", 0.90),
            ]),
            skill_name="cognitive-os-init",
            invoke_command="/cognitive-os-init",
            fallback_command=None,
            reason_template="Cognitive OS initialization detected",
        ),

        # --- COS test ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bcognitive[- ]?os[- ]?test\b", 0.95),
                (r"\b(test|corr[eé]\w*)\s+(the\s+|el\s+)?(cognitive\s+os|cos)\b", 0.85),
            ]),
            skill_name="cognitive-os-test",
            invoke_command="/cognitive-os-test",
            fallback_command=None,
            reason_template="Cognitive OS test suite detected",
        ),

        # --- Batch runner ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bbatch[- ]?run\b", 0.95),
                (r"\b(run|ejecutar?)\s+(multiple|varios|batch)\s+(changes?|cambios?|sdd)\b", 0.80),
            ]),
            skill_name="batch-runner",
            invoke_command="/batch-run",
            fallback_command=None,
            reason_template="Batch execution detected",
        ),

        # --- Sandbox sample ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bsandbox[- ]?sample\b", 0.95),
                (r"\b(sample|muestr\w*)\s+(before|antes)\s+(scal|applying|aplicar)\b", 0.80),
            ]),
            skill_name="sandbox-sample",
            invoke_command="/sandbox-sample",
            fallback_command=None,
            reason_template="Sandbox sampling detected",
        ),

        # --- Resume tasks ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bresume[- ]?tasks?\b", 0.95),
                (r"\b(incomplete|pending)\s+tasks?\s+from\s+(last|previous)\b", 0.80),
                (r"\b(qu[eé]\s+qued[oó]\s+pendiente|what\s+was\s+left)\b", 0.80),
            ]),
            skill_name="resume-tasks",
            invoke_command="/resume-tasks",
            fallback_command=None,
            reason_template="Task resumption detected",
        ),

        # --- Private mode ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bprivate\s+mode\b", 0.90),
            ]),
            skill_name="private-mode",
            invoke_command="/private",
            fallback_command=None,
            reason_template="Private mode toggle detected",
        ),

        # --- GPU sandbox ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bgpu[- ]?sandbox\b", 0.95),
                (r"\bjupyter\b", 0.75),
                (r"\b(run|ejecutar?)\s+(python|ml|data)\s+(in\s+)?(jupyter|notebook|sandbox)\b", 0.80),
            ]),
            skill_name="gpu-sandbox",
            invoke_command="/gpu-sandbox",
            fallback_command="/jupyter-exec",
            reason_template="GPU/Jupyter sandbox detected",
        ),

        # --- Conversation memory ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bconversation[- ]?memory\b", 0.95),
                (r"\b(search|buscar?)\s+(past|previous|anterior\w*)\s+(session|sesi[oó]n|conversation|conversaci[oó]n)\b", 0.85),
            ]),
            skill_name="conversation-memory",
            invoke_command="/conversation-memory",
            fallback_command=None,
            reason_template="Conversation memory search detected",
        ),

        # --- Exhaustive prompt ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bexhaustive[- ]?prompt\b", 0.95),
                (r"\b(enumerate|enumerar?)\s+(the\s+|la\s+|el\s+)?scope\b", 0.80),
            ]),
            skill_name="exhaustive-prompt",
            invoke_command="/exhaustive-prompt",
            fallback_command=None,
            reason_template="Exhaustive prompt generation detected",
        ),

        # --- Compose prompt ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bcompose[- ]?prompt\b", 0.95),
            ]),
            skill_name="compose-prompt",
            invoke_command="/compose-prompt",
            fallback_command=None,
            reason_template="Prompt composition detected",
        ),

        # --- Repair status ---
        _RoutingEntry(
            patterns=_compile([
                (r"\brepair[- ]?status\b", 0.95),
                (r"\bcircuit\s+breaker\s+(status|state|estado)\b", 0.80),
            ]),
            skill_name="repair-status",
            invoke_command="/repair-status",
            fallback_command=None,
            reason_template="Auto-repair status check detected",
        ),

        # --- Capability snapshot ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bcapability[- ]?snapshot\b", 0.95),
            ]),
            skill_name="capability-snapshot",
            invoke_command="/capability-snapshot",
            fallback_command=None,
            reason_template="Capability snapshot detected",
        ),

        # --- Validate config ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bvalidate[- ]?config\b", 0.95),
                (r"\b(validate|validar?)\s+(the\s+|la\s+|el\s+)?(config|configuraci[oó]n)\b", 0.80),
            ]),
            skill_name="validate-config",
            invoke_command="/validate-config",
            fallback_command=None,
            reason_template="Configuration validation detected",
        ),

        # --- Smoke test ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bsmoke[- ]?test\b", 0.95),
            ]),
            skill_name="smoke-test",
            invoke_command="/smoke-test",
            fallback_command=None,
            reason_template="Smoke testing detected",
        ),

        # --- Session manager ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bsession\s+(manager|list|cleanup)\b", 0.85),
                (r"\b(active|concurrent)\s+sessions?\b", 0.75),
            ]),
            skill_name="session-manager",
            invoke_command="/sessions",
            fallback_command=None,
            reason_template="Session management detected",
        ),

        # --- Persistent agent ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bpersistent[- ]?agent\b", 0.95),
                (r"\bcreate[- ]?persistent[- ]?agent\b", 0.95),
            ]),
            skill_name="persistent-agent",
            invoke_command="/create-persistent-agent",
            fallback_command=None,
            reason_template="Persistent agent creation detected",
        ),

        # --- Auto rollback ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bauto[- ]?rollback\b", 0.95),
                (r"\brollback\s+(the\s+|el\s+)?(failed|fallido)?\s*(change|cambio|apply)\b", 0.80),
            ]),
            skill_name="auto-rollback",
            invoke_command="/auto-rollback",
            fallback_command=None,
            reason_template="Auto-rollback detected",
        ),

        # --- Arena ---
        _RoutingEntry(
            patterns=_compile([
                (r"\barena\b", 0.75),
                (r"\bbenchmark\s+(against|vs|comparison)\b", 0.80),
            ]),
            skill_name="arena",
            invoke_command="/arena",
            fallback_command=None,
            reason_template="Arena benchmark detected",
        ),

        # --- Simulation ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bsimulat\w+\b", 0.80),
                (r"\bsimulation[- ]?arena\b", 0.95),
            ]),
            skill_name="simulation-arena",
            invoke_command="/simulate",
            fallback_command=None,
            reason_template="Simulation scenario detected",
        ),

        # --- SDD continue / resume ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bsdd[- ]?continue\b", 0.95),
                (r"\bcontinue\s+(the\s+|el\s+)?sdd\b", 0.85),
            ]),
            skill_name="sdd-continue",
            invoke_command="/sdd-continue",
            fallback_command=None,
            reason_template="SDD continuation detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bsdd[- ]?resume\b", 0.95),
                (r"\bresume\s+(the\s+|el\s+)?sdd\b", 0.85),
            ]),
            skill_name="sdd-resume",
            invoke_command="/sdd-resume",
            fallback_command=None,
            reason_template="SDD resume detected",
        ),

        # --- Devbox checkpoint ---
        _RoutingEntry(
            patterns=_compile([
                (r"\b(devbox\s+)?checkpoint\b", 0.75),
                (r"\b(save|restore)\s+(environment|env)\s+state\b", 0.80),
            ]),
            skill_name="devbox-checkpoint",
            invoke_command="/checkpoint",
            fallback_command=None,
            reason_template="Environment checkpoint detected",
        ),

        # --- Resolve blockers ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bresolve[- ]?blockers?\b", 0.95),
                (r"\b(fix|resolver?)\s+(the\s+|los\s+)?blockers?\b", 0.85),
            ]),
            skill_name="resolve-blockers",
            invoke_command="/resolve-blockers",
            fallback_command=None,
            reason_template="Blocker resolution detected",
        ),

        # --- Webhook trigger ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bwebhook[- ]?trigger\b", 0.95),
            ]),
            skill_name="webhook-trigger",
            invoke_command="/webhook-trigger",
            fallback_command=None,
            reason_template="Webhook trigger detected",
        ),

        # --- Pre-development & audit skills ---
        _RoutingEntry(
            patterns=_compile([
                (r"\bcontext[- ]?analysis\b", 0.95),
                (r"\b(analiz[áa]\w*|analyze)\s+(the\s+|el\s+|la\s+)?(project\s+)?context\b", 0.85),
                (r"\b(new\s+project|project\s+brief|stakeholders|business\s+context)\b", 0.80),
                (r"\b(brief|contexto)\s+(del\s+|de\s+)?(proyecto|project)\b", 0.80),
            ]),
            skill_name="context-analysis",
            invoke_command="/context-analysis",
            fallback_command=None,
            reason_template="Project context analysis detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bthreat[- ]?model\b", 0.95),
                (r"\bstride\b", 0.85),
                (r"\b(security\s+assessment|risk\s+analysis|threat\s+identification)\b", 0.80),
                (r"\b(modelo\s+de\s+amenazas?|an[áa]lisis\s+de\s+riesgo)\b", 0.85),
            ]),
            skill_name="threat-model",
            invoke_command="/threat-model",
            fallback_command=None,
            reason_template="Threat modeling detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bcompetitive[- ]?research\b", 0.95),
                (r"\bbenchmarking\b", 0.80),
                (r"\b(library|librer[ií]a)\s+evaluation\b", 0.80),
                (r"\b(competitive|competencia)\s+(analysis|an[áa]lisis|landscape)\b", 0.85),
                (r"\b(alternativas?|alternatives?)\s+(para|for|to)\b", 0.75),
            ]),
            skill_name="competitive-research",
            invoke_command="/competitive-research",
            fallback_command=None,
            reason_template="Competitive research / benchmarking detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\bexecution[- ]?plan\b", 0.95),
                (r"\b(plan\s+de\s+ejecuci[oó]n|phased\s+(execution|plan))\b", 0.90),
                (r"\b(budget\s+estimation|estimaci[oó]n\s+de\s+presupuesto)\b", 0.85),
                (r"\b(milestones?|timeline|phases?)\s+(plan|planning|breakdown)\b", 0.80),
            ]),
            skill_name="execution-plan",
            invoke_command="/execution-plan",
            fallback_command=None,
            reason_template="Execution plan creation detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\baudience[- ]?summar\w*\b", 0.95),
                (r"\bexecutive\s+summary\b", 0.85),
                (r"\bstakeholder\s+(report|summary|resumen)\b", 0.85),
                (r"\b(res[uú]menes?\s+para\s+audiencias?|audience[- ]?targeted)\b", 0.85),
            ]),
            skill_name="audience-summaries",
            invoke_command="/audience-summaries",
            fallback_command=None,
            reason_template="Audience-targeted summaries detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\baudit[- ]?report\b", 0.95),
                (r"\b(sprint\s+review|work\s+summary|progress\s+report)\b", 0.80),
                (r"\b(informe\s+de\s+auditor[ií]a|reporte\s+de\s+sprint)\b", 0.85),
                (r"\b(audit\s+report|comprehensive\s+audit)\b", 0.90),
            ]),
            skill_name="audit-report",
            invoke_command="/audit-report",
            fallback_command=None,
            reason_template="Audit report generation detected",
        ),
        _RoutingEntry(
            patterns=_compile([
                (r"\btraceability[- ]?check\b", 0.95),
                (r"\b(coverage\s+gaps?|requirement\s+tracking)\b", 0.80),
                (r"\b(trazabilidad|rastreabilidad)\b", 0.85),
                (r"\b(requirement[- ]?to[- ]?test|req\s+coverage)\b", 0.85),
            ]),
            skill_name="traceability-check",
            invoke_command="/traceability-check",
            fallback_command=None,
            reason_template="Traceability gap detection detected",
        ),
    ]


# ---------------------------------------------------------------------------
# Catalog parser
# ---------------------------------------------------------------------------

def _parse_catalog(catalog_path: str) -> Set[str]:
    """Parse CATALOG.md and return set of skill names (directory names)."""
    skills: Set[str] = set()
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("|") and "|" in line[1:]:
                    cols = [c.strip() for c in line.split("|")]
                    # cols[0] is empty (before first |), cols[1] is skill name
                    if len(cols) >= 4 and cols[1] and cols[1] != "Skill":
                        name = cols[1].strip()
                        if name and not name.startswith("-"):
                            skills.add(name)
                    continue
                bullet_match = re.match(r"^- \*\*([^*]+)\*\*\s+—", line)
                if bullet_match:
                    skills.add(bullet_match.group(1).strip())
    except (OSError, IOError):
        pass
    return skills


# ---------------------------------------------------------------------------
# SkillRouter
# ---------------------------------------------------------------------------

class SkillRouter:
    """Match user messages to Cognitive OS skills using pattern-based routing.

    Args:
        catalog_path: Path to skills/CATALOG.md. Used to validate that
            skills in the routing table actually exist.
    """

    def __init__(
        self,
        catalog_path: Optional[str] = None,
        *,
        project_root: Optional[Path | str] = None,
        profile: Optional[str] = None,
    ):
        if project_root is None:
            # Auto-detect relative to this file's location
            lib_dir = Path(__file__).resolve().parent
            resolved_project_root = lib_dir.parent
        else:
            resolved_project_root = Path(project_root).resolve()
        if catalog_path is None:
            catalog_path = str(resolved_project_root / "skills" / "CATALOG.md")
        self._project_root = resolved_project_root
        self._profile = _canonical_profile(profile)
        self._catalog_path = catalog_path
        self._known_skills = _parse_catalog(catalog_path)
        self._skill_md_paths = _detect_skill_md_paths(resolved_project_root)
        self._disk_skills = set(self._skill_md_paths.keys())
        self._routing_table = _build_default_routing_table(resolved_project_root)
        visible_skills = _load_profile_projected_skills(resolved_project_root, self._profile)
        if visible_skills is not None:
            self._routing_table = [
                entry for entry in self._routing_table if entry.skill_name in visible_skills
            ]
            self._known_skills = self._known_skills & visible_skills if self._known_skills else visible_skills
            self._disk_skills = self._disk_skills & visible_skills
            self._skill_md_paths = {
                k: v for k, v in self._skill_md_paths.items() if k in visible_skills
            }
        # Semantic fallback (ADR-017 carve-out: additive language-agnostic
        # correctness fix). Lazily constructed so cold-start cost is paid
        # only on the first `match()` call that needs it.
        self._semantic_matcher = None  # type: ignore[assignment]
        self._semantic_matcher_loaded = False

    @property
    def known_skills(self) -> Set[str]:
        """Set of skill names parsed from CATALOG.md."""
        return self._known_skills

    @property
    def routing_table(self) -> List[_RoutingEntry]:
        """The full routing table (frontmatter-derived + hand-coded fallback)."""
        return self._routing_table

    @property
    def routing_entry_count(self) -> int:
        """Number of entries in the routing table."""
        return len(self._routing_table)

    def match(self, user_message: str) -> List[SkillMatch]:
        """Match user message to skills, sorted by confidence (descending).

        Returns an empty list if no patterns match.
        """
        if not user_message or not user_message.strip():
            return []

        text = user_message.strip()
        matches: List[SkillMatch] = []

        for entry in self._routing_table:
            if (
                (entry.skill_name == "auto-rollback" and _is_auto_rollback_meta_reference(text))
                or _is_router_negative_context(text, entry)
            ):
                continue

            best_conf = 0.0
            for pattern, base_conf in entry.patterns:
                if pattern.search(text):
                    best_conf = max(best_conf, base_conf)

            if best_conf > 0:
                matches.append(SkillMatch(
                    skill_name=entry.skill_name,
                    confidence=best_conf,
                    reason=entry.reason_template,
                    invoke_command=entry.invoke_command,
                ))

                # Also add fallback at lower confidence if it exists
                if entry.fallback_command and best_conf >= 0.5:
                    fallback_name = entry.fallback_command.lstrip("/")
                    # Only add if not already matched at higher confidence
                    if not any(m.skill_name == fallback_name for m in matches):
                        matches.append(SkillMatch(
                            skill_name=fallback_name,
                            confidence=best_conf * 0.7,
                            reason=f"Fallback for {entry.skill_name}",
                            invoke_command=entry.fallback_command,
                        ))

        # Deduplicate: keep highest confidence per skill
        best_per_skill: Dict[str, SkillMatch] = {}
        for m in matches:
            if m.skill_name not in best_per_skill or m.confidence > best_per_skill[m.skill_name].confidence:
                best_per_skill[m.skill_name] = m

        # --- Semantic fallback (language-agnostic) -----------------------
        # Only consult the semantic matcher when the regex path failed to
        # produce a confident match (>= 0.75). The semantic path NEVER
        # replaces or duplicates an existing regex match — it only adds
        # candidates for skills the regex layer missed entirely.
        top_regex_conf = max((m.confidence for m in best_per_skill.values()), default=0.0)
        if top_regex_conf < 0.75:
            for sm in self._semantic_match(text):
                if sm.skill_name in best_per_skill:
                    continue
                best_per_skill[sm.skill_name] = SkillMatch(
                    skill_name=sm.skill_name,
                    confidence=sm.confidence,
                    reason=sm.reason,
                    invoke_command=sm.invoke_command,
                )

        result = sorted(best_per_skill.values(), key=lambda m: m.confidence, reverse=True)
        return result

    def _semantic_match(self, text: str) -> List[Any]:
        """Return semantic fallback matches (empty list on any failure)."""
        try:
            if not self._semantic_matcher_loaded:
                self._semantic_matcher_loaded = True
                from lib.semantic_skill_matcher import (
                    SemanticSkillMatcher,
                    load_skill_metadata,
                )

                metadata = load_skill_metadata(self._skill_md_paths)
                if metadata:
                    self._semantic_matcher = SemanticSkillMatcher.from_routing_table(
                        self._routing_table, metadata
                    )
            if self._semantic_matcher is None:
                return []
            return self._semantic_matcher.match(text)
        except Exception:
            return []

    def best_match(self, user_message: str) -> Optional[SkillMatch]:
        """Return the highest-confidence match, or None if no good match.

        Only returns matches with confidence >= 0.50 to avoid false positives.
        """
        matches = self.match(user_message)
        if matches and matches[0].confidence >= 0.50:
            return matches[0]
        return None

    def format_suggestion(self, matches: List[SkillMatch]) -> str:
        """Format skill matches as a readable suggestion for the orchestrator.

        Returns empty string if no matches.
        """
        if not matches:
            return ""

        top = matches[0]
        lines = [
            f"Detected intent: {top.reason}. "
            f"Suggested skill: {top.invoke_command} "
            f"(confidence: {top.confidence:.2f})"
        ]

        if len(matches) > 1:
            alternatives = ", ".join(
                f"{m.invoke_command} ({m.confidence:.2f})"
                for m in matches[1:4]  # Show up to 3 alternatives
            )
            lines.append(f"Alternatives: {alternatives}")

        return "\n".join(lines)

    def get_routing_skills(self) -> Set[str]:
        """Return set of all skill names referenced in the routing table."""
        skills: Set[str] = set()
        for entry in self._routing_table:
            skills.add(entry.skill_name)
            if entry.fallback_command:
                skills.add(entry.fallback_command.lstrip("/"))
        return skills

    def get_primary_routing_skills(self) -> Set[str]:
        """Return skill names that can be selected as primary router matches.

        Fallback commands are intentionally excluded. They may be command
        aliases (for example ``/sdd-verify`` or ``/cost-predict``) rather than
        concrete skill directories, so coverage ratchets should measure primary
        routeability separately from fallback compatibility.
        """
        return {entry.skill_name for entry in self._routing_table}

    def validate_routing_table(self) -> List[str]:
        """Check that all skills in routing table exist in CATALOG.md.

        Returns list of missing skill names.
        """
        if not self._known_skills:
            return []  # Can't validate without catalog
        routing_skills = self.get_routing_skills()
        known_or_present = self._known_skills | self._disk_skills
        missing = sorted(routing_skills - known_or_present)
        return missing


class SkillRoutingIndexCache:
    """Project/profile-aware SkillRouter cache for service runtimes.

    The cache key includes project root, profile, and the checksum of visible
    SKILL.md files. Any SKILL.md edit invalidates the cached router so a
    long-running COS service does not serve stale routing patterns.
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, Optional[str]], Tuple[str, SkillRouter]] = {}

    def get_router(self, *, project_root: Path | str, profile: Optional[str] = None) -> SkillRouter:
        root = Path(project_root).resolve()
        canonical = _canonical_profile(profile)
        checksum = _skill_md_checksum(root)
        key = (str(root), canonical)
        cached = self._cache.get(key)
        if cached and cached[0] == checksum:
            return cached[1]
        router = SkillRouter(project_root=root, profile=canonical)
        self._cache[key] = (checksum, router)
        return router

    def clear(self) -> None:
        """Drop all cached routers."""
        self._cache.clear()


# ---------------------------------------------------------------------------
# ADR-188: last_suggestion — orchestrator-skill-invocation-gate support
# ---------------------------------------------------------------------------

def _project_root_for_runtime() -> Path:
    """Return the project root used for runtime artifact lookups.

    Honors PROJECT_DIR env, then falls back to this file's repository.
    """
    import os as _os
    p = _os.environ.get("PROJECT_DIR")
    if p:
        try:
            return Path(p).resolve()
        except Exception:
            pass
    return Path(__file__).resolve().parents[1]


def last_suggestion(
    session_id: str,
    *,
    project_root: Optional[Path | str] = None,
) -> Optional[Dict[str, Any]]:
    """Return the highest-confidence skill suggestion since the most recent
    UserPromptSubmit event for ``session_id`` (ADR-188).

    Reads, in order:
      1. ``.cognitive-os/sessions/events.jsonl`` (ADR-183 cross-session log) to
         locate the latest UserPromptSubmit-equivalent event for the session.
      2. ``.cognitive-os/metrics/skill-suggestion.jsonl`` (router log) to find
         the highest-confidence suggestion at-or-after that timestamp.

    The cross-session events log uses a permissive set of event_types
    (``user_prompt_submit``, ``user_prompt``, ``UserPromptSubmit``) since
    different harnesses emit slightly different names. If no anchor is found
    we treat the entire suggestion log for that session as in-scope.

    Returns ``{"skill", "confidence", "prompt_hash", "timestamp"}`` or None.
    """
    if not session_id:
        return None

    root = Path(project_root).resolve() if project_root else _project_root_for_runtime()

    events_path = root / ".cognitive-os" / "sessions" / "events.jsonl"
    suggestions_path = root / ".cognitive-os" / "metrics" / "skill-suggestion.jsonl"

    # Step 1: find anchor timestamp (latest user prompt for this session).
    anchor_ts: Optional[str] = None
    if events_path.exists():
        try:
            with events_path.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = __import__("json").loads(line)
                    except Exception:
                        continue
                    if evt.get("session_id") != session_id:
                        continue
                    et = (evt.get("event_type") or "").lower()
                    if et in ("user_prompt_submit", "userpromptsubmit", "user_prompt"):
                        ts = evt.get("ts")
                        if ts and (anchor_ts is None or ts > anchor_ts):
                            anchor_ts = ts
        except Exception:
            anchor_ts = None

    # Step 2: scan suggestion log for entries since anchor with same session.
    if not suggestions_path.exists():
        return None

    best: Optional[Dict[str, Any]] = None
    try:
        with suggestions_path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = __import__("json").loads(line)
                except Exception:
                    continue
                if rec.get("session_id") != session_id:
                    continue
                if not rec.get("threshold_met"):
                    # still consider matches: ADR-188 needs the highest-conf
                    # suggestion regardless of soft-suggest threshold, but only
                    # if there is a real skill name present.
                    if not rec.get("skill_name"):
                        continue
                ts = rec.get("ts")
                if anchor_ts and ts and ts < anchor_ts:
                    continue
                conf = float(rec.get("confidence") or 0.0)
                if best is None or conf > float(best.get("confidence") or 0.0):
                    best = {
                        "skill": rec.get("skill_name"),
                        "confidence": conf,
                        "prompt_hash": rec.get("prompt_hash") or "",
                        "timestamp": ts or "",
                    }
    except Exception:
        return None

    if best is None or not best.get("skill"):
        return None
    return best
