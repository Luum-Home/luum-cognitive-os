from lib.maintainer_proposals import deterministic_proposal_id


def test_deterministic_proposal_id_is_stable():
    first = deterministic_proposal_id(
        "skill-router",
        "recovery_skill_suggested_in_meta_discussion",
        "2026-05-06",
    )
    second = deterministic_proposal_id(
        "skill-router",
        "recovery_skill_suggested_in_meta_discussion",
        "2026-05-06",
    )

    assert first == second
    assert first.startswith("perf-ledger-skill-router-recovery-skill-suggested-in-meta-discussion-2026-05-06-")


def test_deterministic_proposal_id_changes_by_day_window():
    first = deterministic_proposal_id("skill-router", "same-pattern", "2026-05-06")
    second = deterministic_proposal_id("skill-router", "same-pattern", "2026-05-07")

    assert first != second
