from __future__ import annotations

from cos_lib.manifest_loader import load_manifest


def test_duplicate_quality_tools_are_manifested_for_installable_profiles() -> None:
    manifest = load_manifest()
    duplicate_quality_tools = {"jscpd", "pmd", "dupl", "ast-grep", "semgrep"}

    for tool_name in duplicate_quality_tools:
        tool = manifest.tool(tool_name)
        assert tool is not None
        assert tool.check
        assert tool.install

    for profile_name in ("dev", "ci", "full", "headless-instance"):
        profile = manifest.profile(profile_name)
        assert duplicate_quality_tools.issubset(set(profile.tools_recommended))


def test_duplicate_quality_tools_do_not_expand_default_profile() -> None:
    manifest = load_manifest()
    duplicate_quality_tools = {"jscpd", "pmd", "dupl", "ast-grep", "semgrep"}

    profile = manifest.profile("default")
    selected_tools = set(profile.tools_required) | set(profile.tools_recommended)
    assert selected_tools.isdisjoint(duplicate_quality_tools)


def test_iroh_profile_is_manifested_but_not_default() -> None:
    manifest = load_manifest()

    iroh_profile = manifest.profile("iroh")
    assert iroh_profile.tools_required == ["python3", "cargo"]
    assert "iroh" in iroh_profile.tools_recommended
    assert "iroh" in manifest.profile("full").tools_recommended

    default_tools = set(manifest.profile("default").tools_required) | set(manifest.profile("default").tools_recommended)
    assert "iroh" not in default_tools
