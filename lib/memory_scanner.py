"""
Memory Scanner — Content security scanning before Engram persistence.

Scans for prompt injection, credential exfiltration, invisible Unicode,
and other threats before allowing content to be saved to memory.

Adopted from: Hermes Agent tools/memory_tool.py (MIT license)
Source commit: see .cognitive-os/adoption-registry.yaml
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class ScanResult:
    blocked: bool
    reasons: List[str]
    content: str  # original content


class MemoryScanner:
    """Lightweight content security scanner for Engram memory saves.

    Detects prompt injection, role hijacking, credential exfiltration,
    and invisible Unicode characters that could poison future sessions.
    """

    def __init__(self) -> None:
        self.patterns: List[Tuple[str, re.Pattern]] = self._build_patterns()
        self.invisible_unicode: List[Tuple[str, re.Pattern]] = self._build_unicode_patterns()

    def scan(self, content: str) -> ScanResult:
        """Scan content for threats.

        Returns a ScanResult; ``blocked`` is True if any threat is found.
        All matching category names are collected in ``reasons`` so callers
        can report every violation, not just the first.
        """
        reasons: List[str] = []

        # Invisible Unicode check — these chars are used to hide injections
        for name, pattern in self.invisible_unicode:
            if pattern.search(content):
                reasons.append(f"invisible_unicode:{name}")

        # Threat pattern check
        for category, pattern in self.patterns:
            if pattern.search(content):
                reasons.append(category)

        return ScanResult(
            blocked=len(reasons) > 0,
            reasons=reasons,
            content=content,
        )

    # ------------------------------------------------------------------
    # Pattern builders — ported verbatim from Hermes memory_tool.py
    # ------------------------------------------------------------------

    def _build_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """Build compiled regex patterns for all 12 threat categories."""
        raw: List[Tuple[str, str]] = [
            # Prompt injection
            ("prompt_injection",       r"ignore\s+(previous|all|above|prior)\s+instructions"),
            ("role_hijack",            r"you\s+are\s+now\s+"),
            ("deception_hide",         r"do\s+not\s+tell\s+the\s+user"),
            ("sys_prompt_override",    r"system\s+prompt\s+override"),
            ("disregard_rules",        r"disregard\s+(your|all|any)\s+(instructions|rules|guidelines)"),
            ("bypass_restrictions",    r"act\s+as\s+(if|though)\s+you\s+(have\s+no|don\'t\s+have)\s+(restrictions|limits|rules)"),
            # Exfiltration via curl/wget with secrets
            ("exfil_curl",             r"curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)"),
            ("exfil_wget",             r"wget\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)"),
            ("read_secrets",           r"cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass|\.npmrc|\.pypirc)"),
            # Persistence / backdoor via shell config
            ("ssh_backdoor",           r"authorized_keys"),
            ("ssh_access",             r"\$HOME/\.ssh|\~/\.ssh"),
            ("hermes_env",             r"\$HOME/\.hermes/\.env|\~/\.hermes/\.env"),
        ]
        return [(category, re.compile(pattern, re.IGNORECASE)) for category, pattern in raw]

    def _build_unicode_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """Build patterns for invisible / directional Unicode characters."""
        chars: List[Tuple[str, str]] = [
            ("ZWSP",   "\u200b"),   # Zero Width Space
            ("ZWNJ",   "\u200c"),   # Zero Width Non-Joiner
            ("ZWJ",    "\u200d"),   # Zero Width Joiner
            ("WJ",     "\u2060"),   # Word Joiner
            ("BOM",    "\ufeff"),   # Byte Order Mark / Zero Width No-Break Space
            ("LRE",    "\u202a"),   # Left-to-Right Embedding
            ("RLE",    "\u202b"),   # Right-to-Left Embedding
            ("PDF",    "\u202c"),   # Pop Directional Formatting
            ("LRO",    "\u202d"),   # Left-to-Right Override
            ("RLO",    "\u202e"),   # Right-to-Left Override (most dangerous)
        ]
        return [(name, re.compile(re.escape(char))) for name, char in chars]
