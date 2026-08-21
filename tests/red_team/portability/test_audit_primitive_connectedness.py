# SCOPE: os-only
"""Portability + falsification proof for scripts/audit_primitive_connectedness.py.

These tests execute the classifier against synthetic corpora. They do not assert
file existence; each one drives real code and checks the verdict changes when the
evidence changes -- a probe that answers the same on both branches is broken.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "audit_primitive_connectedness.py"


def _load():
    spec = importlib.util.spec_from_file_location("apc", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repo_root_is_derived_from_file_not_cwd() -> None:
    """Portability: the root must not depend on the caller's working directory."""
    module = _load()
    assert module.REPO_ROOT == REPO_ROOT
    source = SCRIPT.read_text(encoding="utf-8")
    assert "Path(__file__).resolve().parents[1]" in source
    assert str(Path.home()) not in source


def test_classifier_discriminates_wired_from_unreferenced() -> None:
    """The counterfactual must produce DIFFERENT verdicts on the two branches."""
    module = _load()
    corpus = {
        "scripts/target.sh": "#!/bin/sh\necho hi\n",
        "scripts/orphan.sh": "#!/bin/sh\necho hi\n",
        "hooks/caller.sh": 'bash "$DIR/scripts/target.sh" run\n',
    }
    index = module.build_reverse_index(corpus)
    wired = module.classify_script("scripts/target.sh", corpus, set(), index, {})
    orphan = module.classify_script("scripts/orphan.sh", corpus, set(), index, {})
    assert wired == "AUTO_INVOCABLE"
    assert orphan == "UNREFERENCED"
    assert wired != orphan, "probe does not discriminate"


def test_roster_referrer_does_not_count_as_a_call_site() -> None:
    """An enumerating file must not be able to fake wiring for its whole list."""
    module = _load()
    members = [f"scripts/s{i}.sh" for i in range(module.ROSTER_THRESHOLD + 5)]
    corpus = {name: "#!/bin/sh\n" for name in members}
    corpus["tests/test_census.py"] = "\n".join(members)
    index = module.build_reverse_index(corpus)
    family = {m.rsplit("/", 1)[-1] for m in members}
    rosters = module.find_roster_files(index, family)

    assert "tests/test_census.py" in rosters, "roster detection did not fire"
    # Without demotion the census would read as a test call site.
    undemoted = module.classify_script(members[0], corpus, set(), index, {})
    demoted = module.classify_script(members[0], corpus, set(), index, rosters)
    assert undemoted == "TEST_ONLY"
    assert demoted == "ROSTER_ONLY"
    assert undemoted != demoted, "roster demotion is inert"


def test_telemetry_is_positive_evidence_only() -> None:
    """Absence from telemetry must never create a verdict; presence may rescue."""
    module = _load()
    corpus = {"scripts/lonely.sh": "#!/bin/sh\n"}
    index = module.build_reverse_index(corpus)
    absent = module.classify_script("scripts/lonely.sh", corpus, set(), index, {})
    present = module.classify_script(
        "scripts/lonely.sh", corpus, {"lonely.sh"}, index, {}
    )
    assert absent == "UNREFERENCED"
    assert present == "OBSERVED_ONLY"
    assert present != absent, "telemetry channel has no effect"


def test_manifest_comment_only_mention_is_not_parsing() -> None:
    """L2: naming a manifest in a comment must not count as reading it."""
    module = _load()
    corpus = {
        "manifests/thing.yaml": "a: 1\n",
        "scripts/commenter.py": "# manifests/thing.yaml is planned\nopen('other')\n",
        "scripts/reader.py": "import yaml\np='manifests/thing.yaml'\nyaml.safe_load(open(p))\n",
    }
    index = module.build_reverse_index(corpus)
    assert module.parses_target("scripts/reader.py", "manifests/thing.yaml", corpus)
    assert not module.parses_target("scripts/commenter.py", "manifests/thing.yaml", corpus)


def test_positive_control_blocks_reporting_when_fixtures_vanish() -> None:
    """An empty corpus must fail the control, not silently report zeros."""
    module = _load()
    failures = module.positive_control({}, set(), {}, {})
    assert failures, "positive control passed on an empty corpus"
