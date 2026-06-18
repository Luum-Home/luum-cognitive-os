import json
from pathlib import Path

import pytest

from scripts import cos_iroh


def test_local_contract_keypair_roundtrip():
    keypair = cos_iroh.LocalContractKeypair.generate()
    loaded = cos_iroh.LocalContractKeypair.from_dict(keypair.to_dict())
    assert loaded.public_key == keypair.public_key
    assert loaded.secret_key == keypair.secret_key
    assert len(loaded.public_key) == 64


@pytest.mark.parametrize("value", ["", "abc", "A" * 64, "g" * 64])
def test_validate_public_key_rejects_invalid_values(value):
    with pytest.raises(cos_iroh.IrohContractError):
        cos_iroh.validate_public_key(value)


def test_default_config_disabled_by_default(tmp_path):
    config = cos_iroh.load_config(tmp_path)
    assert config["enabled"] is False
    assert config["backend"] == "local-loopback-contract"
    assert config["relay_mode"] == "disabled"


def test_doctor_can_initialize_local_contract_keypair(tmp_path, capsys):
    rc = cos_iroh.main(["doctor", "--project-dir", str(tmp_path), "--init-keypair", "--json"])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == "cos-iroh-doctor/v1"
    assert report["enabled"] is False
    assert report["keypair"]["status"] == "generated"
    assert Path(report["keypair"]["path"]).exists()


def test_ping_self_test_uses_two_local_endpoints(capsys):
    rc = cos_iroh.main(["ping", "--self-test", "--json"])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == "cos-iroh-ping/v1"
    assert report["status"] == "pass"
    assert report["transport_backend"] == "local-loopback-contract"
    assert report["server_public_key"] != report["client_public_key"]


def test_agent_bus_disabled_by_default(tmp_path, capsys):
    peer = cos_iroh.LocalContractKeypair.generate().public_key
    rc = cos_iroh.main([
        "agent-bus-adapter",
        "--project-dir",
        str(tmp_path),
        "--peer-key",
        peer,
        "--allow-peer",
        peer,
        "--json",
    ])
    assert rc == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "disabled"
    assert not cos_iroh.bus_ledger_path(tmp_path).exists()


def test_agent_bus_self_test_records_safe_events(capsys):
    rc = cos_iroh.main(["agent-bus-adapter", "--self-test", "--json"])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "pass"
    assert [record["event"] for record in report["records"]] == ["heartbeat", "status", "message"]
