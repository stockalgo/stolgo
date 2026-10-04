"""Regression cases for causal multi-contract options fills and lifecycle risk."""
from dataclasses import replace
import numpy as np
import pandas as pd
import pytest
from stolgo.options import OptionSession, ReplayConfig, replay_session
from stolgo.options.replay import IndianOptionCharges, OptionSlippage
from stolgo.core.types import Bar, Order, OrderType, Side
from stolgo.oms.order_book import OrderBook


def session(n=12):
    keys=tuple((side,k) for side in ('CE','PE') for k in range(24600,25601,50))
    p=np.empty((n,len(keys),5)); p[:,:,:4]=100.; p[:,:,4]=10000
    return OptionSession('NIFTY','2026-09-08','2026-09-08',0,65,50,
        pd.date_range('2026-09-08 09:29',periods=n,freq='min',tz='Asia/Kolkata').tz_convert('UTC').asi8,
        np.arange(569,569+n),np.full(n,25000.),keys,p)


def config(**kwargs):
    # The old ReplayConfig defaults are passed explicitly so these tests keep their meaning.
    return replace(ReplayConfig('test',scenario='STATIC',exit_minute=578,target=0.75,hard_loss=2500.0),**kwargs)


def test_cashflow_identity_and_next_open():
    s=session()
    for j in range(len(s.contracts)):
        s.prices[2:,j,:4]=90
    r=replay_session(s,config(),keep_path=True)
    assert r['status']=='COMPLETE'
    assert len(r['fills'])==4
    assert all(f['timestamp']>=f['signal_available_timestamp'] for f in r['fills'])
    assert r['fills'][0]['timestamp']==s.timestamps[1]
    manual=sum((1 if f['side']=='sell' else -1)*f['qty']*f['price']-f['fee'] for f in r['fills'])
    assert r['net_pnl']==pytest.approx(manual)
    assert r['gross_pnl']-r['fees']-r['slippage']==pytest.approx(manual)
    assert sum(t['net_pnl'] for t in r['trades'])==pytest.approx(manual)


def test_close_stop_cannot_fill_at_earlier_open():
    s=session(); j=s.contracts.index(('CE',25100))
    s.prices[2,j,:4]=[100,180,100,170]
    s.prices[3:,j,:4]=[300,310,290,300]
    r=replay_session(s,config())
    ce=[f for f in r['fills'] if f['option_type']=='CE' and f['side']=='buy'][0]
    assert ce['timestamp']==s.timestamps[3]
    assert ce['price']>=300
    assert r['net_pnl'] < -2500
    assert r['max_intraday_dd_inr']>2500


@pytest.mark.parametrize('side,open_,high,low,stop,expected',[
    (Side.BUY,100,120,90,110,110),(Side.BUY,130,140,125,110,130),
    (Side.SELL,100,120,80,90,90),(Side.SELL,70,80,60,90,70)])
def test_resting_stop_gap_and_intrabar_prices(side,open_,high,low,stop,expected):
    book=OrderBook()
    book.add(Order('1','X',side,OrderType.STOP,1,stop_price=stop))
    assert book.match(Bar(1,open_,high,low,open_,100,'X'))[0][1]==expected


def test_missing_held_quote_recovers_without_entry_price_fallback():
    s=session(); j=s.contracts.index(('CE',25100))
    s.prices[2:5,j,:]=np.nan
    s.prices[5:,j,:4]=200
    r=replay_session(s,config())
    assert r['reason']=='MISSING_HELD_QUOTE'
    ce=[f for f in r['fills'] if f['side']=='buy' and f['option_type']=='CE'][0]
    assert ce['timestamp']==s.timestamps[5]
    assert ce['price']>=200
    assert r['status']=='COMPLETE'


def test_unresolved_short_is_never_reported_zero_pnl():
    s=session(); j=s.contracts.index(('CE',25100)); s.prices[2:,j,:]=np.nan
    r=replay_session(s,config())
    assert r['status']=='UNRESOLVED' and np.isnan(r['net_pnl'])


@pytest.mark.parametrize('direction',[-1,1])
def test_conversion_has_two_shorts_and_sequential_fills(direction):
    s=session(); s.spot[2:]=25000+direction*100
    r=replay_session(s,config(scenario='ONE',max_adjustments=1))
    assert r['conversions']==1
    cf=[f for f in r['fills'] if f['reason']=='CONVERSION']
    assert len(cf)==2 and cf[0]['side']=='buy' and cf[1]['side']=='sell'
    assert cf[1]['timestamp']>cf[0]['timestamp']
    assert cf[1]['strike']==25000+direction*100
    assert r['orders']==6


@pytest.mark.parametrize('scenario',['A','B','C','D'])
def test_all_defenses_and_adjustment_cap(scenario):
    s=session(20); s.spot[2:5]=25100; s.spot[5:]=25300
    r=replay_session(s,config(scenario=scenario,max_adjustments=2,exit_minute=586))
    assert r['conversions']==1 and r['defenses']==1 and r['adjustments']==2
    assert r['status']=='COMPLETE'
    assert r['reason']=='TIME_EXIT'


def test_hard_stop_preempts_touch_conversion():
    s=session(); s.spot[2:]=25100
    j=s.contracts.index(('CE',25100)); s.prices[2:,j,:4]=180
    r=replay_session(s,config(scenario='D'))
    assert r['adjustments']==0 and r['reason']=='DAILY_STOP'


def test_future_prices_do_not_change_past_entry():
    a=session(); b=session(); b.prices[4:,:,:4]=500
    ra=replay_session(a,config()); rb=replay_session(b,config())
    assert ra['fills'][:2]==rb['fills'][:2]


def test_fees_are_dated_and_slippage_adverse():
    assert IndianOptionCharges('NIFTY','2024-09-30').stt==.000625
    assert IndianOptionCharges('NIFTY','2024-10-01').stt==.001
    assert IndianOptionCharges('NIFTY','2026-04-01').stt==.0015
    assert OptionSlippage(.005,.05).adjust(Side.BUY,100,65)==100.5
    assert OptionSlippage(.005,.05).adjust(Side.SELL,100,65)==99.5


def test_close_only_stops_do_not_invent_intrabar_path():
    s=session(); s.prices[2,:,1]=1000
    r=replay_session(s,config())
    assert r['reason']=='TIME_EXIT'


@pytest.mark.parametrize('scenario',['B','D'])
def test_uncapped_defenses_do_not_silently_lock(scenario):
    s=session(26)
    s.spot[2:5]=25100; s.spot[5:10]=25300
    s.spot[10:15]=25100; s.spot[15:]=25300
    r=replay_session(s,config(scenario=scenario,max_adjustments=99,exit_minute=592))
    assert r['defenses']>=2
    assert r['adjustments']==1+r['defenses']
    assert r['status']=='COMPLETE'


def test_failed_replacement_closes_retained_short():
    s=session(); s.spot[2:]=25100
    j=s.contracts.index(('PE',25100)); s.prices[4,j,:]=np.nan
    r=replay_session(s,config(scenario='ONE',max_adjustments=1))
    assert r['reason']=='REPLACEMENT_REJECTED'
    assert r['status']=='COMPLETE'
    assert r['adjustments']==0
    assert len([f for f in r['fills'] if f['side']=='sell'])==2


def _target_session():
    s=session()
    s.prices[3:,:,:4]=10  # both short legs collapse: old default target (0.75) is hit
    return s


def _stop_session():
    s=session(); j=s.contracts.index(('CE',25100))
    s.prices[3:,j,:4]=300  # one leg triples: old default hard loss (2500) is hit
    return s


def test_default_config_has_no_target_or_daily_stop():
    cfg=ReplayConfig('test',scenario='STATIC',exit_minute=578)
    assert cfg.target is None and cfg.hard_loss is None
    for s in (_target_session(),_stop_session()):
        r=replay_session(s,cfg)
        assert r['status']=='COMPLETE'
        assert r['reason']=='TIME_EXIT'
    assert np.isnan(r['stop_overshoot'])


def test_explicit_old_values_reproduce_old_exits():
    old=ReplayConfig('test',scenario='STATIC',exit_minute=578,target=0.75,hard_loss=2500.0)
    assert replay_session(_target_session(),old)['reason']=='PORTFOLIO_TARGET'
    assert replay_session(_stop_session(),old)['reason']=='DAILY_STOP'


def test_result_records_full_replay_config():
    from dataclasses import asdict
    cfg=ReplayConfig('test',scenario='STATIC',exit_minute=578,target=0.5)
    r=replay_session(session(),cfg)
    assert r['config']==asdict(cfg)
    assert r['config']['target']==0.5 and r['config']['hard_loss'] is None


def test_non_positive_hard_loss_still_rejected():
    with pytest.raises(ValueError):
        ReplayConfig('test',hard_loss=0.0)


def test_static_does_not_require_spot_after_entry():
    s = session()
    s.spot[2:] = np.nan
    result = replay_session(s, config())
    assert result["status"] == "COMPLETE"
    assert result["reason"] == "TIME_EXIT"


def test_touch_strategy_still_requires_spot_after_entry():
    s = session()
    s.spot[2] = np.nan
    assert replay_session(s, config(scenario="EXIT_TOUCH"))["reason"] == "MISSING_SPOT"
