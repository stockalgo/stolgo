# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D
# [ ] no look-ahead: only data[:t+1] in strategy loop
# [ ] no pandas in oms/portfolio hot path
# [ ] no bandl imports outside stolgo.data / stolgo.broker
# [ ] fill default = next_open unless RunConfig.fill_on == "close"
# [ ] pytest tests for this module pass before next build step

"""Binance USDT-M perpetual futures symbol universe (HLD §4.2 ext).

Thin helper on top of the `bandl` client's crypto facet — lists actively
trading Binance perpetual contracts and optionally filters by minimum 24h
quote volume, for use as the scan universe of multi-symbol screeners (e.g.
:mod:`stolgo.strategy.builtins.parabolic_short`).

Network calls only happen when :func:`get_binance_perp_universe` is invoked
explicitly by the caller (never at import time or inside a strategy loop).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PerpSymbol:
    """A single Binance USDT-M perpetual, with its trailing 24h quote volume."""

    symbol: str
    base: str
    quote: str
    quote_volume_24h: float


def get_binance_perp_universe(
    client=None,
    *,
    min_quote_volume_usd: float = 0.0,
    quote_asset: str | None = "USDT",
    limit: int | None = None,
) -> list[PerpSymbol]:
    """Return actively-trading Binance USDT-M perpetual symbols.

    Parameters
    ----------
    client:
        A `bandl.Bandl()` instance; a new one is constructed if omitted.
    min_quote_volume_usd:
        Minimum rolling 24h quote (USDT) volume required to include a symbol.
        Use this to exclude illiquid/manipulated perpetuals from the scan
        universe. Default 0.0 = no filter.
    quote_asset:
        Restrict to this quote asset (default "USDT"). Pass None to include
        all quote assets returned by the exchange.
    limit:
        Optional cap on the number of symbols returned (post-filter, sorted
        by descending 24h quote volume).

    Returns
    -------
    list[PerpSymbol]
        Sorted by descending 24h quote volume.
    """
    if client is None:
        from bandl import Bandl

        client = Bandl()

    from bandl.models.market.types import AssetType

    symbol_infos = client.crypto.list_symbols(source="binance", asset_type=AssetType.CRYPTO_PERP)
    tickers = client.crypto.get_24hr_tickers(source="binance", asset_type=AssetType.CRYPTO_PERP)
    volume_by_symbol = {t.symbol.upper(): float(t.volume_24h or 0.0) for t in tickers}
    # Ticker.volume_24h is base-asset volume for Binance; approximate quote
    # volume as volume_24h * last_price when quote volume isn't directly
    # exposed on the Ticker model (last_price always is).
    quote_volume_by_symbol = {
        t.symbol.upper(): float((t.volume_24h or 0.0) * (t.last_price or 0.0)) for t in tickers
    }

    out: list[PerpSymbol] = []
    for info in symbol_infos:
        if quote_asset is not None and (info.quote or "").upper() != quote_asset.upper():
            continue
        qvol = quote_volume_by_symbol.get(info.canonical.upper())
        if qvol is None:
            # Fall back to base-asset volume proxy if 24h ticker missing this symbol.
            qvol = volume_by_symbol.get(info.canonical.upper(), 0.0)
        if qvol < min_quote_volume_usd:
            continue
        out.append(
            PerpSymbol(
                symbol=info.canonical.upper(),
                base=info.base.upper(),
                quote=info.quote.upper(),
                quote_volume_24h=qvol,
            )
        )

    out.sort(key=lambda p: p.quote_volume_24h, reverse=True)
    if limit is not None:
        out = out[:limit]
    return out
