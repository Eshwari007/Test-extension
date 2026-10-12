#!/usr/bin/env python3
"""Build and cache the datasets for the Gajjala research backtest.

Outputs (pickles in cache/):
  daily.pkl      {symbol: DataFrame[o,h,l,c,v]} daily, split-adjusted, from DAILY_START
  spy_daily.pkl  SPY daily
  leaders.pkl    {session_date: DataFrame of Stage 1 rows ranked by 21d return, top LEADER_N}
  intra/<SYM>.pkl  5-min regular-hours bars with features for the symbol's leader spans
  spy5.pkl       SPY 5-min with features over the whole range
"""
import sys, os, pickle, time, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gajjala_scanner_us as g

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
DAILY_START = "2024-01-01"
BT_START, BT_END = dt.date(2025, 1, 2), dt.date(2026, 10, 9)
LEADER_N = 30


def load(name):
    with open(os.path.join(CACHE, name), "rb") as fh:
        return pickle.load(fh)


def save(obj, name):
    os.makedirs(os.path.dirname(os.path.join(CACHE, name)), exist_ok=True)
    with open(os.path.join(CACHE, name), "wb") as fh:
        pickle.dump(obj, fh)


def stage1_all(daily, spy, asof, n):
    sp = spy[spy.index.tz_convert(g.ET).date <= asof]["c"]
    spy_ret = sp.iloc[-1] / sp.iloc[-g.LOOKBACK_1M - 1] - 1
    rows = []
    for sym, df in daily.items():
        d = df[df.index.tz_convert(g.ET).date <= asof]
        if len(d) < 60:
            continue
        c = d["c"]; close = c.iloc[-1]
        ret1m = close / c.iloc[-g.LOOKBACK_1M - 1] - 1
        sma50 = c.iloc[-50:].mean()
        sma200 = c.iloc[-200:].mean() if len(c) >= 200 else np.nan
        dvol = (d["c"] * d["v"]).iloc[-20:].mean()
        hi52 = d["h"].iloc[-252:].max()
        ret3m = close / c.iloc[-64] - 1 if len(c) > 64 else np.nan
        ok = ret1m > spy_ret and close > sma50 and close > g.MIN_PRICE and dvol > g.MIN_DOLLAR_VOL
        if ok:
            rows.append(dict(symbol=sym, close=close, ret_1m=ret1m, ret_3m=ret3m, rs_vs_spy=ret1m - spy_ret,
                             above_200sma=bool(close > sma200) if not np.isnan(sma200) else False,
                             pct_off_52w_high=close / hi52 - 1, avg_dollar_vol=dvol))
    df = pd.DataFrame(rows).sort_values("ret_1m", ascending=False).head(n)
    df["rank"] = range(1, len(df) + 1)
    df["spy_ret_1m"] = spy_ret
    return df


def main():
    os.makedirs(CACHE, exist_ok=True)
    sp = pd.read_csv(os.path.join(os.path.dirname(CACHE), "..", "data", "sp500.csv"))
    universe = sorted((set(sp["Symbol"]) | set(g.NDX_EXTRA)) - g.BLACKLIST)

    if not os.path.exists(os.path.join(CACHE, "daily.pkl")):
        t0 = time.time()
        daily = g.get_bars(universe + ["SPY"], "1Day", DAILY_START)
        spy = daily.pop("SPY")
        save(daily, "daily.pkl"); save(spy, "spy_daily.pkl")
        print(f"daily: {len(daily)} symbols, {time.time()-t0:.0f}s", flush=True)
    daily, spy = load("daily.pkl"), load("spy_daily.pkl")

    all_sessions = sorted(set(spy.index.tz_convert(g.ET).date))
    sessions = [d for d in all_sessions if BT_START <= d <= BT_END]
    if not os.path.exists(os.path.join(CACHE, "leaders.pkl")):
        t0 = time.time(); leaders = {}
        for k, d in enumerate(sessions):
            prev = all_sessions[all_sessions.index(d) - 1]
            leaders[d] = stage1_all(daily, spy, prev, LEADER_N)
            if k % 50 == 0:
                print(f"stage1 {d} ({k}/{len(sessions)})", flush=True)
        save(leaders, "leaders.pkl")
        print(f"leaders: {len(leaders)} sessions, {time.time()-t0:.0f}s", flush=True)
    leaders = load("leaders.pkl")

    # spans per symbol
    spans = {}
    for d, df in leaders.items():
        for s in df.symbol:
            lo, hi = spans.get(s, (d, d))
            spans[s] = (min(lo, d), max(hi, d))
    print(f"{len(spans)} unique leader symbols", flush=True)

    def utc(dd, days):
        return dt.datetime.combine(dd + dt.timedelta(days=days), dt.time(0), g.ET).astimezone(dt.timezone.utc).isoformat()

    if not os.path.exists(os.path.join(CACHE, "spy5.pkl")):
        spy5 = g.get_bars(["SPY"], "5Min", utc(BT_START, -7), utc(BT_END, 15))["SPY"]
        save(g.intraday_features(spy5), "spy5.pkl")
        print("spy5 done", flush=True)

    os.makedirs(os.path.join(CACHE, "intra"), exist_ok=True)
    todo = [s for s in spans if not os.path.exists(os.path.join(CACHE, "intra", f"{s}.pkl"))]
    t0 = time.time()
    for k, s in enumerate(sorted(todo)):
        lo, hi = spans[s]
        bars = g.get_bars([s], "5Min", utc(lo, -7), utc(hi, 15)).get(s)
        if bars is None or bars.empty:
            print("no intraday data", s, flush=True); continue
        save(g.intraday_features(bars), f"intra/{s}.pkl")
        if k % 10 == 0:
            print(f"intra {k}/{len(todo)} {s} span {lo}..{hi} {time.time()-t0:.0f}s", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
