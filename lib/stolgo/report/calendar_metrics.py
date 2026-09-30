# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D
# Explicit daily sampling; initial capital included; no network dependencies.
"""Calendar-aware metrics for sparse strategies and independently marked paths."""
import math
import numpy as np
import pandas as pd
from stolgo.report.metrics import compute_metrics


def calendar_metrics(daily_pnl, capital, trades, *, intraday_equity=None):
    """daily_pnl includes every exchange session (idle=0, unresolved=NaN).

    Calendar CAGR uses the elapsed time between first-session opening and
    last-session closing equity. Cash earns zero; the risk-free benchmark is zero.
    Missing P&L is not converted to an idle day.
    """
    if daily_pnl.isna().any():
        raise ValueError('Cannot compute investable metrics with unresolved P&L')
    if daily_pnl.empty or capital <= 0:
        raise ValueError('Positive capital and explicit calendar are required')
    dates=pd.DatetimeIndex(daily_pnl.index)
    if dates.tz is None or not dates.is_monotonic_increasing or dates.has_duplicates:
        raise ValueError('Daily calendar must be unique, sorted, and timezone-aware')
    initial = dates[0].normalize() + pd.Timedelta(hours=3, minutes=45)  # 09:15 IST
    if initial >= dates[0]:
        initial = dates[0] - pd.Timedelta(seconds=1)
    equity = pd.concat([pd.Series([capital], index=[initial]), capital + daily_pnl.cumsum()])
    m=compute_metrics(equity,trades)
    # These require actual quantity/notional and intraday holding-time series.
    # Sparse daily/session inputs must not claim measured zero exposure/turnover.
    m.pop('exposure_pct', None)
    if not {'qty', 'entry_price', 'exit_price'}.issubset(trades.columns):
        m.pop('turnover', None)
    years=(equity.index[-1]-equity.index[0]).total_seconds()/(365.25*86400)
    ratio=float(equity.iloc[-1]/capital)
    m['cagr']=ratio**(1/years)-1 if ratio>0 and years>0 else float('nan')
    previous=capital+daily_pnl.cumsum().shift(1,fill_value=0)
    returns=daily_pnl/previous
    downside_rms=float(np.sqrt(np.mean(np.minimum(returns.to_numpy(),0)**2)))
    m['sortino']=float(returns.mean()/downside_rms*math.sqrt(252)) if downside_rms else float('nan')
    m['calmar']=m['cagr']/abs(m['max_drawdown']) if m['max_drawdown']<0 else float('nan')
    m['mar']=m['calmar']
    m['worst_day']=float(daily_pnl.min())
    m['expected_shortfall_95']=float(daily_pnl[daily_pnl<=daily_pnl.quantile(.05)].mean())
    if intraday_equity is not None and len(intraday_equity):
        full=pd.concat([pd.Series([capital],index=[initial]),intraday_equity]).sort_index()
        full=full.groupby(level=0).last()
        dd=full/full.cummax()-1
        m['intraday_max_drawdown']=float(dd.min())
    return m,equity
