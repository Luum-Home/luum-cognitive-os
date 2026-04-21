"""Tests for hooks/agent-qwen-bridge.sh + lib/skill_routing ADR-056 L3 fields.

Covers:
  - `SkillRequirements` dataclass: new `auto_fallback_to_qwen` +
    `fallback_min_pressure` fields with defaults + clamping
  - `parse_routing_block` accepts the new L3 fields and applies defaults
  - `find_skill_md` / `load_skill_requirements_by_name` resolvers
  - Hook behaviour via subprocess:
      - No-op when skill has no routing frontmatter
      - No-op when skill opted in but pressure below threshold (emits advisory only)
      - Rewrites via `hookSpecificOutput.updatedInput` when pressure >= threshold
      - `COS_DISABLE_AGENT_BRIDGE=1` bypasses
      - `CI=1` bypasses (testing env)
      - Unknown skill name → silent no-op
      - Malformed frontmatter → silent no-op + warning
      - Non-Agent tool name → silent no-op
      - `updatedInput` JSON is well-formed
      - `fallback_min_pressure` honoured per-skill

All hook invocations happen in an isolated tmp project directory with a
synthetic `.cognitive-os/metrics/rate-limit-events.jsonl` to control pressure.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from lib import skill_routing as _sr  # noqa: E402

HOOK = _REPO / "hooks" / "agent-qwen-bridge.sh"


# --------------------------------------------------------------------------- #
# SkillRequirements L3 fields
# --------------------------------------------------------------------------- #


class TestL3Fields(unittest.TestCase):
    def test_defaults(self):
        req = _sr.SkillRequirements()
        self.assertFalse(req.auto_fallback_to_qwen)
        self.assertAlmostEqual(req.fallback_min_pressure, 0.7)

    def test_parse_opt_in_block(self):
        req = _sr.parse_routing_block(
            {"routing": {"auto_fallback_to_qwen": True, "fallback_min_pressure": 0.55}}
        )
        self.assertIsNotNone(req)
        self.assertTrue(req.auto_fallback_to_qwen)
        self.assertAlmostEqual(req.fallback_min_pressure, 0.55)

    def test_missing_fields_preserve_defaults(self):
        # Backward-compat: a routing block that existed pre-ADR-056 still parses
        req = _sr.parse_routing_block({"routing": {"tier": "cheap"}})
        self.assertIsNotNone(req)
        self.assertFalse(req.auto_fallback_to_qwen)
        self.assertAlmostEqual(req.fallback_min_pressure, 0.7)

    def test_pressure_clamped_to_unit_interval(self):
        req = _sr.parse_routing_block(
            {"routing": {"auto_fallback_to_qwen": True, "fallback_min_pressure": 1.5}}
        )
        self.assertAlmostEqual(req.fallback_min_pressure, 1.0)

        req2 = _sr.parse_routing_block(
            {"routing": {"auto_fallback_to_qwen": True, "fallback_min_pressure": -0.3}}
        )
        self.assertAlmostEqual(req2.fallback_min_pressure, 0.0)

    def test_malformed_pressure_ignored(self):
        req = _sr.parse_routing_block(
            {"routing": {"fallback_min_pressure": "not-a-number"}}
        )
        self.assertIsNotNone(req)
        # Default preserved
        self.assertAlmostEqual(req.fallback_min_pressure, 0.7)

    def test_dispatch_dict_exposes_new_fields(self):
        req = _sr.SkillRequirements(auto_fallback_to_qwen=True, fallback_min_pressure=0.5)
        d = _sr.to_dispatch_dict(req)
        self.assertIn("auto_fallback_to_qwen", d)
        self.assertIn("fallback_min_pressure", d)
        self.assertTrue(d["auto_fallback_to_qwen"])
        self.assertAlmostEqual(d["fallback_min_pressure"], 0.5)


# --------------------------------------------------------------------------- #
# find_skill_md / load_skill_requirements_by_name
# --------------------------------------------------------------------------- #


class TestSkillNameResolution(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="cos-skill-resolve-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def _mk_skill(self, path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def test_resolves_top_level_skill(self):
        self._mk_skill(
            self.root / "skills" / "demo-skill" / "SKILL.md",
            "---\nname: demo-skill\nrouting:\n  auto_fallback_to_qwen: true\n---\n",
        )
        got = _sr.find_skill_md("demo-skill", project_root=self.root)
        self.assertIsNotNone(got)
        self.assertTrue(got.name == "SKILL.md")

    def test_resolves_package_nested_skill(self):
        self._mk_skill(
            self.root / "packages" / "pkg-a" / "skills" / "pkg-skill" / "SKILL.md",
            "---\nname: pkg-skill\n---\n",
        )
        got = _sr.find_skill_md("pkg-skill", project_root=self.root)
        self.assertIsNotNone(got)

    def test_unknown_skill_returns_none(self):
        self.assertIsNone(_sr.find_skill_md("nonexistent", project_root=self.root))

    def test_rejects_path_traversal(self):
        self.assertIsNone(_sr.find_skill_md("../etc/passwd", project_root=self.root))
        self.assertIsNone(_sr.find_skill_md("a/b", project_root=self.root))

    def test_load_by_name_returns_requirements(self):
        self._mk_skill(
            self.root / "skills" / "opt-in-skill" / "SKILL.md",
            textwrap.dedent(
                """\
                ---
                name: opt-in-skill
                routing:
                  auto_fallback_to_qwen: true
                  fallback_min_pressure: 0.4
                ---
                body
                """
            ),
        )
        req = _sr.load_skill_requirements_by_name(
            "opt-in-skill", project_root=self.root
        )
        self.assertIsNotNone(req)
        self.assertTrue(req.auto_fallback_to_qwen)
        self.assertAlmostEqual(req.fallback_min_pressure, 0.4)


# --------------------------------------------------------------------------- #
# Hook subprocess tests
# --------------------------------------------------------------------------- #


def _run_hook(stdin_payload: dict, project_dir: Path, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke hooks/agent-qwen-bridge.sh with the given stdin payload + env.

    Returns the CompletedProcess. Stdout is expected to be either empty
    (silent no-op) or a JSON document with `hookSpecificOutput`.
    """
    env = os.environ.copy()
    # IMPORTANT: the hook explicitly no-ops when CI=1 / PYTEST_CURRENT_TEST is set,
    # because we do not want sub-agent dispatch decisions mutated inside the test
    # harness. Here we're testing the hook ITSELF, so we must clear those guards
    # for the subprocess — but we only clear them when the test opts in.
    for var in ("CI", "PYTEST_CURRENT_TEST", "COS_DISABLE_AGENT_BRIDGE"):
        env.pop(var, None)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(stdin_payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


class TestHookBehaviour(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="cos-qwen-bridge-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
        # Stage lib/skill_routing.py visibility under the scratch project by
        # mirroring the real `lib` directory so `sys.path.insert(0, project_dir)`
        # in the hook finds the real module.
        # Easiest: symlink the real lib/ into the scratch tree.
        real_lib = _REPO / "lib"
        try:
            os.symlink(real_lib, self.root / "lib")
        except OSError:
            shutil.copytree(real_lib, self.root / "lib")

    def _write_skill(self, name: str, frontmatter: dict) -> None:
        import yaml as _yaml

        body = "---\n" + _yaml.safe_dump({"name": name, **frontmatter}).rstrip() + "\n---\nbody\n"
        (self.root / "skills" / name).mkdir(parents=True, exist_ok=True)
        (self.root / "skills" / name / "SKILL.md").write_text(body, encoding="utf-8")

    def _write_pressure(self, rate_limit_fraction: float, total_events: int = 10) -> None:
        """Populate rate-limit-events.jsonl so the local pressure heuristic
        returns approximately the requested fraction."""
        path = self.root / ".cognitive-os" / "metrics" / "rate-limit-events.jsonl"
        lines = []
        now = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
        rl_count = int(round(rate_limit_fraction * total_events))
        for i in range(total_events):
            is_rl = i < rl_count
            rec = {
                "timestamp": now,
                "event": "rate_limit" if is_rl else "call",
                "detail": "rate_limit" if is_rl else "ok",
            }
            lines.append(json.dumps(rec))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- Tests ---- #

    def test_noop_when_skill_has_no_opt_in(self):
        """Skill exists with frontmatter but hasn't opted into Qwen bridge."""
        self._write_skill("plain", {"routing": {"tier": "balanced"}})
        self._write_pressure(0.9)  # high pressure — should NOT matter
        payload = {
            "tool_name": "Agent",
            "tool_input": {"skill": "plain", "prompt": "do the thing"},
        }
        res = _run_hook(payload, self.root)
        self.assertEqual(res.returncode, 0)
        # No JSON emitted on stdout → hook is a no-op
        self.assertEqual(res.stdout.strip(), "")

    def test_rewrites_when_opt_in_and_pressure_high(self):
        self._write_skill(
            "qwen-ok",
            {
                "routing": {
                    "auto_fallback_to_qwen": True,
                    "fallback_min_pressure": 0.5,
                }
            },
        )
        self._write_pressure(0.9)  # high
        payload = {
            "tool_name": "Agent",
            "tool_input": {"skill": "qwen-ok", "prompt": "archive the change"},
        }
        res = _run_hook(payload, self.root)
        self.assertEqual(res.returncode, 0, msg=f"stderr={res.stderr}")
        self.assertNotEqual(res.stdout.strip(), "", msg="expected hookSpecificOutput JSON")
        out = json.loads(res.stdout)
        self.assertIn("hookSpecificOutput", out)
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso.get("hookEventName"), "PreToolUse")
        self.assertIn("updatedInput", hso)
        self.assertIn("prompt", hso["updatedInput"])
        # Redirected prompt must contain both the banner and the original
        self.assertIn("ADR-056 L3", hso["updatedInput"]["prompt"])
        self.assertIn("archive the change", hso["updatedInput"]["prompt"])

    def test_advisory_only_when_pressure_below_threshold(self):
        self._write_skill(
            "qwen-opt",
            {
                "routing": {
                    "auto_fallback_to_qwen": True,
                    "fallback_min_pressure": 0.8,
                }
            },
        )
        self._write_pressure(0.1)  # low pressure
        payload = {
            "tool_name": "Agent",
            "tool_input": {"skill": "qwen-opt", "prompt": "do the thing"},
        }
        res = _run_hook(payload, self.root)
        self.assertEqual(res.returncode, 0)
        # Advisory only: hook emits additionalContext but NO updatedInput
        out = json.loads(res.stdout)
        hso = out["hookSpecificOutput"]
        self.assertNotIn("updatedInput", hso)
        self.assertIn("additionalContext", hso)
        self.assertIn("pressure", hso["additionalContext"].lower())

    def test_fallback_min_pressure_honoured_per_skill(self):
        """Two opt-in skills with different thresholds — pressure between them
        should redirect only the one with the lower threshold."""
        self._write_skill(
            "low-thresh",
            {"routing": {"auto_fallback_to_qwen": True, "fallback_min_pressure": 0.3}},
        )
        self._write_skill(
            "high-thresh",
            {"routing": {"auto_fallback_to_qwen": True, "fallback_min_pressure": 0.9}},
        )
        self._write_pressure(0.5)  # between the two thresholds

        # Low threshold — should redirect
        r1 = _run_hook(
            {"tool_name": "Agent", "tool_input": {"skill": "low-thresh", "prompt": "x"}},
            self.root,
        )
        out1 = json.loads(r1.stdout)
        self.assertIn("updatedInput", out1["hookSpecificOutput"])

        # High threshold — should NOT redirect
        r2 = _run_hook(
            {"tool_name": "Agent", "tool_input": {"skill": "high-thresh", "prompt": "x"}},
            self.root,
        )
        out2 = json.loads(r2.stdout)
        self.assertNotIn("updatedInput", out2["hookSpecificOutput"])

    def test_updated_input_json_is_valid(self):
        """Sanity: the emitted JSON conforms to Claude Code hookSpecificOutput schema."""
        self._write_skill(
            "valid-json",
            {"routing": {"auto_fallback_to_qwen": True, "fallback_min_pressure": 0.0}},
        )
        self._write_pressure(0.9)
        payload = {
            "tool_name": "Agent",
            "tool_input": {"skill": "valid-json", "prompt": "quoted \"stuff\" in prompt"},
        }
        res = _run_hook(payload, self.root)
        self.assertEqual(res.returncode, 0)
        # Must be parseable JSON, not a fragment
        out = json.loads(res.stdout)
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "allow")

    def test_kill_switch_bypasses(self):
        self._write_skill(
            "would-redirect",
            {"routing": {"auto_fallback_to_qwen": True, "fallback_min_pressure": 0.0}},
        )
        self._write_pressure(0.9)
        payload = {
            "tool_name": "Agent",
            "tool_input": {"skill": "would-redirect", "prompt": "x"},
        }
        res = _run_hook(payload, self.root, env_overrides={"COS_DISABLE_AGENT_BRIDGE": "1"})
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "", msg="kill switch must silence hook entirely")

    def test_ci_env_bypasses(self):
        self._write_skill(
            "would-redirect",
            {"routing": {"auto_fallback_to_qwen": True, "fallback_min_pressure": 0.0}},
        )
        self._write_pressure(0.9)
        payload = {
            "tool_name": "Agent",
            "tool_input": {"skill": "would-redirect", "prompt": "x"},
        }
        res = _run_hook(payload, self.root, env_overrides={"CI": "1"})
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "")

    def test_unknown_skill_noop(self):
        self._write_pressure(0.9)
        payload = {
            "tool_name": "Agent",
            "tool_input": {"skill": "no-such-skill-anywhere", "prompt": "x"},
        }
        res = _run_hook(payload, self.root)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "")

    def test_malformed_frontmatter_noop(self):
        """A skill with broken YAML must not crash the hook — degrade to no-op."""
        (self.root / "skills" / "broken").mkdir(parents=True)
        (self.root / "skills" / "broken" / "SKILL.md").write_text(
            "---\nname: broken\nrouting: {unterminated\n---\nbody\n",
            encoding="utf-8",
        )
        self._write_pressure(0.9)
        payload = {
            "tool_name": "Agent",
            "tool_input": {"skill": "broken", "prompt": "x"},
        }
        res = _run_hook(payload, self.root)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "")

    def test_non_agent_tool_noop(self):
        """Hook only processes Agent/task/delegate tool calls."""
        self._write_skill(
            "would-redirect",
            {"routing": {"auto_fallback_to_qwen": True, "fallback_min_pressure": 0.0}},
        )
        self._write_pressure(0.9)
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/foo"},
        }
        res = _run_hook(payload, self.root)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "")

    def test_skill_name_extracted_from_prompt_fallback(self):
        """When tool_input.skill is absent, the hook falls back to scanning
        tool_input.prompt for a `skills/<name>/SKILL.md` reference."""
        self._write_skill(
            "prompt-ref",
            {"routing": {"auto_fallback_to_qwen": True, "fallback_min_pressure": 0.0}},
        )
        self._write_pressure(0.9)
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "SKILL: Load `skills/prompt-ref/SKILL.md` and do work"
            },
        }
        res = _run_hook(payload, self.root)
        self.assertEqual(res.returncode, 0, msg=f"stderr={res.stderr}")
        self.assertNotEqual(res.stdout.strip(), "")
        out = json.loads(res.stdout)
        self.assertIn("updatedInput", out["hookSpecificOutput"])


if __name__ == "__main__":
    unittest.main()
