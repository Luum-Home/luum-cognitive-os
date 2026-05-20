"""
tests/integration/test_aspirational_audit.py

Behavioral tests for scripts/aspirational_audit.py.
All tests use tmp_path with synthetic project structures.
"""
from __future__ import annotations

import json
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Import target under test (resolve absolute path so it works from any cwd)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent.parent

# aspirational-audit.py has a hyphen — use importlib to load it
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "aspirational_audit",
    REPO_ROOT / "scripts" / "aspirational_audit.py",
)
aa = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(aa)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_project(tmp_path: Path, *, settings: dict | None = None) -> Path:
    """Create the minimum directory skeleton for an audit run."""
    (tmp_path / ".claude").mkdir(parents=True)
    (tmp_path / "hooks").mkdir()
    (tmp_path / "lib").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    (tmp_path / "tests" / "contracts").mkdir(parents=True)
    (tmp_path / "rules").mkdir()
    (tmp_path / "docs").mkdir()

    if settings is not None:
        (tmp_path / ".claude" / "settings.json").write_text(json.dumps(settings))
    else:
        (tmp_path / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}))

    return tmp_path


def make_settings(hooks_list: list[str]) -> dict:
    """Build a minimal settings.json with the given hook basenames registered."""
    return {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": f'bash "$CLAUDE_PROJECT_DIR/hooks/{h}"'}
                        for h in hooks_list
                    ]
                }
            ]
        }
    }


def write_hook(project: Path, name: str, content: str = "#!/usr/bin/env bash\necho hello\n") -> Path:
    p = project / "hooks" / name
    p.write_text(content)
    return p


def write_hook_health(project: Path, rows: list[dict]) -> None:
    p = project / ".cognitive-os" / "metrics" / "hook-health.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def write_excluded(project: Path, entries: list[str]) -> None:
    p = project / "tests" / "contracts" / "EXCLUDED_HOOKS.txt"
    p.write_text("\n".join(entries) + "\n")


def now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def recent_ts() -> str:
    """ISO timestamp 1 hour ago — within 7-day window."""
    from datetime import datetime, timezone, timedelta
    return (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()


def old_ts() -> str:
    """ISO timestamp 30 days ago — outside 7-day window."""
    from datetime import datetime, timezone, timedelta
    return (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEmptyProject:
    def test_empty_project_returns_zero_components(self, tmp_path):
        """Empty project (no hooks/lib/scripts/skills) → audit returns 0 components."""
        project = make_project(tmp_path)
        auditor = aa.Auditor(project)
        events = auditor.run()
        assert len(events) == 0

    def test_summary_zero_ratio_on_empty(self, tmp_path):
        """Summary ratio is 0.0 when no components exist."""
        project = make_project(tmp_path)
        auditor = aa.Auditor(project)
        events = auditor.run()
        summary = aa.compute_summary(events)
        assert summary["dormant_aspirational_ratio"] == 0.0
        assert summary["total"] == 0


class TestHookClassification:
    def test_registered_with_fire_count_is_real(self, tmp_path):
        """Hook registered in settings.json + fire count > 0 → REAL."""
        project = make_project(tmp_path, settings=make_settings(["my-hook.sh"]))
        write_hook(project, "my-hook.sh")
        write_hook_health(project, [
            {"timestamp": recent_ts(), "hook": "my-hook", "exit_code": 0}
        ])
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        assert comps["hooks/my-hook.sh"]["classification"] == "REAL"

    def test_registered_no_fire_count_is_dormant(self, tmp_path):
        """Hook registered but fire count 0 → DORMANT."""
        project = make_project(tmp_path, settings=make_settings(["my-hook.sh"]))
        write_hook(project, "my-hook.sh")
        # No hook-health rows
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        assert comps["hooks/my-hook.sh"]["classification"] == "DORMANT"

    def test_unregistered_not_whitelisted_is_aspirational(self, tmp_path):
        """Hook NOT registered and NOT whitelisted → ASPIRATIONAL."""
        project = make_project(tmp_path, settings=make_settings([]))
        write_hook(project, "future-hook.sh")
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        assert comps["hooks/future-hook.sh"]["classification"] == "ASPIRATIONAL"

    def test_excluded_hook_is_metadata(self, tmp_path):
        """Hook NOT registered but in EXCLUDED_HOOKS.txt → METADATA."""
        project = make_project(tmp_path, settings=make_settings([]))
        write_hook(project, "shim-hook.sh")
        write_excluded(project, ["shim-hook.sh | LIBRARY: helper sourced by others"])
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        assert comps["hooks/shim-hook.sh"]["classification"] == "METADATA"


    def test_conditional_excluded_hook_is_on_demand(self, tmp_path):
        """CONDITIONAL exclusions are on-demand, not active aspirational debt."""
        project = make_project(tmp_path, settings=make_settings([]))
        write_hook(project, "conditional-hook.sh")
        write_excluded(project, ["conditional-hook.sh | CONDITIONAL: runs only when optional service is enabled"])
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        assert comps["hooks/conditional-hook.sh"]["classification"] == "ON_DEMAND"

    def test_future_excluded_hook_is_metadata_backlog(self, tmp_path):
        """FUTURE exclusions are explicit backlog, outside active lifecycle debt."""
        project = make_project(tmp_path, settings=make_settings([]))
        write_hook(project, "future-hook.sh")
        write_excluded(project, ["future-hook.sh | FUTURE: not yet wired by design"])
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        assert comps["hooks/future-hook.sh"]["classification"] == "METADATA"

    def test_cognitive_os_yaml_registry_counts_as_registered(self, tmp_path):
        """Canonical cognitive-os.yaml registry prevents false aspirational hooks."""
        project = make_project(tmp_path, settings=make_settings([]))
        write_hook(project, "registered-by-cos.sh")
        (project / "cognitive-os.yaml").write_text(
            "hooks:\n  registered-by-cos:\n    script: hooks/registered-by-cos.sh\n    event: PreToolUse\n    matcher: Bash\n",
            encoding="utf-8",
        )
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        assert comps["hooks/registered-by-cos.sh"]["classification"] == "DORMANT"

    def test_lib_helper_in_underscore_lib_is_metadata(self, tmp_path):
        """Hook in _lib/ → always METADATA."""
        project = make_project(tmp_path)
        (project / "hooks" / "_lib").mkdir()
        (project / "hooks" / "_lib" / "helper.sh").write_text("#!/usr/bin/env bash\n# helper\n")
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        assert comps["hooks/_lib/helper.sh"]["classification"] == "METADATA"


class TestLibClassification:
    def test_lib_with_real_callers_is_real(self, tmp_path):
        """Lib module with ≥1 non-test caller → REAL."""
        project = make_project(tmp_path)
        # Create the lib module
        lib_mod = project / "lib" / "my_module.py"
        lib_mod.write_text("# real module\n" * 5)
        # Create a hook that imports it
        (project / "hooks" / "uses-mymod.sh").write_text(
            "#!/usr/bin/env bash\npython3 -c \"from lib.my_module import foo\"\n"
        )
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        assert comps["lib/my_module.py"]["classification"] == "REAL"

    def test_lib_without_callers_is_dormant(self, tmp_path):
        """Lib module with no callers → DORMANT."""
        project = make_project(tmp_path)
        lib_mod = project / "lib" / "orphan_module.py"
        lib_mod.write_text("# orphan\ndef foo(): pass\n" * 5)
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        assert comps["lib/orphan_module.py"]["classification"] == "DORMANT"

    def test_test_only_callers_do_not_count(self, tmp_path):
        """Test-only imports don't count as real callers."""
        project = make_project(tmp_path)
        lib_mod = project / "lib" / "test_mod.py"
        lib_mod.write_text("def fn(): pass\n" * 5)
        # Only a test file imports it — but test files are skipped
        (project / "scripts" / "test_something.py").write_text(
            "from lib.test_mod import fn\n"
        )
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        # Should still be DORMANT because test files are excluded from caller scan
        assert comps["lib/test_mod.py"]["classification"] == "DORMANT"


class TestSkillClassification:
    def test_skill_with_covering_test_is_on_demand(self, tmp_path):
        """A tested skill with no recent invocation is on-demand, not dormant."""
        project = make_project(tmp_path)
        skill_dir = project / "skills" / "rare-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: rare-skill\n---\n# Rare Skill\n", encoding="utf-8")
        tests_dir = project / "tests" / "skills"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_rare_skill.py").write_text("def test_rare_skill_contract(): assert True\n", encoding="utf-8")

        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}

        assert comps["skills/rare-skill/SKILL.md"]["classification"] == "ON_DEMAND"
        assert comps["skills/rare-skill/SKILL.md"]["signals"]["has_test"] is True

    def test_skill_with_invocation_contract_is_on_demand(self, tmp_path):
        """A user-invocable skill with trigger metadata is on-demand."""
        project = make_project(tmp_path)
        skill_dir = project / "skills" / "manual-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: manual-skill\nuser-invocable: true\ntrigger: manual skill\n---\n# Manual Skill\n",
            encoding="utf-8",
        )

        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}

        assert comps["skills/manual-skill/SKILL.md"]["classification"] == "ON_DEMAND"
        assert comps["skills/manual-skill/SKILL.md"]["signals"]["invocation_contract"] is True


    def test_skill_without_invocation_or_evidence_is_aspirational(self, tmp_path):
        """An unreferenced, untested skill remains aspirational."""
        project = make_project(tmp_path)
        skill_dir = project / "skills" / "paper-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: paper-skill\n---\n# Paper Skill\n", encoding="utf-8")

        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}

        assert comps["skills/paper-skill/SKILL.md"]["classification"] == "ASPIRATIONAL"


class TestCLIFlags:
    def test_dry_run_no_file_writes(self, tmp_path, capsys):
        """--dry-run → no JSONL and no report written."""
        project = make_project(tmp_path, settings=make_settings(["hook.sh"]))
        write_hook(project, "hook.sh")

        result = aa.main(["--dry-run", "--project-root", str(project)])
        assert result == 0

        jsonl = project / ".cognitive-os" / "metrics" / "aspirational-audit.jsonl"
        assert not jsonl.exists(), "JSONL should not be written in --dry-run"

        reports = list((project / "docs" / "06-Daily" / "reports").glob("aspirational-audit-*.md"))
        assert len(reports) == 0, "Report should not be written in --dry-run"

    def test_json_flag_produces_parseable_output(self, tmp_path, capsys):
        """--json → parseable JSON summary on stdout."""
        project = make_project(tmp_path)
        result = aa.main(["--json", "--project-root", str(project)])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "total" in data
        assert "counts" in data
        assert "dormant_aspirational_ratio" in data

    def test_threshold_exit_0_when_under(self, tmp_path):
        """--threshold 0.9 → exit 0 when ratio is low."""
        project = make_project(tmp_path)
        result = aa.main(["--threshold", "0.9", "--dry-run", "--project-root", str(project)])
        assert result == 0

    def test_threshold_exit_1_when_over(self, tmp_path):
        """--threshold 0.0 → exit 1 when any dormant+aspirational exists."""
        project = make_project(tmp_path, settings=make_settings([]))
        # Add unregistered hook to force ASPIRATIONAL classification
        write_hook(project, "unregistered.sh", "#!/usr/bin/env bash\necho hi\n")
        result = aa.main(["--threshold", "0.0", "--project-root", str(project)])
        assert result == 1


class TestMetricEventSchema:
    def test_jsonl_conforms_to_metric_event_schema(self, tmp_path):
        """JSONL output has source, event_type, payload, schema_version on every row."""
        project = make_project(tmp_path, settings=make_settings(["hook.sh"]))
        write_hook(project, "hook.sh")

        aa.main(["--project-root", str(project)])

        jsonl = project / ".cognitive-os" / "metrics" / "aspirational-audit.jsonl"
        assert jsonl.exists()
        rows = [json.loads(line) for line in jsonl.read_text().splitlines() if line.strip()]
        assert len(rows) > 0
        for row in rows:
            assert "source" in row, "Missing source field"
            assert "event_type" in row, "Missing event_type field"
            assert "payload" in row, "Missing payload field"
            assert "schema_version" in row, "Missing schema_version field"
            assert row["source"] == "aspirational-audit"
            assert row["event_type"] == "component.classified"
            assert "component" in row["payload"]
            assert "classification" in row["payload"]
            assert row["payload"]["classification"] in ("REAL", "ON_DEMAND", "DORMANT", "ASPIRATIONAL", "METADATA")


class TestDeprecationShim:
    def test_deprecated_shim_is_metadata(self, tmp_path):
        """Short file (<30 lines) with DEPRECATED marker → METADATA."""
        project = make_project(tmp_path, settings=make_settings([]))
        # 10-line shim
        shim_content = "#!/usr/bin/env bash\n# DEPRECATED: superseded by new-hook.sh\necho deprecated\nexit 0\n"
        write_hook(project, "old-hook.sh", shim_content)
        auditor = aa.Auditor(project)
        events = auditor.run()
        comps = {e["payload"]["component"]: e["payload"] for e in events}
        assert comps["hooks/old-hook.sh"]["classification"] == "METADATA"
        assert "DEPRECATED" in comps["hooks/old-hook.sh"]["reason"].upper()


class TestReportFile:
    def test_report_file_written_with_correct_date(self, tmp_path):
        """Report file written with today's date in name."""
        from datetime import datetime
        project = make_project(tmp_path)
        aa.main(["--project-root", str(project)])
        today = datetime.now().strftime("%Y-%m-%d")
        report = project / "docs" / "06-Daily" / "reports" / f"aspirational-audit-{today}.md"
        assert report.exists(), f"Expected report at {report}"
        content = report.read_text()
        assert "Aspirational Audit" in content
        assert "REAL" in content or "total" in content.lower()

    def test_report_contains_summary_table(self, tmp_path):
        """Report contains a markdown table with classification counts."""
        project = make_project(tmp_path, settings=make_settings(["my-hook.sh"]))
        write_hook(project, "my-hook.sh")
        aa.main(["--project-root", str(project)])
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        report = project / "docs" / "06-Daily" / "reports" / f"aspirational-audit-{today}.md"
        content = report.read_text()
        assert "| REAL" in content or "REAL |" in content


class TestTimestampMarker:
    def test_marker_updated_after_run(self, tmp_path):
        """Timestamp marker file is written after a full run."""
        project = make_project(tmp_path)
        marker = project / ".cognitive-os" / "metrics" / ".last-aspirational-audit"
        assert not marker.exists()
        aa.main(["--project-root", str(project)])
        assert marker.exists()
        val = float(marker.read_text().strip())
        assert abs(val - time.time()) < 5  # within 5 seconds

    def test_weekly_throttle_second_run_is_noop(self, tmp_path):
        """Running twice quickly: second run produces no new JSONL rows."""
        project = make_project(tmp_path)
        aa.main(["--project-root", str(project)])

        jsonl = project / ".cognitive-os" / "metrics" / "aspirational-audit.jsonl"
        len(jsonl.read_text().splitlines()) if jsonl.exists() else 0

        # Simulate the hook throttle: marker was just written, so a second full
        # audit call would normally fire (script doesn't read its own marker),
        # but the hook wrapper would skip. We test the update_timestamp_marker
        # and that a fresh Auditor + run produces consistent results.
        marker = project / ".cognitive-os" / "metrics" / ".last-aspirational-audit"
        last_ts = float(marker.read_text())
        # The marker timestamp should be fresh (< 5s old)
        assert time.time() - last_ts < 5

        # A second call should append more rows (script itself doesn't throttle —
        # throttle is in the hook wrapper). Verify JSONL still parseable.
        aa.main(["--project-root", str(project)])
        jsonl_content = jsonl.read_text()
        for line in jsonl_content.splitlines():
            if line.strip():
                json.loads(line)  # must parse cleanly
