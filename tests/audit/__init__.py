"""Audit tests — functional validation of install/update/uninstall shell scripts.

All tests in this package are marked with @pytest.mark.audit and isolated via
pytest's tmp_path fixture.  They invoke shell scripts via subprocess with strict
timeouts and never run against the real project root.

See docs/architecture/functional-audit/scorecard-install-scripts.md for the test
matrix and known limitations.
"""
