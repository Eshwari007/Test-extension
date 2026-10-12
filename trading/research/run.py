#!/usr/bin/env python3
"""Research driver: baseline, one-at-a-time sensitivity, grid search in-sample, validate out-of-sample."""
import sys, os, itertools, datetime as dt, time, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Dataset, Params, run, stats, monthly
from dataclasses import replace, asdict

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
IS = (dt.date(2025, 1, 2), dt.date(2025, 12, 31))
OOS = (dt.date(2026, 1, 2), dt.date(2026, 10, 9))
ALL = (IS[0], OOS[1])


_DS = None


def _grid_one(args):
    base, kw, period = args
    s = stats(run(_DS, replace(base, **kw), *period)); s.update(kw); return s


def show(label, tr):
    s = stats(tr)
    print(f"{label:60s} n={s['n']:4d} win={s['win']!s:6} totR={s['totR']:7} avgR={s['avgR']!s:7} pf={s['pf']!s:6} maxDD={s['maxdd_R']:6} pnl=${s['pnl']:,.0f}")
    return s


def main():
    t0 = time.time()
    ds = Dataset()
    print(f"loaded {len(ds.sym)} symbols, {len(ds.sessions)} sessions in {time.time()-t0:.0f}s\n")

    # ---------- 1. baseline as specified ----------
    base = Params()
    print("=== BASELINE (PDF rules) ===")
    tr = run(ds, base, *ALL); show("spec, intraday, full period", tr)
    tr.to_csv(f"{OUT}/baseline_trades.csv", index=False)
    print(monthly(tr).to_string())
    show("spec, overnight", run(ds, replace(base, hold="overnight"), *ALL))

    # ---------- 2. one-at-a-time sensitivity (full period) ----------
    print("\n=== ONE-AT-A-TIME SENSITIVITY (full period, intraday) ===")
    variants = {
        "pole_min=1.0": dict(pole_min=1.0), "pole_min=0.75": dict(pole_min=0.75), "pole_min=0.5": dict(pole_min=0.5),
        "pole_min=0.0 (off)": dict(pole_min=-100),
        "flag_max_range=1.5": dict(flag_max_range=1.5), "flag_max_range=2.0": dict(flag_max_range=2.0),
        "vol_mult=1.2": dict(vol_mult=1.2), "vol_mult=1.0": dict(vol_mult=1.0), "vol off": dict(vol_mult=0),
        "vol_mult=2.0": dict(vol_mult=2.0),
        "no ema stack": dict(ema_stack=False), "no flag_above_vwap": dict(flag_above_vwap=False),
        "no spy filter": dict(spy_vwap=False),
        "top_n=30": dict(top_n=30), "top_n=10": dict(top_n=10),
        "flag_bars=4": dict(flag_bars=4), "flag_bars=8": dict(flag_bars=8), "pole_bars=4": dict(pole_bars=4),
        "pole_bars=10": dict(pole_bars=10),
        "earliest=10:00": dict(earliest="10:00"), "latest=14:00": dict(latest="14:00"), "latest=12:00": dict(latest="12:00"),
        "min_risk_pct=0.5": dict(min_risk_pct=0.5), "min_risk_pct=0.8": dict(min_risk_pct=0.8),
        "stop=pole_low": dict(stop_mode="pole_low"), "stop=atr1.5": dict(stop_mode="atr", atr_mult=1.5),
        "trail=ema21": dict(trail="ema21"), "trail=none": dict(trail="none"), "trail=be": dict(trail="be"),
        "trail trigger 2R": dict(trail_trigger_r=2.0),
        "no targets, ema9 trail": dict(targets=()), "targets 2R only": dict(targets=(0,), scale=(1.0,)),
        "hold overnight": dict(hold="overnight"), "overnight 3d": dict(hold="overnight", max_hold_days=3),
        "require_200sma": dict(require_200sma=True), "max_off_high=10": dict(max_off_high=10),
    }
    loose = replace(base, pole_min=0.75)  # need enough trades for sensitivity to mean anything
    print("(each on top of pole_min=0.75 so there are enough trades)")
    show("pole_min=0.75 reference", run(ds, loose, *ALL))
    rows = []
    for name, kw in variants.items():
        p = replace(loose, **kw) if "pole_min" not in kw else replace(base, **kw)
        if name == "targets 2R only":
            continue
        s = show(name, run(ds, p, *ALL)); s["variant"] = name; rows.append(s)
    pd.DataFrame(rows).to_csv(f"{OUT}/sensitivity.csv", index=False)

    # ---------- 3. grid search in-sample ----------
    print("\n=== GRID SEARCH, in-sample 2025 ===")
    grid = dict(
        pole_min=[0.5, 0.75, 1.0],
        flag_max_range=[1.2, 2.0],
        vol_mult=[0, 1.2, 1.5],
        flag_above_vwap=[True, False],
        spy_vwap=[True, False],
        top_n=[15, 30],
        latest=["14:00", "15:55"],
        min_risk_pct=[0, 0.6],
        trail=["ema9", "ema21"],
        hold=["intraday", "overnight"],
    )
    keys = list(grid)
    combos = list(itertools.product(*grid.values()))
    print(f"{len(combos)} combinations", flush=True)
    global _DS
    _DS = ds
    from multiprocessing import Pool
    t0 = time.time()
    with Pool(4) as pool:
        res = pool.map(_grid_one, [(base, dict(zip(keys, c)), IS) for c in combos], chunksize=8)
    print(f"  grid done in {time.time()-t0:.0f}s", flush=True)
    G = pd.DataFrame(res)
    G.to_csv(f"{OUT}/grid_is.csv", index=False)
    G = G[G.n >= 40].copy()
    G["score"] = G.avgR * np.sqrt(G.n)  # t-stat-like
    print("\nTop 25 in-sample by avgR*sqrt(n), n>=40:")
    print(G.sort_values("score", ascending=False).head(25).to_string(index=False))

    # ---------- 4. validate the top configs out-of-sample ----------
    print("\n=== OUT-OF-SAMPLE 2026 for top 25 in-sample configs ===")
    rows = []
    for _, r in G.sort_values("score", ascending=False).head(25).iterrows():
        kw = {k: r[k] for k in keys}
        kw["top_n"] = int(kw["top_n"]); kw["flag_above_vwap"] = bool(kw["flag_above_vwap"]); kw["spy_vwap"] = bool(kw["spy_vwap"])
        p = replace(base, **kw)
        so = stats(run(ds, p, *OOS))
        rows.append({**kw, "IS_n": r.n, "IS_avgR": r.avgR, "IS_pf": r.pf, "OOS_n": so["n"], "OOS_win": so["win"],
                     "OOS_avgR": so["avgR"], "OOS_totR": so["totR"], "OOS_pf": so["pf"], "OOS_dd": so["maxdd_R"]})
    V = pd.DataFrame(rows)
    V.to_csv(f"{OUT}/validation.csv", index=False)
    print(V.to_string(index=False))

    # ---------- 5. parameter marginals: which settings are robust across the grid? ----------
    print("\n=== MARGINALS (mean avgR across all in-sample grid combos with n>=40) ===")
    for k in keys:
        print(G.groupby(k).agg(combos=("n", "size"), mean_avgR=("avgR", "mean"), mean_pf=("pf", lambda x: np.mean(np.clip(x, 0, 5))), mean_n=("n", "mean")).round(3).to_string())
        print()


if __name__ == "__main__":
    main()
