from datetime import datetime, timezone, timedelta
import pytest
from src.brain.training import chronological_splits, split_name

def test_default_purge_minutes_covers_extended_hold_horizon():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    times = [start + timedelta(hours=i) for i in range(100)]
    # Default without explicit purge_minutes must be >= 120 minutes (max_hold_extended_minutes)
    splits = chronological_splits(times)
    assert splits['purge_minutes'] >= 120

def test_labels_within_hold_horizon_are_purged():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    times = [start + timedelta(hours=i) for i in range(100)]
    splits = chronological_splits(times)
    train_end_dt = datetime.fromisoformat(splits['train_end']).replace(tzinfo=timezone.utc)

    # 60 minutes after train_end (a 120-min trade would still be open!)
    overlap_time = train_end_dt + timedelta(minutes=60)
    assert split_name(overlap_time, splits) == 'purged'
