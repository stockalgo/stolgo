import numpy as np


def robustness(net_pnl, *, resamples: int = 4000, seed: int = 7) -> dict:
    p = np.asarray(net_pnl, dtype=float)
    p = p[np.isfinite(p)]
    k = len(p)
    if k < 2:
        return {
            "method": "bootstrap_trade_pnl",
            "seed": seed,
            "resamples": resamples,
            "p_net_positive": None,
            "pf_p05": None,
            "pf_p95": None,
            "net_p05": None,
            "net_p95": None,
            "net_without_top5": None,
            "net_without_top10": None,
            "longest_losing_streak": None,
        }
    rng = np.random.default_rng(seed)
    s = p[rng.integers(0, k, (resamples, k))]
    net = s.sum(1)
    wins = np.where(s > 0, s, 0).sum(1)
    losses = -np.where(s < 0, s, 0).sum(1)
    pf = np.where(losses > 0, wins / np.where(losses > 0, losses, 1), np.nan)
    srt = np.sort(p)[::-1]
    streak = longest = 0
    for v in p:
        streak = streak + 1 if v < 0 else 0
        longest = max(longest, streak)
    return {
        "method": "bootstrap_trade_pnl",
        "seed": seed,
        "resamples": resamples,
        "p_net_positive": float((net > 0).mean()),
        "pf_p05": float(np.nanpercentile(pf, 5)),
        "pf_p95": float(np.nanpercentile(pf, 95)),
        "net_p05": float(np.percentile(net, 5)),
        "net_p95": float(np.percentile(net, 95)),
        "net_without_top5": float(p.sum() - srt[:5].sum()) if k > 5 else None,
        "net_without_top10": float(p.sum() - srt[:10].sum()) if k > 10 else None,
        "longest_losing_streak": int(longest),
    }
