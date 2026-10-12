#!/usr/bin/env python3
"""Round 3: is the multi-day ORB edge real? Benchmarks, stop types, hold lengths, filters, yearly and loss profile."""
import sys, os, datetime as dt
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Dataset, Params, run, stats, monthly
from dataclasses import replace
from run import IS, OOS, ALL, OUT

ds = Dataset()
rows = []
def ev(label, p, keep=False):
    tr = run(ds, p, *ALL)
    a = stats(tr); i = stats(tr[tr.session <= IS[1]]); o = stats(tr[tr.session >= OOS[0]])
    print(f"{label:58s} ALL n={a['n']:4d} win={a['win']!s:5} avgR={a['avgR']!s:7} pf={a['pf']!s:5} dd={a['maxdd_R']:7} | IS avgR={i['avgR']!s:7} pf={i['pf']!s:5} | OOS avgR={o['avgR']!s:7} pf={o['pf']!s:5} n={o['n']:3d}", flush=True)
    rows.append(dict(label=label, **{f"all_{k}": v for k, v in a.items()}, **{f"is_{k}": v for k, v in i.items()}, **{f"oos_{k}": v for k, v in o.items()}))
    return tr

sw = Params(mode="orb", orb_bars=3, vol_mult=1.5, stop_mode="atr", atr_mult=2.0, targets=(), trail="none",
            hold="overnight", max_hold_days=3, earliest="09:45")
print("=== BENCHMARKS: buy every leader unconditionally at 09:45 (bar 3) and hold N days ===")
for days in (1, 3, 5):
    ev(f"BENCH buy@09:45 all leaders, hold {days}d, ATR2 stop", replace(sw, mode="open", max_hold_days=days))
    ev(f"BENCH buy@09:45 all leaders, hold {days}d, 5% stop", replace(sw, mode="open", max_hold_days=days, stop_mode="pct", stop_pct=5))
    ev(f"BENCH buy@09:45 all leaders, hold {days}d, no stop", replace(sw, mode="open", max_hold_days=days, stop_mode="pct", stop_pct=50))
print("\n=== ORB-15 vol1.5 swing: stop type x hold ===")
for days in (1, 2, 3, 5, 8):
    for sm, kw in (("ATR2", dict(stop_mode="atr", atr_mult=2.0)), ("ATR4", dict(stop_mode="atr", atr_mult=4.0)),
                   ("ORB low", dict(stop_mode="flag_low")), ("3%", dict(stop_mode="pct", stop_pct=3)),
                   ("5%", dict(stop_mode="pct", stop_pct=5)), ("8%", dict(stop_mode="pct", stop_pct=8))):
        ev(f"ORB15 vol1.5 hold {days}d stop {sm}", replace(sw, max_hold_days=days, **kw))
print("\n=== ORB-15 swing 3d, 5% stop: filters ===")
s5 = replace(sw, stop_mode="pct", stop_pct=5)
ev("ref: ORB15 vol1.5 3d 5%", s5)
ev("vol>=1.2", replace(s5, vol_mult=1.2)); ev("vol>=2.0", replace(s5, vol_mult=2.0)); ev("vol off", replace(s5, vol_mult=0))
ev("no ema stack", replace(s5, ema_stack=False)); ev("no vwap", replace(s5, above_vwap=False)); ev("no spy", replace(s5, spy_vwap=False))
ev("no ema/vwap/spy filters", replace(s5, ema_stack=False, above_vwap=False, spy_vwap=False))
ev("top_n=10", replace(s5, top_n=10)); ev("top_n=5", replace(s5, top_n=5)); ev("top_n=30", replace(s5, top_n=30))
ev("latest 10:30", replace(s5, latest="10:30")); ev("latest 12:00", replace(s5, latest="12:00"))
ev("day gain >= 1% at entry", replace(s5, min_pole_pct_day=1.0)); ev("day gain >= 2% at entry", replace(s5, min_pole_pct_day=2.0))
ev("require 200sma", replace(s5, require_200sma=True)); ev("within 10% of 52w high", replace(s5, max_off_high=10)); ev("within 5% of 52w high", replace(s5, max_off_high=5))
ev("ORB 30min instead of 15", replace(s5, orb_bars=6)); ev("ORB 10min", replace(s5, orb_bars=2))
ev("ema21 trail after 2R", replace(s5, trail="ema21", trail_trigger_r=2)); ev("BE after 2R", replace(s5, trail="be", trail_trigger_r=2))
ev("targets 5/10/15", replace(s5, targets=(5, 10, 15)))
pd.DataFrame(rows).to_csv(f"{OUT}/round3.csv", index=False)

print("\n=== DEEP DIVE: ORB15 vol1.5, 3d hold, 5% stop ===")
tr = run(ds, s5, *ALL); tr.to_csv(f"{OUT}/orb_swing_trades.csv", index=False)
t = tr.copy(); t["month"] = pd.to_datetime(t.session).dt.to_period("M"); t["year"] = pd.to_datetime(t.session).dt.year
print(t.groupby("year").agg(n=("R", "size"), win=("R", lambda x: (x > 0).mean()), avgR=("R", "mean"), totR=("R", "sum"), pnl=("pnl", "sum")).round(3).to_string())
print(t.groupby("month").agg(n=("R", "size"), win=("R", lambda x: (x > 0).mean()), R=("R", "sum"), pnl=("pnl", "sum")).round(2).to_string())
print("\nR distribution:", t.R.describe().round(2).to_dict())
print("losses worse than -1.5R (gaps):", (t.R < -1.5).sum(), " worst 5:", t.nsmallest(5, "R")[["session", "symbol", "R", "exits"]].to_string())
print("top 10 winners:", t.nlargest(10, "R")[["session", "symbol", "R", "pnl", "exits"]].to_string())
# concurrency
ev_ = []
for _, r in t.iterrows():
    ev_.append((r.time, 1)); ev_.append((r.exit_time, -1))
ev_.sort(); cur = 0; mx = 0
for _, dlt in ev_:
    cur += dlt; mx = max(mx, cur)
print("max concurrent positions:", mx)
# share of P&L from top trades
tt = t.sort_values("pnl", ascending=False)
print(f"total pnl ${t.pnl.sum():,.0f}; top 10 trades = ${tt.pnl.head(10).sum():,.0f}; without top 10: ${t.pnl.sum()-tt.pnl.head(10).sum():,.0f}")
print("exit reasons:", t.exits.str.extract(r":(\w+)$")[0].value_counts().to_dict())
