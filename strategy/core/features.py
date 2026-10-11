"""Indicators as pure functions on closed bars.

Every function takes pandas Series/DataFrames indexed by bar timestamp and
returns a Series aligned to the same index. A value at row t uses rows <= t
only. Where a signal needs "prior" values (e.g. prior 20-day high) the signal
layer shifts explicitly, so no function here looks ahead.

The look-ahead test in tests/test_lookahead.py truncates the input at t,
recomputes, and asserts every feature at t is unchanged.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    # adjust=False so the recursion matches TA-Lib's EMA after the seed period.
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's ATR (matches TA-Lib ATR)."""
    tr = true_range(high, low, close)
    return _wilder_smooth(tr, period)


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    values = series.to_numpy(dtype=float)
    out = np.full_like(values, np.nan)
    # TA-Lib seeds with the simple mean of the first `period` valid values.
    valid = ~np.isnan(values)
    if valid.sum() < period:
        return pd.Series(out, index=series.index)
    first = np.argmax(valid)
    start = first + period - 1
    out[start] = values[first : start + 1].mean()
    for i in range(start + 1, len(values)):
        out[i] = (out[i - 1] * (period - 1) + values[i]) / period
    return pd.Series(out, index=series.index)


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's ADX."""
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=high.index)
    tr = true_range(high, low, close)
    atr_s = _wilder_smooth(tr, period)
    plus_di = 100 * _wilder_smooth(plus_dm, period) / atr_s
    minus_di = 100 * _wilder_smooth(minus_dm, period) / atr_s
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return _wilder_smooth(dx, period)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    fast_e = ema(series, fast)
    slow_e = ema(series, slow)
    line = fast_e - slow_e
    sig = ema(line.dropna(), signal).reindex(series.index)
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def donchian_high(high: pd.Series, period: int) -> pd.Series:
    """Highest high over the trailing `period` bars INCLUDING the current bar.

    Signals compare the current close with `donchian_high(...).shift(1)` so the
    breakout level is the prior N-bar high.
    """
    return high.rolling(period, min_periods=period).max()


def donchian_low(low: pd.Series, period: int) -> pd.Series:
    return low.rolling(period, min_periods=period).min()


def rolling_volume_avg(volume: pd.Series, period: int) -> pd.Series:
    return volume.rolling(period, min_periods=period).mean()


def log_returns(close: pd.Series) -> pd.Series:
    return np.log(close / close.shift(1))


def realized_vol(close: pd.Series, period: int) -> pd.Series:
    """Std-dev of log returns over `period` bars (not annualized)."""
    return log_returns(close).rolling(period, min_periods=period).std()


def momentum_score(close: pd.Series, period: int) -> pd.Series:
    """`period`-bar return divided by `period`-bar realized volatility."""
    ret = close / close.shift(period) - 1
    vol = realized_vol(close, period)
    return ret / vol.replace(0, np.nan)


def dollar_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
    return close * volume


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = _wilder_smooth(gain, period)
    avg_loss = _wilder_smooth(loss, period)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(avg_loss != 0, 100.0)
