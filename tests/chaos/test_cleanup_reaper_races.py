from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from scripts.cos_cleanup_preserved_wip import validation_capsule_removal_blocker

pytestmark = pytest.mark.chaos


def test_cleanup_reaper_does_not_remove_active_validation_capsule(tmp_path: Path) -> None:
    capsule = tmp_path / "cos-validation-capsules" / "active"
    capsule.mkdir(parents=True)
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "validation-capsule.lock").write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "capsule_dir": str(capsule),
                "expires_at_epoch": int(time.time()) + 300,
                "last_heartbeat_epoch": int(time.time()),
                "heartbeat_interval_seconds": 30,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    blocker = validation_capsule_removal_blocker(tmp_path, capsule)

    assert blocker == "validation capsule lock is active"
