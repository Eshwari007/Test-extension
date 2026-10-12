#!/usr/bin/env python3
"""Backtest the Gajjala US scanner over a date range with the PDF's exit rules.

Exit rules: stop at flag low. Scale out 1/3 at T1 (+2.5%), 1/3 at T2 (+5.5%), 1/3 at T3 (+10%).
Once the trade reaches +1R the stop trails under EMA9 (never lowered). Anything left is sold
at the last 5-minute bar of the session (intraday setup, no overnight hold). A second variant
holds the remainder overnight and keeps trailing until stopped or T3 (for comparison).
Fills: entry at the signal bar close; stop/targets filled at the level (stop at the bar open if
the bar gaps through it). One open trade per symbol at a time. No commissions or slippage.
"""
import sys, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, ".")
import gajjala_scanner_us as g


def manage(f, i0, entry, stop0, qty, hold_overnight):
    """Walk bars after signal bar i0; return list of (time, qty, price, reason)."""
    fills, remaining, stop = [], qty, stop0
    r = entry - stop0
    parts = [qty // 3, qty // 3, qty - 2 * (qty // 3)]
    targets = [entry * (1 + p / 100) for p in g.TARGETS_PCT]
    hit = [False] * 3
    trailing = False
    day0 = f["date"].iloc[i0]
    if not hold_overnight and (i0 + 1 >= len(f) or f["date"].iloc[i0 + 1] != day0):
        return [(f.index[i0], qty, entry, "no-bars-left")]  # signal on last bar of session: no trade
    for i in range(i0 + 1, len(f)):
        row = f.iloc[i]
        if not hold_overnight and row["date"] != day0:
            break
        # stop first (conservative: if bar touches both stop and target, assume stop)
        if row.l <= stop:
            px = min(row.o, stop)
            fills.append((f.index[i], remaining, px, "trail" if trailing else "stop")); remaining = 0; break
        for k in range(3):
            if not hit[k] and row.h >= targets[k] and remaining > 0:
                q = min(parts[k], remaining)
                px = max(row.o, targets[k])
                fills.append((f.index[i], q, px, f"T{k+1}")); remaining -= q; hit[k] = True
        if remaining == 0:
            break
        if row.h >= entry + r:
            trailing = True
        if trailing:
            stop = max(stop, row.ema9)
        if not hold_overnight and i + 1 < len(f) and f["date"].iloc[i + 1] != day0:
            fills.append((f.index[i], remaining, row.c, "eod")); remaining = 0; break
    if remaining > 0:  # ran out of data
        fills.append((f.index[-1], remaining, f["c"].iloc[-1], "end"))
    return fills


def run(start_date, end_date, hold_overnight=False):
    sp = pd.read_csv("data/sp500.csv")
    universe = sorted((set(sp["Symbol"]) | set(g.NDX_EXTRA)) - g.BLACKLIST)
    daily = g.get_bars(universe + ["SPY"], "1Day", (start_date - dt.timedelta(days=330)).isoformat(),
                       end=dt.datetime.combine(end_date + dt.timedelta(days=1), dt.time(0), g.ET).astimezone(dt.timezone.utc).isoformat())
    spy = daily.pop("SPY")
    all_sessions = sorted(set(spy.index.tz_convert(g.ET).date))
    sessions = [d for d in all_sessions if start_date <= d <= end_date]
    leaders_by_day = {}
    for d in sessions:
        prev = all_sessions[all_sessions.index(d) - 1]
        leaders, _, _ = g.stage1(daily, spy, prev)
        leaders_by_day[d] = list(leaders.symbol)
    syms = sorted({s for v in leaders_by_day.values() for s in v})
    s5 = dt.datetime.combine(start_date - dt.timedelta(days=6), dt.time(0), g.ET).astimezone(dt.timezone.utc).isoformat()
    e5 = dt.datetime.combine(end_date + dt.timedelta(days=10), dt.time(0), g.ET).astimezone(dt.timezone.utc).isoformat()
    intra = g.get_bars(syms + ["SPY"], "5Min", s5, e5)
    spy5 = g.intraday_features(intra.pop("SPY"))
    spy_flag = spy5["c"] > spy5["vwap"]
    feats = {s: g.intraday_features(df) for s, df in intra.items()}

    trades = []
    open_until = {}  # symbol -> timestamp when trade closed
    for d in sessions:
        for s in leaders_by_day[d]:
            if s not in feats:
                continue
            f = feats[s]
            for i in np.where(f["date"].values == d)[0]:
                ts = f.index[i]
                if s in open_until and ts <= open_until[s]:
                    continue
                res = g.check_bar(f, i, bool(spy_flag.get(ts, False)))
                if not res or not res["signal"] or res["qty"] <= 0:
                    continue
                fills = manage(f, i, res["entry"], res["stop"], res["qty"], hold_overnight)
                pnl = sum(q * (px - res["entry"]) for _, q, px, _ in fills)
                r_unit = (res["entry"] - res["stop"]) * res["qty"]
                open_until[s] = fills[-1][0]
                trades.append(dict(session=d, time=ts.strftime("%m-%d %H:%M"), symbol=s, entry=round(res["entry"], 2),
                                   stop=round(res["stop"], 2), qty=res["qty"], risk_usd=round(r_unit, 0),
                                   exit_time=fills[-1][0].strftime("%m-%d %H:%M"),
                                   exits="|".join(f"{q}@{px:.2f}:{why}" for _, q, px, why in fills),
                                   pnl=round(pnl, 2), R=round(pnl / r_unit, 2)))
    return pd.DataFrame(trades), leaders_by_day


if __name__ == "__main__":
    a, b = dt.date.fromisoformat(sys.argv[1]), dt.date.fromisoformat(sys.argv[2])
    for hold in (False, True):
        tr, lb = run(a, b, hold_overnight=hold)
        label = "HOLD OVERNIGHT (trail until stopped)" if hold else "INTRADAY (flat at close)"
        print(f"\n================ {label}: {a} to {b} ================")
        if tr.empty:
            print("No trades."); continue
        print(tr.to_string(index=False))
        wins = (tr.pnl > 0).sum()
        print(f"\nTrades: {len(tr)}  Wins: {wins}  Losses: {len(tr)-wins}  Win rate: {wins/len(tr):.0%}")
        print(f"Total P&L: ${tr.pnl.sum():,.2f}  ({tr.pnl.sum()/g.ACCOUNT_SIZE:+.2%} of ${g.ACCOUNT_SIZE:,})   Total R: {tr.R.sum():+.2f}")
        print(f"Avg win: ${tr[tr.pnl>0].pnl.mean():,.2f}   Avg loss: ${tr[tr.pnl<=0].pnl.mean():,.2f}   Best: ${tr.pnl.max():,.2f}   Worst: ${tr.pnl.min():,.2f}")
        tr.to_csv(f"out/backtest_{a}_{b}_{'overnight' if hold else 'intraday'}.csv", index=False)
    print("\nStage 1 leaders by session:")
    for d, v in lb.items():
        print(d, ", ".join(v))
