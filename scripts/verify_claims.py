#!/usr/bin/env python3
# SCOPE: os-only
"""Reproduce the numeric claims a report carries, by running their commands.

Contract (ADR-none yet; first executable slice of the `evidencia-ejecutable`
norm): a claim that carries a number travels with the command that reproduces
it. This script extracts those claims from a Markdown report, runs each command
read-only, and compares the observed output against the declared expectation.

It never asks the agent whether it is confident. It runs the command.

Claim block syntax (fenced code block tagged `claim`, body is YAML):

    ```claim
    id: hooks-registrados
    topic: hooks/registrados-en-settings
    claim: settings.json registra 255 hooks
    cmd: grep -c '"command"' .claude/settings.json
    expect: 255
    match: numeric
    ```

Required keys: `id`, `claim`, `cmd`, `expect`.
Optional: `topic` (cross-run alignment key), `match`
(exact|contains|regex|numeric, default exact), `tolerance` (numeric only),
`timeout` (seconds, default 60).

Exit codes: 0 no findings, 1 findings, 2 error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cos_lib.script_io import read_text  # noqa: E402

SCHEMA_VERSION = "verifiable-claim.v1"

CLAIM_BLOCK = re.compile(
    r"^[ \t]*```[ \t]*claim[ \t]*\r?\n(.*?)^[ \t]*```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
REQUIRED_KEYS = ("id", "claim", "cmd", "expect")
VALID_MATCH = ("exact", "contains", "regex", "numeric")
DEFAULT_TIMEOUT = 60

# Read-only by default. The verifier executes text that lives in a document, so
# the denylist is the boundary, not a nicety. `--allow-unsafe` exists for the
# operator who knowingly runs a mutating reproduction in a sandbox.
UNSAFE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?<![\w-])sudo(?![\w-])", "sudo"),
    (r"(?<![\w-])rm(?![\w-])", "rm"),
    (r"(?<![\w-])rmdir(?![\w-])", "rmdir"),
    (r"(?<![\w-])mv(?![\w-])", "mv"),
    (r"(?<![\w-])cp(?![\w-])", "cp"),
    (r"(?<![\w-])mkdir(?![\w-])", "mkdir"),
    (r"(?<![\w-])touch(?![\w-])", "touch"),
    (r"(?<![\w-])truncate(?![\w-])", "truncate"),
    (r"(?<![\w-])tee(?![\w-])", "tee"),
    (r"(?<![\w-])dd(?![\w-])", "dd"),
    (r"(?<![\w-])chmod(?![\w-])", "chmod"),
    (r"(?<![\w-])chown(?![\w-])", "chown"),
    (r"(?<![\w-])kill(?![\w-])", "kill"),
    (r"(?<![\w-])curl(?![\w-])", "network access (curl)"),
    (r"(?<![\w-])wget(?![\w-])", "network access (wget)"),
    (r"(?<![\w-])nc(?![\w-])", "network access (nc)"),
    (r"(?<![\w-])ssh(?![\w-])", "network access (ssh)"),
    (r"\bsed\b[^|;&]*\s-i\b", "sed -i"),
    (r"\bperl\b[^|;&]*\s-i\b", "perl -i"),
    (r"\bgit\s+(add|commit|checkout|switch|reset|clean|push|pull|fetch|stash|rebase|merge|restore|rm|tag|apply|worktree)\b", "mutating git subcommand"),
    (r"\b(pip|pip3|npm|pnpm|yarn|bun|uv|brew|apt|apt-get)\s+(install|add|remove|uninstall|update|upgrade)\b", "package mutation"),
)
# Redirections that only discard output are fine; anything else writes a file.
BENIGN_REDIRECTS = (
    r"2>&1",
    r"&>\s*/dev/null",
    r"2>\s*/dev/null",
    r">\s*/dev/null",
)


@dataclass
class ClaimResult:
    """One extracted claim plus what happened when its command ran."""

    source: str
    block_index: int
    line: int
    id: str = ""
    topic: str = ""
    claim: str = ""
    cmd: str = ""
    expect: str = ""
    match: str = "exact"
    tolerance: float | None = None
    status: str = "MALFORMED"
    observed: str = ""
    stderr: str = ""
    returncode: int | None = None
    reason: str = ""
    key: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def unsafe_reason(cmd: str) -> str:
    """Return why a command is refused under read-only mode, or an empty string."""
    for pattern, label in UNSAFE_PATTERNS:
        if re.search(pattern, cmd):
            return label
    stripped = cmd
    for benign in BENIGN_REDIRECTS:
        stripped = re.sub(benign, " ", stripped)
    # `>>` and a bare `>` that survived the benign sweep write to a file.
    if re.search(r">>?(?!&)", stripped):
        return "output redirection to a file"
    return ""


def _as_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def parse_claims(text: str, source: str) -> list[ClaimResult]:
    """Extract every ```claim block from a Markdown document, in order."""
    results: list[ClaimResult] = []
    for index, match in enumerate(CLAIM_BLOCK.finditer(text)):
        line = text[: match.start()].count("\n") + 1
        result = ClaimResult(source=source, block_index=index, line=line)
        body = match.group(1)
        try:
            payload = yaml.safe_load(body)
        except yaml.YAMLError as exc:
            result.reason = f"invalid YAML in claim block: {exc.__class__.__name__}"
            results.append(result)
            continue
        if not isinstance(payload, dict):
            result.reason = "claim block body must be a YAML mapping"
            results.append(result)
            continue

        missing = [key for key in REQUIRED_KEYS if _as_text(payload.get(key)).strip() == ""]
        result.id = _as_text(payload.get("id")).strip()
        result.topic = _as_text(payload.get("topic")).strip()
        result.claim = _as_text(payload.get("claim")).strip()
        result.cmd = _as_text(payload.get("cmd")).strip()
        result.expect = _as_text(payload.get("expect")).strip()
        result.match = (_as_text(payload.get("match")).strip() or "exact").lower()
        result.key = result.topic or result.id
        if payload.get("tolerance") is not None:
            try:
                result.tolerance = float(payload["tolerance"])
            except (TypeError, ValueError):
                missing.append("tolerance (not a number)")
        if payload.get("timeout") is not None:
            try:
                result.extra["timeout"] = float(payload["timeout"])
            except (TypeError, ValueError):
                missing.append("timeout (not a number)")

        if missing:
            result.reason = "missing or empty required keys: " + ", ".join(sorted(missing))
            results.append(result)
            continue
        if result.match not in VALID_MATCH:
            result.reason = f"unknown match mode {result.match!r} (expected one of {', '.join(VALID_MATCH)})"
            results.append(result)
            continue
        result.status = "PENDING"
        results.append(result)
    return results


def _first_number(text: str) -> float | None:
    found = re.search(r"-?\d+(?:[.,]\d+)?", text.replace(",", "."))
    if not found:
        return None
    try:
        return float(found.group(0))
    except ValueError:
        return None


def compare(result: ClaimResult) -> tuple[bool, str]:
    """Compare observed output against the declared expectation."""
    observed = result.observed.strip()
    expect = result.expect.strip()
    if result.match == "exact":
        return observed == expect, "" if observed == expect else "observed output differs from expect"
    if result.match == "contains":
        ok = expect in observed
        return ok, "" if ok else "expect string not present in observed output"
    if result.match == "regex":
        try:
            ok = re.search(expect, observed) is not None
        except re.error as exc:
            return False, f"invalid regex in expect: {exc}"
        return ok, "" if ok else "expect regex did not match observed output"
    if result.match == "numeric":
        got = _first_number(observed)
        want = _first_number(expect)
        if got is None or want is None:
            return False, "numeric match needs a number in both expect and observed output"
        tolerance = result.tolerance or 0.0
        ok = abs(got - want) <= tolerance
        return ok, "" if ok else f"expected {want:g} (tolerance {tolerance:g}), observed {got:g}"
    return False, f"unknown match mode {result.match!r}"


def run_claim(result: ClaimResult, cwd: Path, allow_unsafe: bool, default_timeout: float) -> ClaimResult:
    """Run one claim's command and score it. Mutates and returns the result."""
    if result.status != "PENDING":
        return result
    reason = "" if allow_unsafe else unsafe_reason(result.cmd)
    if reason:
        result.status = "BLOCKED"
        result.reason = f"refused under read-only mode: {reason}"
        return result

    env = dict(os.environ)
    env.update({"LC_ALL": "C", "LANG": "C", "COS_VERIFY_CLAIMS": "1"})
    timeout = float(result.extra.get("timeout", default_timeout))
    try:
        proc = subprocess.run(  # noqa: S602 - executing the claim's command is the point
            ["bash", "-c", result.cmd],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        result.status = "ERROR"
        result.reason = f"command timed out after {timeout:g}s"
        return result
    except OSError as exc:
        result.status = "ERROR"
        result.reason = f"could not execute command: {exc}"
        return result

    result.observed = proc.stdout.strip()
    result.stderr = proc.stderr.strip()[:2000]
    result.returncode = proc.returncode
    if proc.returncode != 0 and not result.observed:
        result.status = "ERROR"
        result.reason = f"command exited {proc.returncode} with no stdout"
        return result

    ok, why = compare(result)
    result.status = "REPRODUCE" if ok else "MISMATCH"
    result.reason = why
    return result


NUMERIC_LINE = re.compile(r"(?<![\w.])\d[\d.,]*\s*%?")
FENCE = re.compile(r"^[ \t]*```")


def heuristic_numeric_lines(text: str) -> int:
    """Count prose lines that carry a number, outside code blocks.

    Heuristic, and labelled as such everywhere it is reported. It exists only to
    give the claim count a denominator: `0 of 0` and `0 of 47` are very
    different findings.
    """
    count = 0
    in_fence = False
    for raw in text.splitlines():
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = raw.strip()
        if not line or line.startswith(("#", ">", "|---", "---")):
            continue
        if NUMERIC_LINE.search(line):
            count += 1
    return count


def verify_file(path: Path, cwd: Path, allow_unsafe: bool, timeout: float, dry_run: bool) -> dict[str, Any]:
    text = read_text(path)
    claims = parse_claims(text, source=path.as_posix())
    if not dry_run:
        for claim in claims:
            run_claim(claim, cwd=cwd, allow_unsafe=allow_unsafe, default_timeout=timeout)
    counts: dict[str, int] = {}
    for claim in claims:
        counts[claim.status] = counts.get(claim.status, 0) + 1
    return {
        "path": path.as_posix(),
        "claims_found": len(claims),
        "heuristic_numeric_prose_lines": heuristic_numeric_lines(text),
        "counts": counts,
        "claims": [asdict(claim) for claim in claims],
    }


def _print_report(payload: dict[str, Any], verbose: bool) -> None:
    for report in payload["reports"]:
        print(f"\n== {report['path']}")
        print(
            f"   claims with command: {report['claims_found']}"
            f"   (heuristic: {report['heuristic_numeric_prose_lines']} prose lines carry a number)"
        )
        for claim in report["claims"]:
            label = claim["id"] or f"block#{claim['block_index']}"
            print(f"   [{claim['status']:<9}] {label} (line {claim['line']})")
            if claim["claim"]:
                print(f"       claim : {claim['claim']}")
            if claim["cmd"]:
                print(f"       cmd   : {claim['cmd']}")
            if claim["status"] not in ("REPRODUCE", "PENDING"):
                print(f"       expect: {claim['expect']!r}")
                print(f"       got   : {claim['observed']!r}")
                print(f"       why   : {claim['reason']}")
            elif verbose:
                print(f"       got   : {claim['observed']!r}")
    totals = payload["totals"]
    print("\n-- totals --")
    print(f"   files              : {totals['files']}")
    print(f"   claims with command: {totals['claims_found']}")
    print(f"   reproduce          : {totals['reproduce']}")
    print(f"   mismatch           : {totals['mismatch']}")
    print(f"   error              : {totals['error']}")
    print(f"   blocked            : {totals['blocked']}")
    print(f"   malformed          : {totals['malformed']}")
    print(f"   heuristic numeric prose lines (NOT claims): {totals['heuristic_numeric_prose_lines']}")
    if totals["claims_found"] == 0:
        print(
            "\n   NO_CLAIMS: no file carried a single ```claim block. Under the"
            "\n   executable-evidence norm that is the finding, not a parser bug."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce a report's verifiable claims by running their commands.")
    parser.add_argument("paths", nargs="+", help="Markdown reports to verify")
    parser.add_argument("--project-dir", default=str(ROOT), help="working directory for claim commands")
    parser.add_argument("--json", dest="json_out", help="write the machine-readable run to this path")
    parser.add_argument("--allow-unsafe", action="store_true", help="run commands the read-only denylist refuses")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="per-command timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="extract claims without running anything")
    parser.add_argument("--require-claims", action="store_true", help="treat a report with zero claims as a finding")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    cwd = Path(args.project_dir).resolve()
    if not cwd.is_dir():
        print(f"error: project dir not found: {cwd}", file=sys.stderr)
        return 2

    reports: list[dict[str, Any]] = []
    for raw in args.paths:
        path = Path(raw)
        if not path.is_file():
            print(f"error: report not found: {path}", file=sys.stderr)
            return 2
        reports.append(verify_file(path, cwd, args.allow_unsafe, args.timeout, args.dry_run))

    def total(status: str) -> int:
        return sum(report["counts"].get(status, 0) for report in reports)

    totals = {
        "files": len(reports),
        "claims_found": sum(report["claims_found"] for report in reports),
        "reproduce": total("REPRODUCE"),
        "mismatch": total("MISMATCH"),
        "error": total("ERROR"),
        "blocked": total("BLOCKED"),
        "malformed": total("MALFORMED"),
        "pending": total("PENDING"),
        "heuristic_numeric_prose_lines": sum(report["heuristic_numeric_prose_lines"] for report in reports),
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "project_dir": cwd.as_posix(),
        "dry_run": args.dry_run,
        "totals": totals,
        "reports": reports,
    }

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    _print_report(payload, args.verbose)

    if args.dry_run:
        return 0
    findings = totals["mismatch"] + totals["error"] + totals["blocked"] + totals["malformed"]
    if args.require_claims and totals["claims_found"] == 0:
        findings += 1
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
