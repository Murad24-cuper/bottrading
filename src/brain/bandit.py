"""Risk-neutral Thompson sampling helpers for scan priority."""
from __future__ import annotations

from collections import defaultdict
import random


def sample_arm_priorities(rows: list[dict], arms: list[str], rng=None) -> dict[str, float]:
    """Sample recent win-rate posteriors and allocate bounded scan shares.

    Each arm is strategy × asset group × session. Shares are clamped to 5–40%
    and normalized; risk sizing and all hard risk rules remain untouched.
    """
    unique = list(dict.fromkeys(str(arm) for arm in arms))
    if not unique:
        return {}
    generator = rng or random
    outcomes: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        arm = str(row.get('arm', ''))
        if arm in unique:
            outcomes[arm].append(bool(row.get('win')))
    samples = {}
    for arm in unique:
        wins = sum(outcomes[arm])
        losses = len(outcomes[arm]) - wins
        samples[arm] = generator.betavariate(1 + wins, 1 + losses)
    total = sum(samples.values()) or 1.0
    raw = {arm: samples[arm] / total for arm in unique}
    shares = {arm: min(.40, max(.05, value)) for arm, value in raw.items()}
    for _ in range(len(unique)):
        excess = sum(shares.values()) - 1.0
        if excess <= 1e-12:
            break
        adjustable = [arm for arm, value in shares.items() if value > .05]
        if not adjustable:
            break
        reduction = min(excess / len(adjustable), min(shares[arm] - .05 for arm in adjustable))
        for arm in adjustable:
            shares[arm] -= reduction
    return shares


def arm_key(strategy: str, asset_group: str, session: str) -> str:
    """Create the stable strategy/group/session bandit key."""
    return '|'.join((str(strategy), str(asset_group), str(session)))
