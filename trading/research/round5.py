#!/usr/bin/env python3
"""Round 5: robustness of the chosen config (ORB15 + vol1.5 + within 10% of 52w high + 3d hold + 5% stop)."""
import sys, os, datetime as dt
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Dataset, Params, run, stats
from dataclasses import replace
from run import IS, OOS, ALL, OUT

ds = Dataset()
C = Params(mode="orb", orb_bars=3, vol_mult=1.5, stop_mode="pct", stop_pct=5, targets=(), trail="none",
           hold="overnight", max_hold_days=3, earliest="09:45", max_off_high=10)
def ev(label, p):
    tr = run(ds, p, *ALL); a = stats(tr); i = stats(tr[tr.session <= IS[1]]); o = stats(tr[tr.session >= OOS[0]])
    print(f"{label:48s} n={a['n']:4d} win={a['win']!s:5} avgR={a['avgR']!s:7} pf={a['pf']!s:5} dd={a['maxdd_R']:6} | IS avgR={i['avgR']!s:7} pf={i['pf']!s:5} | OOS avgR={o['avgR']!s:7} pf={o['pf']!s:5}", flush=True)
    return tr

tr = ev("CHOSEN", C)
print("\n--- by quarter ---")
t = tr.copy(); t["q"] = pd.to_datetime(t.session).dt.to_period("Q")
print(t.groupby("q").agg(n=("R", "size"), win=("R", lambda x: round((x > 0).mean(), 2)), avgR=("R", "mean"), totR=("R", "sum"), pnl=("pnl", "sum")).round(2).to_string())
print("\n--- parameter neighbourhood ---")
for v in (5, 7.5, 10, 15, 20, 100): ev(f"max_off_high={v}", replace(C, max_off_high=v))
for v in (3, 4, 5, 6, 7, 8): ev(f"stop_pct={v}", replace(C, stop_pct=v))
for v in (1, 2, 3, 4, 5): ev(f"max_hold_days={v}", replace(C, max_hold_days=v))
for v in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5): ev(f"vol_mult={v}", replace(C, vol_mult=v))
for v in (2, 3, 4, 6): ev(f"orb_bars={v}", replace(C, orb_bars=v))
for v in (10, 15, 20, 30): ev(f"top_n={v}", replace(C, top_n=v))
for v in ("10:30", "12:00", "14:00", "15:55"): ev(f"latest={v}", replace(C, latest=v))
print("\n--- which filters matter ---")
ev("no ema stack", replace(C, ema_stack=False)); ev("no vwap", replace(C, above_vwap=False)); ev("no spy vwap", replace(C, spy_vwap=False))
ev("no ema, no vwap", replace(C, ema_stack=False, above_vwap=False)); ev("none of the three", replace(C, ema_stack=False, above_vwap=False, spy_vwap=False))
ev("require_200sma too", replace(C, require_200sma=True))
ev("exit at close of day 3 (same) but 09:30 entries allowed", replace(C, earliest="09:30"))
print("\n--- entry time of day ---")
t["hour"] = pd.to_datetime(t.time).dt.hour
print(t.groupby("hour").agg(n=("R", "size"), avgR=("R", "mean"), pf=("R", lambda x: x[x > 0].sum() / max(1e-9, -x[x <= 0].sum()))).round(2).to_string())
print("\n--- exit reasons / holding ---")
print(t.exits.str.extract(r":(\w+)$")[0].value_counts().to_dict())
print("\n--- symbol concentration (top 15 by P&L) ---")
g = t.groupby("symbol").agg(n=("R", "size"), R=("R", "sum"), pnl=("pnl", "sum")).sort_values("pnl", ascending=False)
print(g.head(15).round(1).to_string()); print(f"top 5 symbols = {g.pnl.head(5).sum()/t.pnl.sum():.0%} of P&L; {len(g)} symbols traded")
print("\n--- bootstrap: 2000 reshuffles of trade order, 10% size, drawdown of a sum-of-R equity ---")
rng = np.random.default_rng(0); R = t.R.values; dds = []; tot = []
for _ in range(2000):
    s = rng.choice(R, size=len(R), replace=True); eq = np.cumsum(s); dds.append((eq - np.maximum.accumulate(eq)).min()); tot.append(eq[-1])
print(f"total R: median {np.median(tot):.0f}, 5th pct {np.percentile(tot,5):.0f}, P(total<=0)={np.mean(np.array(tot)<=0):.3f}; maxDD R: median {np.median(dds):.0f}, 95th pct {np.percentile(dds,5):.0f}")
print("(1R = 5% of a position = 0.5% of equity at 10% sizing, so a 20R drawdown ~ 10% of equity)")
tr.to_csv(f"{OUT}/chosen_trades.csv", index=False)
