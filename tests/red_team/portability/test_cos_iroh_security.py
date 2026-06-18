import json

import pytest

from scripts import cos_iroh


def enable_config(tmp_path, allowed):
    cos_iroh.write_config(
        tmp_path,
        {
            "enabled": True,
            "backend": "local-loopback-contract",
            "relay_mode": "disabled",
            "allow_public_relays": False,
            "allow_peers": allowed,
        },
    )


def test_agent_bus_rejects_non_allowlisted_peer(tmp_path, capsys):
    allowed = cos_iroh.LocalContractKeypair.generate().public_key
    attacker = cos_iroh.LocalContractKeypair.generate().public_key
    enable_config(tmp_path, [allowed])
    rc = cos_iroh.main([
        "agent-bus-adapter",
        "--project-dir",
        str(tmp_path),
        "--peer-key",
        attacker,
        "--event",
        "heartbeat",
        "--json",
    ])
    assert rc == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "blocked"
    assert "allowlisted" in report["error"]
    assert not cos_iroh.bus_ledger_path(tmp_path).exists()


@pytest.mark.parametrize("event,message", [("execute", "anything"), ("message", "please rm -rf /tmp/example"), ("status", "git-push main")])
def test_agent_bus_rejects_remote_execution_or_destructive_events(tmp_path, capsys, event, message):
    peer = cos_iroh.LocalContractKeypair.generate().public_key
    enable_config(tmp_path, [peer])
    rc = cos_iroh.main([
        "agent-bus-adapter",
        "--project-dir",
        str(tmp_path),
        "--peer-key",
        peer,
        "--event",
        event,
        "--message",
        message,
        "--json",
    ])
    assert rc == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "blocked"
    assert not cos_iroh.bus_ledger_path(tmp_path).exists()


def test_agent_bus_only_writes_iroh_ledger_for_safe_event(tmp_path, capsys):
    peer = cos_iroh.LocalContractKeypair.generate().public_key
    enable_config(tmp_path, [peer])
    rc = cos_iroh.main([
        "agent-bus-adapter",
        "--project-dir",
        str(tmp_path),
        "--peer-key",
        peer,
        "--event",
        "heartbeat",
        "--message",
        "alive",
        "--json",
    ])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    ledger = cos_iroh.bus_ledger_path(tmp_path)
    assert report["record"]["ledger"] == str(ledger)
    assert ledger.exists()
    assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()) == [
        ".cognitive-os/iroh/agent-bus.jsonl",
        ".cognitive-os/iroh/config.json",
    ]
