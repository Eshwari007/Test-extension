#!/usr/bin/env python3
"""Gajjala Momentum Scanner (US) - replay version.

Stage 1 (daily): rank S&P 500 + Nasdaq 100 names by 21-day return, keep those that
beat SPY's 21-day return, close above the 50-day SMA, trade above $10 and average
at least $25M/day over 20 days. Top N go to Stage 2.

Stage 2 (5-min, regular hours): close > EMA9 > EMA21, close > session VWAP,
6-bar pole >= +1.5%, 6-bar flag with range <= 1.2% holding above VWAP, breakout
close > flag high on volume >= 1.5x the 20-bar average, SPY above its own VWAP.

This replay runs Stage 1 as of each prior close for the last SESSIONS sessions and
scans every 5-minute bar of that session, so it reports every signal that fired,
not just the latest bar.
"""
import sys, time, json, math, datetime as dt
from zoneinfo import ZoneInfo
import requests
import pandas as pd
import numpy as np

DATA = "https://data.alpaca.markets/v2/stocks/bars"
FEED = "sip"
ACCOUNT_SIZE = 100_000
RISK_PCT = 0.005
MIN_PRICE = 10.0
MIN_DOLLAR_VOL = 25_000_000
REQUIRE_200SMA = False
LOOKBACK_1M = 21
TOP_N = 15
FLAG_BARS = 6
POLE_BARS = 6
MIN_POLE_PCT = 1.5
MAX_FLAG_RANGE_PCT = 1.2
VOL_MULT = 1.5
TARGETS_PCT = (2.5, 5.5, 10.0)
SESSIONS = 5
BLACKLIST = {"MP"}
# Nasdaq-100 members that are not in the S&P 500 (Wikipedia is unreachable here).
NDX_EXTRA = ["SHOP", "ARM", "MSTR", "MELI", "PDD", "ASML", "AZN", "TEAM", "ZS",
             "CCEP", "GFS", "TTD", "CRWV"]
ET = ZoneInfo("America/New_York")

sess = requests.Session()


def get_bars(symbols, timeframe, start, end=None, adjustment="split"):
    """Fetch bars for many symbols, following pagination. Returns {sym: DataFrame}."""
    out = {s: [] for s in symbols}
    for i in range(0, len(symbols), 200):
        chunk = symbols[i:i + 200]
        params = {"symbols": ",".join(chunk), "timeframe": timeframe, "start": start,
                  "limit": 10000, "feed": FEED, "adjustment": adjustment, "sort": "asc"}
        if end:
            params["end"] = end
        token = None
        while True:
            if token:
                params["page_token"] = token
            for attempt in range(5):
                r = sess.get(DATA, params=params, timeout=60)
                if r.status_code == 429:
                    time.sleep(2 ** attempt); continue
                r.raise_for_status(); break
            js = r.json()
            for s, bars in (js.get("bars") or {}).items():
                out[s].extend(bars)
            token = js.get("next_page_token")
            if not token:
                break
    frames = {}
    for s, bars in out.items():
        if not bars:
            continue
        df = pd.DataFrame(bars)
        df["t"] = pd.to_datetime(df["t"], utc=True)
        df = df.set_index("t").sort_index()[["o", "h", "l", "c", "v"]].astype(float)
        frames[s] = df
    return frames


def stage1(daily, spy, asof):
    """Daily filter using bars up to and including `asof` (a date). Returns leaders DF."""
    sp = spy[spy.index.tz_convert(ET).date <= asof]["c"]
    spy_ret = sp.iloc[-1] / sp.iloc[-LOOKBACK_1M - 1] - 1
    rows = []
    for sym, df in daily.items():
        d = df[df.index.tz_convert(ET).date <= asof]
        if len(d) < 60:
            continue
        c = d["c"]
        close = c.iloc[-1]
        ret1m = close / c.iloc[-LOOKBACK_1M - 1] - 1
        sma50 = c.iloc[-50:].mean()
        sma200 = c.iloc[-200:].mean() if len(c) >= 200 else np.nan
        dvol = (d["c"] * d["v"]).iloc[-20:].mean()
        hi52 = d["h"].iloc[-252:].max()
        ok = (ret1m > spy_ret and close > sma50 and close > MIN_PRICE and dvol > MIN_DOLLAR_VOL
              and (not REQUIRE_200SMA or close > sma200))
        rows.append(dict(symbol=sym, close=close, ret_1m=ret1m, rs_vs_spy=ret1m - spy_ret,
                         above_50sma=close > sma50, above_200sma=bool(close > sma200) if not np.isnan(sma200) else None,
                         pct_off_52w_high=close / hi52 - 1, avg_dollar_vol=dvol, passes=ok))
    allrows = pd.DataFrame(rows).sort_values("ret_1m", ascending=False)
    leaders = allrows[allrows.passes].head(TOP_N).copy()
    leaders["rank"] = range(1, len(leaders) + 1)
    return leaders, allrows, spy_ret


def intraday_features(df):
    """Regular-hours filter, per-session VWAP, EMA9/21, 20-bar avg volume."""
    idx = df.index.tz_convert(ET)
    df = df.copy(); df.index = idx
    t = df.index.time
    df = df[(t >= dt.time(9, 30)) & (t < dt.time(16, 0))]
    df["date"] = df.index.date
    tp = (df["h"] + df["l"] + df["c"]) / 3
    df["tpv"] = tp * df["v"]
    g = df.groupby("date")
    df["vwap"] = g["tpv"].cumsum() / g["v"].cumsum()
    df["ema9"] = df["c"].ewm(span=9, adjust=False).mean()
    df["ema21"] = df["c"].ewm(span=21, adjust=False).mean()
    df["avgvol20"] = df["v"].shift(1).rolling(20).mean()
    return df


def check_bar(df, i, spy_above_vwap):
    """Evaluate all seven checks on bar i of df (positional)."""
    row = df.iloc[i]
    flag = df.iloc[i - FLAG_BARS:i]
    pole = df.iloc[i - FLAG_BARS - POLE_BARS:i - FLAG_BARS]
    if len(flag) < FLAG_BARS or len(pole) < POLE_BARS or np.isnan(row.avgvol20):
        return None
    # all bars must be in the same session
    if len(set(df["date"].iloc[i - FLAG_BARS - POLE_BARS:i + 1])) != 1:
        return None
    pole_pct = (pole["c"].iloc[-1] / pole["o"].iloc[0] - 1) * 100
    flag_hi, flag_lo = flag["h"].max(), flag["l"].min()
    flag_range_pct = (flag_hi / flag_lo - 1) * 100
    checks = {
        "ema_stack": row.c > row.ema9 > row.ema21,
        "above_vwap": row.c > row.vwap,
        "pole": pole_pct >= MIN_POLE_PCT,
        "flag_tight": flag_range_pct <= MAX_FLAG_RANGE_PCT,
        "flag_above_vwap": bool((flag["c"] > flag["vwap"]).all()),
        "breakout": row.c > flag_hi,
        "volume": row.v >= VOL_MULT * row.avgvol20,
        "spy_above_vwap": bool(spy_above_vwap),
    }
    entry, stop = row.c, flag_lo
    risk = entry - stop
    qty = math.floor(ACCOUNT_SIZE * RISK_PCT / risk) if risk > 0 else 0
    return dict(time=df.index[i], checks=checks, n_pass=sum(checks.values()),
                signal=all(checks.values()), entry=entry, stop=stop,
                risk_pct=risk / entry * 100, qty=qty, pole_pct=pole_pct,
                flag_range_pct=flag_range_pct, flag_high=flag_hi,
                vol_ratio=row.v / row.avgvol20,
                t1=entry * (1 + TARGETS_PCT[0] / 100), t2=entry * (1 + TARGETS_PCT[1] / 100),
                t3=entry * (1 + TARGETS_PCT[2] / 100))


def main(sp500_csv, outdir):
    sp = pd.read_csv(sp500_csv)
    universe = sorted((set(sp["Symbol"]) | set(NDX_EXTRA)) - BLACKLIST)
    print(f"Universe: {len(universe)} symbols")
    today = dt.date.today()
    start_daily = (today - dt.timedelta(days=320)).isoformat()
    t0 = time.time()
    daily = get_bars(universe + ["SPY"], "1Day", start_daily)
    spy = daily.pop("SPY")
    print(f"Daily bars for {len(daily)} symbols in {time.time()-t0:.0f}s; last SPY bar {spy.index[-1].date()}")
    sessions = sorted(set(spy.index.tz_convert(ET).date))[-SESSIONS:]
    all_sessions = sorted(set(spy.index.tz_convert(ET).date))

    leaders_by_day, signals, near = {}, [], []
    for d in sessions:
        prev = all_sessions[all_sessions.index(d) - 1]
        leaders, allrows, spy_ret = stage1(daily, spy, prev)
        leaders["asof"] = prev; leaders["session"] = d
        leaders_by_day[d] = leaders
        print(f"\n=== Session {d}  (Stage 1 as of {prev} close; SPY 21d return {spy_ret*100:+.2f}%; "
              f"{int(allrows.passes.sum())} pass filters) ===")
        print(leaders[["rank", "symbol", "close", "ret_1m", "rs_vs_spy", "pct_off_52w_high", "avg_dollar_vol"]]
              .to_string(index=False, formatters={"ret_1m": "{:+.1%}".format, "rs_vs_spy": "{:+.1%}".format,
                                                  "pct_off_52w_high": "{:+.1%}".format,
                                                  "avg_dollar_vol": "${:,.0f}".format, "close": "{:.2f}".format}))
        syms = list(leaders.symbol)
        start = dt.datetime.combine(d - dt.timedelta(days=4), dt.time(0), ET).astimezone(dt.timezone.utc).isoformat()
        end = dt.datetime.combine(d, dt.time(23, 59), ET).astimezone(dt.timezone.utc).isoformat()
        intra = get_bars(syms + ["SPY"], "5Min", start, end)
        spy5 = intraday_features(intra.pop("SPY"))
        spy_flag = (spy5["c"] > spy5["vwap"])
        for s in syms:
            if s not in intra:
                continue
            f = intraday_features(intra[s])
            idxs = np.where(f["date"].values == d)[0]
            best = None
            for i in idxs:
                ts = f.index[i]
                spy_ok = bool(spy_flag.get(ts, False))
                res = check_bar(f, i, spy_ok)
                if res is None:
                    continue
                res["symbol"] = s; res["session"] = d
                if res["signal"]:
                    signals.append(res)
                if best is None or res["n_pass"] > best["n_pass"]:
                    best = res
            if best:
                near.append(best)

    # ---- output ----
    sig = pd.DataFrame([{**{k: v for k, v in r.items() if k != "checks"},
                         **{"chk_" + k: v for k, v in r["checks"].items()}} for r in signals])
    nr = pd.DataFrame([{**{k: v for k, v in r.items() if k != "checks"},
                        **{"chk_" + k: v for k, v in r["checks"].items()}} for r in near])
    pd.concat(leaders_by_day.values()).to_csv(f"{outdir}/us_momentum_leaders.csv", index=False)
    sig.to_csv(f"{outdir}/us_intraday_setups.csv", index=False)
    nr.to_csv(f"{outdir}/us_best_bar_per_leader.csv", index=False)
    print("\n\n######## SIGNALS (all 8 checks passed) ########")
    if sig.empty:
        print("None.")
    else:
        print(sig[["session", "time", "symbol", "entry", "stop", "risk_pct", "qty", "t1", "t2", "t3",
                   "pole_pct", "flag_range_pct", "vol_ratio"]].to_string(index=False))
    print("\n\n######## Best bar per leader per session (checks passed out of 8) ########")
    cols = ["session", "symbol", "time", "n_pass"] + [c for c in nr.columns if c.startswith("chk_")]
    print(nr.sort_values(["session", "n_pass"], ascending=[True, False])[cols]
          .to_string(index=False, formatters={"time": lambda t: t.strftime("%H:%M")}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
