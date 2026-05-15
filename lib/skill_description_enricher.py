# SCOPE: os-only
"""LLM-driven enrichment of skill ``routing_intents`` (ADR-299).

Background
----------
ADR-296 introduced a multilingual semantic skill matcher. The matcher reads
``description + summary_line + routing_intents`` from each SKILL.md and embeds
them with paraphrase-multilingual-MiniLM-L12-v2. The SkillRouter paper
(arXiv 2603.22455) showed that description-only corpora drop routing accuracy
31–44 points compared to corpora enriched with paraphrased user utterances.

This module fixes the missing-utterance gap by generating, per skill, a small
set of natural-language paraphrases per target language and writing them back
into the SKILL.md frontmatter under ``routing_intents``. Auto-generated
entries are tagged with ``auto_generated: true`` so subsequent runs can
distinguish them from operator-curated intents.

Design contract
---------------
- Vendor-neutral: dispatch goes through :mod:`lib.dispatch` (ADR-049 cascade —
  Qwen primary, Claude fallback) via lazy import. Tests inject a fake
  ``dispatch_fn``.
- Strict JSON output: the LLM is asked for a specific JSON shape; prose or
  malformed responses are logged and skipped (the skill file is NOT touched).
- Idempotent: rerunning skips skills whose existing intents are all
  ``auto_generated: true``; ``--force`` lets operators re-roll.
- Cost-capped: an estimated USD ceiling halts the batch gracefully and saves
  what was completed.
- Kill switch: ``COS_DISABLE_ENRICHMENT=1`` makes the public entry point a
  no-op (returns an empty report).
- Audit trail: every dispatch attempt appends one JSONL line to
  ``.cognitive-os/metrics/skill-enrichment.jsonl``.

Public surface
--------------
- :func:`enrich_skills` — programmatic entry point. Returns
  :class:`EnrichmentReport`.
- :func:`main` — argparse-driven CLI used by ``scripts/cos-skill-description-enrich``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

DEFAULT_LANGUAGES: tuple[str, ...] = ("en", "es", "pt", "de", "fr", "it")
DEFAULT_INTENTS_PER_LANG = 2
DEFAULT_COST_CAP_USD = 5.0
DEFAULT_RATE_LIMIT_PER_MIN = 60

KILL_SWITCH_ENV = "COS_DISABLE_ENRICHMENT"
AUDIT_REL = Path(".cognitive-os") / "metrics" / "skill-enrichment.jsonl"

# Cost-estimate heuristic — used only when the dispatch path returns
# ``cost_usd == 0.0`` (e.g. test injection or self-hosted providers). The
# values are intentionally conservative so cost-cap honours the worst case.
_FALLBACK_COST_USD_PER_CALL = 0.001


@dataclass
class SkillEnrichment:
    """Per-skill enrichment outcome."""

    skill_name: str
    path: str
    wrote_file: bool = False
    intents_added: int = 0
    languages: list[str] = field(default_factory=list)
    skipped_reason: str = ""
    provider_used: str = ""
    cost_usd: float = 0.0
    latency_ms: int = 0


@dataclass
class EnrichmentReport:
    """Summary returned by :func:`enrich_skills`."""

    project_root: str
    dry_run: bool = False
    forced: bool = False
    cost_cap_usd: float = DEFAULT_COST_CAP_USD
    total_cost_usd: float = 0.0
    skills_processed: int = 0
    skills_written: int = 0
    skills_skipped: int = 0
    halted_by_cost_cap: bool = False
    kill_switch_active: bool = False
    results: list[SkillEnrichment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["results"] = [asdict(r) for r in self.results]
        return d


# ---------------------------------------------------------------------------
# Frontmatter I/O
# ---------------------------------------------------------------------------


_FRONTMATTER_BOUNDS_RE = re.compile(r"^---\s*$", re.MULTILINE)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _split_frontmatter(text: str) -> tuple[str, str, str]:
    """Return ``(prefix, frontmatter_yaml, body)``.

    Preserves any leading HTML comment (``<!-- SCOPE: ... -->``) and lines
    before the opening ``---`` as the prefix so the rewrite is byte-faithful.
    """
    lines = text.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            start = i
            break
        if line.strip().startswith("<!--") or line.strip() == "":
            continue
        # Non-blank, non-comment, non-fence content before the fence — no FM.
        return text, "", ""

    if start is None:
        return text, "", ""

    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return text, "", ""

    prefix = "".join(lines[: start + 1])
    fm = "".join(lines[start + 1 : end])
    suffix = "".join(lines[end:])  # includes closing --- line
    return prefix, fm, suffix


def _parse_yaml(yaml_text: str) -> dict[str, Any]:
    import yaml  # type: ignore[import]

    data = yaml.safe_load(yaml_text) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _dump_yaml(data: dict[str, Any]) -> str:
    import yaml  # type: ignore[import]

    # ``sort_keys=False`` preserves authoring order — important so diffs are
    # small and reviewable. ``allow_unicode=True`` keeps Spanish/Portuguese
    # accents intact.
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        width=120,
        default_flow_style=False,
    )


# ---------------------------------------------------------------------------
# Intent merging + classification
# ---------------------------------------------------------------------------


def _is_auto_generated(entry: Any) -> bool:
    return isinstance(entry, dict) and bool(entry.get("auto_generated"))


def _classify_existing_intents(
    intents: list[Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split *intents* into (human_curated, auto_generated) dicts.

    Non-dict / malformed entries are treated as human-curated to err on the
    side of preservation.
    """
    human: list[dict[str, Any]] = []
    auto: list[dict[str, Any]] = []
    for entry in intents or []:
        if not isinstance(entry, dict):
            # Preserve as-is (wrapped) so we don't drop anything.
            human.append({"intent": str(entry), "description": str(entry)})
            continue
        if _is_auto_generated(entry):
            auto.append(entry)
        else:
            human.append(entry)
    return human, auto


# ---------------------------------------------------------------------------
# LLM prompt construction + response parsing
# ---------------------------------------------------------------------------


_LANG_LABEL = {
    "en": "English",
    "es": "Spanish",
    "pt": "Portuguese",
    "de": "German",
    "fr": "French",
    "it": "Italian",
}


def build_prompt(
    skill_name: str,
    description: str,
    invoke_command: str,
    languages: Iterable[str],
    intents_per_lang: int,
) -> str:
    """Construct the LLM prompt for one skill."""
    lang_lines = []
    for lang in languages:
        label = _LANG_LABEL.get(lang, lang)
        lang_lines.append(f'  "{lang}": [ {intents_per_lang} short {label} utterances ]')
    schema = "{\n" + ",\n".join(lang_lines) + "\n}"

    return (
        "You generate natural-language paraphrases that a human user would "
        "type to invoke a Cognitive OS skill. Output STRICT JSON only — no "
        "prose, no markdown fence, no explanations.\n\n"
        f"Skill: {skill_name}\n"
        f"Invoke command (DO NOT include in utterances): {invoke_command}\n"
        f"Description: {description}\n\n"
        f"Produce EXACTLY {intents_per_lang} natural-language utterances per "
        "language. Each utterance must:\n"
        "  - Be a short sentence or question a user would actually type.\n"
        "  - NOT mention slash commands, the skill name, or technical jargon "
        "the user wouldn't know.\n"
        "  - Be distinct from the other utterances in the same language.\n\n"
        "Return JSON with this exact shape (keys are ISO language codes):\n"
        f"{schema}"
    )


def parse_llm_response(
    text: str, languages: Iterable[str], intents_per_lang: int
) -> Optional[dict[str, list[str]]]:
    """Parse strict-JSON response. Returns ``None`` on any malformation."""
    if not text:
        return None
    # Tolerate fenced output by stripping a single ```json ... ``` wrapper.
    stripped = text.strip()
    if stripped.startswith("```"):
        # remove first line + last fence
        parts = stripped.split("\n", 1)
        if len(parts) == 2:
            stripped = parts[1]
        if stripped.endswith("```"):
            stripped = stripped[: -3]
        stripped = stripped.strip()

    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    out: dict[str, list[str]] = {}
    for lang in languages:
        raw = data.get(lang)
        if not isinstance(raw, list) or not raw:
            return None
        cleaned: list[str] = []
        for item in raw:
            if not isinstance(item, str):
                return None
            s = item.strip()
            if s:
                cleaned.append(s)
        if len(cleaned) < intents_per_lang:
            # Under-produced — reject rather than write half a row.
            return None
        out[lang] = cleaned[:intents_per_lang]
    return out


def utterances_to_intent_entries(
    utterances: dict[str, list[str]],
    *,
    skill_name: str,
) -> list[dict[str, Any]]:
    """Flatten ``{lang: [u1, u2]}`` to routing-intents YAML entries."""
    entries: list[dict[str, Any]] = []
    for lang, items in utterances.items():
        for i, u in enumerate(items, start=1):
            entries.append(
                {
                    "intent": f"auto_{skill_name}_{lang}_{i}",
                    "description": u,
                    "confidence": 0.85,
                    "language": lang,
                    "auto_generated": True,
                }
            )
    return entries


# ---------------------------------------------------------------------------
# Dispatch wrapper (lazy import of lib.dispatch)
# ---------------------------------------------------------------------------


def _default_dispatch(prompt: str) -> dict[str, Any]:
    """Thin wrapper around :func:`lib.dispatch.dispatch`.

    Imported lazily so tests can run without pulling the full provider stack.
    Returns a dict with the small subset of fields the enricher needs:
    ``success, text, cost_usd, provider_used, latency_ms``.
    """
    from lib.dispatch import dispatch  # local import — keeps cold path cheap

    res = dispatch(
        prompt,
        task_type="skill_enrichment",
    )
    return {
        "success": bool(res.success),
        "text": res.text or "",
        "cost_usd": float(res.cost_usd or 0.0),
        "provider_used": res.provider_used or "",
        "latency_ms": int(res.latency_ms or 0),
        "error": res.error or "",
    }


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def _audit_path(project_root: Path) -> Path:
    return project_root / AUDIT_REL


def _audit_emit(project_root: Path, record: dict[str, Any]) -> None:
    """Append one JSONL line to the audit file. Best-effort — never raises."""
    try:
        p = _audit_path(project_root)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except (OSError, TypeError, ValueError):
        pass


# ---------------------------------------------------------------------------
# Skill discovery + selection
# ---------------------------------------------------------------------------


def discover_skill_files(project_root: Path) -> list[Path]:
    """Find every SKILL.md under ``skills/`` and ``packages/*/skills/``."""
    paths: list[Path] = []
    for base in (project_root / "skills", *list((project_root / "packages").glob("*/skills"))):
        if base.is_dir():
            paths.extend(base.rglob("SKILL.md"))
    return sorted(set(paths))


def filter_skills(
    all_paths: list[Path], requested: Optional[Iterable[str]]
) -> list[Path]:
    """Restrict *all_paths* to those whose parent dir name matches *requested*."""
    if not requested:
        return all_paths
    wanted = {s.strip() for s in requested if s and s.strip()}
    if not wanted or "all" in wanted:
        return all_paths
    return [p for p in all_paths if p.parent.name in wanted]


# ---------------------------------------------------------------------------
# Core enrichment loop
# ---------------------------------------------------------------------------


def _rate_limit_sleep(rate_per_min: int, last_call_ts: float) -> float:
    """Return wall-clock to sleep so the dispatch rate stays under cap."""
    if rate_per_min <= 0:
        return 0.0
    min_interval = 60.0 / rate_per_min
    delta = time.monotonic() - last_call_ts
    return max(0.0, min_interval - delta)


def enrich_skills(
    project_root: Path | str,
    *,
    skills: Optional[Iterable[str]] = None,
    languages: Optional[Iterable[str]] = None,
    intents_per_lang: int = DEFAULT_INTENTS_PER_LANG,
    dispatch_fn: Optional[Callable[[str], dict[str, Any]]] = None,
    dry_run: bool = False,
    force: bool = False,
    cost_cap_usd: float = DEFAULT_COST_CAP_USD,
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT_PER_MIN,
) -> EnrichmentReport:
    """Enrich SKILL.md ``routing_intents`` with multilingual paraphrases.

    See module docstring for design contract.
    """
    root = Path(project_root).resolve()
    report = EnrichmentReport(
        project_root=str(root),
        dry_run=dry_run,
        forced=force,
        cost_cap_usd=cost_cap_usd,
    )

    if os.environ.get(KILL_SWITCH_ENV, "").strip() == "1":
        report.kill_switch_active = True
        return report

    lang_list = list(languages) if languages else list(DEFAULT_LANGUAGES)
    dispatch_call = dispatch_fn or _default_dispatch

    all_paths = discover_skill_files(root)
    target_paths = filter_skills(all_paths, skills)

    last_call = 0.0
    for path in target_paths:
        result = _enrich_one(
            path=path,
            project_root=root,
            languages=lang_list,
            intents_per_lang=intents_per_lang,
            dispatch_call=dispatch_call,
            dry_run=dry_run,
            force=force,
            audit_emit=lambda rec: _audit_emit(root, rec),
            rate_limit_per_minute=rate_limit_per_minute,
            last_call_ts=last_call,
        )
        report.results.append(result)
        report.skills_processed += 1
        if result.wrote_file:
            report.skills_written += 1
        elif result.skipped_reason:
            report.skills_skipped += 1
        report.total_cost_usd += result.cost_usd
        if result.latency_ms:
            last_call = time.monotonic()

        # Cost-cap halt — graceful stop, partial save.
        if cost_cap_usd > 0 and report.total_cost_usd >= cost_cap_usd:
            report.halted_by_cost_cap = True
            break
        if cost_cap_usd > 0 and report.total_cost_usd >= 0.8 * cost_cap_usd:
            print(
                f"[enrich] WARNING: 80% of cost cap reached "
                f"(${report.total_cost_usd:.4f} / ${cost_cap_usd:.4f})",
                file=sys.stderr,
            )

    return report


def _enrich_one(
    *,
    path: Path,
    project_root: Path,
    languages: list[str],
    intents_per_lang: int,
    dispatch_call: Callable[[str], dict[str, Any]],
    dry_run: bool,
    force: bool,
    audit_emit: Callable[[dict[str, Any]], None],
    rate_limit_per_minute: int,
    last_call_ts: float,
) -> SkillEnrichment:
    """Process exactly one SKILL.md."""
    rel_path = str(path.relative_to(project_root)) if path.is_absolute() else str(path)
    skill_name = path.parent.name
    entry = SkillEnrichment(skill_name=skill_name, path=rel_path)

    try:
        original = _read_text(path)
    except OSError as exc:
        entry.skipped_reason = f"read_error: {exc}"
        return entry

    prefix, fm_yaml, suffix = _split_frontmatter(original)
    if not fm_yaml:
        entry.skipped_reason = "no_frontmatter"
        return entry

    try:
        fm = _parse_yaml(fm_yaml)
    except Exception as exc:  # noqa: BLE001
        entry.skipped_reason = f"yaml_parse_error: {exc}"
        return entry

    description = str(fm.get("description") or "").strip()
    if not description:
        entry.skipped_reason = "missing_description"
        return entry

    invoke_command = str(fm.get("invoke_command") or f"/{skill_name}").strip()

    existing = fm.get("routing_intents") or []
    if not isinstance(existing, list):
        existing = []
    human_curated, auto_generated = _classify_existing_intents(existing)

    # Idempotency: if auto-generated intents already exist and not forced, skip.
    if auto_generated and not force:
        entry.skipped_reason = "already_enriched"
        return entry

    # Rate limit
    delay = _rate_limit_sleep(rate_limit_per_minute, last_call_ts)
    if delay > 0:
        time.sleep(delay)

    prompt = build_prompt(
        skill_name=skill_name,
        description=description,
        invoke_command=invoke_command,
        languages=languages,
        intents_per_lang=intents_per_lang,
    )
    t0 = time.monotonic()
    try:
        resp = dispatch_call(prompt)
    except Exception as exc:  # noqa: BLE001 — dispatch errors must never crash batch
        resp = {"success": False, "error": str(exc)[:300], "text": ""}
    latency_ms = int((time.monotonic() - t0) * 1000)
    if not isinstance(resp, dict):
        resp = {"success": False, "text": "", "error": "dispatch_returned_non_dict"}

    cost = float(resp.get("cost_usd") or 0.0)
    if cost == 0.0 and resp.get("success"):
        cost = _FALLBACK_COST_USD_PER_CALL
    entry.cost_usd = cost
    entry.latency_ms = latency_ms
    entry.provider_used = str(resp.get("provider_used") or "")
    error_text = str(resp.get("error") or "")

    audit_emit(
        {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "skill": skill_name,
            "languages": languages,
            "intents_per_lang": intents_per_lang,
            "success": bool(resp.get("success")),
            "provider": entry.provider_used,
            "cost_usd": cost,
            "latency_ms": latency_ms,
            "error": error_text[:200],
        }
    )

    if not resp.get("success"):
        entry.skipped_reason = f"dispatch_failed: {error_text[:120]}"
        return entry

    parsed = parse_llm_response(str(resp.get("text") or ""), languages, intents_per_lang)
    if parsed is None:
        entry.skipped_reason = "invalid_llm_response"
        return entry

    new_auto_entries = utterances_to_intent_entries(parsed, skill_name=skill_name)
    if not new_auto_entries:
        entry.skipped_reason = "no_entries_produced"
        return entry

    # Merge: keep human-curated first, then new auto-generated entries.
    merged = list(human_curated) + new_auto_entries
    fm["routing_intents"] = merged

    new_yaml = _dump_yaml(fm)
    new_text = f"{prefix}{new_yaml}{suffix}"

    if dry_run:
        print(
            f"[enrich] DRY-RUN {skill_name}: would write "
            f"{len(new_auto_entries)} auto-intents across {len(languages)} languages",
            file=sys.stderr,
        )
        entry.intents_added = len(new_auto_entries)
        entry.languages = list(languages)
        return entry

    try:
        path.write_text(new_text, encoding="utf-8")
    except OSError as exc:
        entry.skipped_reason = f"write_error: {exc}"
        return entry

    entry.wrote_file = True
    entry.intents_added = len(new_auto_entries)
    entry.languages = list(languages)
    return entry


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _split_csv(value: Optional[str]) -> Optional[list[str]]:
    if value is None or value.strip() == "":
        return None
    return [s.strip() for s in value.split(",") if s.strip()]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cos-skill-description-enrich",
        description="Enrich SKILL.md routing_intents with LLM-generated "
        "multilingual user utterances (ADR-299).",
    )
    parser.add_argument(
        "--project-root",
        default=os.environ.get("COGNITIVE_OS_PROJECT_DIR", "."),
        help="Project root (default: $COGNITIVE_OS_PROJECT_DIR or cwd).",
    )
    parser.add_argument(
        "--skills",
        default="all",
        help="Comma-separated skill names or 'all' (default: all).",
    )
    parser.add_argument(
        "--languages",
        default=",".join(DEFAULT_LANGUAGES),
        help=f"Comma-separated ISO codes (default: {','.join(DEFAULT_LANGUAGES)}).",
    )
    parser.add_argument(
        "--intents-per-lang",
        type=int,
        default=DEFAULT_INTENTS_PER_LANG,
        help=f"Utterances per language (default: {DEFAULT_INTENTS_PER_LANG}).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print proposals; write nothing.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing auto-generated intents (human-curated still preserved).",
    )
    parser.add_argument(
        "--cost-cap-usd",
        type=float,
        default=DEFAULT_COST_CAP_USD,
        help=f"Stop when cumulative cost exceeds cap (default: ${DEFAULT_COST_CAP_USD}).",
    )
    parser.add_argument(
        "--rate-limit-per-minute",
        type=int,
        default=DEFAULT_RATE_LIMIT_PER_MIN,
        help=f"Max dispatch calls / minute (default: {DEFAULT_RATE_LIMIT_PER_MIN}).",
    )
    parser.add_argument("--json", action="store_true", help="Print final report as JSON.")
    args = parser.parse_args(argv)

    skills_list = _split_csv(args.skills) if args.skills != "all" else None
    langs = _split_csv(args.languages)

    report = enrich_skills(
        project_root=args.project_root,
        skills=skills_list,
        languages=langs,
        intents_per_lang=args.intents_per_lang,
        dry_run=args.dry_run,
        force=args.force,
        cost_cap_usd=args.cost_cap_usd,
        rate_limit_per_minute=args.rate_limit_per_minute,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(
            f"[enrich] processed={report.skills_processed} "
            f"written={report.skills_written} skipped={report.skills_skipped} "
            f"cost=${report.total_cost_usd:.4f} cap=${report.cost_cap_usd:.4f} "
            f"halted_by_cap={report.halted_by_cost_cap} "
            f"kill_switch={report.kill_switch_active}"
        )
        for r in report.results:
            if r.wrote_file:
                print(f"  WROTE  {r.skill_name}: +{r.intents_added} intents")
            elif r.skipped_reason:
                print(f"  SKIP   {r.skill_name}: {r.skipped_reason}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
