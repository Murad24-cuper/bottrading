import importlib

from src.dashboard.health import check_dashboard_render


def test_dashboard_module_and_direct_imports_resolve():
    """Import app.py so a renamed direct dependency fails during pytest."""
    app = importlib.import_module('src.dashboard.app')
    assert callable(app.assert_fastparquet_available)


def test_dashboard_renders_without_streamlit_exception():
    ok, detail = check_dashboard_render(timeout=30)
    assert ok, detail
