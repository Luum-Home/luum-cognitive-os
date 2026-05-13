# SCOPE: both
"""Derive routing_patterns frontmatter for auto-generated SKILL.md files.

Called by auto-skill-generator.sh after determining a skill name + description.
Standard library only — no third-party imports.

CLI usage (for shell integration):
    python3 -m lib.routing_pattern_deriver --skill-name <name> --description <desc>

Returns a YAML block suitable for embedding in SKILL.md frontmatter.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass


# Words that are too generic to use as standalone patterns.
_GENERIC_WORDS: frozenset[str] = frozenset(
    {
        "create",
        "fix",
        "test",
        "run",
        "use",
        "get",
        "set",
        "add",
        "make",
        "do",
        "build",
        "update",
        "show",
        "find",
        "list",
        "help",
        "check",
        "debug",
        "new",
        "the",
        "and",
        "or",
        "for",
        "with",
        "from",
        "this",
        "that",
    }
)

# Spanish action verbs that indicate the description is bilingual or Spanish-heavy.
_SPANISH_ACTION_VERBS: tuple[str, ...] = (
    "crear",
    "generar",
    "arreglar",
    "corregir",
    "ejecutar",
    "agregar",
    "añadir",
    "construir",
    "actualizar",
    "verificar",
    "revisar",
    "analizar",
    "implementar",
    "configurar",
    "depurar",
    "optimizar",
    "refactorizar",
    "migrar",
    "desplegar",
    "probar",
)


@dataclass
class RoutingPattern:
    """A single routing pattern entry (maps to one element in routing_patterns: list)."""

    pattern: str
    confidence: float
    source: str  # human-readable rationale


class RoutingPatternDeriver:
    """Derive 2-3 routing_patterns for a skill from its name and description."""

    def derive(
        self,
        skill_name: str,
        description: str,
        name_aliases: list[str] | None = None,
    ) -> list[dict]:
        """Return 2-3 routing_pattern dicts ordered by descending confidence.

        Each dict has keys: pattern (str), confidence (float).
        The source key is included for traceability but is not part of the SKILL.md spec.

        Rules:
        1. Skill name as \\b<name>\\b  → confidence 0.95
        2. Hyphen-collapsed variant (hyphens replaced by spaces) → 0.85
           (skipped if identical to rule 1 result after normalisation)
        3. Spanish trigger if description contains a known Spanish action verb → 0.80
        4. 2-word keyword combo extracted from description → 0.75
           (skipped if both keywords are generic)
        """
        if name_aliases is None:
            name_aliases = []

        patterns: list[RoutingPattern] = []

        clean_name = skill_name.strip().lower()

        # --- Rule 1: exact skill name as word-boundary regex ---
        if clean_name and not self._is_generic(clean_name):
            patterns.append(
                RoutingPattern(
                    pattern=rf"\b{re.escape(clean_name)}\b",
                    confidence=0.95,
                    source="skill-name-exact",
                )
            )

        # --- Rule 2: hyphen-collapsed variant ---
        collapsed = clean_name.replace("-", " ").replace("_", " ")
        if collapsed != clean_name and not self._is_generic(collapsed):
            # Check not already covered
            if not any(p.pattern == rf"\b{re.escape(collapsed)}\b" for p in patterns):
                patterns.append(
                    RoutingPattern(
                        pattern=rf"\b{re.escape(collapsed)}\b",
                        confidence=0.85,
                        source="skill-name-collapsed",
                    )
                )

        # --- Rule 3: Spanish trigger ---
        desc_lower = description.lower()
        matched_es_verb = next(
            (v for v in _SPANISH_ACTION_VERBS if re.search(rf"\b{v}\b", desc_lower)),
            None,
        )
        if matched_es_verb:
            es_pattern = rf"\b{re.escape(matched_es_verb)}\b.*\b{re.escape(collapsed if collapsed != clean_name else clean_name)}\b"
            # Simpler alternative: just the verb + name combo as a looser anchor
            patterns.append(
                RoutingPattern(
                    pattern=es_pattern,
                    confidence=0.80,
                    source="spanish-action-verb",
                )
            )

        # --- Rule 4: 2-word keyword combo from description ---
        keywords = self._extract_keywords(description, clean_name)
        if len(keywords) >= 2:
            kw1, kw2 = keywords[0], keywords[1]
            combo_pattern = rf"\b{re.escape(kw1)}\b.*\b{re.escape(kw2)}\b"
            # Deduplicate
            if not any(p.pattern == combo_pattern for p in patterns):
                patterns.append(
                    RoutingPattern(
                        pattern=combo_pattern,
                        confidence=0.75,
                        source="description-keyword-combo",
                    )
                )

        # --- Name aliases (bonus, confidence 0.85) ---
        for alias in name_aliases:
            alias_clean = alias.strip().lower()
            if alias_clean and not self._is_generic(alias_clean):
                alias_pattern = rf"\b{re.escape(alias_clean)}\b"
                if not any(p.pattern == alias_pattern for p in patterns):
                    patterns.append(
                        RoutingPattern(
                            pattern=alias_pattern,
                            confidence=0.85,
                            source="name-alias",
                        )
                    )

        # Limit to 3, sorted by confidence descending
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        top = patterns[:3]

        # Ensure at least 2 patterns; if we only have 1 (e.g. very short name),
        # add a fallback description-fragment pattern.
        if len(top) < 2 and description.strip():
            fragment = description.strip()[:40].lower()
            fragment = re.sub(r"[^a-z0-9 ]+", " ", fragment).strip()
            if fragment and not self._is_generic(fragment):
                top.append(
                    RoutingPattern(
                        pattern=rf"\b{re.escape(fragment[:20])}\b",
                        confidence=0.70,
                        source="description-fragment-fallback",
                    )
                )

        return [{"pattern": p.pattern, "confidence": p.confidence} for p in top]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_generic(self, word: str) -> bool:
        """Return True if the word (or phrase) is purely generic vocabulary."""
        tokens = word.lower().split()
        return all(t in _GENERIC_WORDS for t in tokens)

    def _extract_keywords(self, description: str, skill_name: str) -> list[str]:
        """Extract up to 3 meaningful content words from the description."""
        # Tokenise: lowercase alphanum words, length >= 4, not generic, not in skill name parts
        name_parts = set(re.split(r"[-_ ]", skill_name.lower()))
        tokens = re.findall(r"[a-z][a-z0-9]{2,}", description.lower())
        seen: set[str] = set()
        result: list[str] = []
        for tok in tokens:
            if tok in seen:
                continue
            seen.add(tok)
            if tok in _GENERIC_WORDS:
                continue
            if tok in name_parts:
                continue
            result.append(tok)
            if len(result) >= 3:
                break
        return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def derive_intent_examples(skill_name: str, description: str) -> list[str]:
    """Derive multilingual intent example phrases for semantic routing.

    Returns 4-6 example phrases in EN/ES/PT/DE that describe when to invoke
    the skill. Used as the training signal for ``lib/semantic_skill_matcher``.

    The output is deliberately simple — it seeds the semantic index for a
    new skill without requiring an LLM call. Authors are expected to refine
    or extend these examples in the SKILL.md frontmatter.
    """
    base = (description or "").strip().rstrip(".")
    if not base:
        base = skill_name.replace("-", " ")
    pretty = skill_name.replace("-", " ").replace("_", " ")

    # Trim to a reasonable length for templated phrasing.
    short = base if len(base) <= 80 else base[:80].rsplit(" ", 1)[0]

    examples: list[str] = [
        # English (2)
        f"I want to {pretty}",
        f"help me with: {short}",
        # Spanish (2)
        f"quiero {pretty}",
        f"necesito ayuda con: {short}",
        # Portuguese (1)
        f"preciso de ajuda com: {short}",
        # German (1)
        f"ich brauche Hilfe bei: {short}",
    ]
    return examples


def _build_yaml_block(patterns: list[dict]) -> str:
    """Render patterns as a YAML list block for embedding in SKILL.md frontmatter."""
    lines = ["routing_patterns:"]
    for p in patterns:
        lines.append(f"  - pattern: '{p['pattern']}'")
        lines.append(f"    confidence: {p['confidence']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Derive routing_patterns for a SKILL.md file"
    )
    parser.add_argument("--skill-name", required=True, help="The skill slug/name")
    parser.add_argument(
        "--description", default="", help="One-line skill description"
    )
    parser.add_argument(
        "--aliases",
        default="",
        help="Comma-separated list of name aliases",
    )
    parser.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Output format (default: yaml)",
    )
    args = parser.parse_args(argv)

    aliases = [a.strip() for a in args.aliases.split(",") if a.strip()]
    deriver = RoutingPatternDeriver()
    patterns = deriver.derive(args.skill_name, args.description, aliases)

    if args.format == "json":
        print(json.dumps(patterns))
    else:
        print(_build_yaml_block(patterns))


if __name__ == "__main__":
    main()
