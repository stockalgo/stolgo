"""Multi-contract intraday short-options replay.

EXPERIMENTAL: this API may change without notice between releases. See the
"Known limitations" section of ``docs/OPTIONS_REPLAY.md``.

This specialized runner extends the single-symbol Engine: every actual fill is
matched by Stolgo SimBroker, with one broker per immutable contract. It does not
pretend that the price of a synthetic spread has a tradeable OHLC path.
No bid/ask, SPAN margin or tick liquidity is implied by minute trade-price data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math

import numpy as np

from stolgo.core.exceptions import AccountingError
from stolgo.core.types import Bar, OrderType, Side
from stolgo.oms.fill_model import NextOpenFill
from stolgo.oms.sim_broker import SimBroker


@dataclass
class OptionSession:
    index: str
    date: str
    expiry: str
    dte: int
    lot: int
    step: int
    timestamps: np.ndarray  # UTC nanoseconds; minute START labels
    minutes: np.ndarray  # IST minutes from midnight, including absent minutes
    spot: np.ndarray  # observable only once that minute completes
    contracts: tuple[tuple[str, int], ...]
    prices: np.ndarray  # [time, contract, open/high/low/close/volume]; missing=NaN
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.prices.shape != (len(self.timestamps), len(self.contracts), 5):
            raise ValueError("Invalid option array shape")
        if len(set(self.contracts)) != len(self.contracts):
            raise ValueError("Duplicate contract identity")
        if len(self.spot) != len(self.timestamps) or len(self.minutes) != len(self.timestamps):
            raise ValueError("Mismatched session arrays")
        if np.any(np.diff(self.timestamps) != 60_000_000_000):
            raise ValueError("Session must have an explicit continuous minute grid")
        if self.lot <= 0 or self.step <= 0:
            raise ValueError("Invalid contract multiplier/grid")


@dataclass(frozen=True)
class ReplayConfig:
    name: str
    scenario: str = "EXIT_TOUCH"  # STATIC, EXIT_TOUCH, ONE, A, B, C, D, CUT
    max_adjustments: int = 2
    deep_steps: int = 2
    wing_steps: int = 1
    initial_steps: int = 2
    target: float | None = None  # fraction of initial credit; None disables the profit target
    hard_loss: float | None = None  # whole-session loss in INR, never reset by roll; None disables the daily stop
    slippage_pct: float = 0.005
    tick: float = 0.05
    latency_bars: int = 1
    entry_minute: int = 570  # 09:30 fill, decision from 09:29 completed bar
    exit_minute: int = 885  # 14:45 exit submission/fill when quote exists
    no_new_risk_minute: int = 840
    leg_stop: float | None = None  # close WHOLE position if one leg exceeds limit
    cost_mode: str = "dated"  # dated retail approximation or forward tariff stress

    def __post_init__(self):
        if self.scenario not in {"STATIC", "EXIT_TOUCH", "ONE", "A", "B", "C", "D", "CUT"}:
            raise ValueError("Unknown scenario")
        if self.latency_bars < 1 or self.max_adjustments < 0 or self.initial_steps < 1:
            raise ValueError("Invalid replay settings")
        if self.slippage_pct < 0 or self.tick <= 0:
            raise ValueError("Invalid cost/risk inputs")
        if self.hard_loss is not None and self.hard_loss <= 0:
            raise ValueError("Invalid cost/risk inputs")


class OptionSlippage:
    def __init__(self, pct: float, tick: float):
        self.pct, self.tick = pct, tick

    def adjust(self, side: Side, price: float, qty: float) -> float:
        adverse = max(self.tick, math.ceil(price * self.pct / self.tick - 1e-10) * self.tick)
        raw = price + adverse if side == Side.BUY else price - adverse
        ticks = math.ceil(raw / self.tick - 1e-10) if side == Side.BUY else math.floor(raw / self.tick + 1e-10)
        return round(max(0.0, ticks * self.tick), 8)


class IndianOptionCharges:
    """Explicit per-order charges; early exchange slabs are a disclosed retail proxy.

    NSE exchange+IPFT: 0.0500% before Oct 2024, 0.03553% afterwards.
    BSE proxy 0.0500% before Oct 2024 (conservative, not historical slab exact),
    then 0.0325%. Forward stress uses STT 0.15% and current combined exchange rate.
    """
    def __init__(self, index: str, date: str, mode: str = "dated"):
        self.stt = 0.0015 if mode == "forward" or date >= "2026-04-01" else (0.001 if date >= "2024-10-01" else 0.000625)
        self.exchange = (0.0003553 if index == "NIFTY" else 0.000325) if mode == "forward" or date >= "2024-10-01" else 0.0005

    def fee(self, side: Side, price: float, qty: float) -> float:
        turnover = price * qty
        broker, exchange, sebi = 20.0, turnover * self.exchange, turnover * 0.000001
        gst = (broker + exchange + sebi) * 0.18
        stt = turnover * self.stt if side == Side.SELL else 0.0
        stamp = turnover * 0.00003 if side == Side.BUY else 0.0
        return round(broker + exchange + sebi + gst + stt + stamp, 2)


def replay_session(s: OptionSession, cfg: ReplayConfig, *, keep_path: bool = False) -> dict:
    """Replay one session. Unknown open exposure produces NaN P&L, never a fake fill.

    Targets/stops use synchronous completed-minute liquidation marks; hence even
    'hard' stops can overshoot. No intrabar high/low order is invented. Replacement
    shorts open at least one full bar after old shorts close. Risk exits preempt
    pending opening risk. Ordinary entries require positive observed bar volume,
    which is a coarse fill assumption, not proof of liquidity at the open.

    ``cfg.target`` and ``cfg.hard_loss`` are off when ``None`` (the default); the
    returned dict carries the full ``ReplayConfig`` under ``config`` so a saved
    result shows which exit rules were active.
    """
    p = s.prices
    lookup = {key: j for j, key in enumerate(s.contracts)}
    slip = OptionSlippage(cfg.slippage_pct, cfg.tick)
    charges = IndianOptionCharges(s.index, s.date, cfg.cost_mode)
    brokers = {}
    open_legs = {}  # contract column -> filled entry record
    fills, trades, path, decisions = [], [], [], []
    cash = raw_cash = fees = slippage = 0.0
    peak_pnl = worst_pnl = 0.0
    max_dd_inr = 0.0
    adjustments = conversions = defenses = 0
    state, exit_reason, status = "FLAT", "", "SKIPPED"
    pending = None
    initial_credit = 0.0
    reference = None
    initial_ce = initial_pe = None
    missing_marks = 0
    reject_reason = ""
    initial_entry_i = next((i for i, m in enumerate(s.minutes) if m == cfg.entry_minute), None)
    if initial_entry_i is None or initial_entry_i < 1:
        return dict(index=s.index, date=s.date, expiry=s.expiry, dte=s.dte, strategy=cfg.name,
                    status="SKIPPED", reason="missing_entry_grid", net_pnl=0.0, fills=[], trades=[], path=[], decisions=[],
                    config=asdict(cfg))

    def valid(j, i, field=0):
        a = p[i, j]
        return np.all(np.isfinite(a)) and a[field] >= cfg.tick and a[4] > 0

    def symbol(j):
        side, strike = s.contracts[j]
        return f"{s.index}:{s.expiry}:{strike}:{side}"

    def execute(j, side, i, reason, signal_i):
        nonlocal cash, raw_cash, fees, slippage
        # Every fill uses an actual later available contract bar through Stolgo OMS.
        if not (i > signal_i):
            raise AccountingError(f"Execute bar index {i} must be greater than signal bar index {signal_i}")
        if j not in brokers:
            brokers[j] = SimBroker(NextOpenFill(), slip, charges)
        broker = brokers[j]
        order = broker.create_order(symbol(j), side, s.lot, OrderType.MARKET)
        broker.submit(order)
        a = p[i, j]
        bar = Bar(int(s.timestamps[i]), *map(float, a[:4]), float(a[4]), symbol(j))
        events = broker.match(bar, bar_index=i)
        if len(events) != 1:
            raise AccountingError(f"Expected exactly 1 fill event, got {len(events)}")
        f = events[0].fill
        direction = 1 if side == Side.SELL else -1
        cash += direction * f.price * f.qty - f.commission
        raw_cash += direction * a[0] * f.qty
        fees += f.commission
        impact = abs(f.price - a[0]) * f.qty
        slippage += impact
        rec = dict(contract=symbol(j), option_type=s.contracts[j][0], strike=s.contracts[j][1],
                   timestamp=int(f.ts), signal_timestamp=int(s.timestamps[signal_i]),
                   signal_available_timestamp=int(s.timestamps[signal_i] + 60_000_000_000),
                   side=side.value, qty=f.qty, raw_price=float(a[0]), price=f.price,
                   fee=f.commission, slippage=impact, reason=reason)
        fills.append(rec)
        if side == Side.SELL:
            if j in open_legs:
                raise AccountingError(f"Contract {j} already in open_legs")
            open_legs[j] = rec
        else:
            entry = open_legs.pop(j)
            gross = (entry["raw_price"] - a[0]) * s.lot
            net = (entry["price"] - f.price) * s.lot - entry["fee"] - f.commission
            trades.append(dict(contract=symbol(j), entry_ts=entry["timestamp"], exit_ts=f.ts,
                               entry_price=entry["price"], exit_price=f.price, qty=s.lot,
                               gross_pnl=float(gross), net_pnl=float(net),
                               commission=entry["fee"] + f.commission,
                               slippage=entry["slippage"] + impact, tag=reason))
        return rec

    def liquidation(i):
        # Missing marks force liquidation/recovery; stale values are diagnostic only.
        value = cash
        missing = False
        for j in open_legs:
            px = p[i, j, 3]
            if not np.isfinite(px) or px <= 0:
                missing = True
                value = float("nan")
                continue
            out = slip.adjust(Side.BUY, float(px), s.lot)
            value -= out * s.lot + charges.fee(Side.BUY, out, s.lot)
        return value, missing

    def queue_exit(i, why):
        nonlocal pending, state, exit_reason
        pending = dict(due=i + cfg.latency_bars, signal=i, close=list(open_legs), new=[], stage="exit", reason=why)
        state, exit_reason = "EXIT_PENDING", why
        decisions.append(dict(minute=int(s.minutes[i]), action=why, adjustments=adjustments))

    def opening_columns(keys):
        return [lookup.get(k, -1) for k in keys]

    for i in range(initial_entry_i - 1, len(s.minutes)):
        minute = int(s.minutes[i])
        # Risk known from previous close is checked before executing opening risk.
        # Previous loop can replace pending adjustments with an exit.
        if pending and i >= pending["due"]:
            stage = pending["stage"]
            if stage in {"exit", "roll_close"}:
                for j in list(pending["close"]):
                    if j not in open_legs:
                        pending["close"].remove(j)
                    elif valid(j, i):
                        execute(j, Side.BUY, i, pending["reason"], pending["signal"])
                        pending["close"].remove(j)
                if not pending["close"]:
                    if stage == "exit":
                        pending, state = None, "DONE"
                        break
                    pending = {**pending, "stage": "roll_open", "due": i + cfg.latency_bars, "signal": i}
            elif stage in {"entry", "roll_open"}:
                columns = pending["new"]
                can_open = minute < cfg.no_new_risk_minute and all(j >= 0 and valid(j, i) and slip.adjust(Side.SELL, float(p[i,j,0]),s.lot)>0 for j in columns)
                if can_open:
                    new_fills = [execute(j, Side.SELL, i, pending["reason"], pending["signal"]) for j in columns]
                    if stage == "entry":
                        initial_credit = sum(f["price"] * s.lot for f in new_fills)
                        state, status = "INITIAL", "COMPLETE"
                    else:
                        adjustments += 1
                        if pending["reason"] == "CONVERSION":
                            conversions += 1
                        else:
                            defenses += 1
                        reference = pending["reference"]
                        state = "ADJUSTED"
                    pending = None
                else:
                    reject_reason = "opening_quote_or_cutoff"
                    if stage == "entry":
                        state, pending = "DONE", None
                        break
                    queue_exit(i, "REPLACEMENT_REJECTED")
        if state == "DONE":
            break
        value, missing = liquidation(i)
        if open_legs and missing:
            missing_marks += 1
            if state != "EXIT_PENDING":
                queue_exit(i, "MISSING_HELD_QUOTE")
        if np.isfinite(value):
            peak_pnl = max(peak_pnl, value)
            worst_pnl = min(worst_pnl, value)
            max_dd_inr = max(max_dd_inr, peak_pnl - value)
        if keep_path:
            path.append((int(s.timestamps[i] + 60_000_000_000), value, len(open_legs)))
        # Mark-to-market and risk priorities apply even during a multi-step roll.
        if open_legs and state != "EXIT_PENDING":
            if cfg.hard_loss is not None and np.isfinite(value) and value <= -cfg.hard_loss:
                queue_exit(i, "DAILY_STOP")
            elif minute + 1 >= cfg.exit_minute:
                queue_exit(i, "TIME_EXIT")
            elif cfg.target is not None and initial_credit and np.isfinite(value) and value >= cfg.target * initial_credit:
                queue_exit(i, "PORTFOLIO_TARGET")
            elif cfg.leg_stop is not None and any(np.isfinite(p[i,j,3]) and p[i,j,3] >= e["price"] * (1 + cfg.leg_stop) for j,e in open_legs.items()):
                queue_exit(i, "LEG_THRESHOLD_CLOSE_ALL")
        # No new risk after a realized stop during a flat interval between rolls.
        if cfg.hard_loss is not None and pending and pending["stage"] == "roll_open" and cash <= -cfg.hard_loss:
            queue_exit(i, "DAILY_STOP")
        if pending or state == "EXIT_PENDING":
            continue
        if state == "FLAT" and i == initial_entry_i - 1:
            spot = s.spot[i]
            if not np.isfinite(spot):
                reject_reason = "missing_entry_spot"
                break
            atm = int(math.floor(spot / s.step + .5) * s.step)
            initial_ce, initial_pe = atm + cfg.initial_steps*s.step, atm - cfg.initial_steps*s.step
            cols = opening_columns([("CE",initial_ce),("PE",initial_pe)])
            if any(j < 0 or not valid(j,i,3) for j in cols):
                reject_reason = "missing_entry_contract_quote"
                break
            pending = dict(due=i+cfg.latency_bars, signal=i, new=cols, stage="entry", reason="ENTRY")
            continue
        # STATIC has no spot-based adjustment or touch rule after entry.
        # Its price/time/risk exits above still run when spot is unavailable.
        if cfg.scenario == "STATIC":
            continue
        if not open_legs or not np.isfinite(s.spot[i]):
            if open_legs and state != "EXIT_PENDING":
                queue_exit(i, "MISSING_SPOT")
            continue
        spot = float(s.spot[i])
        if state == "INITIAL" and (spot >= initial_ce or spot <= initial_pe):
            if cfg.scenario == "EXIT_TOUCH" or cfg.max_adjustments == 0 or minute+1 >= cfg.no_new_risk_minute:
                queue_exit(i, "FIRST_TOUCH_EXIT")
                continue
            k = initial_ce if spot >= initial_ce else initial_pe
            winning = "PE" if spot >= initial_ce else "CE"
            closing = [j for j in open_legs if s.contracts[j][0] == winning]
            new = opening_columns([(winning,k)])
            if len(open_legs) != 2 or len(closing) != 1 or new[0] < 0 or not valid(new[0],i,3):
                queue_exit(i, "INVALID_CONVERSION")
                continue
            pending = dict(due=i+cfg.latency_bars, signal=i, close=closing, new=new,
                           stage="roll_close", reason="CONVERSION", reference=k)
            decisions.append(dict(minute=minute, action="CONVERSION", adjustments=adjustments))
        elif state == "ADJUSTED" and cfg.scenario != "ONE" and abs(spot-reference) >= cfg.deep_steps*s.step:
            if adjustments >= cfg.max_adjustments:
                continue  # cap prevents new risk, never disables loss/time/target exits
            action = cfg.scenario
            atm = int(math.floor(spot/s.step + .5)*s.step)
            if minute+1 >= cfg.no_new_risk_minute or action == "CUT":
                queue_exit(i,"DEFENSE_CASH")
                continue
            if action == "C":
                # Price the proposed ATM pair, using synchronized known CLOSEs.
                cols = opening_columns([("CE",atm),("PE",atm)])
                if any(j<0 or not valid(j,i,3) for j in cols):
                    queue_exit(i,"MISSING_CANDIDATE")
                    continue
                premium = sum(p[i,j,3] for j in cols)
                floor = 15 if s.index == "NIFTY" else 45
                if premium < floor:
                    queue_exit(i,"LOW_CANDIDATE_PREMIUM")
                    continue
                action = "A" if minute+1 < 750 else "B"
            if action in {"A","B"}:
                width = 0 if action=="A" else cfg.wing_steps*s.step
                keys = [("CE",atm+width),("PE",atm-width)]
                closing = list(open_legs)
            elif action == "D":
                winning = "PE" if spot >= reference else "CE"
                keys = [(winning,atm)]
                closing = [j for j in open_legs if s.contracts[j][0]==winning]
            else:
                raise ValueError(f"Unsupported action {action}")
            new = opening_columns(keys)
            if len(open_legs)!=2 or not closing or any(j<0 or not valid(j,i,3) for j in new):
                queue_exit(i,"INVALID_DEFENSE")
                continue
            pending = dict(due=i+cfg.latency_bars, signal=i, close=closing,new=new,
                           stage="roll_close",reason=f"DEFENSE_{action}",reference=atm)
            decisions.append(dict(minute=minute,action=f"DEFENSE_{action}",adjustments=adjustments))
    if open_legs:
        status = "UNRESOLVED"
        net = float("nan")
        exit_reason = "NO_EXECUTABLE_EXIT_BEFORE_DATA_END"
    else:
        net = cash
        if abs(raw_cash - fees - slippage - net) >= 1e-6:
            raise AccountingError(
                f"Replay raw_cash - fees - slippage != net: {raw_cash} - {fees} - {slippage} != {net}"
            )
        if abs(sum(t["net_pnl"] for t in trades) - net) >= 1e-6:
            raise AccountingError(
                f"Replay sum(trades.net_pnl) != net: {sum(t['net_pnl'] for t in trades)} != {net}"
            )
        worst_pnl = min(worst_pnl, net)
        max_dd_inr = max(max_dd_inr, peak_pnl - net)
    if keep_path and fills and not open_legs:
        path.append((fills[-1]["timestamp"], net, 0))
    return dict(index=s.index,date=s.date,expiry=s.expiry,dte=s.dte,strategy=cfg.name,
                status=status,reason=exit_reason or reject_reason,lot=s.lot,
                net_pnl=net,gross_pnl=raw_cash,fees=fees,slippage=slippage,
                conversions=conversions,defenses=defenses,adjustments=adjustments,
                orders=len(fills),worst_mtm=worst_pnl,max_intraday_dd_inr=max_dd_inr,
                stop_overshoot=max(0,-net-cfg.hard_loss) if cfg.hard_loss is not None and np.isfinite(net) else float("nan"),
                missing_marks=missing_marks,initial_credit=initial_credit,
                fills=fills,trades=trades,path=path,decisions=decisions,
                config=asdict(cfg))
