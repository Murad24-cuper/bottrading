import pytest
from src.db import Database

def test_sql_injection_in_columns_rejected(tmp_path):
    db = Database(tmp_path / "test.db")
    with pytest.raises(ValueError, match="Invalid column identifier"):
        db.insert_trade(**{"ticket": 123, "volume; DROP TABLE trades--": 1.0})

def test_sql_injection_in_update_rejected(tmp_path):
    db = Database(tmp_path / "test.db")
    with pytest.raises(ValueError, match="Invalid column identifier"):
        db.update_open_trade(123, **{"sl = 0; --": 1.0})

def test_invalid_table_rejected(tmp_path):
    db = Database(tmp_path / "test.db")
    with db.connect() as conn:
        with pytest.raises(ValueError, match="Invalid table name"):
            db._insert(conn, "trades; DROP TABLE trades--", {"ticket": 123})
