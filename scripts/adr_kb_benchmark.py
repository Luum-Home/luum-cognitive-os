#!/usr/bin/env python3
"""ADR knowledge-pilot benchmark harness (sdd/adr-knowledge-pilot).

Measures injected-context token cost per question, per retrieval "arm", using
the same tokenizer ADR-186 already uses in production
(`cos_lib.context_budget.count_tokens`). This is a paired benchmark: each question
in the frozen fixture is scored under one or more arms and results are written
as one JSON object per line (JSONL) plus an optional summary report.

Arms
----
BEFORE
    Raw ADR file(s) named by the question's ``gold_adr`` list are read
    directly from ``docs/02-Decisions/adrs/`` and concatenated. This is the
    context a naive/pre-synthesis retrieval would inject today. This arm can
    run standalone, right now, with no other pipeline changes.

AFTER
    The ADR-NNN.synthesis.md page for each gold ADR (produced by the Tier-1
    synthesis authoring task) plus the relevant Tier-2 index node. This arm
    requires the synthesis pages to exist AND the `context_injector.py`
    `_search_adrs` path-remap helper to be wired in behind
    `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` per the design doc
    (sdd/adr-knowledge-pilot/design). Running this arm before that landing is
    a hard user-visible error, not a silent skip, so a partial/misleading
    "AFTER" result never lands in the metrics stream by accident.

Both arms consume the same frozen question fixture (see
``docs/00-MOCs/adr-kb-benchmark-questions.md`` for the human-readable list, or
pass an equivalent JSONL fixture with ``--questions``) so results are directly
paired/comparable question-by-question.

Usage
-----
    # BEFORE arm only (works today):
    python3 scripts/adr_kb_benchmark.py --arm before \\
        --questions docs/00-MOCs/adr-kb-benchmark-questions.jsonl \\
        --json-out .cognitive-os/metrics/adr-kb-benchmark-before.jsonl \\
        --report

    # AFTER arm (only once synthesis pages + remap exist):
    python3 scripts/adr_kb_benchmark.py --arm after \\
        --questions docs/00-MOCs/adr-kb-benchmark-questions.jsonl \\
        --json-out .cognitive-os/metrics/adr-kb-benchmark-after.jsonl --report

Fixture format (JSONL, one row per question)
---------------------------------------------
    {"id": "q01", "question": "...", "gold_adr": ["ADR-049"], "category": "decision"}

``gold_adr`` may reference bare numbers (``"049"``, ``"28"``) or full slugs
(``"ADR-049-llm-gateway-selection-and-overflow-providers"``); this script
resolves either form to the actual file(s) on disk.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = REPO_ROOT / "docs" / "02-Decisions" / "adrs"

sys.path.insert(0, str(REPO_ROOT))
from cos_lib.context_budget import count_tokens  # noqa: E402

ARMS = ("before", "after")


class BenchmarkError(RuntimeError):
    """Raised for hard, user-visible harness failures (never swallowed)."""


@dataclass(frozen=True)
class QuestionResult:
    id: str
    question: str
    arm: str
    gold_adr: list[str]
    resolved_files: list[str]
    missing_files: list[str]
    tokens_estimate: int
    chars: int
    category: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_questions(path: Path) -> list[dict[str, Any]]:
    """Load the frozen question fixture (JSONL, one question object per line)."""
    if not path.is_file():
        raise BenchmarkError(f"question fixture not found: {path}")
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise BenchmarkError(f"{path}:{lineno}: invalid JSON — {exc}") from exc
            for required in ("id", "question", "gold_adr"):
                if required not in row:
                    raise BenchmarkError(f"{path}:{lineno}: missing required field '{required}'")
            rows.append(row)
    if not rows:
        raise BenchmarkError(f"question fixture is empty: {path}")
    return rows


def _normalize_adr_token(token: str) -> str:
    token = token.strip()
    if not token:
        return token
    if not token.upper().startswith("ADR-"):
        # bare number like "49" or "049" or "28a"
        digits = "".join(ch for ch in token if ch.isdigit())
        suffix = "".join(ch for ch in token if ch.isalpha())
        if digits:
            token = f"ADR-{int(digits):03d}{suffix}"
    return token


def resolve_adr_files(gold_adr: list[str], adr_dir: Path = ADR_DIR) -> tuple[list[Path], list[str]]:
    """Resolve gold_adr entries (bare numbers or full slugs) to files on disk.

    Returns (resolved_paths, missing_identifiers).
    """
    resolved: list[Path] = []
    missing: list[str] = []
    for raw_id in gold_adr:
        normalized = _normalize_adr_token(raw_id)
        # Exact filename match first (e.g. "ADR-028.md" or full slug given).
        candidate = adr_dir / normalized
        if candidate.suffix != ".md":
            candidate = adr_dir / f"{normalized}.md"
        if candidate.is_file():
            resolved.append(candidate)
            continue
        # Fall back to glob on the ADR-NNN prefix (slug unknown).
        prefix = normalized.split("-")[0] + "-" + normalized.split("-")[1] if "-" in normalized else normalized
        matches = sorted(adr_dir.glob(f"{prefix}*.md"))
        # Exclude synthesis pages from the BEFORE arm's raw-file resolution.
        matches = [m for m in matches if not m.name.endswith(".synthesis.md")]
        if matches:
            resolved.append(matches[0])
        else:
            missing.append(raw_id)
    return resolved, missing


def resolve_synthesis_files(gold_adr: list[str], adr_dir: Path = ADR_DIR) -> tuple[list[Path], list[str]]:
    """Resolve gold_adr entries to their ADR-NNN.synthesis.md page, if present."""
    resolved: list[Path] = []
    missing: list[str] = []
    for raw_id in gold_adr:
        normalized = _normalize_adr_token(raw_id)
        prefix = normalized.split("-")[0] + "-" + normalized.split("-")[1] if "-" in normalized else normalized
        candidate = adr_dir / f"{prefix}.synthesis.md"
        if candidate.is_file():
            resolved.append(candidate)
        else:
            missing.append(raw_id)
    return resolved, missing


def run_before_arm(questions: list[dict[str, Any]], adr_dir: Path = ADR_DIR) -> list[QuestionResult]:
    """Run the BEFORE arm: raw ADR file(s) as injected context, tokenized."""
    results: list[QuestionResult] = []
    for row in questions:
        gold_adr = list(row["gold_adr"])
        files, missing = resolve_adr_files(gold_adr, adr_dir)
        if not files:
            raise BenchmarkError(
                f"question '{row['id']}': no raw ADR file resolved for gold_adr={gold_adr} "
                f"(missing={missing}). Fix the fixture or the ADR path."
            )
        text = "\n\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files)
        tokens = count_tokens(text)
        results.append(
            QuestionResult(
                id=row["id"],
                question=row["question"],
                arm="before",
                gold_adr=gold_adr,
                resolved_files=[str(p.relative_to(REPO_ROOT)) for p in files],
                missing_files=missing,
                tokens_estimate=tokens,
                chars=len(text),
                category=row.get("category", ""),
            )
        )
    return results


def run_after_arm(questions: list[dict[str, Any]], adr_dir: Path = ADR_DIR) -> list[QuestionResult]:
    """Run the AFTER arm: synthesis page(s) + Tier-2 index node as injected context.

    Hard-fails (does not silently fall back to raw ADRs) if synthesis pages are
    missing, since a silent fallback would make AFTER look identical to BEFORE
    and corrupt the paired comparison. This arm additionally requires
    `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`-gated wiring of the context_injector
    remap per the design doc — the harness itself does not check that env var
    (it does not touch context_injector.py), but AFTER numbers are only valid
    once that wiring has actually landed and been exercised end-to-end.
    """
    results: list[QuestionResult] = []
    for row in questions:
        gold_adr = list(row["gold_adr"])
        files, missing = resolve_synthesis_files(gold_adr, adr_dir)
        if missing:
            raise BenchmarkError(
                f"AFTER arm: question '{row['id']}' is missing synthesis page(s) for "
                f"{missing}. AFTER arm requires all Tier-1 synthesis pages to exist — "
                "run the synthesis authoring task first, or run --arm before."
            )
        text = "\n\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files)
        tokens = count_tokens(text)
        results.append(
            QuestionResult(
                id=row["id"],
                question=row["question"],
                arm="after",
                gold_adr=gold_adr,
                resolved_files=[str(p.relative_to(REPO_ROOT)) for p in files],
                missing_files=missing,
                tokens_estimate=tokens,
                chars=len(text),
                category=row.get("category", ""),
            )
        )
    return results


def summarize(results: list[QuestionResult]) -> dict[str, Any]:
    if not results:
        return {"count": 0}
    tokens = sorted(r.tokens_estimate for r in results)
    n = len(tokens)
    p95_idx = min(n - 1, max(0, int(round(0.95 * (n - 1)))))
    return {
        "count": n,
        "median_tokens": statistics.median(tokens),
        "mean_tokens": round(statistics.mean(tokens), 2),
        "p95_tokens": tokens[p95_idx],
        "min_tokens": tokens[0],
        "max_tokens": tokens[-1],
        "questions_with_missing_files": sum(1 for r in results if r.missing_files),
    }


def write_jsonl(results: list[QuestionResult], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--arm",
        choices=ARMS,
        required=True,
        help="Which retrieval arm to run. 'after' hard-fails until synthesis pages exist.",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=REPO_ROOT / "docs" / "00-MOCs" / "adr-kb-benchmark-questions.jsonl",
        help="Path to the frozen question fixture (JSONL).",
    )
    parser.add_argument(
        "--adr-dir",
        type=Path,
        default=ADR_DIR,
        help="Directory containing ADR-*.md files (default: docs/02-Decisions/adrs).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write per-question JSONL results to this path.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print a summary report (median/p95/mean tokens) to stdout.",
    )
    args = parser.parse_args(argv)

    questions = load_questions(args.questions)

    started = time.time()
    if args.arm == "before":
        results = run_before_arm(questions, args.adr_dir)
    else:
        results = run_after_arm(questions, args.adr_dir)
    elapsed = time.time() - started

    if args.json_out:
        write_jsonl(results, args.json_out)

    summary = summarize(results)
    summary["arm"] = args.arm
    summary["elapsed_seconds"] = round(elapsed, 3)
    summary["fixture"] = str(args.questions)

    if args.report or not args.json_out:
        print(json.dumps(summary, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
