"""Context Diet — Token-efficient rule selection for sub-agents.

Each sub-agent launched by the orchestrator currently loads all rules from
.claude/rules/cos/ into context (~73K tokens). Most sub-agents need at most
2-3 rules relevant to their task type.

This module implements:
  - estimate_rules_tokens(): count approximate tokens in all rules
  - get_minimal_rules(): return only the rules needed for a task type
  - format_diet_report(): show current vs optimal token usage
  - ContextDiet: class-based API for orchestrator integration

Token estimation uses a conservative ratio of 1 token per 4 characters
(the industry standard approximation for English prose).

Task-to-rules mapping (functional API):
    implementation  — acceptance-criteria, closed-loop-prompts, trust-score
    review          — adversarial-review, trust-score, agent-quality
    debugging       — error-learning, closed-loop-prompts
    docs            — agent-quality
    archiving       — (none — agent-preamble only)

Task-to-rules mapping (ContextDiet class, expanded):
    implement/apply — go-architecture, clean-arch-patterns, definition-of-done,
                      acceptance-criteria, phase-aware-agents
    test            — testing-patterns, definition-of-done
    review          — agent-quality, trust-score, acceptance-criteria
    debug           — error-learning, closed-loop-prompts
    explore         — (minimal — just RULES-COMPACT)
    propose/spec/design — architecture rules, constitutional-gates
    verify          — trust-score, acceptance-criteria, definition-of-done
    archive         — (minimal)

The ALWAYS_INCLUDED rules are injected regardless of task type because they
form the irreducible baseline of agent governance.
"""

from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml as _yaml
except ImportError:
    _yaml = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHARS_PER_TOKEN = 4  # Conservative approximation: 1 token ≈ 4 chars

# Rules that are always included in any sub-agent context.
# These are the mandatory governance floor — removing them would break
# the core quality guarantees.
ALWAYS_INCLUDED: List[str] = [
    "RULES-COMPACT.md",
    "adaptive-bypass.md",
    "agent-quality.md",
    "credential-management.md",
]

# Task-specific rules on top of ALWAYS_INCLUDED.
# Key is task_type string; value is the list of additional rule filenames.
TASK_RULES: Dict[str, List[str]] = {
    "implementation": [
        "acceptance-criteria.md",
        "closed-loop-prompts.md",
        "trust-score.md",
    ],
    "review": [
        "adversarial-review.md",
        "trust-score.md",
    ],
    "debugging": [
        "error-learning.md",
        "closed-loop-prompts.md",
    ],
    "docs": [],  # agent-quality already in ALWAYS_INCLUDED
    "archiving": [],  # preamble only — minimal governance
}

# Approximate token count for the agent preamble template.
# Loaded from templates/agent-preamble.md; estimated here for offline use.
PREAMBLE_TOKENS = 500

# Approximate token count for a typical task prompt with acceptance criteria.
TASK_PROMPT_TOKENS = 2000

# Token budget constants for the diet report
SYSTEM_PROMPT_TOKENS = 20_000   # Claude Code system prompt
GLOBAL_CLAUDE_MD_TOKENS = 5_000  # User's ~/.claude/CLAUDE.md


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def estimate_rules_tokens(rules_dir: str) -> int:
    """Count the approximate total token count of all rules in a directory.

    Uses the 1 token per 4 characters approximation, which is accurate
    to within ~10% for English technical prose.

    Args:
        rules_dir: Path to the directory containing rule markdown files.
            Typically `.claude/rules/cos/` or `rules/`.

    Returns:
        Estimated total token count across all .md files in the directory.
        Returns 0 if the directory does not exist.
    """
    path = Path(rules_dir)
    if not path.is_dir():
        return 0

    total_chars = sum(
        f.stat().st_size
        for f in path.glob("*.md")
        if f.is_file()
    )
    return max(0, total_chars // CHARS_PER_TOKEN)


def get_minimal_rules(task_type: str) -> List[str]:
    """Return the minimal set of rule filenames needed for a task type.

    The returned list includes ALWAYS_INCLUDED rules plus any task-specific
    rules. The list is deduplicated and sorted alphabetically (RULES-COMPACT.md
    always first).

    Args:
        task_type: One of "implementation", "review", "debugging", "docs",
            "archiving". Unknown task types receive only ALWAYS_INCLUDED rules.

    Returns:
        Sorted list of rule filenames (basename only, e.g. "trust-score.md").
        RULES-COMPACT.md is always first when present.
    """
    task_specific = TASK_RULES.get(task_type, [])

    combined: set = set(ALWAYS_INCLUDED) | set(task_specific)

    # Sort alphabetically but keep RULES-COMPACT.md first
    sorted_rules = sorted(combined)
    if "RULES-COMPACT.md" in sorted_rules:
        sorted_rules.remove("RULES-COMPACT.md")
        sorted_rules = ["RULES-COMPACT.md"] + sorted_rules

    return sorted_rules


def estimate_minimal_tokens(
    task_type: str,
    rules_dir: Optional[str] = None,
) -> int:
    """Estimate tokens for the minimal rule set for a given task type.

    If rules_dir is provided, reads actual file sizes from disk.
    Otherwise, uses a pre-computed estimate of 800 tokens per rule file
    (typical for the COS rule set).

    Args:
        task_type: Task type (see get_minimal_rules).
        rules_dir: Optional path to the rules directory.

    Returns:
        Estimated token count for the minimal rule set.
    """
    TOKENS_PER_RULE_FILE = 800  # avg across the COS rule set

    minimal_rules = get_minimal_rules(task_type)

    if rules_dir:
        path = Path(rules_dir)
        if path.is_dir():
            total = 0
            for rule_file in minimal_rules:
                rule_path = path / rule_file
                if rule_path.exists():
                    total += rule_path.stat().st_size // CHARS_PER_TOKEN
            return total

    return len(minimal_rules) * TOKENS_PER_RULE_FILE


def format_diet_report(rules_dir: str) -> str:
    """Generate a human-readable context diet report.

    Shows the current total rules token cost, the optimal token cost per
    task type, and the potential savings.

    Args:
        rules_dir: Path to the directory containing rule markdown files.

    Returns:
        Formatted multi-line string suitable for terminal output.
    """
    path = Path(rules_dir)

    # ── Current baseline ─────────────────────────────────────────────
    rules_tokens = estimate_rules_tokens(rules_dir)
    rule_files = sorted(path.glob("*.md")) if path.is_dir() else []
    rule_count = len(rule_files)

    full_context = (
        SYSTEM_PROMPT_TOKENS
        + GLOBAL_CLAUDE_MD_TOKENS
        + rules_tokens
        + TASK_PROMPT_TOKENS
    )

    # ── Per-task optimal ─────────────────────────────────────────────
    task_types = list(TASK_RULES.keys())
    optimal_rows: List[str] = []
    for task in task_types:
        minimal = get_minimal_rules(task)
        minimal_rules_tokens = estimate_minimal_tokens(task, rules_dir)
        minimal_total = (
            SYSTEM_PROMPT_TOKENS
            + GLOBAL_CLAUDE_MD_TOKENS
            + PREAMBLE_TOKENS
            + minimal_rules_tokens
            + TASK_PROMPT_TOKENS
        )
        savings_pct = max(0, int((1 - minimal_total / full_context) * 100))
        optimal_rows.append(
            f"  {task:<18} {len(minimal):>2} rules  "
            f"~{minimal_total:>6,} tokens  saves {savings_pct}%"
        )

    lines = [
        "Context Diet Report",
        "=" * 60,
        "",
        "Current baseline (full rules load):",
        f"  System prompt:       ~{SYSTEM_PROMPT_TOKENS:>6,} tokens",
        f"  CLAUDE.md global:    ~{GLOBAL_CLAUDE_MD_TOKENS:>6,} tokens",
        f"  Rules ({rule_count} files):      ~{rules_tokens:>6,} tokens",
        f"  Task prompt:         ~{TASK_PROMPT_TOKENS:>6,} tokens",
        f"  TOTAL:               ~{full_context:>6,} tokens",
        "",
        "Optimal per task type (minimal rules + preamble):",
        *optimal_rows,
        "",
        "Recommendations:",
        "  1. Set model_capability.level: 4 in cognitive-os.yaml",
        "     (disables 5 redundant governance hooks for Opus 4.6)",
        "  2. Set efficiency.profile: lean for sub-agents",
        "     (loads RULES-COMPACT.md only — ~1,500 tokens)",
        "  3. Use prompt-composition to inject task-specific rules",
        "     via templates/ instead of file-based loading",
        "",
        "Target: < 10,000 tokens per sub-agent launch",
        f"Current: ~{full_context:,} tokens — {full_context // 10000}x over target",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ContextDiet class — orchestrator integration API
# ---------------------------------------------------------------------------

# Expanded task-type to rule-file mapping for the class-based API.
# These rule filenames are looked up relative to the rules directory.
_CLASS_TASK_RULES: Dict[str, List[str]] = {
    "implement": [
        "definition-of-done.md",
        "acceptance-criteria.md",
        "phase-aware-agents.md",
        "closed-loop-prompts.md",
        "trust-score.md",
    ],
    "apply": [
        "definition-of-done.md",
        "acceptance-criteria.md",
        "phase-aware-agents.md",
        "closed-loop-prompts.md",
        "trust-score.md",
    ],
    "test": [
        "definition-of-done.md",
    ],
    "review": [
        "adversarial-review.md",
        "trust-score.md",
        "acceptance-criteria.md",
    ],
    "debug": [
        "error-learning.md",
        "closed-loop-prompts.md",
    ],
    "explore": [],  # RULES-COMPACT only
    "propose": [
        "constitutional-gates.md",
        "phase-aware-agents.md",
    ],
    "spec": [
        "constitutional-gates.md",
        "phase-aware-agents.md",
        "acceptance-criteria.md",
    ],
    "design": [
        "constitutional-gates.md",
        "phase-aware-agents.md",
    ],
    "verify": [
        "trust-score.md",
        "acceptance-criteria.md",
        "definition-of-done.md",
    ],
    "archive": [],  # RULES-COMPACT only
}

# Capability level → hooks to disable (cumulative: higher level includes lower).
_DISABLED_HOOKS: Dict[int, List[str]] = {
    3: ["context-management"],
    4: [
        "clarification-gate",
        "assumption-tracking",
        "confidence-gate",
        "blast-radius",
    ],
    5: [
        "completeness-check",
        "scope-proportionality",
        "trust-score-validator",
        "claim-validator",
    ],
}

# Token budget for sub-agent context target
_TARGET_TOKENS = 10_000


def _load_yaml_config(config_path: str) -> dict:
    """Load and parse a YAML config file.

    Falls back to an empty dict if the file is missing or pyyaml is unavailable.
    """
    path = Path(config_path)
    if not path.exists():
        return {}

    text = path.read_text()

    if _yaml is not None:
        return _yaml.safe_load(text) or {}

    # Minimal fallback: extract phase value only
    result: dict = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("phase:"):
            val = stripped.split(":", 1)[1].strip().split("#")[0].strip()
            result.setdefault("project", {})["phase"] = val
    return result


class ContextDiet:
    """Reduces agent context to only what's needed for the task.

    Reads configuration from cognitive-os.yaml to determine the current
    project phase and applies task-type specific rule selection to keep
    sub-agent context well below 10K tokens.

    Usage::

        diet = ContextDiet.from_yaml("cognitive-os.yaml")
        rules = diet.select_rules("implement", "Build a new payment endpoint")
        context = diet.get_lean_context("implement", "Build a new payment endpoint")
        hooks = diet.get_disabled_hooks(4)
    """

    def __init__(self, cognitive_os_config: dict) -> None:
        """Initialise from an already-parsed config dictionary.

        Args:
            cognitive_os_config: Parsed contents of cognitive-os.yaml.
                Typically obtained via :meth:`from_yaml`.
        """
        self._config = cognitive_os_config
        project = cognitive_os_config.get("project", {}) or {}
        self._phase: str = project.get("phase", "reconstruction") if isinstance(project, dict) else "reconstruction"

        # Resolve the rules directory from the config or fall back to the
        # canonical .claude/rules location relative to the repo root.
        # We store it as a string; callers may override via from_yaml.
        self._rules_dir: Optional[str] = None

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(
        cls,
        config_path: str = "cognitive-os.yaml",
        rules_dir: Optional[str] = None,
    ) -> "ContextDiet":
        """Create a ContextDiet by loading configuration from a YAML file.

        Args:
            config_path: Path to cognitive-os.yaml.
            rules_dir: Optional override for the rules directory path.
                If None, defaults to .claude/rules/ relative to the
                directory containing config_path.

        Returns:
            Configured ContextDiet instance.
        """
        config = _load_yaml_config(config_path)
        instance = cls(config)

        if rules_dir is not None:
            instance._rules_dir = rules_dir
        else:
            config_file = Path(config_path)
            candidate = config_file.parent / ".claude" / "rules"
            if candidate.is_dir():
                instance._rules_dir = str(candidate)

        return instance

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def select_rules(self, task_type: str, task_description: str = "") -> List[str]:
        """Select only relevant rules for this task type.

        Task types: implement, test, review, debug, explore, propose, spec,
        design, apply, verify, archive.

        Unknown task types fall back to RULES-COMPACT.md only.

        Args:
            task_type: One of the recognised task type strings (case-insensitive).
            task_description: Optional description used for future keyword-based
                expansion (currently unused but part of the stable API).

        Returns:
            Deduplicated list of rule filenames.  RULES-COMPACT.md is always
            first; remaining rules are sorted alphabetically.
        """
        task_key = task_type.lower().strip()
        task_specific: List[str] = list(_CLASS_TASK_RULES.get(task_key, []))

        # Always include the compact index
        combined: set = {"RULES-COMPACT.md"} | set(task_specific)

        # Phase-aware additions: in production/maintenance, add phase rules
        if self._phase in ("production", "maintenance") and task_key in (
            "implement",
            "apply",
        ):
            combined.add("phase-aware-agents.md")

        sorted_rules = sorted(combined - {"RULES-COMPACT.md"})
        return ["RULES-COMPACT.md"] + sorted_rules

    def get_lean_context(self, task_type: str, task_description: str = "") -> str:
        """Build minimal context string for a sub-agent.

        Reads selected rule files from disk (if the rules directory is
        resolvable) and concatenates their content, targeting < 10K tokens.

        Args:
            task_type: Task type (see :meth:`select_rules`).
            task_description: Optional task description (passed through to
                :meth:`select_rules` for future keyword expansion).

        Returns:
            Concatenated rule content as a single string.  If the rules
            directory is not set or files are missing, returns a lightweight
            fallback that lists the selected rule filenames instead.
        """
        rule_files = self.select_rules(task_type, task_description)

        if not self._rules_dir:
            return self._fallback_context(task_type, rule_files)

        rules_path = Path(self._rules_dir)
        sections: List[str] = []
        total_tokens = 0

        for rule_file in rule_files:
            rule_path = rules_path / rule_file
            if not rule_path.exists():
                continue
            content = rule_path.read_text(encoding="utf-8")
            file_tokens = len(content) // CHARS_PER_TOKEN
            if total_tokens + file_tokens > _TARGET_TOKENS:
                # Budget exceeded — stop adding more rules
                break
            sections.append(f"<!-- rule: {rule_file} -->\n{content}")
            total_tokens += file_tokens

        if not sections:
            return self._fallback_context(task_type, rule_files)

        return "\n\n".join(sections)

    def get_disabled_hooks(self, model_capability_level: int) -> List[str]:
        """Return hooks to disable based on model capability level.

        Disabled hooks are cumulative: level 4 includes everything disabled
        at level 3 plus its own additions.

        Level mapping:
            1-2: all hooks active
            3 (haiku): disable context-management
            4 (sonnet): + clarification-gate, assumption-tracking,
                           confidence-gate, blast-radius
            5 (opus): + completeness-check, scope-proportionality,
                        trust-score-validator, claim-validator

        Args:
            model_capability_level: Integer from 1 to 5.

        Returns:
            Sorted deduplicated list of hook names to disable.
        """
        level = max(1, min(5, int(model_capability_level)))
        disabled: set = set()
        for lvl in sorted(_DISABLED_HOOKS.keys()):
            if lvl <= level:
                disabled.update(_DISABLED_HOOKS[lvl])
        return sorted(disabled)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def phase(self) -> str:
        """Current project phase from cognitive-os.yaml."""
        return self._phase

    @property
    def rules_dir(self) -> Optional[str]:
        """Path to the rules directory, or None if not configured."""
        return self._rules_dir

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fallback_context(self, task_type: str, rule_files: List[str]) -> str:
        """Generate a lightweight context when rule files cannot be read."""
        lines = [
            f"# Context Diet — {task_type} task (phase: {self._phase})",
            "",
            "Selected rules for this task (load from .claude/rules/):",
        ]
        for f in rule_files:
            lines.append(f"  - {f}")
        return "\n".join(lines)
