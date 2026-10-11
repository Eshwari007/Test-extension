"""Event-driven loop replaying bars through signals -> risk -> execution -> SimBroker.

Per bar t (a CLOSED bar on the candidate's signal timeframe):
  1. fill orders queued at t-1's close against t's open;
  2. check stops against t's low (gap-through at the open is modeled);
  3. mark to t's close, update peak equity, evaluate the drawdown governor;
  4. manage open positions (ladders, trails, time exits) -> queue sells;
  5. if the regime is off and the candidate exits on regime-off, flatten;
  6. generate entries (unless the governor blocks them) -> queue buys.

Deterministic: the same data and config produce byte-identical results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .broker import Order, SimBroker, make_client_order_id
from .config import Spec
from .data import eligible_at
from .execution import DecisionLog, ExecutionEngine
from .portfolio import Fill, Portfolio
from .reporting import compute_metrics
from .risk import GovernorLevel, RiskManager
from .signals import BarContext, Strategy


@dataclass
class BacktestResult:
    candidate: str
    variant: str | None
    tier: str
    config_hash: str
    timeframe: str
    equity: pd.Series
    trades: pd.DataFrame
    exposure: pd.Series
    fills: list[Fill]
    governor_events: list[dict[str, Any]]
    killed: bool
    decision_log: pd.DataFrame
    rejections: pd.DataFrame
    params: dict[str, Any] = field(default_factory=dict)

    def metrics(self) -> dict[str, Any]:
        m = compute_metrics(self.equity, self.trades, self.timeframe, self.exposure)
        m["killed"] = self.killed
        m["governor_events"] = len(self.governor_events)
        return m


def run_backtest(
    spec: Spec,
    strategy: Strategy,
    bars: dict[str, pd.DataFrame],
    btc_daily: pd.DataFrame,
    btc_signal: pd.DataFrame | None = None,
    tier: str = "T2",
    eligibility: pd.DataFrame | None = None,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    initial_cash: float = 10_000.0,
    stress: bool = False,
    taker_everywhere: bool = False,
    measured_spread: dict[str, float] | None = None,
) -> BacktestResult:
    risk_tier = spec.tiers[tier]
    if btc_signal is None:
        btc_signal = btc_daily
    strategy.prepare(bars, btc_daily, btc_signal)
    frames = strategy.feature_frames
    btc = strategy.btc_frame
    assert btc is not None

    portfolio = Portfolio(initial_cash)
    broker = SimBroker(spec.costs, spec.coin_tier, stress=stress, taker_everywhere=taker_everywhere)
    broker.measured_spread = dict(measured_spread or {})
    risk = RiskManager(risk_tier, spec.governor, spec.max_order_notional_usd, spec.coin_tier)
    execution = ExecutionEngine(broker, risk, portfolio, DecisionLog())

    # ---- timeline and row lookups ---------------------------------------------
    t0 = to_utc(start)
    t1 = to_utc(end)
    all_times: set[pd.Timestamp] = set()
    row_maps: dict[str, dict[pd.Timestamp, int]] = {}
    for sym, df in frames.items():
        idx = df.index
        row_maps[sym] = {t: i for i, t in enumerate(idx)}
        sel = idx
        if t0 is not None:
            sel = sel[sel >= t0]
        if t1 is not None:
            sel = sel[sel <= t1]
        all_times.update(sel)
    timeline = sorted(all_times)
    btc_index = btc.index

    prices: dict[str, float] = {}
    exposure_rows: list[tuple[pd.Timestamp, float]] = []
    governor_events: list[dict[str, Any]] = []
    last_level = GovernorLevel.NORMAL
    killed = False
    extra = {"exposure_cap": risk_tier.gross_exposure_cap}

    for t in timeline:
        bars_now: dict[str, pd.Series] = {}
        rows: dict[str, int] = {}
        for sym, rm in row_maps.items():
            i = rm.get(t)
            if i is not None:
                rows[sym] = i
                bars_now[sym] = frames[sym].iloc[i]

        # 1-2. fills at the open, then stops against the low
        execution.process_pending(t, bars_now)
        execution.check_stops(t, bars_now)

        # 3. mark at the close
        for sym, bar in bars_now.items():
            prices[sym] = float(bar["close"])
        equity = portfolio.mark(t, prices)
        exposure_rows.append((t, portfolio.gross_exposure(prices) / equity if equity > 0 else 0.0))
        level = risk.governor_level(portfolio.drawdown(prices))
        if level != last_level:
            governor_events.append({"time": t, "from": last_level.name, "to": level.name, "equity": equity,
                                    "drawdown": portfolio.drawdown(prices)})
            last_level = level

        bi = int(btc_index.searchsorted(t, side="right")) - 1
        if bi < 0:
            continue  # no BTC history yet: nothing to decide
        ctx = BarContext(time=t, features=frames, row=rows, btc=btc, btc_row=bi,
                         eligible=_eligible(eligibility, t, rows), portfolio=portfolio, prices=prices, extra=extra)

        if level >= GovernorLevel.FLATTEN:
            if level == GovernorLevel.KILL:
                killed = True
            execution.flatten(ctx, f"governor:{level.name.lower()}")
            if killed and not portfolio.positions and not execution.pending:
                break
            continue

        # 4. manage open positions
        for sym, pos in list(portfolio.positions.items()):
            if sym not in rows:
                continue
            pos.bars_held += 1
            for intent in strategy.manage(ctx, pos):
                execution.queue_exit(intent, ctx)

        # 5. regime-off exit (C3)
        if strategy.exit_all_when_regime_off() and not strategy.regime_on(ctx):
            execution.flatten(ctx, "regime_off")
            continue

        # 6. entries
        if level < GovernorLevel.BLOCK:
            for intent in strategy.entries(ctx):
                execution.queue_entry(intent, ctx, level)

    # Close anything still open at the final mark so every trade is realized.
    if portfolio.positions and timeline:
        t = timeline[-1]
        for sym, pos in list(portfolio.positions.items()):
            if sym not in prices:
                continue
            bar = pd.Series({"open": prices[sym], "high": prices[sym], "low": prices[sym], "close": prices[sym]})
            order = Order(sym, "sell", pos.qty, "market", reason="end_of_test")
            order.client_order_id = make_client_order_id(order, salt=f"eot{t}")
            fill = broker.submit(order, bar=bar, time=t)
            if fill is not None:
                portfolio.apply_fill(fill)
        portfolio.equity_curve[-1] = (t, portfolio.equity(prices))

    exposure = pd.Series(dict(exposure_rows), dtype=float)
    return BacktestResult(
        candidate=strategy.id,
        variant=strategy.variant,
        tier=tier,
        config_hash=spec.config_hash(),
        timeframe=strategy.signal_timeframe,
        equity=portfolio.equity_series(),
        trades=portfolio.trades_frame(),
        exposure=exposure,
        fills=portfolio.fills,
        governor_events=governor_events,
        killed=killed,
        decision_log=execution.log.frame(),
        rejections=pd.DataFrame(execution.rejections),
        params={"stress": stress, "taker_everywhere": taker_everywhere, "initial_cash": initial_cash,
                "start": str(start), "end": str(end), **strategy.parameter_grid()},
    )


def to_utc(x) -> pd.Timestamp | None:
    """Accept None, a string, a naive or a tz-aware Timestamp and return a UTC Timestamp."""
    if x is None:
        return None
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _eligible(table: pd.DataFrame | None, t: pd.Timestamp, rows: dict[str, int]) -> set[str]:
    have_bar = set(rows)
    if table is None or table.empty:
        return have_bar
    return eligible_at(table, t) & have_bar


def benchmark_buy_and_hold(bars: dict[str, pd.DataFrame], start=None, end=None, initial_cash: float = 10_000.0) -> pd.Series:
    """Equal-weight buy-and-hold equity curve over the given symbols (rebalanced never)."""
    closes = pd.concat({s: df["close"] for s, df in bars.items()}, axis=1).sort_index()
    if start is not None:
        closes = closes[closes.index >= to_utc(start)]
    if end is not None:
        closes = closes[closes.index <= to_utc(end)]
    closes = closes.dropna(how="all")
    first = closes.apply(lambda c: c.dropna().iloc[0] if c.notna().any() else np.nan)
    weights = initial_cash / len(first.dropna())
    units = weights / first
    value = (closes * units).sum(axis=1, min_count=1)
    value.name = "equity"
    return value
