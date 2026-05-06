"""Contract: reference/optional services must declare a future `review_by` date.

Backs `docs/architecture/infrastructure-service-catalog.md` §Sunset Policy.

Scope:
- Every service whose `mode` in `cognitive-os.yaml` is one of
  {on_demand, cloud, disabled} AND whose classification (derived from the
  integration service-health contract) marks it as a reference/optional
  stack MUST declare `services.<name>.review_by: YYYY-MM-DD`.
- `review_by` MUST be parseable as an ISO date and MUST be >= today. A passed
  review_by means the sunset decision is overdue — the test fails to force
  the operator to act (keep with new date, or downgrade to `disabled`).

Truth sources:
- `cognitive-os.yaml` services block (authoritative for mode + review_by).
- `tests/integration/test_service_health.py::SERVICE_CONTRACTS` (authoritative
  for classification → runtime_service mapping).

Helpers reused:
- `tests/utils.jsonl` is available for future JSONL evidence checks (not
  required today — this is a static-manifest contract).
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.contract, pytest.mark.unit]


# Modes that REQUIRE a review_by declaration. Services in `pip` / `cli` /
# `always` mode are either library-backed or truly core and are not in scope
# for the sunset policy (MemU is the one explicit exception — Part B spec).
REVIEW_REQUIRED_MODES = {"on_demand", "cloud", "disabled"}

# Classifications considered "reference / optional-extension" for the sunset
# policy. Derived from the language used in test_service_health.py.
REVIEW_REQUIRED_CLASSIFICATIONS = {
    "legacy-reference",
    "reference-stack",
    "optional-extension",
    "optional-local-backend",
    "optional-ui-extension",
    "optional-automation-extension",
}

# Explicit inclusions that don't fit the mode filter but are required by
# catalog policy (Part B — MemU has explicit sunset deadline 2026-06-01).
ALWAYS_REQUIRED = {"memu"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_cognitive_os_services() -> dict:
    path = _repo_root() / "cognitive-os.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return (
        data.get("resources", {})
        .get("infrastructure", {})
        .get("services", {})
        or {}
    )


def _load_classifications() -> dict[str, str]:
    """Import SERVICE_CONTRACTS from the integration test as the classification
    source of truth (avoids duplicating the mapping in two places)."""
    import importlib.util

    svc_health = (
        _repo_root() / "tests" / "integration" / "test_service_health.py"
    )
    spec = importlib.util.spec_from_file_location("_svc_health", svc_health)
    assert spec and spec.loader, "cannot load test_service_health.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    classifications: dict[str, str] = {}
    for contract in getattr(module, "SERVICE_CONTRACTS", ()):
        classifications[contract["runtime_service"]] = contract["classification"]
    for contract in getattr(module, "UNMANAGED_COMPOSE_CONTRACTS", ()):
        classifications.setdefault(
            contract["runtime_service"], contract["classification"]
        )
    return classifications


def _services_requiring_review_by() -> list[tuple[str, dict]]:
    services = _load_cognitive_os_services()
    classifications = _load_classifications()
    out: list[tuple[str, dict]] = []
    for name, cfg in services.items():
        if not isinstance(cfg, dict):
            continue
        mode = cfg.get("mode")
        classification = classifications.get(name)
        mode_triggers = mode in REVIEW_REQUIRED_MODES
        class_triggers = classification in REVIEW_REQUIRED_CLASSIFICATIONS
        explicit = name in ALWAYS_REQUIRED
        if (mode_triggers and class_triggers) or explicit:
            out.append((name, cfg))
    return out


def _parse_review_by(raw: object) -> _dt.date:
    """PyYAML auto-parses `YYYY-MM-DD` into datetime.date. Accept both forms."""
    if isinstance(raw, _dt.date) and not isinstance(raw, _dt.datetime):
        return raw
    if isinstance(raw, _dt.datetime):
        return raw.date()
    if isinstance(raw, str):
        return _dt.date.fromisoformat(raw)
    raise AssertionError(
        f"review_by has unexpected type {type(raw).__name__}: {raw!r} "
        "(expected YYYY-MM-DD date)"
    )


def test_sunset_policy_covers_at_least_the_known_services():
    """Sanity: the filter captures the services the catalog sunset policy
    enumerates (valkey, memu, automaker).

    ADR-058 (2026-04-24): the former observability trace-UI service entry
    was retired; the sunset policy no longer needs to cover it.
    ADR-060 (2026-04-24): Opik removed per local-only policy (was mode:cloud,
    Phoenix covers observability locally)."""
    names = {name for name, _ in _services_requiring_review_by()}
    expected_subset = {"valkey", "memu", "automaker"}
    missing = expected_subset - names
    assert not missing, (
        "Sunset-policy filter lost services it should cover. "
        f"Missing: {sorted(missing)}. Present: {sorted(names)}. "
        "Check REVIEW_REQUIRED_MODES / REVIEW_REQUIRED_CLASSIFICATIONS / "
        "ALWAYS_REQUIRED in this test."
    )


@pytest.mark.parametrize(
    "service_name",
    [name for name, _ in _services_requiring_review_by()],
)
def test_review_by_is_declared(service_name):
    services = _load_cognitive_os_services()
    cfg = services[service_name]
    assert "review_by" in cfg, (
        f"{service_name}: sunset policy requires services.{service_name}.review_by "
        "(YYYY-MM-DD) in cognitive-os.yaml. "
        "See docs/architecture/infrastructure-service-catalog.md §Sunset Policy."
    )


@pytest.mark.parametrize(
    "service_name",
    [name for name, _ in _services_requiring_review_by()],
)
def test_review_by_is_future_dated(service_name):
    services = _load_cognitive_os_services()
    cfg = services[service_name]
    if "review_by" not in cfg:
        pytest.skip(
            f"{service_name}: missing review_by — covered by test_review_by_is_declared"
        )
    review_by = _parse_review_by(cfg["review_by"])
    today = _dt.date.today()
    assert review_by >= today, (
        f"{service_name}: review_by={review_by.isoformat()} has passed (today={today.isoformat()}). "
        "HALT — operator must either extend the date (and justify) or downgrade "
        "the service to mode=disabled per catalog §Sunset Policy."
    )


def test_review_by_dates_are_staggered():
    """Dates should not all collide on the same day — spec requirement."""
    entries = _services_requiring_review_by()
    dates: list[_dt.date] = []
    for name, cfg in entries:
        if "review_by" in cfg:
            dates.append(_parse_review_by(cfg["review_by"]))
    if len(dates) < 2:
        pytest.skip("need >=2 review_by dates to evaluate staggering")
    # No single day may hold >50% of reviews — cheap proxy for "staggered".
    from collections import Counter

    counts = Counter(dates)
    max_on_one_day = max(counts.values())
    assert max_on_one_day <= max(1, len(dates) // 2), (
        f"review_by dates are clustered: {counts}. Stagger them across the "
        "next 6 months per catalog §Sunset Policy."
    )


def test_memu_has_explicit_sunset_deadline():
    """Part B: MemU sunset deadline is hard-coded to 2026-06-01."""
    services = _load_cognitive_os_services()
    memu = services.get("memu")
    assert memu, "memu entry missing from cognitive-os.yaml services block"
    assert "review_by" in memu, "memu must declare review_by per Part B"
    assert _parse_review_by(memu["review_by"]) == _dt.date(2026, 6, 1), (
        "MemU sunset deadline is fixed at 2026-06-01 per catalog §Memory."
    )


def test_legacy_langfuse_record_completion_e2e_lane_is_retired():
    """ADR-058 moved record-completion trace proof to Phoenix/OTel.

    The optional E2E reference file may still keep infrastructure health checks
    for migration context, but it must not resurrect the removed
    record_completion -> Langfuse ingestion lane or call the deleted private
    sender API.
    """
    e2e_file = _repo_root() / "tests" / "integration" / "test_e2e_flows.py"
    text = e2e_file.read_text(encoding="utf-8")

    assert "TestCOSLangfuseIntegration" not in text
    assert "_send_langfuse_trace" not in text
