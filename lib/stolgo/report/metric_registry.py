from dataclasses import asdict, dataclass
from typing import Literal

Unit = Literal["inr", "fraction", "ratio", "count", "sessions", "r"]


@dataclass(frozen=True)
class MetricDef:
    key: str
    label: str
    unit: Unit
    decimals: int
    better: Literal["higher", "lower", "none"]
    help: str


METRICS: tuple[MetricDef, ...] = (
    MetricDef("net_pnl", "Net P&L", "inr", 0, "higher", "Sum of net trade P&L after fees and slippage."),
    MetricDef("gross_pnl", "Gross P&L", "inr", 0, "higher", "Sum of trade P&L before fees and slippage."),
    MetricDef("fees", "Fees", "inr", 0, "lower", "Brokerage + statutory charges."),
    MetricDef("slippage", "Slippage", "inr", 0, "lower", "Modelled execution slippage."),
    MetricDef("total_return", "Total return", "fraction", 1, "higher", "Net P&L ÷ capital."),
    MetricDef("cagr", "CAGR", "fraction", 1, "higher", "Annualised over elapsed calendar time of the window."),
    MetricDef("sharpe", "Sharpe", "ratio", 2, "higher", "Mean/stdev of daily returns over every session × √252. Risk-free = 0."),
    MetricDef("sortino", "Sortino", "ratio", 2, "higher", "Mean daily return ÷ downside RMS × √252."),
    MetricDef("calmar", "Calmar", "ratio", 2, "higher", "CAGR ÷ |max drawdown|."),
    MetricDef("max_drawdown", "Max drawdown", "fraction", 1, "higher", "Worst peak-to-trough of daily equity incl. initial capital."),
    MetricDef("max_drawdown_duration", "Longest drawdown", "sessions", 0, "lower", "Sessions spent below a prior peak."),
    MetricDef("intraday_max_drawdown", "Intraday max DD", "fraction", 1, "higher", "From mark-to-market path, when available."),
    MetricDef("volatility", "Volatility", "fraction", 1, "lower", "Annualised stdev of daily returns."),
    MetricDef("worst_day", "Worst day", "inr", 0, "higher", "Lowest daily P&L."),
    MetricDef("expected_shortfall_95", "ES 95%", "inr", 0, "higher", "Mean of the worst 5% daily P&L."),
    MetricDef("num_trades", "Trades", "count", 0, "none", "Closed position lifecycles."),
    MetricDef("hit_rate", "Hit rate", "fraction", 1, "higher", "Share of trades with net P&L > 0."),
    MetricDef("profit_factor", "Profit factor", "ratio", 2, "higher", "Gross wins ÷ gross losses. Null when no losses."),
    MetricDef("payoff", "Payoff", "ratio", 2, "higher", "Average win ÷ |average loss|."),
    MetricDef("avg_win", "Avg win", "inr", 0, "higher", ""),
    MetricDef("avg_loss", "Avg loss", "inr", 0, "higher", ""),
    MetricDef("expectancy", "Expectancy", "inr", 0, "higher", "Mean net P&L per trade (₹, not R)."),
    MetricDef("avg_r", "Avg R", "r", 2, "higher", "Mean r_multiple over trades where R is known."),
    MetricDef("final_equity", "Final equity", "inr", 0, "higher", "Capital + net P&L."),
)


def metric_defs() -> list[dict]:
    return [asdict(m) for m in METRICS]
