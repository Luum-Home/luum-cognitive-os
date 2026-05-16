from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "cos-product-answer"


def _utf8(hex_text: str) -> str:
    return bytes.fromhex(hex_text).decode("utf-8")


def _product_manifest_source_paths() -> set[str]:
    paths: set[str] = set()
    question_bank = yaml.safe_load((ROOT / "manifests" / "product-question-bank.yaml").read_text(encoding="utf-8"))
    claim_evidence = yaml.safe_load((ROOT / "manifests" / "product-claim-evidence.yaml").read_text(encoding="utf-8"))
    for question in question_bank["questions"].values():
        paths.update(str(item) for item in question.get("approved_sources", []) or [])
    for claim in claim_evidence["claims"].values():
        paths.update(str(item) for item in claim.get("evidence", []) or [])
    return paths


def test_product_answer_manifest_sources_are_clean_checkout_portable() -> None:
    """Product answers must not depend on local-only strategy/cache files."""
    missing: list[str] = []
    untracked: list[str] = []
    for rel in sorted(_product_manifest_source_paths()):
        if not (ROOT / rel).exists():
            missing.append(rel)
            continue
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if tracked.returncode != 0:
            untracked.append(rel)
    assert missing == []
    assert untracked == []


def test_product_answer_cli_answers_differentiator_json() -> None:
    result = subprocess.run(
        [str(CLI), "What is our differentiator?", "--no-cache", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["schema_version"] == "product-answer-report/v1"
    assert report["adr"] == "ADR-280"
    assert report["question_id"] == "differentiator"
    assert "behavioral governance" in report["answer_short"]
    assert report["unsafe_claims_to_avoid"]
    assert report["claims"]


def test_product_answer_cli_renders_markdown_by_question_id() -> None:
    result = subprocess.run(
        [str(CLI), "--question-id", "landing_pitch", "--format", "markdown"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "# Product Answer: landing_pitch" in result.stdout
    assert "AI agents ship faster. Cognitive OS makes them prove it." in result.stdout
    assert "TRUST_REPORT:" in result.stdout


def test_product_answer_cli_unknown_question_fails() -> None:
    result = subprocess.run(
        [str(CLI), "unmatched procurement policy", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "no product question matched" in report["error"]



def test_product_answer_refresh_cli_materializes_and_answer_cli_uses_cache(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cards"
    refresh = subprocess.run(
        [str(ROOT / "scripts" / "cos-product-answer-refresh"), "--question-id", "differentiator", "--cache-dir", str(cache_dir), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    answer = subprocess.run(
        [str(CLI), "What is our differentiator?", "--cache-dir", str(cache_dir), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert refresh.returncode == 0
    refresh_report = json.loads(refresh.stdout)
    assert refresh_report["adr"] == "ADR-282"
    assert refresh_report["refreshed_count"] == 1
    assert (cache_dir / "differentiator.md").exists()
    assert (cache_dir / "differentiator.json").exists()
    assert (cache_dir / "index.yaml").exists()

    assert answer.returncode == 0
    answer_report = json.loads(answer.stdout)
    assert answer_report["cache"]["mode"] == "card"
    assert answer_report["cache"]["freshness"] == "fresh"
    assert answer_report["question_id"] == "differentiator"


def test_product_answer_cli_no_cache_forces_live_generation_after_refresh(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cards"
    subprocess.run(
        [str(ROOT / "scripts" / "cos-product-answer-refresh"), "--question-id", "differentiator", "--cache-dir", str(cache_dir)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    result = subprocess.run(
        [str(CLI), "--question-id", "differentiator", "--cache-dir", str(cache_dir), "--no-cache", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["cache"]["mode"] == "live"
    assert report["question_id"] == "differentiator"


def test_product_answer_cli_competitors_uses_local_radar_before_browsing() -> None:
    result = subprocess.run(
        [str(CLI), "--question-id", "competitors", "--no-cache", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["question_id"] == "competitors"
    assert "local Tech Radar" in report["answer_long"]
    assert "Use internet research only for volatile" in report["answer_long"]
    assert "docs/06-Daily/reports/external-tools-radar-INDEX.md" in report["approved_sources"]
    assert "docs/08-References/root/vs-alternatives.md" in report["approved_sources"]
    assert "docs/04-Concepts/root/component-sources.md" in report["approved_sources"]
    assert any(
        "Do not browse by default" in boundary
        for claim in report["claims"]
        for boundary in claim["boundaries"]
    )


def test_product_answer_cli_routes_vanilla_usage_question() -> None:
    result = subprocess.run(
        [str(CLI), "cuando uso configuraciones vanilla sin cognitive os", "--no-cache", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["question_id"] == "vanilla_usage"
    assert "Use vanilla IDE-agent setups" in report["answer_short"]
    assert "docs/08-References/business/cos-vs-vanilla-dx-review.md" in report["approved_sources"]
    assert any(claim["claim_id"] == "vanilla_boundary" for claim in report["claims"])
    assert "COS is always better than vanilla IDE agents" in report["unsafe_claims_to_avoid"]


def test_product_answer_cli_routes_runtime_surface_question() -> None:
    result = subprocess.run(
        [str(CLI), "puede correr como servicio tiene ui y cli", "--no-cache", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["question_id"] == "runtime_surfaces"
    assert "operator CLI" in report["answer_long"]
    assert "docs/02-Decisions/adrs/ADR-211-service-mode-readiness-gate.md" in report["approved_sources"]
    assert any(claim["claim_id"] == "service_mode_readiness_partial" for claim in report["claims"])
    assert "COS is already a polished SaaS dashboard" in report["unsafe_claims_to_avoid"]


def test_product_answer_cli_routes_alternative_choice_question() -> None:
    result = subprocess.run(
        [str(CLI), "por que no uso hermes en su lugar", "--no-cache", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["question_id"] == "alternatives_choice"
    assert "Use Hermes, Agent Zero, or OpenClaw" in report["answer_short"]
    assert "docs/08-References/root/vs-alternatives.md" in report["approved_sources"]
    assert any(claim["claim_id"] == "alternative_complementarity" for claim in report["claims"])
    assert "browse only for volatile current facts" in report["answer_long"]


def test_product_answer_cli_routes_ssr_primitive_enablement_question() -> None:
    result = subprocess.run(
        [
            str(CLI),
            _utf8(
                "736920736f79206465762073737220636f6e206c696d69746163696f6e657320"
                "646520617271756974656374757261207920676f6265726e616e7a6120636f6d"
                "6f206d6520617975646120636f6e207072696d697469766173"
            ),
            "--no-cache",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["question_id"] == "ssr_primitive_enablement"
    assert "governed skills" in report["answer_short"]
    assert "docs/04-Concepts/architecture/ssr-agentic-primitive-enablement-gaps.md" in report["approved_sources"]
    assert any(claim["claim_id"] == "ssr_primitive_enablement_gap_backlog" for claim in report["claims"])
    assert "COS autonomously rewrites itself from chat" in report["unsafe_claims_to_avoid"]


def test_product_answer_cli_routes_commercial_architecture_map_question() -> None:
    result = subprocess.run(
        [
            str(CLI),
            _utf8(
                "6d6520706173617320756e206d61706120726564756369646f206465206c6120"
                "6172717569746563747572612064656c20534f20636f6d65726369616c"
            ),
            "--no-cache",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["question_id"] == "architecture_map"
    assert "governance and evidence layer" in report["answer_short"]
    assert "```mermaid" in report["answer_long"]
    assert "graph TD" in report["answer_long"]
    assert "Engineering team" in report["answer_long"]
    assert "Cognitive OS<br/>Governance and evidence layer" in report["answer_long"]
    assert "commercial_architecture_map_primitive" in {
        claim["claim_id"] for claim in report["claims"]
    }
    public_copy = "\n".join(
        [
            report["answer_short"],
            report["answer_long"],
            report["recommended_pitch"],
        ]
    )
    assert "Claude" not in public_copy
    assert "Codex" not in public_copy
    assert "Engram" not in public_copy
    assert "hooks" not in public_copy.casefold()
    assert "skills" not in public_copy.casefold()
    assert any(
        "internal implementation counts" in claim
        for claim in report["unsafe_claims_to_avoid"]
    )
