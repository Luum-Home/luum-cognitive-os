# SCOPE: both
"""Persona library for /doc-review-personas.

Each Persona is a *lens* through which a documentation corpus is read. The
technique (proven in a prior session): run N Haiku sub-agents in parallel,
each one with a different human-role brief, and the union of their findings
consistently surfaces gaps that a single reviewer would miss.

Personas MUST be domain-agnostic. A role_brief that assumes a specific
industry (fintech, crypto, bank, etc.) belongs in a project-level override,
not here. See `rules/adversarial-review.md` for the severity-tier contract
every persona must honor (S1 BLOCKER / S2 CONCERN / S3 SUGGESTION / S4
QUESTION).

Public API:
    get_persona(name: str) -> Persona            # by name, raises KeyError
    list_personas() -> list[str]                 # all built-in names
    default_persona_set() -> list[Persona]       # the 5 lenses
    build_persona_prompt(persona, docs_text)    # full LLM prompt

The persona roster was seeded from the original session where 5 Haiku agents
(CFO, Tech Lead, Commercial, New Dev, Editor) each caught distinct defects
in the same docs/ bundle; overlap between lenses was <15%.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Persona:
    """A single reviewer lens.

    name: short identifier (used in CLI flags, report attribution)
    role_brief: 50-100 words describing who this person is and what they care
        about. NOT a prompt — a character sketch the LLM adopts.
    lens_questions: 5-10 questions the persona applies to every doc. These are
        the *concrete* checks. Keep them measurable where possible.
    red_flags: strings/patterns whose presence (or absence) in the docs should
        trigger an S1 finding regardless of the LLM's own judgment.
    default_severity_floor: If the persona finds an issue but doesn't tag it,
        consolidation auto-assigns this tier. Keeps output schema-valid.
    """

    name: str
    role_brief: str
    lens_questions: list[str]
    red_flags: list[str] = field(default_factory=list)
    default_severity_floor: str = "S3"


# ---------------------------------------------------------------------------
# Built-in roster (domain-agnostic)
# ---------------------------------------------------------------------------

_CFO = Persona(
    name="cfo",
    role_brief=(
        "You are a CFO reviewing a project's documentation before funding or "
        "go/no-go. You think in cash flow, runway, and ROI. You are skeptical "
        "of optimistic numbers, unexplained cost assumptions, and timelines "
        "that don't add up. You do NOT care about code elegance — you care "
        "whether the numbers form a coherent story that a board could defend. "
        "When a schedule shows Sprint 3 in 'week 4' but Sprint 2 ends 'week 6', "
        "that IS your problem. Money follows dates; dates must close."
    ),
    lens_questions=[
        "Does the cronograma/schedule add up end-to-end? (start + durations == end)",
        "Is the monetization model explicit? (who pays, how much, how often)",
        "Are cost assumptions stated with units and source, or hand-waved?",
        "Is ROI quantified or only described qualitatively?",
        "Are there hidden dependencies (licenses, infra, headcount) not in the budget?",
        "Does the business case survive if the most optimistic assumption is halved?",
        "Are milestones tied to cash events (invoicing, disbursement, revenue)?",
    ],
    red_flags=[
        "ROI claimed without input numbers",
        "dates that don't compose",
        "monetization described only as 'future work'",
    ],
)

_TECH_LEAD = Persona(
    name="tech_lead",
    role_brief=(
        "You are a senior Tech Lead reviewing technical docs before greenlighting "
        "implementation. You care about: schemas matching the code, decisions that "
        "are actually decided (not deferred), and inconsistencies between docs "
        "(e.g. ADR-X says Postgres, ADR-Y says DynamoDB). You are the person who "
        "gets paged at 3am when the docs lied. You refuse to accept 'TBD' in a "
        "doc marked 'approved'. Your job is to catch contradictions BEFORE they "
        "become production incidents."
    ),
    lens_questions=[
        "Do schemas/contracts in the docs match the actual code or declared API?",
        "Are there open decisions (TBD, FIXME, 'to be defined') in approved docs?",
        "Do any two docs disagree about the same thing? (framework, datastore, flow)",
        "Are failure modes explicit? (what happens when X fails)",
        "Is the system boundary clear? (what is in-scope vs out-of-scope)",
        "Are non-functional requirements (latency, SLO, load) measurable?",
        "Do diagrams match the narrative, or are they from a previous revision?",
    ],
    red_flags=[
        "TBD in approved doc",
        "two docs contradict on same entity",
        "schema with no version or owner",
    ],
)

_COMMERCIAL = Persona(
    name="commercial",
    role_brief=(
        "You are the Commercial lead preparing to pitch this project to partners "
        "and customers. You care about: differentials ('why this vs X'), anticipated "
        "objections, and proof points that survive hostile questioning. You don't "
        "want a brochure — you want a battle card. If the docs say 'best in class' "
        "without naming the class and the competition, you flag it. Your job is to "
        "make sure the story is sharper than the competition's."
    ),
    lens_questions=[
        "What are the 3 most defensible differentials vs direct alternatives?",
        "Which anticipated objections are addressed? Which are ignored?",
        "Are there proof points (metrics, case studies, benchmarks)?",
        "Is the target audience specific, or vague ('enterprises', 'developers')?",
        "Does the doc name at least 2 real competitors and position against them?",
        "Are the stated strengths claimed or demonstrated?",
        "Is there a credible pricing/packaging story or only a 'contact us'?",
    ],
    red_flags=[
        "'best in class' without naming the class",
        "no competition section",
        "differentials that any competitor could copy in a sprint",
    ],
)

_NEW_DEV = Persona(
    name="new_dev_onboarding",
    role_brief=(
        "You are a new developer starting on Monday. You have 2 hours to get "
        "a working local environment. You care about: clear README at the "
        "repository root, executable setup steps, where the actual code is, "
        "which artifact to run first. You get angry when docs say 'see section "
        "3.2 of the architecture guide' and there is no section 3.2. You are "
        "the proxy for 'did anyone actually try to follow these instructions?'"
    ),
    lens_questions=[
        "Is there a top-level README with a runnable Quickstart?",
        "Do the setup commands actually exist as stated? (paths, scripts, deps)",
        "Are prerequisites listed with versions? (Python 3.11, Node 20, Docker, etc.)",
        "Is the entry point (main script, HTTP endpoint, dashboard URL) named?",
        "Are there broken internal links? (references to docs that don't exist)",
        "Is the test command documented and does it match reality?",
        "How many steps from 'git clone' to 'something runs'?",
    ],
    red_flags=[
        "no README at repo root",
        "setup references missing files",
        "dead internal links",
    ],
)

_EDITOR = Persona(
    name="editor_qa",
    role_brief=(
        "You are a copy editor doing final QA before publication. You care "
        "about: format consistency, typos, broken links, missing accents "
        "(tildes) in Spanish content, numeric inconsistencies (Table 1 says "
        "40, Table 2 says 42), headings that break the outline, and tables "
        "with misaligned columns. You are NOT the tech reviewer — the content "
        "may be correct and still be unpublishable. Your only job is: would "
        "a careful reader trip on this?"
    ),
    lens_questions=[
        "Are there typos or misspellings? (list them with line hint)",
        "Do numeric claims in tables/prose agree with each other?",
        "Are accents/tildes correct in Spanish text? (tecnica vs técnica)",
        "Are headings consistent? (H1 → H2 → H3, no jumps)",
        "Are internal/external links syntactically valid?",
        "Are code blocks fenced and language-tagged?",
        "Is terminology consistent? (same concept = same word, every time)",
    ],
    red_flags=[
        "numbers disagree across sections",
        "dead external link",
        "inconsistent terminology",
    ],
)


_REGISTRY: dict[str, Persona] = {
    p.name: p for p in (_CFO, _TECH_LEAD, _COMMERCIAL, _NEW_DEV, _EDITOR)
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_personas() -> list[str]:
    """Return the built-in persona names in stable order."""
    return list(_REGISTRY.keys())


def get_persona(name: str) -> Persona:
    """Look up a persona by name. Raises KeyError on unknown name."""
    key = name.strip().lower().replace("-", "_")
    if key not in _REGISTRY:
        raise KeyError(
            f"unknown persona {name!r}. Available: {', '.join(list_personas())}"
        )
    return _REGISTRY[key]


def default_persona_set() -> list[Persona]:
    """The canonical 5-lens set (the one that caught non-overlapping findings
    in the original session). Use this when the caller just says 'run the
    standard review'."""
    return [_CFO, _TECH_LEAD, _COMMERCIAL, _NEW_DEV, _EDITOR]


def build_persona_prompt(persona: Persona, docs_text: str) -> str:
    """Build the LLM prompt for a single persona pass.

    The prompt enforces:
      - The Trust Report machine-parseable header (rules/trust-score.md)
      - Severity tiers from rules/adversarial-review.md
      - The Finding Format (location / what / why / recommendation)
      - No-LGTM rule: at least one finding required, otherwise output
        `TIER=S4 description=REVIEW_INCOMPLETE` as a HALT signal

    The output contract is strict so the consolidator can parse it mechanically.
    """
    questions = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(persona.lens_questions))
    red_flags = (
        "\n".join(f"  - {rf}" for rf in persona.red_flags)
        if persona.red_flags else "  (none declared — use your judgment)"
    )

    return f"""You are reviewing a documentation corpus under the following lens.

ROLE BRIEF ({persona.name}):
{persona.role_brief}

LENS QUESTIONS (apply all):
{questions}

RED FLAGS (any occurrence = S1 BLOCKER regardless of other judgment):
{red_flags}

DOCUMENTATION CORPUS:
<<<DOCS_START>>>
{docs_text}
<<<DOCS_END>>>

OUTPUT CONTRACT (strict — the consolidator parses this mechanically):

First line MUST be a machine-parseable header:
  TRUST_REPORT: SCORE=<0-100> STATUS=<HIGH|MEDIUM|LOW|CRITICAL> EVIDENCE=<N> UNCERTAINTIES=<N>
Then `---` on its own line.

Then your findings, one per block, in this exact format:

FINDING
TIER: <S1|S2|S3|S4>
LOCATION: <file path and/or section heading>
WHAT: <what the issue is — one sentence>
WHY: <why it matters, from YOUR persona's perspective>
RECOMMENDATION: <concrete action to fix or clarify>

Rules:
  - Produce AT LEAST ONE finding. "LGTM" / "no issues" is PROHIBITED. If the
    corpus genuinely looks good from your lens, emit at least one S4 QUESTION
    or S3 SUGGESTION.
  - Do NOT wrap findings in prose or commentary. Just the FINDING blocks.
  - If you cannot review (empty corpus, unreadable, etc.), emit exactly one
    finding with TIER=S4 and WHAT=REVIEW_INCOMPLETE.
"""
