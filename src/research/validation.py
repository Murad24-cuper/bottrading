"""Minimum validation toolkit: Random benchmark, Walk-Forward, and Deflated Sharpe Ratio."""
from __future__ import annotations
import math
import numpy as np

def _norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def _norm_ppf(p: float) -> float:
    """Standard normal percent point function (inverse CDF) using rational approximation."""
    if p <= 0.0:
        return -8.0
    if p >= 1.0:
        return 8.0
    # Winitzki / Acklam approximation
    if p < 0.5:
        # F_inv(p) = -F_inv(1-p)
        return -_norm_ppf(1.0 - p)
    t = math.sqrt(-2.0 * math.log(1.0 - p))
    # Coefficients for minimax approximation
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308
    return t - ((c2 * t + c1) * t + c0) / (((d3 * t + d2) * t + d1) * t + 1.0)

def _calc_skew(x: np.ndarray) -> float:
    n = len(x)
    if n < 3:
        return 0.0
    mu = float(np.mean(x))
    std = float(np.std(x, ddof=0))
    if std <= 1e-9:
        return 0.0
    m3 = float(np.mean((x - mu) ** 3))
    return m3 / (std ** 3)

def _calc_kurt(x: np.ndarray) -> float:
    n = len(x)
    if n < 4:
        return 3.0
    mu = float(np.mean(x))
    std = float(np.std(x, ddof=0))
    if std <= 1e-9:
        return 3.0
    m4 = float(np.mean((x - mu) ** 4))
    return m4 / (std ** 4)

def random_entry_benchmark(trade_results: list[dict], n_reps: int = 200, seed: int = 42) -> dict:
    """Simulate random entries with identical trade count and win/loss payoff structure.
    
    Returns mean expectancy R and 95th percentile expectancy R across repetitions.
    """
    if not trade_results:
        return {'mean_r': 0.0, 'p95_r': 0.0, 'beats_p95': False}
    
    n_trades = len(trade_results)
    actual_r = np.array([t['net_r'] for t in trade_results], dtype=float)
    actual_mean = float(actual_r.mean())
    
    # Extract R-multiples for win and loss from actual trades
    win_rs = [t['net_r'] for t in trade_results if t['net_r'] > 0]
    loss_rs = [t['net_r'] for t in trade_results if t['net_r'] <= 0]
    
    avg_win_r = float(np.mean(win_rs)) if win_rs else 1.5
    avg_loss_r = float(np.mean(loss_rs)) if loss_rs else -1.0
    
    rng = np.random.default_rng(seed)
    rep_means = []
    
    # Under the null of no edge, random direction against market moves
    avg_cost_r = float(np.mean([t.get('cost_r', 0.05) for t in trade_results]))
    for _ in range(n_reps):
        random_wins = rng.random(n_trades) < 0.5
        sim_r = np.where(random_wins, avg_win_r, avg_loss_r) - avg_cost_r
        rep_means.append(float(np.mean(sim_r)))
    
    rep_means = np.array(rep_means)
    p95 = float(np.percentile(rep_means, 95))
    mean_val = float(np.mean(rep_means))
    
    return {
        'mean_r': mean_val,
        'p95_r': p95,
        'actual_r': actual_mean,
        'beats_p95': bool(actual_mean > p95)
    }

def walk_forward_share(trades: list[dict], n_windows: int = 6) -> dict:
    """Split trades chronologically into n_windows and calculate share of windows with positive expectancy."""
    if not trades or len(trades) < n_windows:
        return {'share': 0.0, 'positive_windows': 0, 'total_windows': n_windows, 'passed': False}
    
    sorted_trades = sorted(trades, key=lambda t: t['entry_time'])
    window_size = len(sorted_trades) // n_windows
    
    positive = 0
    window_stats = []
    for w in range(n_windows):
        start_idx = w * window_size
        end_idx = (w + 1) * window_size if w < n_windows - 1 else len(sorted_trades)
        w_trades = sorted_trades[start_idx:end_idx]
        if w_trades:
            net_r_vals = [t['net_r'] for t in w_trades]
            ev = float(np.mean(net_r_vals))
            is_pos = ev > 0.0
            if is_pos:
                positive += 1
            window_stats.append({'window': w + 1, 'trades': len(w_trades), 'ev': ev, 'positive': is_pos})
        else:
            window_stats.append({'window': w + 1, 'trades': 0, 'ev': 0.0, 'positive': False})
            
    share = positive / n_windows
    return {
        'share': float(share),
        'positive_windows': positive,
        'total_windows': n_windows,
        'window_stats': window_stats,
        'passed': bool(share >= 0.60)
    }

def deflated_sharpe_ratio(trades: list[dict], n_trials: int = 18, var_sr: float = 0.5) -> dict:
    """Compute Deflated Sharpe Ratio (DSR) based on Bailey & Lopez de Prado (2014).
    
    Adjusts standard Sharpe for multiple testing over n_trials variants.
    """
    if not trades or len(trades) < 5:
        return {'dsr': 0.0, 'sharpe': 0.0, 'passed': False}
        
    r_vals = np.array([t['net_r'] for t in trades], dtype=float)
    n = len(r_vals)
    std = float(np.std(r_vals, ddof=1))
    if std <= 1e-9:
        return {'dsr': 0.0, 'sharpe': 0.0, 'passed': False}
        
    mean = float(np.mean(r_vals))
    sharpe = mean / std
    
    skew = _calc_skew(r_vals)
    kurt = _calc_kurt(r_vals)  # Pearson kurtosis (normal = 3)
    
    # Expected maximum Sharpe under null across n_trials independent tests
    gamma = 0.5772156649
    if n_trials > 1:
        z1 = _norm_ppf(1.0 - 1.0 / n_trials)
        z2 = _norm_ppf(1.0 - 1.0 / (n_trials * math.e))
        sr_star = math.sqrt(var_sr) * ((1 - gamma) * z1 + gamma * z2)
    else:
        sr_star = 0.0
        
    # Variance of Sharpe estimator under non-normality
    var_estimator = (1.0 - skew * sharpe + ((kurt - 1.0) / 4.0) * (sharpe ** 2)) / max(1, n - 1)
    if var_estimator <= 0:
        var_estimator = 1.0 / max(1, n - 1)
        
    test_stat = (sharpe - sr_star) / math.sqrt(var_estimator)
    dsr_pvalue = float(_norm_cdf(test_stat))
    
    return {
        'sharpe': float(sharpe),
        'sr_star': float(sr_star),
        'dsr': dsr_pvalue,
        'passed': bool(sharpe > 0 and dsr_pvalue > 0.5)
    }
