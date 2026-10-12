#!/usr/bin/env python3
"""Vectorized research backtest for the Gajjala intraday momentum setup.

Everything is precomputed per symbol as numpy arrays; a parameter set is then a boolean
mask over bars (signals) plus a short Python loop per signal for trade management.
"""
import os, sys, datetime as dt, math
from dataclasses import dataclass, field, asdict
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data as D

ET = D.g.ET


@dataclass
class Params:
    top_n: int = 15
    pole_bars: int = 6
    flag_bars: int = 6
    pole_min: float = 1.5          # % gain over the pole
    flag_max_range: float = 1.2    # % high-low range of the flag
    vol_mult: float = 1.5          # breakout volume vs 20-bar avg (0 = off)
    ema_stack: bool = True         # close > EMA9 > EMA21
    above_vwap: bool = True        # close > session VWAP
    flag_above_vwap: bool = True   # every flag close above VWAP
    spy_vwap: bool = True          # SPY above its VWAP on the signal bar
    earliest: str = "09:30"        # earliest signal bar time (bar start)
    latest: str = "15:55"          # latest signal bar time
    min_risk_pct: float = 0.0      # skip if (entry-stop)/entry below this
    max_risk_pct: float = 100.0
    stop_mode: str = "flag_low"    # flag_low | pole_low | atr
    atr_mult: float = 1.0          # for stop_mode=atr: stop = entry - atr_mult*ATR14(5m)
    targets: tuple = (2.5, 5.5, 10.0)   # % targets; empty = no targets
    scale: tuple = (1/3, 1/3, 1/3)      # fraction out at each target (last gets remainder)
    trail: str = "ema9"            # ema9 | ema21 | none | be (break-even only)
    trail_trigger_r: float = 1.0   # start trailing at +X R
    hold: str = "intraday"         # intraday | overnight
    max_hold_days: int = 10        # for overnight
    eod_time: str = "15:55"        # last bar at which intraday trades are flattened
    one_per_symbol_day: bool = True
    account: float = 100_000
    risk_pct: float = 0.005
    require_200sma: bool = False
    max_off_high: float = 100.0    # skip leaders more than X% below 52w high
    mode: str = "flag"             # flag | orb (opening range breakout) | open (benchmark: buy at bar orb_bars unconditionally)
    stop_pct: float = 3.0          # for stop_mode=pct: stop = entry*(1-stop_pct/100)
    orb_bars: int = 6              # bars in the opening range (6 = 30 min)
    min_pole_pct_day: float = -100 # orb: require day gain so far (open->close) >= X% (-100 = off)


def tmin(s):
    h, m = s.split(":"); return int(h) * 60 + int(m)


class Dataset:
    def __init__(self):
        self.leaders = D.load("leaders.pkl")
        self.spy5 = D.load("spy5.pkl")
        self.spy_above = (self.spy5["c"] > self.spy5["vwap"])
        self.sym = {}
        self.sessions = sorted(self.leaders)
        for f in os.listdir(os.path.join(D.CACHE, "intra")):
            s = f[:-4]
            self.sym[s] = self._prep(D.load(f"intra/{f}"))
        self._feat_cache = {}

    def _prep(self, df):
        df = df.copy()
        df["spy_above"] = self.spy_above.reindex(df.index).fillna(False).astype(bool).values
        # ATR14 on 5m
        prev_c = df["c"].shift(1)
        tr = pd.concat([df["h"] - df["l"], (df["h"] - prev_c).abs(), (df["l"] - prev_c).abs()], axis=1).max(axis=1)
        df["atr14"] = tr.rolling(14).mean()
        df["minute"] = df.index.hour * 60 + df.index.minute
        # position of bar within its session
        df["bar_in_day"] = df.groupby("date").cumcount()
        return df

    def feats(self, s, pole_bars, flag_bars):
        key = (s, pole_bars, flag_bars)
        if key in self._feat_cache:
            return self._feat_cache[key]
        df = self.sym[s]
        o, h, l, c, v = (df[k].values for k in "ohlcv")
        vwap = df["vwap"].values
        n = len(df)
        fb, pb = flag_bars, pole_bars
        # flag over bars i-fb..i-1
        hs, ls, cs = pd.Series(h), pd.Series(l), pd.Series(c)
        flag_hi = hs.rolling(fb).max().shift(1).values
        flag_lo = ls.rolling(fb).min().shift(1).values
        above = pd.Series((c > vwap).astype(int))
        flag_above = (above.rolling(fb).sum().shift(1).values == fb)
        # pole over bars i-fb-pb .. i-fb-1 : gain = close[i-fb-1]/open[i-fb-pb] - 1
        pole_end_c = cs.shift(fb + 1).values
        pole_start_o = pd.Series(o).shift(fb + pb).values
        pole_lo = ls.rolling(pb).min().shift(fb + 1).values
        with np.errstate(invalid="ignore", divide="ignore"):
            pole_pct = (pole_end_c / pole_start_o - 1) * 100
            flag_range = (flag_hi / flag_lo - 1) * 100
            vol_ratio = v / df["avgvol20"].values
        same_session = df["bar_in_day"].values >= fb + pb
        # opening range (first orb_bars bars of each session) - computed for 6 bars; others on demand
        out = dict(flag_hi=flag_hi, flag_lo=flag_lo, flag_above=flag_above, pole_pct=pole_pct,
                   pole_lo=pole_lo, flag_range=flag_range, vol_ratio=vol_ratio, same_session=same_session)
        self._feat_cache[key] = out
        return out


def orb_feats(ds, s, nb):
    key = (s, "orb", nb)
    if key in ds._feat_cache:
        return ds._feat_cache[key]
    df = ds.sym[s]
    bid = df["bar_in_day"].values
    g = df.groupby("date")
    orb_hi = g["h"].transform(lambda x: x.iloc[:nb].max()).values
    orb_lo = g["l"].transform(lambda x: x.iloc[:nb].min()).values
    day_open = g["o"].transform("first").values
    out = dict(orb_hi=orb_hi, orb_lo=orb_lo, day_open=day_open, ok=bid >= nb)
    ds._feat_cache[key] = out
    return out


def signals_for(ds, s, p: Params):
    df = ds.sym[s]
    F = ds.feats(s, p.pole_bars, p.flag_bars)
    c = df["c"].values
    if p.mode == "open":
        O = orb_feats(ds, s, p.orb_bars)
        F = dict(F); F["flag_lo"] = O["orb_lo"]; F["flag_hi"] = O["orb_hi"]
        m = df["bar_in_day"].values == p.orb_bars
    elif p.mode == "orb":
        O = orb_feats(ds, s, p.orb_bars)
        F = dict(F); F["flag_lo"] = O["orb_lo"]; F["flag_hi"] = O["orb_hi"]
        prev_c = np.roll(c, 1); prev_c[0] = np.nan
        m = O["ok"] & ~np.isnan(F["vol_ratio"]) & (c > O["orb_hi"]) & (prev_c <= O["orb_hi"])
        if p.min_pole_pct_day > -100:
            m &= (c / O["day_open"] - 1) * 100 >= p.min_pole_pct_day
    else:
        m = F["same_session"] & ~np.isnan(F["pole_pct"]) & ~np.isnan(F["vol_ratio"])
        m &= F["pole_pct"] >= p.pole_min
        m &= F["flag_range"] <= p.flag_max_range
        m &= c > F["flag_hi"]
    if p.vol_mult > 0:
        m &= F["vol_ratio"] >= p.vol_mult
    if p.ema_stack:
        m &= (c > df["ema9"].values) & (df["ema9"].values > df["ema21"].values)
    if p.above_vwap:
        m &= c > df["vwap"].values
    if p.flag_above_vwap and p.mode == "flag":
        m &= F["flag_above"]
    if p.spy_vwap:
        m &= df["spy_above"].values
    mins = df["minute"].values
    m &= (mins >= tmin(p.earliest)) & (mins <= tmin(p.latest))
    return m, F


def manage(df, F, i0, p: Params):
    """Return (exit_index, fills[(idx, qty_frac, price, reason)], stop, qty)."""
    o, h, l, c = (df[k].values for k in "ohlc")
    entry = c[i0]
    if p.stop_mode == "flag_low":
        stop = F["flag_lo"][i0]
    elif p.stop_mode == "pole_low":
        stop = F["pole_lo"][i0]
    elif p.stop_mode == "pct":
        stop = entry * (1 - p.stop_pct / 100)
    else:
        stop = entry - p.atr_mult * df["atr14"].values[i0]
    r = entry - stop
    if not (r > 0):
        return None
    risk_pct = r / entry * 100
    if risk_pct < p.min_risk_pct or risk_pct > p.max_risk_pct:
        return None
    qty = math.floor(p.account * p.risk_pct / r)
    if qty <= 0:
        return None
    dates = df["date"].values
    mins = df["minute"].values
    ema_t = df["ema9"].values if p.trail == "ema9" else df["ema21"].values if p.trail == "ema21" else None
    day0 = dates[i0]
    n = len(df)
    targets = [entry * (1 + t / 100) for t in p.targets]
    parts = []
    rem_frac = 1.0
    for k in range(len(targets)):
        frac = p.scale[k] if k < len(targets) - 1 else rem_frac
        parts.append(min(frac, rem_frac)); rem_frac -= parts[-1]
    hit = [False] * len(targets)
    remaining = 1.0
    fills = []
    trailing = False
    eod = tmin(p.eod_time)
    if p.hold == "intraday" and (i0 + 1 >= n or dates[i0 + 1] != day0 or mins[i0] >= eod):
        return None  # no bars left today
    days_held = 0
    for i in range(i0 + 1, n):
        if dates[i] != dates[i - 1]:
            days_held += 1
        if p.hold == "intraday" and dates[i] != day0:
            break
        if l[i] <= stop:
            px = min(o[i], stop)
            fills.append((i, remaining, px, "trail" if trailing else "stop")); remaining = 0; break
        for k, tg in enumerate(targets):
            if not hit[k] and h[i] >= tg and remaining > 0:
                q = min(parts[k], remaining)
                if q > 1e-9:
                    fills.append((i, q, max(o[i], tg), f"T{k+1}")); remaining -= q
                hit[k] = True
        if remaining <= 1e-9:
            remaining = 0; break
        if h[i] >= entry + p.trail_trigger_r * r:
            trailing = True
        if trailing:
            if p.trail in ("ema9", "ema21"):
                stop = max(stop, ema_t[i])
            elif p.trail == "be":
                stop = max(stop, entry)
        last_today = (i + 1 >= n) or dates[i + 1] != dates[i] or mins[i] >= eod
        if p.hold == "intraday" and last_today:
            fills.append((i, remaining, c[i], "eod")); remaining = 0; break
        if p.hold == "overnight" and days_held >= p.max_hold_days and last_today:
            fills.append((i, remaining, c[i], "maxhold")); remaining = 0; break
    if remaining > 0:
        fills.append((n - 1, remaining, c[n - 1], "end"))
    pnl = sum(q * qty * (px - entry) for _, q, px, _ in fills)
    return dict(entry=entry, stop=entry - r, qty=qty, risk_usd=r * qty,
                risk_pct=risk_pct, exit_i=fills[-1][0], fills=fills, pnl=pnl, R=pnl / (r * qty))


def run(ds: Dataset, p: Params, start: dt.date, end: dt.date):
    trades = []
    open_until = {}
    sig_cache = {}
    for d in ds.sessions:
        if d < start or d > end:
            continue
        L = ds.leaders[d]
        L = L[L["rank"] <= p.top_n]
        if p.require_200sma:
            L = L[L.above_200sma]
        if p.max_off_high < 100:
            L = L[L.pct_off_52w_high * 100 >= -p.max_off_high]
        for s in L.symbol:
            if s not in ds.sym:
                continue
            df = ds.sym[s]
            dates = df["date"].values
            idx = np.where(dates == d)[0]
            if len(idx) == 0:
                continue
            if s not in sig_cache:
                sig_cache[s] = signals_for(ds, s, p)
            m, F = sig_cache[s]
            for i in idx:
                if not m[i]:
                    continue
                if s in open_until and i <= open_until[s]:
                    continue
                t = manage(df, F, i, p)
                if t is None:
                    continue
                open_until[s] = t["exit_i"] if not p.one_per_symbol_day else max(t["exit_i"], idx[-1])
                trades.append(dict(session=d, time=df.index[i], symbol=s, entry=round(t["entry"], 2),
                                   stop=round(t["stop"], 2), qty=t["qty"], risk_pct=round(t["risk_pct"], 2),
                                   exit_time=df.index[t["exit_i"]],
                                   exits="|".join(f"{q:.2f}@{px:.2f}:{why}" for _, q, px, why in t["fills"]),
                                   pnl=round(t["pnl"], 2), R=round(t["R"], 3)))
    return pd.DataFrame(trades)


def stats(tr: pd.DataFrame):
    if tr is None or tr.empty:
        return dict(n=0, win=np.nan, totR=0, avgR=np.nan, pf=np.nan, maxdd_R=0, pnl=0)
    w = tr.R > 0
    gp, gl = tr.R[w].sum(), -tr.R[~w].sum()
    eq = tr.sort_values("time").R.cumsum()
    dd = (eq - eq.cummax()).min()
    return dict(n=len(tr), win=round(w.mean(), 3), totR=round(tr.R.sum(), 1), avgR=round(tr.R.mean(), 3),
                pf=round(gp / gl, 2) if gl > 0 else np.inf, maxdd_R=round(dd, 1), pnl=round(tr.pnl.sum(), 0))


def monthly(tr):
    if tr.empty:
        return pd.DataFrame()
    t = tr.copy(); t["month"] = pd.to_datetime(t.session).dt.to_period("M")
    return t.groupby("month").agg(n=("R", "size"), win=("R", lambda x: (x > 0).mean()), R=("R", "sum"), pnl=("pnl", "sum"))
