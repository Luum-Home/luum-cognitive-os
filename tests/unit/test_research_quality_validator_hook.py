# SCOPE: os-only
"""Tests for hooks/research-quality-validator.sh (ADR-175).

The hook is non-blocking and writes a JSONL log entry per scored report.
We invoke the hook with synthetic stdin payloads and assert:

* good report -> entry logged, exit 0, no warning on stderr.
* poor report -> entry logged, exit 0, WARNING string on stderr.
* killswitch env -> hook short-circuits with exit 0 and no log.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "research-quality-validator.sh"


HIGH_QUALITY_REPORT = """# Synthetic deep audit

```bash
grep -c CanonicalEvent lib/harness_adapter/base.py
# 11
wc -l lib/providers/__init__.py
# 65
```

| Dim | A | B | Verdict |
|---|---|---|---|
| Events | a/file.py:23-100 wires 11 events | b/file.py:5-50 wires 10 events | IGUAL |
| Providers | c/file.py:1-65 lists 7 providers | d/file.py:5-200 lists 22 providers | B MEJOR |
| Hooks | e/foo.sh:10-40 has 9 hooks | f/bar.sh:1-100 has 10 hooks | IGUAL |

**Verdict**: the comparison is balanced. Confidence HIGH.

**Finding**: providers differ by an order of magnitude. Confidence HIGH.

**Recommendation**: borrow ProviderProfile pattern. Confidence MEDIUM.

## Uncertainties

- Heuristic regex may miss subtle semantic evidence.
- Threshold chosen by convention.
- Provider count could be stale if registry changes.
"""

LOW_QUALITY_REPORT = """# Synthetic shallow audit

| Dim | A | B | Verdict |
|---|---|---|---|
| Events | scripts/foo.sh:10-50 wires several events | several events roughly | IGUAL |
| Providers | lib/bar.py:1-20 has 7 providers approximately | various providers around 4 | B MEJOR |
"""


def _run_hook(tmp_path: Path, file_path: Path, env_extra=None) -> subprocess.CompletedProcess:
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(file_path)},
    }
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload).encode(),
        capture_output=True,
        env=env,
        timeout=10,
    )


def _make_report(tmp_path: Path, name: str, content: str) -> Path:
    reports_dir = tmp_path / "docs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    fpath = reports_dir / name
    fpath.write_text(content, encoding="utf-8")
    return fpath


def _read_log(tmp_path: Path):
    log = tmp_path / ".cognitive-os" / "metrics" / "research-quality.jsonl"
    if not log.exists():
        return []
    return [json.loads(l) for l in log.read_text().splitlines() if l.strip()]


def test_high_quality_no_warning(tmp_path):
    report = _make_report(tmp_path, "good.md", HIGH_QUALITY_REPORT)
    res = _run_hook(tmp_path, report)
    assert res.returncode == 0
    log = _read_log(tmp_path)
    assert len(log) == 1
    assert log[0]["overall_score"] >= 70
    # No WARNING for good reports.
    assert b"WARNING [research-quality]" not in res.stderr


def test_low_quality_emits_warning(tmp_path):
    report = _make_report(tmp_path, "bad.md", LOW_QUALITY_REPORT)
    res = _run_hook(tmp_path, report)
    assert res.returncode == 0
    log = _read_log(tmp_path)
    assert len(log) == 1
    assert log[0]["overall_score"] < 70
    assert b"WARNING [research-quality]" in res.stderr


def test_killswitch_skips(tmp_path):
    report = _make_report(tmp_path, "any.md", LOW_QUALITY_REPORT)
    res = _run_hook(tmp_path, report, env_extra={"DISABLE_HOOK_RESEARCH_QUALITY_VALIDATOR": "1"})
    assert res.returncode == 0
    assert _read_log(tmp_path) == []


def test_non_report_path_ignored(tmp_path):
    other = tmp_path / "src" / "foo.md"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_text(LOW_QUALITY_REPORT, encoding="utf-8")
    res = _run_hook(tmp_path, other)
    assert res.returncode == 0
    assert _read_log(tmp_path) == []
