"""Verify that the Streamlit dashboard renders without a script exception."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dashboard.health import check_dashboard_render


def main() -> int:
    ok, detail = check_dashboard_render(ROOT)
    print(f"{'OK' if ok else 'ERROR'}: {detail}")
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
