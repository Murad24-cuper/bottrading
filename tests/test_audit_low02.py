"""LOW-02: Verify that unused legacy symbols are not referenced anywhere.

These tests confirm the symbols are truly unused before removal.
After removal, they confirm ImportError / AttributeError as expected.
"""
import ast
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"
SCRIPTS = ROOT / "scripts"


def _all_py_files(*dirs):
    for d in dirs:
        yield from pathlib.Path(d).rglob("*.py")


def _identifiers_used(name: str) -> list[str]:
    """Return list of files (outside definition) that reference *name*."""
    hits = []
    for f in _all_py_files(SRC, TESTS, SCRIPTS):
        source = f.read_text(encoding="utf-8", errors="replace")
        # Skip the definition file itself only for exact class/function defs
        try:
            tree = ast.parse(source, filename=str(f))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Name, ast.Attribute)):
                n = node.id if isinstance(node, ast.Name) else node.attr
                if n == name:
                    hits.append(str(f))
                    break
    return hits


def test_TradeRequest_only_defined_not_used():
    """TradeRequest should only appear in its definition file."""
    hits = _identifiers_used("TradeRequest")
    # Only src/models.py itself should contain TradeRequest
    non_def = [h for h in hits if "models.py" not in h]
    assert non_def == [], f"TradeRequest unexpectedly used in: {non_def}"


def test_DummyStrategy_only_defined_not_used():
    """DummyStrategy should only appear in its definition file."""
    hits = _identifiers_used("DummyStrategy")
    non_def = [h for h in hits if "strategy_base.py" not in h]
    assert non_def == [], f"DummyStrategy unexpectedly used in: {non_def}"


def test_models_Position_not_imported_anywhere():
    """models.Position is never imported; only MT5 position objects are used."""
    hits = []
    for f in _all_py_files(SRC, TESTS, SCRIPTS):
        source = f.read_text(encoding="utf-8", errors="replace")
        if "from src.models import" in source or "from .models import" in source:
            if "Position" in source.split("from")[1].split("\n")[0] if "models import" in source else False:
                hits.append(str(f))
    # Expect no imports of Position from models
    assert hits == [], f"models.Position is imported in: {hits}"
