from pathlib import Path

from lib.public_claim_gate import scan


def _manifest(path: Path) -> Path:
    path.write_text(
        """
schema_version: public-claim-evidence/v1
scope:
  include: [README.md]
  exclude: []
policy:
  high_risk_patterns: [self-improving, MAPE-K]
  allowed_context_patterns: [governed, inspired, not autonomous]
""".strip(),
        encoding="utf-8",
    )
    return path


def test_public_claim_gate_blocks_unqualified_self_improving_claim(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Cognitive OS is self-improving at scale.\n", encoding="utf-8")
    manifest = _manifest(tmp_path / "public-claims.yaml")

    report = scan(tmp_path, manifest)

    assert report["status"] == "fail"
    assert report["findings"][0]["pattern"] == "self-improving"


def test_public_claim_gate_allows_bounded_governed_claim(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "Cognitive OS uses MAPE-K-inspired remediation with governed execution, not autonomous mutation.\n",
        encoding="utf-8",
    )
    manifest = _manifest(tmp_path / "public-claims.yaml")

    report = scan(tmp_path, manifest)

    assert report["status"] == "pass"
    assert report["findings"] == []

