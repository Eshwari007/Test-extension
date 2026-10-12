"""Overlap and daily-bar comparison: Gajjala Stage 1 vs an approximation of the RDT Swing Trade Setup."""
import sys, os, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, '.')
import data as D
ET = D.g.ET
daily = D.load("daily.pkl"); spy = D.load("spy_daily.pkl")
def prep(df):
    d = df.copy(); d.index = d.index.tz_convert(ET).date
    c = d["c"]; pc = c.shift(1)
    tr = pd.concat([d["h"]-d["l"], (d["h"]-pc).abs(), (d["l"]-pc).abs()], axis=1).max(axis=1)
    d["ema50"] = c.ewm(span=50, adjust=False).mean(); d["sma50"] = c.rolling(50).mean()
    d["atr5"] = tr.rolling(5).mean(); d["atr20"] = tr.rolling(20).mean()
    d["ret10"] = c / c.shift(10) - 1; d["ret21"] = c / c.shift(21) - 1
    d["hi52"] = d["h"].rolling(252, min_periods=120).max(); d["dvol20"] = (c * d["v"]).rolling(20).mean()
    d["rvol"] = d["v"] / d["v"].rolling(20).mean()
    return d
P = {s: prep(df) for s, df in daily.items()}; S = prep(spy)
sessions = [d for d in S.index if dt.date(2025,1,2) <= d <= dt.date(2026,10,9)]
idx_of = {d: i for i, d in enumerate(S.index)}
rows = []
for d in sessions:
    prev = S.index[idx_of[d]-1]
    spy_r10, spy_r21 = S.loc[prev, "ret10"], S.loc[prev, "ret21"]
    gaj, rdt = [], []
    for s, p in P.items():
        if prev not in p.index: continue
        r = p.loc[prev]
        if np.isnan(r.hi52) or np.isnan(r.sma50): continue
        off = r.c / r.hi52 - 1
        if r.ret21 > spy_r21 and r.c > r.sma50 and r.c > 10 and r.dvol20 > 25e6 and off >= -0.10:
            gaj.append((s, r.ret21))
        rs10 = (r.ret10 - spy_r10) * 100
        if rs10 >= 1 and r.c > r.ema50 and r.atr5 < 0.8 * r.atr20 and off >= -0.10:
            rdt.append((s, rs10))
    gaj = [s for s, _ in sorted(gaj, key=lambda x: -x[1])[:15]]
    rdt_all = [s for s, _ in sorted(rdt, key=lambda x: -x[1])]
    rows.append(dict(session=d, gaj=gaj, rdt_all=rdt_all, rdt15=rdt_all[:15]))
R = pd.DataFrame(rows)
ov_all = R.apply(lambda r: len(set(r.gaj) & set(r.rdt_all)) / max(1, len(r.gaj)), axis=1)
ov15 = R.apply(lambda r: len(set(r.gaj) & set(r.rdt15)) / max(1, len(r.gaj)), axis=1)
print(f"sessions {len(R)}; avg Gajjala list size {R.gaj.str.len().mean():.1f}; avg RDT-swing list size {R.rdt_all.str.len().mean():.1f}")
print(f"share of Gajjala names also in RDT-swing (any rank): {ov_all.mean():.0%}; in RDT-swing top 15: {ov15.mean():.0%}")
print(f"share of RDT-swing top-15 names also in Gajjala top 15: {R.apply(lambda r: len(set(r.gaj)&set(r.rdt15))/max(1,len(r.rdt15)),axis=1).mean():.0%}")
# daily-bar proxy performance: buy next open, 5% stop on lows, sell 3rd close
def proxy(names_by_day):
    out = []
    for r in R.itertuples():
        for s in getattr(r, names_by_day):
            p = P[s]
            if r.session not in p.index: continue
            i = p.index.get_loc(r.session)
            if i + 3 >= len(p): continue
            entry = p["o"].iloc[i]; stop = entry * 0.95; ret = None
            for k in range(i, i + 3):
                if p["l"].iloc[k] <= stop: ret = min(p["o"].iloc[k], stop) / entry - 1 if k > i else stop / entry - 1; break
            if ret is None: ret = p["c"].iloc[i + 2] / entry - 1
            out.append(ret)
    a = np.array(out); w = a > 0
    return f"n={len(a):5d} avg={a.mean()*100:+.2f}% win={w.mean():.0%} PF={a[w].sum()/max(1e-9,-a[~w].sum()):.2f}"
print("\nDaily-bar proxy (buy next open, 5% stop, sell 3rd close), no intraday entry filter:")
print("  Gajjala Stage 1 top 15        ", proxy("gaj"))
print("  RDT Swing approx, top 15 by RS", proxy("rdt15"))
print("  RDT Swing approx, all         ", proxy("rdt_all"))
R["gaj_only"] = R.apply(lambda r: [s for s in r.gaj if s not in set(r.rdt_all)], axis=1)
print("  Gajjala names NOT in RDT swing", proxy("gaj_only"))
R["both"] = R.apply(lambda r: [s for s in r.gaj if s in set(r.rdt_all)], axis=1)
print("  Gajjala names ALSO in RDT swing", proxy("both"))
