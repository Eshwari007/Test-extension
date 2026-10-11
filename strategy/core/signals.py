"""One class per candidate (C1, C2, C3). Signals output intents, never orders.

Contract used by the backtest loop and by live execution alike:

  * `prepare(bars, btc_daily, btc_signal_tf)` precomputes features over the
    full history. Every feature is causal (see features.py), so reading row
    t of a precomputed frame equals recomputing on data truncated at t.
  * `regime_on(ctx)`            -> bool, from BTC closes through ctx.time.
  * `entries(ctx)`              -> EntryIntents for symbols with no position.
  * `manage(ctx, position)`     -> ExitIntents for an open position and may
                                   move `position.stop` (never downward).

A stop is always carried on the Position and enforced by the execution layer
against intrabar lows; signals only decide where it sits.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from . import features as F
from .portfolio import Portfolio, Position


@dataclass
class EntryIntent:
    symbol: str
    stop: float | None
    target_weight: float | None = None
    reason: str = ""


@dataclass
class ExitIntent:
    symbol: str
    fraction: float        # fraction of CURRENT qty to sell, in (0, 1]
    reason: str


@dataclass
class BarContext:
    time: pd.Timestamp
    features: dict[str, pd.DataFrame]       # symbol -> feature frame (full history)
    row: dict[str, int]                     # symbol -> integer row of the bar at ctx.time
    btc: pd.DataFrame                       # BTC feature frame on the signal timeframe
    btc_row: int
    eligible: set[str]
    portfolio: Portfolio
    prices: dict[str, float]
    extra: dict[str, Any] = field(default_factory=dict)

    def feat(self, symbol: str, col: str, back: int = 0) -> float:
        i = self.row[symbol] - back
        if i < 0:
            return np.nan
        return float(self.features[symbol][col].iat[i])

    def btc_feat(self, col: str, back: int = 0) -> float:
        i = self.btc_row - back
        if i < 0:
            return np.nan
        return float(self.btc[col].iat[i])


def daily_to_signal_tf(daily: pd.Series, target_index: pd.DatetimeIndex) -> pd.Series:
    """Map a DAILY series onto an intraday index without look-ahead.

    A daily bar stamped D (its open) is only known after D + 1 day, so its
    value applies to intraday bars at or after that time.
    """
    shifted = daily.copy()
    shifted.index = shifted.index + pd.Timedelta(days=1)
    return shifted.reindex(target_index, method="ffill")


class Strategy(ABC):
    def __init__(self, spec: dict[str, Any], variant: str | None = None):
        self.spec = spec
        self.variant = variant
        self.feature_frames: dict[str, pd.DataFrame] = {}
        self.btc_frame: pd.DataFrame | None = None

    @property
    def id(self) -> str:
        return self.spec["id"]

    @property
    def signal_timeframe(self) -> str:
        return self.spec["signal_timeframe"]

    @abstractmethod
    def warmup_bars(self) -> int: ...

    @abstractmethod
    def build_features(self, bars: pd.DataFrame) -> pd.DataFrame: ...

    @abstractmethod
    def build_btc_features(self, btc_daily: pd.DataFrame, btc_signal: pd.DataFrame) -> pd.DataFrame: ...

    @abstractmethod
    def regime_on(self, ctx: BarContext) -> bool: ...

    @abstractmethod
    def entries(self, ctx: BarContext) -> list[EntryIntent]: ...

    @abstractmethod
    def manage(self, ctx: BarContext, pos: Position) -> list[ExitIntent]: ...

    def exit_all_when_regime_off(self) -> bool:
        return False

    def prepare(self, bars: dict[str, pd.DataFrame], btc_daily: pd.DataFrame, btc_signal: pd.DataFrame) -> None:
        self.feature_frames = {s: self.build_features(df) for s, df in bars.items()}
        self.btc_frame = self.build_btc_features(btc_daily, btc_signal)

    def free_parameters(self) -> int:
        """Simplicity score input (fewer is better)."""
        return len(self.parameter_grid())

    def parameter_grid(self) -> dict[str, float]:
        """Name -> value of every tunable parameter, for the +/-25% sensitivity sweep."""
        return {}

    def with_parameters(self, overrides: dict[str, float]) -> "Strategy":
        import copy

        spec = copy.deepcopy(self.spec)
        for dotted, value in overrides.items():
            node = spec
            parts = dotted.split(".")
            for p in parts[:-1]:
                node = node[p]
            node[parts[-1]] = type(node[parts[-1]])(value) if isinstance(node[parts[-1]], int) else value
        return type(self)(spec, self.variant)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _ohlc_features(bars: pd.DataFrame, atr_period: int) -> pd.DataFrame:
    out = bars.copy()
    out["atr"] = F.atr(bars["high"], bars["low"], bars["close"], atr_period)
    return out


# ---------------------------------------------------------------------------
# C1 — intraday range breakout (1h signal)
# ---------------------------------------------------------------------------
class C1Intraday(Strategy):
    def warmup_bars(self) -> int:
        return max(self.spec["entry"]["volume_avg_bars"], self.spec["regime"]["btc_hourly_sma"]) + 2

    def parameter_grid(self) -> dict[str, float]:
        return {
            "entry.breakout_lookback_bars": self.spec["entry"]["breakout_lookback_bars"],
            "entry.volume_multiple": self.spec["entry"]["volume_multiple"],
            "stop.atr_multiple": self.spec["stop"]["atr_multiple"],
            "exit.target_r": self.spec["exit"]["target_r"],
            "exit.max_hold_bars": self.spec["exit"]["max_hold_bars"],
            "regime.btc_daily_sma": self.spec["regime"]["btc_daily_sma"],
            "regime.btc_hourly_sma": self.spec["regime"]["btc_hourly_sma"],
        }

    def build_features(self, bars: pd.DataFrame) -> pd.DataFrame:
        e = self.spec["entry"]
        out = _ohlc_features(bars, self.spec["stop"]["atr_period"])
        out["prior_high"] = F.donchian_high(bars["high"], e["breakout_lookback_bars"]).shift(1)
        out["vol_avg"] = F.rolling_volume_avg(bars["volume"], e["volume_avg_bars"]).shift(1)
        return out

    def build_btc_features(self, btc_daily: pd.DataFrame, btc_signal: pd.DataFrame) -> pd.DataFrame:
        r = self.spec["regime"]
        out = btc_signal.copy()
        out["sma_h"] = F.sma(btc_signal["close"], r["btc_hourly_sma"])
        daily_on = (btc_daily["close"] > F.sma(btc_daily["close"], r["btc_daily_sma"])).astype(float)
        out["daily_on"] = daily_to_signal_tf(daily_on, out.index)
        return out

    def regime_on(self, ctx: BarContext) -> bool:
        return bool(ctx.btc_feat("daily_on") == 1.0 and ctx.btc_feat("close") > ctx.btc_feat("sma_h"))

    def entries(self, ctx: BarContext) -> list[EntryIntent]:
        if not self.regime_on(ctx):
            return []
        e = self.spec["entry"]
        k = self.spec["stop"]["atr_multiple"]
        out = []
        for sym in sorted(ctx.eligible):
            if sym in ctx.portfolio.positions or sym not in ctx.row:
                continue
            close = ctx.feat(sym, "close")
            ph, va, a, v = (ctx.feat(sym, c) for c in ("prior_high", "vol_avg", "atr", "volume"))
            if any(np.isnan(x) for x in (close, ph, va, a)):
                continue
            if close > ph and v > e["volume_multiple"] * va:
                out.append(EntryIntent(sym, stop=close - k * a, reason="c1_breakout"))
        return out

    def manage(self, ctx: BarContext, pos: Position) -> list[ExitIntent]:
        x = self.spec["exit"]
        close = ctx.prices[pos.symbol]
        if pos.r_multiple(close) >= x["target_r"]:
            return [ExitIntent(pos.symbol, 1.0, "target_r")]
        if pos.bars_held >= x["max_hold_bars"]:
            return [ExitIntent(pos.symbol, 1.0, "time_exit")]
        return []


# ---------------------------------------------------------------------------
# C2 — swing 20-day breakout, three exit variants
# ---------------------------------------------------------------------------
class C2Swing(Strategy):
    def __init__(self, spec: dict[str, Any], variant: str | None = None):
        super().__init__(spec, variant or spec.get("default_exit_variant", "V3"))
        self.exit = spec["exit_variants"][self.variant]

    def warmup_bars(self) -> int:
        return max(self.spec["entry"]["trend_sma"], self.spec["regime"]["btc_daily_sma"]) + 2

    def parameter_grid(self) -> dict[str, float]:
        grid = {
            "entry.breakout_lookback_bars": self.spec["entry"]["breakout_lookback_bars"],
            "entry.trend_sma": self.spec["entry"]["trend_sma"],
            "stop.atr_multiple": self.spec["stop"]["atr_multiple"],
            "regime.btc_daily_sma": self.spec["regime"]["btc_daily_sma"],
        }
        if self.exit["type"] == "chandelier":
            grid[f"exit_variants.{self.variant}.atr_multiple"] = self.exit["atr_multiple"]
        return grid

    def build_features(self, bars: pd.DataFrame) -> pd.DataFrame:
        e = self.spec["entry"]
        out = _ohlc_features(bars, self.spec["stop"]["atr_period"])
        out["prior_high"] = F.donchian_high(bars["high"], e["breakout_lookback_bars"]).shift(1)
        out["sma_trend"] = F.sma(bars["close"], e["trend_sma"])
        return out

    def build_btc_features(self, btc_daily: pd.DataFrame, btc_signal: pd.DataFrame) -> pd.DataFrame:
        out = btc_daily.copy()
        out["sma_d"] = F.sma(btc_daily["close"], self.spec["regime"]["btc_daily_sma"])
        return out

    def regime_on(self, ctx: BarContext) -> bool:
        return bool(ctx.btc_feat("close") > ctx.btc_feat("sma_d"))

    def entries(self, ctx: BarContext) -> list[EntryIntent]:
        if not self.regime_on(ctx):
            return []
        k = self.spec["stop"]["atr_multiple"]
        out = []
        for sym in sorted(ctx.eligible):
            if sym in ctx.portfolio.positions or sym not in ctx.row:
                continue
            close, ph, trend, a = (ctx.feat(sym, c) for c in ("close", "prior_high", "sma_trend", "atr"))
            if any(np.isnan(x) for x in (close, ph, trend, a)):
                continue
            if close > ph and close > trend:
                out.append(EntryIntent(sym, stop=close - k * a, reason="c2_breakout"))
        return out

    def manage(self, ctx: BarContext, pos: Position) -> list[ExitIntent]:
        close = ctx.prices[pos.symbol]
        a = ctx.feat(pos.symbol, "atr")
        pos.highest_close = max(pos.highest_close, close)
        kind = self.exit["type"]
        intents: list[ExitIntent] = []

        if kind == "fixed_ladder":
            rungs = self.exit["rungs"]
            gain = close / pos.avg_entry - 1
            while pos.rungs_hit < len(rungs) and gain >= rungs[pos.rungs_hit]["gain"]:
                frac_of_initial = rungs[pos.rungs_hit]["fraction"]
                remaining_frac = pos.qty / pos.initial_qty
                intents.append(ExitIntent(pos.symbol, min(1.0, frac_of_initial / remaining_frac), f"ladder_{pos.rungs_hit + 1}"))
                remaining_frac -= frac_of_initial
                pos.rungs_hit += 1
                if remaining_frac <= 1e-9:
                    break
            return _merge(intents)

        if kind == "r_ladder":
            rungs = self.exit["rungs"]
            r = pos.r_multiple(close)
            while pos.rungs_hit < len(rungs) and r >= rungs[pos.rungs_hit]["r"]:
                rung = rungs[pos.rungs_hit]
                remaining_frac = pos.qty / pos.initial_qty
                intents.append(ExitIntent(pos.symbol, min(1.0, rung["fraction"] / remaining_frac), f"r_ladder_{pos.rungs_hit + 1}"))
                if rung.get("move_stop_to_breakeven"):
                    pos.stop = max(pos.stop or 0.0, pos.avg_entry)
                pos.rungs_hit += 1
            if pos.rungs_hit >= len(rungs) and not np.isnan(a):
                trail = pos.highest_close - self.exit["trail_remainder"]["atr_multiple"] * a
                pos.stop = max(pos.stop or 0.0, trail)
            return _merge(intents)

        if kind == "chandelier":
            if not np.isnan(a):
                pos.stop = max(pos.stop or 0.0, pos.highest_close - self.exit["atr_multiple"] * a)
            return []

        raise ValueError(f"unknown exit type {kind}")


def _merge(intents: list[ExitIntent]) -> list[ExitIntent]:
    """Collapse several same-bar partial exits into one order (fractions compose)."""
    if len(intents) <= 1:
        return intents
    remaining = 1.0
    for it in intents:
        remaining *= 1 - it.fraction
    return [ExitIntent(intents[0].symbol, min(1.0, 1 - remaining), "+".join(i.reason for i in intents))]


# ---------------------------------------------------------------------------
# C3 — position momentum rotation (weekly rebalance)
# ---------------------------------------------------------------------------
class C3Position(Strategy):
    def warmup_bars(self) -> int:
        return max(self.spec["ranking"]["lookback_days"], self.spec["regime"]["btc_daily_sma"]) + 2

    def parameter_grid(self) -> dict[str, float]:
        return {
            "ranking.lookback_days": self.spec["ranking"]["lookback_days"],
            "ranking.hold_top": self.spec["ranking"]["hold_top"],
            "ranking.drop_below_rank": self.spec["ranking"]["drop_below_rank"],
            "regime.btc_daily_sma": self.spec["regime"]["btc_daily_sma"],
        }

    def build_features(self, bars: pd.DataFrame) -> pd.DataFrame:
        out = bars.copy()
        out["score"] = F.momentum_score(bars["close"], self.spec["ranking"]["lookback_days"])
        return out

    def build_btc_features(self, btc_daily: pd.DataFrame, btc_signal: pd.DataFrame) -> pd.DataFrame:
        out = btc_daily.copy()
        out["sma_d"] = F.sma(btc_daily["close"], self.spec["regime"]["btc_daily_sma"])
        return out

    def regime_on(self, ctx: BarContext) -> bool:
        return bool(ctx.btc_feat("close") > ctx.btc_feat("sma_d"))

    def exit_all_when_regime_off(self) -> bool:
        return True

    def is_rebalance_day(self, t: pd.Timestamp) -> bool:
        return t.weekday() == self.spec["rebalance"]["weekday"]

    def ranking(self, ctx: BarContext) -> list[str]:
        scores = {}
        for sym in ctx.eligible:
            if sym not in ctx.row:
                continue
            s = ctx.feat(sym, "score")
            if not np.isnan(s):
                scores[sym] = s
        return sorted(scores, key=lambda s: (-scores[s], s))

    def entries(self, ctx: BarContext) -> list[EntryIntent]:
        if not self.is_rebalance_day(ctx.time) or not self.regime_on(ctx):
            return []
        top = self.ranking(ctx)[: self.spec["ranking"]["hold_top"]]
        weight = ctx.extra.get("exposure_cap", 1.0) / self.spec["ranking"]["hold_top"]
        return [EntryIntent(s, stop=None, target_weight=weight, reason="c3_top") for s in top if s not in ctx.portfolio.positions]

    def manage(self, ctx: BarContext, pos: Position) -> list[ExitIntent]:
        if not self.is_rebalance_day(ctx.time):
            return []
        ranked = self.ranking(ctx)
        drop = self.spec["ranking"]["drop_below_rank"]
        if pos.symbol not in ranked[:drop]:
            return [ExitIntent(pos.symbol, 1.0, "rank_drop")]
        return []


# ---------------------------------------------------------------------------
# Random-entry benchmark (K11): same exits, sizing and regime filter
# ---------------------------------------------------------------------------
class RandomEntry(Strategy):
    """Wraps a candidate, replacing its entry signal with coin flips at a fixed rate."""

    def __init__(self, base: Strategy, entry_prob: float, seed: int):
        super().__init__(base.spec, base.variant)
        self.base = base
        self.entry_prob = entry_prob
        self.rng = np.random.default_rng(seed)

    def warmup_bars(self) -> int:
        return self.base.warmup_bars()

    def build_features(self, bars: pd.DataFrame) -> pd.DataFrame:
        return self.base.build_features(bars)

    def build_btc_features(self, btc_daily, btc_signal):
        return self.base.build_btc_features(btc_daily, btc_signal)

    def prepare(self, bars, btc_daily, btc_signal) -> None:
        self.base.prepare(bars, btc_daily, btc_signal)
        self.feature_frames = self.base.feature_frames
        self.btc_frame = self.base.btc_frame

    def regime_on(self, ctx: BarContext) -> bool:
        return self.base.regime_on(ctx)

    def exit_all_when_regime_off(self) -> bool:
        return self.base.exit_all_when_regime_off()

    def entries(self, ctx: BarContext) -> list[EntryIntent]:
        if not self.regime_on(ctx):
            return []
        if isinstance(self.base, C3Position) and not self.base.is_rebalance_day(ctx.time):
            return []
        k = self.spec.get("stop", {}).get("atr_multiple")
        out = []
        for sym in sorted(ctx.eligible):
            if sym in ctx.portfolio.positions or sym not in ctx.row:
                continue
            if self.rng.random() >= self.entry_prob:
                continue
            close = ctx.feat(sym, "close")
            if isinstance(self.base, C3Position):
                w = ctx.extra.get("exposure_cap", 1.0) / self.spec["ranking"]["hold_top"]
                out.append(EntryIntent(sym, None, target_weight=w, reason="random"))
            else:
                a = ctx.feat(sym, "atr")
                if np.isnan(a) or np.isnan(close):
                    continue
                out.append(EntryIntent(sym, stop=close - k * a, reason="random"))
        return out

    def manage(self, ctx: BarContext, pos: Position) -> list[ExitIntent]:
        return self.base.manage(ctx, pos)


CANDIDATES = {"C1": C1Intraday, "C2": C2Swing, "C3": C3Position}


def make_strategy(candidate_spec: dict[str, Any], variant: str | None = None) -> Strategy:
    return CANDIDATES[candidate_spec["id"]](candidate_spec, variant)
