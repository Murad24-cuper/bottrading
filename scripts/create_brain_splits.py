"""Freeze chronological brain splits from the configured local Parquet universe."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.brain.training import chronological_splits
from src.config import load_settings


def main() -> int:
    settings = load_settings(require_credentials=False)
    history = settings.root / settings.config['history']['data_dir']
    focus = [str(value) for value in settings.config['universe']['focus_symbols']]
    weekend = [str(value) for value in settings.config['universe']['weekend_symbols']]
    logical_symbols = focus + [value for value in weekend if value not in focus]
    alias_map = settings.config['universe'].get('symbol_aliases', {})
    symbols = []
    for logical in logical_symbols:
        patterns = [str(value) for value in alias_map.get(logical, [logical])]
        candidates = [history / f'{pattern}_M1.parquet' for pattern in patterns]
        for pattern in patterns:
            candidates += sorted(history.glob(f'{pattern}*_M1.parquet'))
        candidates += sorted(history.glob(f'{logical}*_M1.parquet'))
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None:
            print(f'Skipping unavailable M1 history: {logical}')
            continue
        actual = path.name[:-len('_M1.parquet')]
        if actual not in symbols:
            symbols.append(actual)
    stamps = set()
    ranges = {}
    for symbol in symbols:
        path = history / f'{symbol}_M1.parquet'
        frame = pd.read_parquet(path, columns=['close'])
        index = pd.DatetimeIndex(frame.index)
        if index.tz is None:
            index = index.tz_localize('UTC')
        else:
            index = index.tz_convert('UTC')
        sampled = index[(index.minute % 30 == 0) & (index.second == 0)]
        stamps.update(sampled.to_pydatetime())
        ranges[symbol] = {'start_utc': index.min().isoformat(), 'end_utc': index.max().isoformat(), 'bars': len(index)}
    if len(stamps) < 5:
        raise SystemExit('Too few timestamp samples to create chronological splits.')
    purge = max(int(settings.config['risk'].get('max_hold_extended_minutes', settings.config['risk']['max_hold_minutes'])),
                int(settings.config.get('weekend', {}).get('max_hold_extended_minutes', 0)))
    split = chronological_splits(sorted(stamps), purge_minutes=purge)
    payload = {'built_at_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'train_fraction': .60,
               'validation_fraction': .20, 'test_fraction': .20, 'purge_minutes': purge,
               'sample_interval_minutes': 30, 'symbols': ranges, 'timestamps': len(stamps), **split}
    target = settings.data_dir / 'brain' / 'splits.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'Wrote {target}: {len(stamps):,} sampled timestamps; purge={purge} min')
    print(f"Train through {payload['train_end']}; validation {payload['validation_start']}..{payload['validation_end']}; holdout from {payload['test_start']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
