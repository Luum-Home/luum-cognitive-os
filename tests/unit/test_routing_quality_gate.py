from scripts.routing_quality_gate import GateThresholds, evaluate_report


def _report(*, candidate_skills=181, prompts=8, p1=1.0, p5=1.0, failures=0, misses=None):
    return {
        "candidate_skills": candidate_skills,
        "corpus_prompts": prompts,
        "candidate_signature": "abc123",
        "models": [
            {
                "model_id": "semantic-fallback",
                "loaded": True,
                "failures": failures,
                "precision_at_1": p1,
                "precision_at_5": p5,
                "top1_misses": misses or [],
            }
        ],
    }


def test_gate_passes_good_report() -> None:
    result = evaluate_report(_report(), GateThresholds())
    assert result.ok


def test_gate_fails_small_candidate_universe() -> None:
    result = evaluate_report(_report(candidate_skills=5), GateThresholds())
    assert not result.ok
    assert any("candidate_skills" in message for message in result.messages)


def test_gate_fails_low_precision() -> None:
    result = evaluate_report(_report(p1=0.5), GateThresholds(min_precision_at_1=0.8))
    assert not result.ok
    assert any("precision_at_1" in message for message in result.messages)


def test_gate_can_fail_on_top1_misses() -> None:
    result = evaluate_report(
        _report(misses=[{"expected_skill": "run-tests", "top_skill": "smoke-test"}]),
        GateThresholds(allow_top1_misses=False),
    )
    assert not result.ok
    assert any("top1_misses" in message for message in result.messages)
