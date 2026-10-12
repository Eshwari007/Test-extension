import sys, os, math, datetime as dt
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Dataset
from run import ALL
import data as D
ds = None; spy_d = None; daily_close = None
def init(dataset):
    global ds, spy_d, daily_close
    ds = dataset
    spy_d = D.load("spy_daily.pkl"); spy_d.index = spy_d.index.tz_convert(D.g.ET).date
    daily_close = {s: df.groupby("date")["c"].last() for s, df in ds.sym.items()}
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


