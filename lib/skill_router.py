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

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class SkillMatch:
    """A matched skill with confidence and reasoning."""

    skill_name: str
    confidence: float  # 0.0 to 1.0
    reason: str  # why this skill matched
    invoke_command: str  # e.g., "/repo-forensics"

    def __str__(self) -> str:
        return f"{self.invoke_command} (confidence={self.confidence:.2f}): {self.reason}"


@dataclass
class _RoutingEntry:
    """Internal routing table entry."""

    patterns: List[Tuple[re.Pattern, float]]  # (compiled regex, base confidence)
    skill_name: str
    invoke_command: str
    fallback_command: Optional[str]
    reason_template: str


def _compile(patterns: List[Tuple[str, float]]) -> List[Tuple[re.Pattern, float]]:
    """Compile regex patterns with IGNORECASE."""
    return [(re.compile(p, re.IGNORECASE), w) for p, w in patterns]


# ---------------------------------------------------------------------------
# URL detectors (special-cased, not pure regex on the whole message)
# ---------------------------------------------------------------------------

_GITHUB_URL_RE = re.compile(
    r"https?://github\.com/[\w.\-]+/[\w.\-]+", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Routing table definition
# ---------------------------------------------------------------------------

def _build_default_routing_table() -> List[_RoutingEntry]:
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

    def __init__(self, catalog_path: Optional[str] = None):
        if catalog_path is None:
            # Auto-detect relative to this file's location
            lib_dir = Path(__file__).resolve().parent
            project_root = lib_dir.parent
            catalog_path = str(project_root / "skills" / "CATALOG.md")
        self._catalog_path = catalog_path
        self._known_skills = _parse_catalog(catalog_path)
        self._routing_table = _build_default_routing_table()

    @property
    def known_skills(self) -> Set[str]:
        """Set of skill names parsed from CATALOG.md."""
        return self._known_skills

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

        result = sorted(best_per_skill.values(), key=lambda m: m.confidence, reverse=True)
        return result

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

    def validate_routing_table(self) -> List[str]:
        """Check that all skills in routing table exist in CATALOG.md.

        Returns list of missing skill names.
        """
        if not self._known_skills:
            return []  # Can't validate without catalog
        routing_skills = self.get_routing_skills()
        missing = sorted(routing_skills - self._known_skills)
        return missing
