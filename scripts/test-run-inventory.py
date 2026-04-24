#!/usr/bin/env python3
# SCOPE: os-only
"""Build an actionable inventory from a persisted pytest run.

The input is a run directory produced by scripts/pytest-with-summary.sh. The
tool reads JUnit XML plus captured pytest output and writes inventory.md and
inventory.json beside the run artifacts so repair sessions can continue without
rerunning a slow suite just to recover failures, skips, or xfails.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = PROJECT_ROOT / ".cognitive-os" / "reports" / "test-runs" / "latest"


@dataclass(frozen=True)
class TestItem:
    nodeid: str
    outcome: str
    file: str
    test: str
    duration_seconds: float
    message: str = ""
    details: str = ""
    heuristic_tags: list[str] = field(default_factory=list)


def _resolve_run_dir(path: Path) -> Path:
    return path.resolve()


def _split_classname(classname: str) -> tuple[str, list[str]]:
    if not classname:
        return "", []
    parts = classname.split(".")
    module_end = len(parts)
    for idx, part in enumerate(parts):
        if part.startswith("Test") and idx > 0:
            module_end = idx
            break
    module = ".".join(parts[:module_end])
    class_parts = parts[module_end:]
    return module.replace(".", "/") + ".py", class_parts


def _nodeid(classname: str, name: str) -> str:
    file_path, class_parts = _split_classname(classname)
    segments = [file_path, *class_parts, name] if file_path else [*class_parts, name]
    return "::".join(segment for segment in segments if segment)


def _text_from_child(child: ET.Element | None) -> tuple[str, str]:
    if child is None:
        return "", ""
    message = child.attrib.get("message") or child.attrib.get("type") or ""
    details = child.text or ""
    return message.strip(), details.strip()


def _outcome_for_case(case: ET.Element) -> tuple[str, str, str]:
    failure = case.find("failure")
    error = case.find("error")
    skipped = case.find("skipped")
    if failure is not None:
        message, details = _text_from_child(failure)
        return "failed", message, details
    if error is not None:
        message, details = _text_from_child(error)
        return "error", message, details
    if skipped is not None:
        message, details = _text_from_child(skipped)
        combined = f"{message}\n{details}".lower()
        if "xfail" in combined or "expected failure" in combined:
            return "xfailed", message, details
        return "skipped", message, details
    return "passed", "", ""


def _heuristic_tags(item: TestItem) -> list[str]:
    haystack = " ".join(
        [item.nodeid, item.message, item.details]
    ).lower()
    tags: list[str] = []
    patterns: list[tuple[str, str]] = [
        ("timeout", r"\btimeout|timed out|exceeded \d+-second"),
        ("optional-lane", r"docker|service|daemon|not installed|unavailable|credential|api key|localhost|valkey|opik|cognee|mlflow"),
        ("drift", r"\bdrift\b|stale|mismatch|out[- ]?of[- ]?date|catalog|settings|freshness|regenerate"),
        ("aspirational", r"aspirational|dormant|future|placeholder|not implemented|stub|todo"),
        ("false-positive-risk", r"exists|heading|frontmatter|catalog|grep|file_count|count_|structural|shape"),
        ("canonical-portability", r"canonical|projection|driver|harness|codex|claude|\.cognitive-os"),
    ]
    for tag, pattern in patterns:
        if re.search(pattern, haystack):
            tags.append(tag)
    return tags


def parse_junit(junit_path: Path) -> list[TestItem]:
    tree = ET.parse(junit_path)
    root = tree.getroot()
    items: list[TestItem] = []
    for case in root.iter("testcase"):
        classname = case.attrib.get("classname", "")
        name = case.attrib.get("name", "")
        outcome, message, details = _outcome_for_case(case)
        item = TestItem(
            nodeid=_nodeid(classname, name),
            outcome=outcome,
            file=_split_classname(classname)[0],
            test=name,
            duration_seconds=float(case.attrib.get("time", "0") or 0),
            message=message,
            details=details,
        )
        items.append(
            TestItem(
                **{**asdict(item), "heuristic_tags": _heuristic_tags(item)}
            )
        )
    return items


def parse_timeout_fallback(full_output: str) -> list[TestItem]:
    """Extract a synthetic timeout item when pytest died before writing JUnit."""
    if " Timeout " not in full_output and "TimeoutError" not in full_output:
        return []

    matches = re.findall(
        r'File "([^"]+/tests/[^"]+)", line \d+, in ([A-Za-z_][A-Za-z0-9_]*)',
        full_output,
    )
    test_file = "pytest-session"
    test_name = "timeout"
    for file_path, function in reversed(matches):
        if function.startswith("test_"):
            try:
                test_file = str(Path(file_path).resolve().relative_to(PROJECT_ROOT))
            except ValueError:
                test_file = file_path
            test_name = function
            break
    else:
        for file_path, function in reversed(matches):
            try:
                test_file = str(Path(file_path).resolve().relative_to(PROJECT_ROOT))
            except ValueError:
                marker = "/tests/"
                test_file = f"tests/{file_path.split(marker, 1)[1]}" if marker in file_path else file_path
            test_name = function or "timeout"
            break

    message_match = re.search(r"(\+{3,} Timeout \+{3,}.*)", full_output, re.DOTALL)
    message = "pytest run timed out before JUnit XML was completed"
    details = message_match.group(1).strip() if message_match else full_output[-2000:]
    item = TestItem(
        nodeid=f"{test_file}::{test_name}",
        outcome="error",
        file=test_file,
        test=test_name,
        duration_seconds=0.0,
        message=message,
        details=details,
    )
    return [TestItem(**{**asdict(item), "heuristic_tags": _heuristic_tags(item)})]


def _read(path: Path) -> str:
    return path.read_text(errors="replace") if path.exists() else ""


def _parse_metadata(path: Path) -> dict[str, object]:
    metadata: dict[str, object] = {}
    status_lines: list[str] = []
    for line in _read(path).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == "git_status":
            status_lines.append(value)
        elif key not in metadata:
            metadata[key] = value
    if status_lines:
        metadata["git_status"] = status_lines
    return metadata


def _parse_exit_code(path: Path) -> int | None:
    text = _read(path).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _summary_counts(items: Iterable[TestItem]) -> Counter[str]:
    return Counter(item.outcome for item in items)


def _top_slowest(items: list[TestItem], limit: int = 10) -> list[TestItem]:
    return sorted(items, key=lambda item: item.duration_seconds, reverse=True)[:limit]


def _interesting(items: list[TestItem]) -> list[TestItem]:
    return [
        item
        for item in items
        if item.outcome != "passed" or item.heuristic_tags
    ]


def build_inventory(run_dir: Path) -> dict[str, object]:
    run_dir = _resolve_run_dir(run_dir)
    junit = run_dir / "junit.xml"
    full_output = _read(run_dir / "full-output.txt")
    items = parse_junit(junit) if junit.exists() else parse_timeout_fallback(full_output)
    if not items and not junit.exists():
        raise FileNotFoundError(f"JUnit XML not found and no fallback events detected: {junit}")
    counts = _summary_counts(items)
    tag_counts: Counter[str] = Counter()
    for item in items:
        tag_counts.update(item.heuristic_tags)

    return {
        "run_dir": str(run_dir),
        "metadata": _parse_metadata(run_dir / "metadata.txt"),
        "exit_code": _parse_exit_code(run_dir / "exit-code.txt"),
        "counts": dict(sorted(counts.items())),
        "heuristic_tag_counts": dict(sorted(tag_counts.items())),
        "total": len(items),
        "items": [asdict(item) for item in items],
        "interesting": [asdict(item) for item in _interesting(items)],
        "slowest": [asdict(item) for item in _top_slowest(items)],
    }


def _short(text: str, limit: int = 180) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def render_markdown(inventory: dict[str, object]) -> str:
    counts = Counter(inventory.get("counts", {}))
    tag_counts = Counter(inventory.get("heuristic_tag_counts", {}))
    metadata = inventory.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    items = [TestItem(**item) for item in inventory.get("items", [])]  # type: ignore[arg-type]
    interesting = [TestItem(**item) for item in inventory.get("interesting", [])]  # type: ignore[arg-type]
    slowest = [TestItem(**item) for item in inventory.get("slowest", [])]  # type: ignore[arg-type]

    lines = [
        "# Test Run Inventory",
        "",
        f"- Run dir: `{inventory.get('run_dir')}`",
        f"- Exit code: `{inventory.get('exit_code')}`",
        f"- Command: `{metadata.get('args', '')}`",
        f"- Git: `{metadata.get('git_branch', '')}` @ `{metadata.get('git_commit', '')}`",
        f"- Total tests: `{inventory.get('total')}`",
        "",
        "## Outcomes",
        "",
    ]
    for key in ("failed", "error", "skipped", "xfailed", "passed"):
        lines.append(f"- `{key}`: {counts.get(key, 0)}")

    lines.extend(["", "## Heuristic Tags", ""])
    if tag_counts:
        for tag, count in tag_counts.most_common():
            lines.append(f"- `{tag}`: {count}")
    else:
        lines.append("- No heuristic tags detected.")

    lines.extend(["", "## Repair Queue", ""])
    repair_items = [item for item in interesting if item.outcome != "passed"]
    if repair_items:
        for item in repair_items:
            tags = ", ".join(item.heuristic_tags) or "unclassified"
            msg = _short(item.message or item.details)
            lines.append(f"- `{item.outcome}` `{item.nodeid}` [{tags}]")
            if msg:
                lines.append(f"  Evidence: {msg}")
    else:
        lines.append("- No failing, skipped, or xfailed tests in this run.")

    passed_with_tags = [item for item in interesting if item.outcome == "passed"]
    lines.extend(["", "## Passing Tests With Risk Signals", ""])
    if passed_with_tags:
        for item in passed_with_tags[:50]:
            tags = ", ".join(item.heuristic_tags)
            lines.append(f"- `{item.nodeid}` [{tags}]")
        if len(passed_with_tags) > 50:
            lines.append(f"- ... {len(passed_with_tags) - 50} more")
    else:
        lines.append("- No passing tests matched risk heuristics.")

    lines.extend(["", "## Slowest Tests", ""])
    for item in slowest:
        lines.append(f"- `{item.duration_seconds:.3f}s` `{item.nodeid}`")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Heuristic tags are triage hints, not final classifications.",
            "- Final classification still follows `skills/test-contract-repair/SKILL.md` and the repair ledger.",
            "- Use this inventory to choose the next narrow lane before rerunning broad suites.",
            "",
        ]
    )
    return "\n".join(lines)


def write_inventory(run_dir: Path) -> tuple[Path, Path]:
    inventory = build_inventory(run_dir)
    run_dir = _resolve_run_dir(run_dir)
    json_path = run_dir / "inventory.json"
    md_path = run_dir / "inventory.md"
    json_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    md_path.write_text(render_markdown(inventory))
    return md_path, json_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=DEFAULT_RUN_DIR,
        help="pytest-with-summary run directory or latest symlink",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print inventory JSON to stdout instead of writing files only",
    )
    args = parser.parse_args(argv)

    try:
        md_path, json_path = write_inventory(args.run_dir)
        if args.json:
            sys.stdout.write(json_path.read_text())
        else:
            print(f"[test-run-inventory] Markdown: {md_path}")
            print(f"[test-run-inventory] JSON: {json_path}")
        return 0
    except Exception as exc:
        print(f"[test-run-inventory] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
