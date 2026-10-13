#!/usr/bin/env python3
"""Pure out-of-sample test of the swing book, trend book and 50/50 combination on 2023-2024.
Uses the cache built with MOM_CACHE=cache_2324 (daily from 2022, leaders + 5-min bars for 2023-01-03..2024-12-31).
No parameter was touched: same Params as REPORT.md / combined_100k.py."""
import os, sys, io, math, heapq, contextlib, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("MOM_CACHE", os.path.join(HERE, "cache_2324"))
os.environ.setdefault("MOM_DAILY_START", "2022-01-01"); os.environ.setdefault("MOM_BT_START", "2023-01-03"); os.environ.setdefault("MOM_BT_END", "2024-12-31")
sys.path.insert(0, HERE)
import numpy as np, pandas as pd
import data as D
from engine import Dataset, Params, run, stats
import portfolio as P
START, END = D.BT_START, D.BT_END
P.ALL = (START, END)
ET = D.g.ET
ds = Dataset(); P.init(ds)
spy_d = D.load("spy_daily.pkl"); spy_d.index = spy_d.index.tz_convert(ET).date
sessions = sorted(d for d in ds.sessions if START <= d <= END)
spy = spy_d["c"].reindex(sessions)
OUT = os.path.join(HERE, "out")

def show(label, tr):
    s = stats(tr); print(f"{label:48s} n={s['n']:4d} win={s['win']!s:6} avgR={s['avgR']!s:7} PF={s['pf']!s:6} totR={s['totR']:7} maxDD_R={s['maxdd_R']}")
    return s

print(f"=== OUT-OF-SAMPLE {START} -> {END}: {len(sessions)} sessions; SPY {spy.iloc[-1]/spy.iloc[0]-1:+.1%} ===\n")
# ---------------- swing book ----------------
C = Params(mode="orb", orb_bars=3, vol_mult=1.5, stop_mode="pct", stop_pct=5, targets=(), trail="none",
           hold="overnight", max_hold_days=3, earliest="09:45", max_off_high=10)
sw = run(ds, C, START, END)
print("SWING BOOK (per-trade):")
show("  2023-2024", sw); show("  2023", sw[sw.session <= dt.date(2023, 12, 31)]); show("  2024", sw[sw.session >= dt.date(2024, 1, 1)])
q = sw.assign(q=pd.to_datetime(sw.session).dt.to_period("Q")).groupby("q").agg(n=("R", "size"), win=("R", lambda x: round((x > 0).mean(), 2)), totR=("R", "sum"), pf=("R", lambda x: round(x[x > 0].sum() / max(1e-9, -x[x <= 0].sum()), 2)))
print(q.to_string()); sw.to_csv(f"{OUT}/oos2324_swing_trades.csv", index=False)

# ---------------- trend book (B3 rules, daily) ----------------
daily = D.load("daily.pkl")
spy21 = spy_d.c / spy_d.c.shift(21) - 1
def feats(df):
    d = df.copy(); d.index = d.index.tz_convert(ET).date
    d["e21"] = d.c.ewm(span=21, adjust=False).mean(); d["e50"] = d.c.ewm(span=50, adjust=False).mean(); d["s50"] = d.c.rolling(50).mean()
    d["hi20"] = d.h.rolling(20).max().shift(1); d["hi52"] = d.h.rolling(252, min_periods=120).max().shift(1)
    d["r21"] = d.c / d.c.shift(21) - 1; d["dvol"] = (d.c * d.v).rolling(20).mean(); d["rvol"] = d.v / d.v.rolling(20).mean().shift(1)
    d["spy21"] = spy21.reindex(d.index).values
    return d
F = {s: feats(df) for s, df in daily.items()}
trades = []
for s, d in F.items():
    d = d[(d.index >= START - dt.timedelta(days=5)) & (d.index <= END)]
    if len(d) < 30: continue
    cl, lo, op = d.c.values, d.l.values, d.o.values; idx = list(d.index); pos = None
    c = {k: d[k].values for k in ["e21", "e50", "s50", "hi20", "hi52", "r21", "dvol", "rvol", "spy21"]}
    for k in range(1, len(idx) - 1):
        if idx[k] < START: continue
        if pos is None:
            if np.isnan(c["hi52"][k]) or np.isnan(c["e50"][k]): continue
            stage1 = c["r21"][k] > c["spy21"][k] and cl[k] > c["s50"][k] and cl[k] > 10 and c["dvol"][k] > 25e6 and cl[k] / c["hi52"][k] - 1 >= -0.10
            if stage1 and cl[k] > c["hi20"][k] and cl[k] > c["e50"][k] and c["rvol"][k] >= 1.5:
                pos = (k + 1, op[k + 1])
        else:
            ei, ep = pos
            if cl[k] < c["e21"][k]:
                trades.append((s, idx[ei], idx[k + 1], ep, op[k + 1])); pos = None
    if pos: trades.append((s, idx[pos[0]], idx[-1], pos[1], cl[-1]))
tr = pd.DataFrame(trades, columns=["symbol", "entry", "exit", "in_px", "out_px"]); tr["ret"] = tr.out_px / tr.in_px - 1
def tstats(x, label):
    w = x.ret > 0; print(f"{label:48s} n={len(x):4d} win={w.mean():.0%} avg={x.ret.mean()*100:+.2f}% PF={x.ret[w].sum()/max(1e-9,-x.ret[~w].sum()):.2f} avg hold={(pd.to_datetime(x.exit)-pd.to_datetime(x.entry)).dt.days.mean():.0f}d")
print("\nTREND BOOK (per-trade, B3 rules):")
tstats(tr, "  2023-2024"); tstats(tr[tr.entry <= dt.date(2023, 12, 31)], "  2023"); tstats(tr[tr.entry >= dt.date(2024, 1, 1)], "  2024")
tr.to_csv(f"{OUT}/oos2324_trend_trades.csv", index=False)

# ---------------- collar adjustment (earnings-sized gaps inside trend holds) ----------------
gaps = []
for s, d in F.items():
    pc = d.c.shift(1); g = d.o / pc - 1; day = d.c / pc - 1
    m = (g.abs() >= 0.07) & (d.rvol >= 2.0) & (d.index >= START) & (d.index <= END)
    for dte in d.index[m.values]:
        gaps.append((s, dte, day.loc[dte]))
G = pd.DataFrame(gaps, columns=["symbol", "date", "day"])
tr["collar_adj"] = [sum(min(max(e.day, -0.10), 0.15) - e.day for _, e in G[(G.symbol == r.symbol) & (G.date > r.entry) & (G.date <= r.exit)].iterrows()) for _, r in tr.iterrows()]
trc = tr.copy(); trc["ret"] = trc.ret + trc.collar_adj; trc["out_px"] = trc.in_px * (1 + trc.ret)
print(f"earnings-sized gap days inside trend holds: {int((tr.collar_adj != 0).sum())}, collar adds {tr.collar_adj.sum()*100:+.1f} pct-points in total")

# ---------------- portfolios ----------------
closes = {s: F[s].c for s in F}
def trend_port(t, max_pos, size, slip=5e-4, start_eq=1e5):
    t = t.sort_values(["entry", "symbol"]).reset_index(drop=True); by_day = t.groupby("entry"); cash = start_eq; open_pos = {}; eq = []
    for d in sessions:
        for k in [k for k, p in open_pos.items() if p["exit"] == d]:
            p = open_pos.pop(k); cash += p["qty"] * p["out_px"] * (1 - slip)
        if d in by_day.groups:
            for k, r in by_day.get_group(d).iterrows():
                if len(open_pos) >= max_pos: continue
                mv = sum(p["qty"] * closes[p["sym"]].get(d, p["in_px"]) for p in open_pos.values()); px = r.in_px * (1 + slip); qty = math.floor((cash + mv) * size / px)
                if qty <= 0 or qty * px > cash: continue
                cash -= qty * px; open_pos[k] = dict(sym=r.symbol, qty=qty, in_px=px, exit=r.exit, out_px=r.out_px)
        mv = 0.0
        for p in open_pos.values():
            cc = closes[p["sym"]].get(d, np.nan); mv += p["qty"] * (cc if not np.isnan(cc) else p["in_px"])
        eq.append(cash + mv)
    return pd.Series(eq, index=sessions)
def swing_port(t, max_pos, size, start_eq):
    with contextlib.redirect_stdout(io.StringIO()): eq = P.portfolio(t, max_pos, size, 5, start_eq=start_eq, label="")
    return eq.reindex(sessions).ffill()
def pstats(eq, label, base=1e5):
    ret = eq.pct_change().dropna(); yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    y23 = eq[eq.index <= dt.date(2023, 12, 31)]
    print(f"{label:52s} final ${eq.iloc[-1]:,.0f} total {eq.iloc[-1]/base-1:+.1%} CAGR {(eq.iloc[-1]/base)**(1/yrs)-1:+.1%} maxDD {(eq/eq.cummax()-1).min():.1%} Sharpe {ret.mean()/ret.std()*math.sqrt(252):.2f}  2023 {y23.iloc[-1]/base-1:+.1%}  2024 {eq.iloc[-1]/y23.iloc[-1]-1:+.1%}")
print("\nPORTFOLIOS, $100,000, 5 bps slippage:")
spyc = spy / spy.iloc[0] * 1e5; pstats(spyc, "SPY buy and hold")
s100 = swing_port(sw, 10, 0.10, 1e5); pstats(s100, "Swing book only, 10 x 10%")
t100 = trend_port(tr, 10, 0.10); pstats(t100, "Trend book only, 10 x 10%, no collar")
t100c = trend_port(trc, 10, 0.10); pstats(t100c, "Trend book only, 10 x 10%, with collar")
s50 = swing_port(sw, 5, 0.20, 5e4); t50c = trend_port(trc, 5, 0.20, start_eq=5e4); comb5 = s50 + t50c; pstats(comb5, "50/50: swing 5x20% + trend 5x20%, collar (the +111% config)")
s50b = swing_port(sw, 10, 0.10, 5e4); t50bc = trend_port(trc, 10, 0.10, start_eq=5e4); comb10 = s50b + t50bc; pstats(comb10, "50/50: swing 10x10% + trend 10x10%, collar (recommended)")
pd.DataFrame({"spy": spyc, "swing_100k": s100, "trend_100k": t100, "trend_100k_collar": t100c, "combined_5x20": comb5, "combined_10x10": comb10}).to_csv(f"{OUT}/oos2324_curves.csv")
m = comb10.groupby(pd.to_datetime(pd.Series(comb10.index)).dt.to_period("M").values).agg(["first", "last"])
print("\nmonthly P&L, 50/50 10x10% + collar:"); print(((m["last"] / m["first"] - 1) * 100).round(1).to_string())
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(11, 5.5)); x = pd.to_datetime(pd.Series(sessions))
for ser, lab, lw, col in ((comb10, "50/50 swing + trend (10x10%), collar", 2.2, None), (s100, "Swing book only", 1.3, None), (t100c, "Trend book only (collar)", 1.3, None), (spyc, "SPY", 1.2, "gray")):
    ax.plot(x, ser.values, lw=lw, label=lab, ls="--" if lab == "SPY" else "-", color=col)
ax.set_title(f"Out-of-sample: $100,000 from {START} to {END} (rules frozen from the 2025-26 study)"); ax.set_ylabel("USD"); ax.grid(alpha=.3); ax.legend(); fig.tight_layout(); fig.savefig(f"{OUT}/oos2324_curves.png", dpi=130)
print("\nchart saved")
