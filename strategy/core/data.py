"""Download, validate and store bars; build the point-in-time eligibility table.

Bars are stored one file per (symbol, timeframe) under a data directory, as
Parquet when pyarrow is available and CSV otherwise. All timestamps are UTC
and mark the bar's OPEN time; a bar is "closed" once the next bar's open time
has passed.

Fetchers use urllib only so the research engine has no hard network deps:
  * Alpaca crypto bars  -> execution-venue prices (needs APCA_* env keys)
  * Coinbase candles    -> long reference history + volume (public endpoint)
"""

from __future__ import annotations

import json
import os
import time as _time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

BAR_COLUMNS = ["open", "high", "low", "close", "volume"]
TIMEFRAME_DELTA = {
    "1m": pd.Timedelta(minutes=1),
    "15m": pd.Timedelta(minutes=15),
    "1h": pd.Timedelta(hours=1),
    "1d": pd.Timedelta(days=1),
}

try:  # pragma: no cover - environment dependent
    import pyarrow  # noqa: F401

    HAVE_PARQUET = True
except ImportError:  # pragma: no cover
    HAVE_PARQUET = False


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
class BarStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, symbol: str, timeframe: str) -> Path:
        ext = "parquet" if HAVE_PARQUET else "csv"
        return self.root / f"{symbol}_{timeframe}.{ext}"

    def save(self, symbol: str, timeframe: str, bars: pd.DataFrame) -> Path:
        bars = normalize_bars(bars)
        p = self.path(symbol, timeframe)
        if HAVE_PARQUET:
            bars.to_parquet(p)
        else:
            bars.to_csv(p, index_label="time")
        return p

    def load(self, symbol: str, timeframe: str) -> pd.DataFrame | None:
        p = self.path(symbol, timeframe)
        if not p.exists():
            return None
        if HAVE_PARQUET:
            df = pd.read_parquet(p)
        else:
            df = pd.read_csv(p, index_col="time", parse_dates=True)
        return normalize_bars(df)

    def load_many(self, symbols: Iterable[str], timeframe: str) -> dict[str, pd.DataFrame]:
        out = {}
        for s in symbols:
            df = self.load(s, timeframe)
            if df is not None and len(df):
                out[s] = df
        return out


def normalize_bars(df: pd.DataFrame) -> pd.DataFrame:
    """UTC index, sorted, duplicates removed, float columns in canonical order."""
    df = df.copy()
    if "time" in df.columns:
        df = df.set_index("time")
    idx = pd.DatetimeIndex(pd.to_datetime(df.index, utc=True))
    df.index = idx
    df.index.name = "time"
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df[BAR_COLUMNS].astype(float)
    return df


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------
def _get_json(url: str, headers: dict[str, str] | None = None, retries: int = 4) -> Any:
    req = urllib.request.Request(url)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    delay = 1.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception:  # noqa: BLE001 - retry on any transport error
            if attempt == retries - 1:
                raise
            _time.sleep(delay)
            delay *= 2


def alpaca_headers(key: str | None = None, secret: str | None = None) -> dict[str, str]:
    """Alpaca auth headers from args or APCA_* env vars.

    Returns {} when no keys are set: in a cloud environment with a network
    secret configured, the egress proxy injects the headers itself.
    """
    key = key or os.environ.get("APCA_API_KEY_ID", "")
    secret = secret or os.environ.get("APCA_API_SECRET_KEY", "")
    if key and secret:
        return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    return {}


def fetch_alpaca_bars(
    symbol: str,
    timeframe: str,
    start: str,
    end: str | None = None,
    key: str | None = None,
    secret: str | None = None,
) -> pd.DataFrame:
    """Alpaca crypto bars, paged. timeframe: 1Min, 15Min, 1Hour, 1Day (or our short names)."""
    tf_map = {"1m": "1Min", "15m": "15Min", "1h": "1Hour", "1d": "1Day"}
    tf = tf_map.get(timeframe, timeframe)
    headers = alpaca_headers(key, secret)
    pair = symbol if "/" in symbol else f"{symbol}/USD"
    params: dict[str, Any] = {"symbols": pair, "timeframe": tf, "start": start, "limit": 10000}
    if end:
        params["end"] = end
    rows: list[dict[str, Any]] = []
    while True:
        url = "https://data.alpaca.markets/v1beta3/crypto/us/bars?" + urllib.parse.urlencode(params)
        payload = _get_json(url, headers)
        rows.extend(payload.get("bars", {}).get(pair, []))
        token = payload.get("next_page_token")
        if not token:
            break
        params["page_token"] = token
    if not rows:
        return pd.DataFrame(columns=BAR_COLUMNS)
    df = pd.DataFrame(rows).rename(columns={"t": "time", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    return normalize_bars(df)


def fetch_alpaca_assets(key: str | None = None, secret: str | None = None, paper: bool = True) -> list[dict[str, Any]]:
    """GET /v2/assets?asset_class=crypto — re-pull at the start of Phase 1."""
    headers = alpaca_headers(key, secret)
    base = "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
    return _get_json(f"{base}/v2/assets?asset_class=crypto&status=active", headers)


def fetch_coinbase_candles(symbol: str, timeframe: str, start: str, end: str | None = None) -> pd.DataFrame:
    """Coinbase Exchange public candles (max 300 per call), used as the reference exchange."""
    gran = {"1m": 60, "15m": 900, "1h": 3600, "1d": 86400}[timeframe]
    product = symbol if "-" in symbol else f"{symbol}-USD"
    t0 = pd.Timestamp(start, tz="UTC")
    t1 = pd.Timestamp(end, tz="UTC") if end else pd.Timestamp.now(tz="UTC")
    step = pd.Timedelta(seconds=gran * 300)
    rows: list[list[float]] = []
    cur = t0
    while cur < t1:
        nxt = min(cur + step, t1)
        url = (
            f"https://api.exchange.coinbase.com/products/{product}/candles?"
            + urllib.parse.urlencode({"granularity": gran, "start": cur.isoformat(), "end": nxt.isoformat()})
        )
        rows.extend(_get_json(url, {"User-Agent": "strategy-research/1.0"}))
        cur = nxt
        _time.sleep(0.25)  # public rate limit
    if not rows:
        return pd.DataFrame(columns=BAR_COLUMNS)
    df = pd.DataFrame(rows, columns=["time", "low", "high", "open", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return normalize_bars(df)


# ---------------------------------------------------------------------------
# Quality checks (Gate G1)
# ---------------------------------------------------------------------------
@dataclass
class QualityReport:
    symbol: str
    timeframe: str
    bars: int
    missing_fraction: float
    gaps: list[tuple[pd.Timestamp, pd.Timestamp]] = field(default_factory=list)
    extreme_moves: list[pd.Timestamp] = field(default_factory=list)
    zero_volume: list[pd.Timestamp] = field(default_factory=list)
    duplicates_removed: int = 0

    @property
    def passed(self) -> bool:
        return self.missing_fraction < 0.005 and self.bars > 0

    def summary(self) -> str:
        return (
            f"{self.symbol} {self.timeframe}: {self.bars} bars, missing {self.missing_fraction:.3%}, "
            f"{len(self.gaps)} gaps, {len(self.extreme_moves)} extreme moves, "
            f"{len(self.zero_volume)} zero-volume bars -> {'PASS' if self.passed else 'FAIL'}"
        )


def quality_check(
    symbol: str,
    timeframe: str,
    raw: pd.DataFrame,
    listing_windows: list[tuple[pd.Timestamp, pd.Timestamp | None]] | None = None,
) -> QualityReport:
    """Flag missing bars, +/-50% moves and zero volume. Gaps are logged, never forward-filled.

    `listing_windows` (from specs/listings.yaml) marks when the coin was tradable; bars
    outside those windows are not expected, so a documented delisting is not a gap, and
    the first bar after a relisting is not an extreme move.
    """
    if raw.empty:
        return QualityReport(symbol, timeframe, 0, 1.0)
    before = len(raw)
    df = normalize_bars(raw)
    dup = before - len(df)
    delta = TIMEFRAME_DELTA[timeframe]
    expected = pd.date_range(df.index[0], df.index[-1], freq=delta, tz="UTC")
    if listing_windows:
        mask = np.zeros(len(expected), dtype=bool)
        for start, stop in listing_windows:
            hi = stop + pd.Timedelta(days=1) if stop is not None else expected[-1] + delta
            mask |= (expected >= start) & (expected < hi)
        expected = expected[mask]
    missing = expected.difference(df.index)
    gaps: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    if len(missing):
        breaks = np.where(np.diff(missing.values) != delta.to_timedelta64())[0]
        starts = np.r_[0, breaks + 1]
        ends = np.r_[breaks, len(missing) - 1]
        gaps = [(missing[s], missing[e]) for s, e in zip(starts, ends)]
    move = (df["close"] / df["close"].shift(1) - 1).abs()
    if listing_windows:
        for start, _ in listing_windows:
            move[(df.index >= start) & (df.index < start + delta)] = 0.0  # first bar after (re)listing
    extreme = list(df.index[move >= 0.5])
    zero_vol = list(df.index[df["volume"] <= 0])
    return QualityReport(
        symbol=symbol,
        timeframe=timeframe,
        bars=len(df),
        missing_fraction=len(missing) / max(len(expected), 1),
        gaps=gaps,
        extreme_moves=extreme,
        zero_volume=zero_vol,
        duplicates_removed=dup,
    )


def stitch_rebrand(old: pd.DataFrame, new: pd.DataFrame, new_per_old: float = 1.0) -> pd.DataFrame:
    """Prepend the old ticker's history to the new one (e.g. MATIC -> POL).

    `new_per_old` is the conversion ratio (1 old token = N new tokens): prices are
    divided by it and volumes multiplied, so MKR -> SKY uses 24000.
    """
    if old is None or old.empty:
        return new
    old = normalize_bars(old).copy()
    new = normalize_bars(new)
    for c in ("open", "high", "low", "close"):
        old[c] = old[c] / new_per_old
    old["volume"] = old["volume"] * new_per_old
    cutoff = new.index[0]
    return pd.concat([old[old.index < cutoff], new]).sort_index()


# ---------------------------------------------------------------------------
# Point-in-time eligibility
# ---------------------------------------------------------------------------
def build_eligibility_table(
    daily_bars: dict[str, pd.DataFrame],
    min_history_days: int,
    min_median_dollar_volume: float,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    listings: dict[str, list[tuple[pd.Timestamp, pd.Timestamp | None]]] | None = None,
    reference_bars: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Monthly boolean table (rows = month starts, columns = symbols).

    A coin is eligible on month M if, using only data before M:
      1. it is listed on Alpaca (per `listings`, or simply has bars) on that date;
      2. it has >= min_history_days daily bars before M (reference bars count, so a
         coin with long exchange history qualifies as soon as Alpaca lists it);
      3. its median 30-day dollar volume before M, on the reference exchange when
         `reference_bars` is given, is >= the threshold.
    Delisted coins stay in the table for the months they qualified, so the
    universe is survivorship-free.
    """
    if not daily_bars:
        return pd.DataFrame()
    first = min(df.index[0] for df in daily_bars.values())
    last = max(df.index[-1] for df in daily_bars.values())
    start = start or first
    end = end or last
    months = pd.date_range(start.normalize().replace(day=1), end, freq="MS", tz="UTC")
    table = pd.DataFrame(False, index=months, columns=sorted(daily_bars))
    for sym, df in daily_bars.items():
        ref = (reference_bars or {}).get(sym)
        vol_src = ref if ref is not None else df
        hist_src = ref if ref is not None else df
        dv = (vol_src["close"] * vol_src["volume"]).rolling(30, min_periods=30).median()
        windows = (listings or {}).get(sym)
        for m in months:
            if not listed_at(windows, m):
                continue
            hist = hist_src[hist_src.index < m]
            if len(hist) < min_history_days:
                continue
            recent_dv = dv[dv.index < m].dropna()
            if recent_dv.empty or recent_dv.iloc[-1] < min_median_dollar_volume:
                continue
            table.loc[m, sym] = True
    return table


def load_listings(path: Path | str) -> dict[str, list[tuple[pd.Timestamp, pd.Timestamp | None]]]:
    """specs/listings.yaml -> {symbol: [(from, to_or_None), ...]}."""
    import yaml

    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    out: dict[str, list[tuple[pd.Timestamp, pd.Timestamp | None]]] = {}
    for sym, windows in (raw.get("listed") or {}).items():
        out[sym] = [
            (pd.Timestamp(w["from"], tz="UTC"), pd.Timestamp(w["to"], tz="UTC") if w.get("to") else None)
            for w in windows
        ]
    return out


def listed_at(windows: list[tuple[pd.Timestamp, pd.Timestamp | None]] | None, t: pd.Timestamp) -> bool:
    if not windows:
        return True
    return any(t >= a and (b is None or t <= b) for a, b in windows)


def eligible_at(table: pd.DataFrame, t: pd.Timestamp) -> set[str]:
    if table.empty:
        return set()
    rows = table[table.index <= t]
    if rows.empty:
        return set()
    row = rows.iloc[-1]
    return set(row.index[row.astype(bool)])


# ---------------------------------------------------------------------------
# Synthetic data (engine tests; never for research conclusions)
# ---------------------------------------------------------------------------
def synthetic_bars(
    n: int,
    timeframe: str = "1d",
    seed: int = 0,
    start: str = "2020-01-01",
    drift: float = 0.0005,
    vol: float = 0.04,
    price0: float = 100.0,
    volume0: float = 1_000_000.0,
) -> pd.DataFrame:
    """GBM-ish OHLCV bars with intrabar range, deterministic for a seed."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    close = price0 * np.exp(np.cumsum(rets))
    open_ = np.r_[price0, close[:-1]] * np.exp(rng.normal(0, vol / 4, n))
    wick = np.abs(rng.normal(0, vol / 2, n))
    high = np.maximum(open_, close) * (1 + wick)
    low = np.minimum(open_, close) * (1 - wick)
    volume = volume0 * np.exp(rng.normal(0, 0.5, n))
    idx = pd.date_range(start, periods=n, freq=TIMEFRAME_DELTA[timeframe], tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)
