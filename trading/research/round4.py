#!/usr/bin/env python3
"""Round 4: true benchmark, combined filters, and a portfolio simulation with capital limits vs SPY."""
import sys, os, math, datetime as dt
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Dataset, Params, run, stats
from dataclasses import replace
from run import IS, OOS, ALL, OUT
import data as D

ds = Dataset()
spy_d = D.load("spy_daily.pkl"); spy_d.index = spy_d.index.tz_convert(D.g.ET).date
# last 5-min close per symbol per session, for daily marking
daily_close = {s: df.groupby("date")["c"].last() for s, df in ds.sym.items()}

rows = []
def ev(label, p):
    tr = run(ds, p, *ALL)
    a = stats(tr); i = stats(tr[tr.session <= IS[1]]); o = stats(tr[tr.session >= OOS[0]])
    print(f"{label:62s} ALL n={a['n']:4d} win={a['win']!s:5} avgR={a['avgR']!s:7} pf={a['pf']!s:5} dd={a['maxdd_R']:7} | IS avgR={i['avgR']!s:7} pf={i['pf']!s:5} | OOS avgR={o['avgR']!s:7} pf={o['pf']!s:5} n={o['n']:3d}", flush=True)
    rows.append(dict(label=label, **{f"all_{k}": v for k, v in a.items()}, **{f"is_{k}": v for k, v in i.items()}, **{f"oos_{k}": v for k, v in o.items()}))
    return tr


def portfolio(tr, max_pos=10, size_frac=0.10, slip_bps=5, start_eq=100_000, label=""):
    """Single chronological pass. Size = size_frac of current equity; skip signals when max_pos open or cash short."""
    tr = tr.sort_values("time").reset_index(drop=True)
    tr["exit_px"] = tr.exits.str.split("@").str[1].str.split(":").str[0].astype(float)
    sessions = sorted({d for d in ds.sessions if ALL[0] <= d <= ALL[1]})
    # events: exits are processed before entries at the same timestamp
    events = [(r.time, 0, k) for k, r in tr.iterrows()]  # entries; exits are added when a trade is taken
    import heapq
    heapq.heapify(events)
    cash = start_eq; open_pos = {}; skipped = 0; taken = 0
    eq_curve = {}; exposure = []
    si = 0
    def mark(d):
        mv = 0.0
        for p in open_pos.values():
            c = daily_close[p["sym"]].get(d, np.nan)
            mv += p["qty"] * (c if not np.isnan(c) else p["entry"])
        return mv
    while events:
        t, kind, k = heapq.heappop(events)
        # close out sessions that ended before this event
        while si < len(sessions) and pd.Timestamp(dt.datetime.combine(sessions[si], dt.time(16, 0)), tz=D.g.ET) < t:
            mv = mark(sessions[si]); eq_curve[sessions[si]] = cash + mv; exposure.append(mv / (cash + mv)); si += 1
        if kind == -1:  # exit
            p = open_pos.pop(k)
            cash += p["qty"] * p["exit_px"] * (1 - slip_bps / 1e4)
            continue
        r = tr.loc[k]
        if len(open_pos) >= max_pos:
            skipped += 1; continue
        eq = cash + sum(p["qty"] * p["entry"] for p in open_pos.values())
        px = r.entry * (1 + slip_bps / 1e4)
        qty = math.floor(eq * size_frac / px)
        if qty <= 0 or qty * px > cash:
            skipped += 1; continue
        cash -= qty * px; taken += 1
        open_pos[k] = dict(sym=r.symbol, qty=qty, entry=px, exit_px=r.exit_px)
        heapq.heappush(events, (r.exit_time, -1, k))
    while si < len(sessions):
        mv = mark(sessions[si]); eq_curve[sessions[si]] = cash + mv; exposure.append(mv / (cash + mv)); si += 1
    eq = pd.Series(eq_curve)
    ret = eq.pct_change().dropna()
    years = (sessions[-1] - sessions[0]).days / 365.25
    cagr = (eq.iloc[-1] / start_eq) ** (1 / years) - 1
    dd = (eq / eq.cummax() - 1).min()
    sharpe = ret.mean() / ret.std() * math.sqrt(252) if ret.std() > 0 else np.nan
    spy = spy_d["c"].reindex(sessions)
    spy_ret = spy.iloc[-1] / spy.iloc[0] - 1
    spy_cagr = (1 + spy_ret) ** (1 / years) - 1
    spy_dd = (spy / spy.cummax() - 1).min()
    print(f"PORTFOLIO {label:40s} max_pos={max_pos:2d} size={size_frac:.0%} slip={slip_bps}bp | taken={taken:4d} skipped={skipped:4d} | "
          f"final=${eq.iloc[-1]:,.0f} total={eq.iloc[-1]/start_eq-1:+.1%} CAGR={cagr:+.1%} maxDD={dd:.1%} Sharpe={sharpe:.2f} avg exposure={np.mean(exposure):.0%} | "
          f"SPY total={spy_ret:+.1%} CAGR={spy_cagr:+.1%} maxDD={spy_dd:.1%}", flush=True)
    yrs = pd.to_datetime(pd.Series(eq.index)).dt.year.values
    yr = eq.groupby(yrs).agg(["first", "last"])
    print("   by year:", {int(y): f"{r['last']/r['first']-1:+.1%}" for y, r in yr.iterrows()},
          " SPY:", {int(y): f"{g.iloc[-1]/g.iloc[0]-1:+.1%}" for y, g in spy.groupby(pd.to_datetime(pd.Series(spy.index)).dt.year.values)}, flush=True)
    return eq


S = Params(mode="orb", orb_bars=3, vol_mult=1.5, stop_mode="pct", stop_pct=5, targets=(), trail="none",
           hold="overnight", max_hold_days=3, earliest="09:45")
print("=== TRUE BENCHMARKS (no entry filters at all) ===")
B = replace(S, mode="open", vol_mult=0, ema_stack=False, above_vwap=False, spy_vwap=False)
trB = ev("BENCH: buy every leader at 09:45, hold 3d, 5% stop", B)
ev("BENCH: hold 5d", replace(B, max_hold_days=5))
ev("BENCH: hold 8d", replace(B, max_hold_days=8))
ev("BENCH: buy every leader at 09:45, 1d", replace(B, max_hold_days=1))
ev("BENCH: + SPY above VWAP only", replace(B, spy_vwap=True))
ev("BENCH: + vol>=1.5 at 09:45 only", replace(B, vol_mult=1.5))
ev("BENCH: + day gain>=1% at 09:45 only", replace(B, mode="orb", min_pole_pct_day=1.0, orb_bars=3))
print("\n=== CANDIDATES ===")
trS = ev("S: ORB15 vol1.5 3d 5%", S)
ev("S + vol2.0", replace(S, vol_mult=2.0))
tr10 = ev("S + within10% 52w", replace(S, max_off_high=10))
ev("S + vol2.0 + within10%", replace(S, vol_mult=2.0, max_off_high=10))
ev("S + top10", replace(S, top_n=10))
ev("S + top10 + within10%", replace(S, top_n=10, max_off_high=10))
ev("S + latest 12:00 + within10%", replace(S, latest="12:00", max_off_high=10))
ev("S hold 5d", replace(S, max_hold_days=5))
tr5 = ev("S hold 5d + within10%", replace(S, max_hold_days=5, max_off_high=10))
ev("S hold 8d + within10%", replace(S, max_hold_days=8, max_off_high=10))
ev("S hold 5d + within10% + vol2.0", replace(S, max_hold_days=5, max_off_high=10, vol_mult=2.0))
ev("S hold 5d + within10% + 8% stop", replace(S, max_hold_days=5, max_off_high=10, stop_pct=8))
ev("S hold 5d + within10% + ema21 trail 2R", replace(S, max_hold_days=5, max_off_high=10, trail="ema21", trail_trigger_r=2))
pd.DataFrame(rows).to_csv(f"{OUT}/round4.csv", index=False)

print("\n=== PORTFOLIO SIMULATIONS (5 bps slippage each side) ===")
portfolio(trB, 10, 0.10, 5, label="BENCH 3d 5%")
portfolio(trS, 10, 0.10, 5, label="S: ORB15 vol1.5 3d 5%")
portfolio(trS, 5, 0.20, 5, label="S: ORB15 vol1.5 3d 5%")
portfolio(tr10, 10, 0.10, 5, label="S + within10%")
portfolio(tr10, 5, 0.20, 5, label="S + within10%")
portfolio(tr5, 10, 0.10, 5, label="S 5d + within10%")
portfolio(tr5, 5, 0.20, 5, label="S 5d + within10%")
portfolio(tr5, 8, 0.125, 5, label="S 5d + within10%")
portfolio(tr5, 10, 0.10, 10, label="S 5d + within10% (10bp slip)")
tr10.to_csv(f"{OUT}/cand_S_within10_trades.csv", index=False)
tr5.to_csv(f"{OUT}/cand_S5d_within10_trades.csv", index=False)
