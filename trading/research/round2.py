#!/usr/bin/env python3
"""Round 2: structural variants (exits, stops, swing holds, ORB entries) on the full period and IS/OOS."""
import sys, os, datetime as dt
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Dataset, Params, run, stats, monthly
from dataclasses import replace
from run import show, IS, OOS, ALL, OUT

ds = Dataset()
base = Params(pole_min=0.75)
rows = []
def ev(label, p):
    a = stats(run(ds, p, *ALL)); i = stats(run(ds, p, *IS)); o = stats(run(ds, p, *OOS))
    print(f"{label:55s} ALL n={a['n']:4d} win={a['win']!s:5} avgR={a['avgR']!s:7} pf={a['pf']!s:5} dd={a['maxdd_R']:6} | IS avgR={i['avgR']!s:7} pf={i['pf']!s:5} n={i['n']:3d} | OOS avgR={o['avgR']!s:7} pf={o['pf']!s:5} n={o['n']:3d}", flush=True)
    rows.append(dict(label=label, **{f"all_{k}": v for k, v in a.items()}, **{f"is_{k}": v for k, v in i.items()}, **{f"oos_{k}": v for k, v in o.items()}))

print("=== EXITS (flag entry, pole 0.75) ===")
ev("spec exits (T 2.5/5.5/10 + ema9 trail)", base)
ev("hold to close, no targets, no trail", replace(base, targets=(), trail="none"))
ev("hold to close, BE after 1R", replace(base, targets=(), trail="be"))
ev("hold to close, ema21 trail after 1R", replace(base, targets=(), trail="ema21"))
ev("hold to close, ema21 trail after 2R", replace(base, targets=(), trail="ema21", trail_trigger_r=2))
ev("targets 1.5/3/5 + ema9 trail", replace(base, targets=(1.5, 3.0, 5.0)))
ev("targets 5/10/15 + ema21 trail", replace(base, targets=(5, 10, 15), trail="ema21"))
print("\n=== STOPS ===")
for am in (1.0, 1.5, 2.0, 3.0):
    ev(f"ATR stop {am}x, hold to close, ema21 trail", replace(base, stop_mode="atr", atr_mult=am, targets=(), trail="ema21"))
    ev(f"ATR stop {am}x, spec exits", replace(base, stop_mode="atr", atr_mult=am))
ev("pole_low stop, hold to close, ema21 trail", replace(base, stop_mode="pole_low", targets=(), trail="ema21"))
print("\n=== SWING HOLDS (overnight) ===")
for days in (1, 2, 3, 5, 10):
    ev(f"swing {days}d, no targets, no trail, flag stop", replace(base, hold="overnight", max_hold_days=days, targets=(), trail="none"))
    ev(f"swing {days}d, ATR2 stop, no targets, ema21 trail", replace(base, hold="overnight", max_hold_days=days, stop_mode="atr", atr_mult=2.0, targets=(), trail="ema21"))
    ev(f"swing {days}d, ATR2 stop, targets 5/10/15", replace(base, hold="overnight", max_hold_days=days, stop_mode="atr", atr_mult=2.0, targets=(5, 10, 15), trail="none"))
print("\n=== OPENING RANGE BREAKOUT (leaders only) ===")
for nb in (3, 6, 12):
    for vm in (0, 1.5):
        ev(f"ORB {nb*5}min, vol>={vm}, hold to close, no trail", replace(base, mode="orb", orb_bars=nb, vol_mult=vm, targets=(), trail="none", earliest="09:45"))
        ev(f"ORB {nb*5}min, vol>={vm}, hold to close, ema21 trail", replace(base, mode="orb", orb_bars=nb, vol_mult=vm, targets=(), trail="ema21", earliest="09:45"))
        ev(f"ORB {nb*5}min, vol>={vm}, spec exits", replace(base, mode="orb", orb_bars=nb, vol_mult=vm, earliest="09:45"))
        ev(f"ORB {nb*5}min, vol>={vm}, ATR2 stop, hold to close", replace(base, mode="orb", orb_bars=nb, vol_mult=vm, stop_mode="atr", atr_mult=2.0, targets=(), trail="none", earliest="09:45"))
        ev(f"ORB {nb*5}min, vol>={vm}, swing 3d ATR2", replace(base, mode="orb", orb_bars=nb, vol_mult=vm, stop_mode="atr", atr_mult=2.0, targets=(), trail="none", hold="overnight", max_hold_days=3, earliest="09:45"))
ev("ORB 30min no filters at all, hold to close", replace(base, mode="orb", orb_bars=6, vol_mult=0, ema_stack=False, above_vwap=False, spy_vwap=False, targets=(), trail="none", earliest="09:45"))
pd.DataFrame(rows).to_csv(f"{OUT}/round2.csv", index=False)
