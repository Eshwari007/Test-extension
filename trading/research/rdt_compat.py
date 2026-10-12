#!/usr/bin/env python3
"""How does the Gajjala signal set perform under the RDT engine's gate chain and exit ladder?

RDT rules approximated from RDT_SYSTEM_OVERVIEW v2.8:
  gates (same bar, 10:00 <= t < 10:30): SPY above prior close; price >= 30-min ORB high OR >= VWAP;
         RVOL > 1.0 (bar volume vs 20-bar avg); candle path 4/4 CLV >= 0.5 at 09:45/09:50/09:55/10:00;
         fast MACD (3/10/16) line > 0
  exits: stop = entry - 1.5*ATR14(daily), capped at 8%; T1 +1.5% sell 25% -> stop to entry;
         T2 +5.5% sell 25% -> stop to T1; T3 +10% sell 25% -> stop to T2; remainder rides the ratchet stop;
         day-2 EOD: no tier and <= -2.5% -> cut; day-3 EOD: no T1 and <= -0.5% -> cut;
         day-4 EOD: no tier -> exit; T1 hit but no T2 within 4 days -> exit; hard max 8 sessions.
2x2: {Gajjala entry, RDT gates} x {Gajjala exits (5% stop, 3d hold), RDT exit ladder}.
"""
import sys, os, math, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Dataset, Params, run, stats, signals_for, orb_feats, tmin
from run import IS, OOS, ALL, OUT
import data as D
import portfolio as P

ds = Dataset(); P.init(ds)
daily = D.load("daily.pkl"); spy_d = D.load("spy_daily.pkl")
ET = D.g.ET

# daily ATR14 and SPY prior close, keyed by session date (as of prior close)
def daily_atr(df):
    d = df.copy(); d.index = d.index.tz_convert(ET).date
    pc = d["c"].shift(1)
    tr = pd.concat([d["h"] - d["l"], (d["h"] - pc).abs(), (d["l"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(14).mean().shift(1)  # as of prior close
ATR = {s: daily_atr(df) for s, df in daily.items()}
spy_dc = spy_d["c"].copy(); spy_dc.index = spy_dc.index.tz_convert(ET).date
SPY_PREV = spy_dc.shift(1)

# per-symbol 5-min features needed for RDT gates
def rdt_feats(s):
    df = ds.sym[s]
    O = orb_feats(ds, s, 6)  # 30-min ORB
    c = df["c"].values
    e3 = pd.Series(c).ewm(span=3, adjust=False).mean(); e10 = pd.Series(c).ewm(span=10, adjust=False).mean()
    macd = (e3 - e10).values
    hl = (df["h"] - df["l"]).values
    clv = np.where(hl > 0, (df["c"] - df["l"]).values / np.where(hl > 0, hl, 1), 1.0)
    mins = df["minute"].values
    # candle path: CLV>=0.5 on the 09:45, 09:50, 09:55, 10:00 bars of the same day -> computed per day
    dates = df["date"].values
    cp = np.zeros(len(df), dtype=bool)
    sdf = pd.DataFrame({"d": dates, "m": mins, "ok": clv >= 0.5})
    good = sdf[sdf.m.isin([585, 590, 595, 600])].groupby("d")["ok"].agg(lambda x: x.all() and len(x) == 4)
    good_days = set(good[good].index)
    cp = np.array([d in good_days for d in dates])
    return dict(orb30_hi=O["orb_hi"], macd=macd, candle=cp)

def spy_green(ts, d):
    px = ds.spy5["c"].get(ts, np.nan); prev = SPY_PREV.get(d, np.nan)
    return (not np.isnan(px)) and (not np.isnan(prev)) and px > prev

def rdt_gate_signals(s, d, vol_mult=1.0):
    """First bar in [10:00,10:30) where all RDT gates pass. Returns bar index or None."""
    df = ds.sym[s]; F = rdt_feats(s)
    idx = np.where(df["date"].values == d)[0]
    if len(idx) == 0:
        return None
    c, v, vw, av = df["c"].values, df["v"].values, df["vwap"].values, df["avgvol20"].values
    for i in idx:
        m = df["minute"].values[i]
        if m < 600 or m >= 630:
            continue
        if not (c[i] >= F["orb30_hi"][i] or c[i] >= vw[i]):
            continue
        if np.isnan(av[i]) or v[i] < vol_mult * av[i]:
            continue
        if not F["candle"][i] or not (F["macd"][i] > 0):
            continue
        if not spy_green(df.index[i], d):
            continue
        return i
    return None

def gaj_entry_signal(s, d, p):
    """First Gajjala ORB15 signal bar of the day (engine's own mask)."""
    m, F = signals_for(ds, s, p)
    idx = np.where(ds.sym[s]["date"].values == d)[0]
    for i in idx:
        if m[i]:
            return i
    return None

def rdt_exits(s, i0):
    df = ds.sym[s]; o, h, l, c = (df[k].values for k in "ohlc"); dates = df["date"].values; mins = df["minute"].values
    entry = c[i0]; d0 = dates[i0]
    atr = ATR[s].get(d0, np.nan)
    stop = entry - 1.5 * atr if not np.isnan(atr) else entry * 0.92
    stop = max(stop, entry * 0.92)
    t1, t2, t3 = entry * 1.015, entry * 1.055, entry * 1.10
    rem = 1.0; fills = []; hit = [False, False, False]; day = 0; t1_day = None
    n = len(df)
    for i in range(i0 + 1, n):
        if dates[i] != dates[i - 1]:
            day += 1
        if l[i] <= stop:
            fills.append((i, rem, min(o[i], stop), "stop")); rem = 0; break
        for k, (tg, nxt) in enumerate(((t1, entry), (t2, t1), (t3, t2))):
            if not hit[k] and h[i] >= tg:
                q = min(0.25, rem); fills.append((i, q, max(o[i], tg), f"T{k+1}")); rem -= q; hit[k] = True
                stop = max(stop, nxt)
                if k == 0: t1_day = day
        if rem <= 1e-9:
            break
        last = (i + 1 >= n) or dates[i + 1] != dates[i]
        if last:
            ret = c[i] / entry - 1
            if day == 2 and not any(hit) and ret <= -0.025: fills.append((i, rem, c[i], "day2_stall")); rem = 0; break
            if day == 3 and not hit[0] and ret <= -0.005: fills.append((i, rem, c[i], "day3_stall")); rem = 0; break
            if day >= 4 and not any(hit): fills.append((i, rem, c[i], "day4_timestop")); rem = 0; break
            if hit[0] and not hit[1] and t1_day is not None and day - t1_day >= 4: fills.append((i, rem, c[i], "t1_t2_timeout")); rem = 0; break
            if day >= 8: fills.append((i, rem, c[i], "maxhold")); rem = 0; break
    if rem > 0:
        fills.append((n - 1, rem, c[n - 1], "end"))
    r = entry - (entry - 1.5 * atr if not np.isnan(atr) else entry * 0.92); r = min(r, entry * 0.08)
    pnl_frac = sum(q * (px - entry) for _, q, px, _ in fills)
    return dict(entry=entry, R=pnl_frac / r, ret=pnl_frac / entry, exit_i=fills[-1][0], reason=fills[-1][3],
                stop0=entry - r)

def gaj_exits(s, i0, stop_pct=5.0, hold=3):
    df = ds.sym[s]; o, h, l, c = (df[k].values for k in "ohlc"); dates = df["date"].values
    entry = c[i0]; stop = entry * (1 - stop_pct / 100); day = 0; n = len(df)
    for i in range(i0 + 1, n):
        if dates[i] != dates[i - 1]: day += 1
        if l[i] <= stop:
            px = min(o[i], stop); return dict(entry=entry, R=(px - entry) / (entry - stop), ret=px / entry - 1, exit_i=i, reason="stop", stop0=stop)
        if day >= hold and ((i + 1 >= n) or dates[i + 1] != dates[i]):
            return dict(entry=entry, R=(c[i] - entry) / (entry - stop), ret=c[i] / entry - 1, exit_i=i, reason="maxhold", stop0=stop)
    return dict(entry=entry, R=(c[n-1] - entry) / (entry - stop), ret=c[n-1] / entry - 1, exit_i=n - 1, reason="end", stop0=stop)

def run_combo(entry_mode, exit_mode, top_n=15, max_off_high=10, label=""):
    p = Params(mode="orb", orb_bars=3, vol_mult=1.5, earliest="09:45", max_off_high=max_off_high, top_n=top_n)
    rows = []; open_until = {}
    for d in ds.sessions:
        L = ds.leaders[d]; L = L[(L["rank"] <= top_n) & (L.pct_off_52w_high * 100 >= -max_off_high)]
        for s in L.symbol:
            if s not in ds.sym: continue
            df = ds.sym[s]
            idx = np.where(df["date"].values == d)[0]
            if len(idx) == 0: continue
            if s in open_until and idx[0] <= open_until[s]: continue
            i = gaj_entry_signal(s, d, p) if entry_mode == "gajjala" else rdt_gate_signals(s, d)
            if i is None: continue
            t = gaj_exits(s, i) if exit_mode == "gajjala" else rdt_exits(s, i)
            open_until[s] = max(t["exit_i"], idx[-1])
            rows.append(dict(session=d, time=df.index[i], symbol=s, entry=round(t["entry"], 2), ret=t["ret"], R=t["R"],
                             reason=t["reason"], exit_time=df.index[t["exit_i"]], stop=round(t["stop0"], 2),
                             exits=f"1.00@{t['entry']*(1+t['ret']):.2f}:{t['reason']}", qty=1, pnl=t["ret"] * 10000))
    tr = pd.DataFrame(rows)
    def st(x):
        if x.empty: return "n=0"
        w = x.R > 0; gp = x.ret[w].sum(); gl = -x.ret[~w].sum()
        return f"n={len(x):4d} win={w.mean():.2f} avgRet={x.ret.mean()*100:+.2f}% avgR={x.R.mean():+.3f} PF={gp/gl if gl>0 else 99:.2f}"
    print(f"{label:52s} ALL {st(tr)} | IS {st(tr[tr.session<=IS[1]])} | OOS {st(tr[tr.session>=OOS[0]])}", flush=True)
    if not tr.empty:
        print("      exits:", tr.reason.value_counts().to_dict(), flush=True)
    return tr

print("=== 2x2: entry rule x exit rule, on the Gajjala Stage 1 set (top 15, within 10% of 52w high) ===")
A = run_combo("gajjala", "gajjala", label="Gajjala entry + Gajjala exits (validated)")
B = run_combo("gajjala", "rdt", label="Gajjala entry + RDT exit ladder")
C = run_combo("rdt", "gajjala", label="RDT gates (10:00-10:30) + Gajjala exits")
Dd = run_combo("rdt", "rdt", label="RDT gates + RDT exit ladder (= plain 6th strategy)")
for name, tr in (("A", A), ("B", B), ("C", C), ("D", Dd)):
    tr.to_csv(f"{OUT}/rdt_compat_{name}.csv", index=False)
print("\n(avgRet = mean return on notional per trade; PF on return basis. RDT R uses the ATR stop as 1R.)")
# portfolio view, 10% sizing, 10 slots, for A and D using return-based fills
for name, tr in (("A: validated rules", A), ("B: Gajjala entry + RDT exits", B), ("D: RDT gates + RDT exits", Dd)):
    if tr.empty: continue
    t = tr.copy(); t["entry"] = t.entry; t["exits"] = t.exits
    P.portfolio(t, 10, 0.10, 5, label=name)
