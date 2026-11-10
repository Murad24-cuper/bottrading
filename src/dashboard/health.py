"""Render-level health checks for the local Streamlit dashboard."""
from __future__ import annotations

from pathlib import Path


def check_dashboard_render(root: str | Path | None = None, timeout: int = 30) -> tuple[bool, str]:
    """Run the dashboard once and fail when Streamlit renders an exception."""
    from streamlit.testing.v1 import AppTest

    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    app_path = project_root / 'src' / 'dashboard' / 'app.py'
    try:
        app_test = AppTest.from_file(str(app_path))
        app_test.run(timeout=timeout)
    except Exception as exc:
        return False, f'Dashboard failed to start: {type(exc).__name__}: {exc}'
    exceptions = [str(getattr(item, 'value', item)) for item in app_test.exception]
    if exceptions:
        return False, f'Dashboard rendered exception: {exceptions[0]}'
    return True, 'Dashboard rendered without Streamlit exceptions.'
