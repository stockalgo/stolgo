import math
import numpy as np
import pandas as pd
import pytest
from stolgo.report.calendar_metrics import calendar_metrics


def test_initial_loss_and_idle_days_are_included():
    dates=pd.date_range('2024-01-01 10:00',periods=5,freq='B',tz='UTC')
    p=pd.Series([-10.,0.,0.,0.,20.],index=dates)
    m,e=calendar_metrics(p,100,pd.DataFrame())
    assert m['max_drawdown']==pytest.approx(-.1)
    assert m['total_return']==pytest.approx(.1)
    r=p/(100+p.cumsum().shift(1,fill_value=0))
    assert m['sharpe']==pytest.approx(r.mean()/r.std()*math.sqrt(252))
    assert len(e)==6


def test_elapsed_time_not_number_of_trades_for_cagr():
    dates=pd.DatetimeIndex(['2023-01-02 10:00','2024-01-02 10:00'],tz='UTC')
    m,_=calendar_metrics(pd.Series([0.,10.],index=dates),100,pd.DataFrame())
    assert .099<m['cagr']<.101


def test_unknown_pnl_is_not_zero():
    p=pd.Series([np.nan],index=pd.DatetimeIndex(['2024-01-01 10:00'],tz='UTC'))
    with pytest.raises(ValueError): calendar_metrics(p,100,pd.DataFrame())
