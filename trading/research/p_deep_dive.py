"""Deep dive on P (Everpure): where the return came from, and which capture methods harvest it."""
import sys, os, datetime as dt, math
import numpy as np, pandas as pd
sys.path.insert(0, '.')
import data as D
ET = D.g.ET
daily = D.load("daily.pkl"); spyd = D.load("spy_daily.pkl"); leaders = D.load("leaders.pkl")
def dz(df):
    d = df.copy(); d.index = d.index.tz_convert(ET).date; return d
P = dz(daily["P"]); S = dz(spyd)
start = dt.date(2025, 10, 9); end = dt.date(2026, 10, 9)
yr = P[(P.index >= start) & (P.index <= end)].copy()
c = yr.c
yr["ema21"] = P.c.ewm(span=21, adjust=False).mean().reindex(yr.index); yr["ema50"] = P.c.ewm(span=50, adjust=False).mean().reindex(yr.index)
yr["sma50"] = P.c.rolling(50).mean().reindex(yr.index); yr["sma200"] = P.c.rolling(200).mean().reindex(yr.index)
yr["hi52"] = P.h.rolling(252).max().reindex(yr.index); yr["ret21"] = (P.c / P.c.shift(21) - 1).reindex(yr.index)
spy21 = (S.c / S.c.shift(21) - 1).reindex(yr.index)

print("=== 1. Where did the +65% come from? ===")
o2c = (yr.c / yr.o - 1); c2o = (yr.o / yr.c.shift(1) - 1)
print(f"log-return split: overnight gaps {np.log1p(c2o.dropna()).sum()*100:+.1f}%  vs intraday open->close {np.log1p(o2c).sum()*100:+.1f}%  (total log {np.log(c.iloc[-1]/c.iloc[0])*100:+.1f}%)")
r = np.log(c).diff().dropna()
top = r.abs().nlargest(10).index
print(f"10 biggest |days| contribute {r[top].sum()*100:+.1f}% of {r.sum()*100:+.1f}% log return; the other {len(r)-10} days: {r.drop(top).sum()*100:+.1f}%")
up = r[r > 0]; print(f"up days {len(up)} ({len(up)/len(r):.0%}), down days {len(r)-len(up)}; avg up {up.mean()*100:+.2f}% avg down {r[r<0].mean()*100:+.2f}%")
print("\nphases (close-to-close):")
phases = [("Oct 9 25 -> Dec 2 25 (pre-earnings)", start, dt.date(2025,12,2)), ("Dec 3 25 crash day", dt.date(2025,12,2), dt.date(2025,12,3)),
          ("Dec 3 25 -> Mar 30 26 (base/low)", dt.date(2025,12,3), dt.date(2026,3,30)), ("Mar 30 -> May 27 (leg 1)", dt.date(2026,3,30), dt.date(2026,5,27)),
          ("May 28 crash day", dt.date(2026,5,27), dt.date(2026,5,28)), ("May 28 -> Aug 10 (consolidation)", dt.date(2026,5,28), dt.date(2026,8,10)),
          ("Aug 11 -> Oct 9 (leg 2)", dt.date(2026,8,10), dt.date(2026,10,9))]
for name, a, b in phases:
    ca = P.c[P.index <= a].iloc[-1]; cb = P.c[P.index <= b].iloc[-1]
    print(f"  {name:38s} {ca:7.2f} -> {cb:7.2f}  {cb/ca-1:+6.1%}")

print("\n=== 2. Trend structure (days in state, over the year) ===")
print(f"close > EMA21: {(yr.c>yr.ema21).mean():.0%} of days; > EMA50: {(yr.c>yr.ema50).mean():.0%}; > SMA200: {(yr.c>yr.sma200).mean():.0%}")
print(f"within 10% of 52w high: {(yr.c/yr.hi52-1>=-0.10).mean():.0%} of days; 21d return beats SPY: {(yr.ret21>spy21).mean():.0%}")
# pullback depth during leg 2
leg2 = yr[yr.index >= dt.date(2026,8,10)]
dd = (leg2.c / leg2.c.cummax() - 1)
print(f"leg 2 (Aug 10 -> Oct 9): {leg2.c.iloc[-1]/leg2.c.iloc[0]-1:+.0%}, max pullback {dd.min():.1%}, days closing below EMA21: {(leg2.c<leg2.ema21).sum()} of {len(leg2)}")
leg1 = yr[(yr.index >= dt.date(2026,3,30)) & (yr.index <= dt.date(2026,5,27))]
print(f"leg 1 (Mar 30 -> May 27): {leg1.c.iloc[-1]/leg1.c.iloc[0]-1:+.0%}, max pullback {(leg1.c/leg1.c.cummax()-1).min():.1%}, days below EMA21: {(leg1.c<leg1.ema21).sum()} of {len(leg1)}")

print("\n=== 3. When did the Stage 1 scanner see it? ===")
ranks = {d: int(L.set_index('symbol').loc['P','rank']) for d, L in leaders.items() if 'P' in set(L.symbol)}
rk = pd.Series(ranks).sort_index(); rk = rk[rk.index >= start]
print(f"on the top-30 list {len(rk)} sessions; in top 15: {(rk<=15).sum()}; rank 1: {(rk==1).sum()} sessions")
runs = []; cur = None
for d, v in rk.items():
    if v <= 15:
        if cur and (d - cur[1]).days <= 5: cur[1] = d
        else:
            if cur: runs.append(cur)
            cur = [d, d]
if cur: runs.append(cur)
for a, b in runs:
    print(f"  top-15 from {a} to {b}: close {P.c.loc[a]:.2f} -> {P.c.loc[b]:.2f} ({P.c.loc[b]/P.c.loc[a]-1:+.0%})")

print("\n=== 4. Capture methods on P alone, Oct 9 2025 -> Oct 9 2026 (daily bars, $100k notional per method) ===")
def sim(entries_fn, exit_fn, label, start_i=None):
    """Generic daily sim: entries_fn(i)->bool when flat; exit_fn(i, entry_i, entry_px)->bool when long. Fill at next open."""
    idx = list(yr.index); pos = None; trades = []; eq = 1.0
    for k in range(1, len(idx) - 1):
        d = idx[k]
        if pos is None:
            if entries_fn(k):
                pos = (k + 1, yr.o.iloc[k + 1])
        else:
            if exit_fn(k, pos[0], pos[1]):
                px = yr.o.iloc[k + 1]; trades.append((idx[pos[0]], idx[k + 1], px / pos[1] - 1)); eq *= px / pos[1]; pos = None
    if pos is not None:
        px = yr.c.iloc[-1]; trades.append((idx[pos[0]], idx[-1], px / pos[1] - 1)); eq *= px / pos[1]
    t = pd.DataFrame(trades, columns=["in", "out", "ret"])
    held = sum((pd.Timestamp(b) - pd.Timestamp(a)).days for a, b, _ in trades)
    print(f"  {label:58s} trades={len(t):3d} win={((t.ret>0).mean() if len(t) else 0):.0%} total={eq-1:+7.1%}  exposure~{held/365:.0%}  worst={t.ret.min() if len(t) else 0:+.1%}")
    return t
bh = yr.c.iloc[-1] / yr.c.iloc[0] - 1
print(f"  {'buy and hold (Oct 9 2025 -> Oct 9 2026)':58s} total={bh:+7.1%}  max DD -42%")
print(f"  {'buy and hold from Mar 30 2026 low':58s} total={yr.c.iloc[-1]/P.c.loc[dt.date(2026,3,30)]-1:+7.1%}")
cl, hi, lo, e21, e50, s200 = yr.c.values, yr.h.values, yr.l.values, yr.ema21.values, yr.ema50.values, yr.sma200.values
hi20 = pd.Series(hi).rolling(20).max().shift(1).values; lo10 = pd.Series(lo).rolling(10).min().shift(1).values
hi52 = yr.hi52.values; r21 = yr.ret21.values; s21 = spy21.values
vol20 = yr.v.rolling(20).mean().shift(1).values
# A. Gajjala Stage-1 membership + 3-day hold, 5% stop (daily proxy)
def ent_gaj(k): return r21[k] > s21[k] and cl[k] > yr.sma50.values[k] and cl[k]/hi52[k]-1 >= -0.10
sim(ent_gaj, lambda k, ei, ep: (k - ei) >= 2 or lo[k] <= ep*0.95, "A. Stage-1 qualifies -> hold 3 days, 5% stop, re-enter")
# B. 20-day breakout entry, exit on close < EMA21
sim(lambda k: cl[k] > hi20[k] and cl[k] > e50[k], lambda k, ei, ep: cl[k] < e21[k], "B. 20-day high breakout, exit close < EMA21")
sim(lambda k: cl[k] > hi20[k] and cl[k] > e50[k], lambda k, ei, ep: cl[k] < lo10[k], "C. 20-day high breakout, exit close < 10-day low")
sim(lambda k: cl[k] > hi20[k] and cl[k] > e50[k], lambda k, ei, ep: cl[k] < e50[k], "D. 20-day high breakout, exit close < EMA50")
# E. EMA21 reclaim entry
sim(lambda k: cl[k] > e21[k] and cl[k-1] <= e21[k-1] and cl[k] > e50[k], lambda k, ei, ep: cl[k] < e21[k], "E. EMA21 reclaim (above EMA50), exit close < EMA21")
sim(lambda k: cl[k] > e21[k] and cl[k-1] <= e21[k-1] and cl[k] > e50[k], lambda k, ei, ep: cl[k] < lo10[k], "F. EMA21 reclaim, exit close < 10-day low")
# G. Stage-1 + trend trail
sim(ent_gaj, lambda k, ei, ep: cl[k] < e21[k], "G. Stage-1 qualifies, exit close < EMA21 (swing -> trend)")
sim(ent_gaj, lambda k, ei, ep: cl[k] < lo10[k] or lo[k] <= ep*0.92, "H. Stage-1 qualifies, exit < 10-day low or -8% stop")
# I. gap-up continuation: gap >= 5% on 2x volume, hold until close < EMA21
gap = yr.o.values / np.r_[np.nan, cl[:-1]] - 1
sim(lambda k: gap[k] >= 0.05 and yr.v.values[k] >= 2*vol20[k] and cl[k] > yr.o.values[k], lambda k, ei, ep: cl[k] < e21[k], "I. 5% gap-up on 2x vol, close>open, exit close < EMA21")
# J. 52-week-high breakout
sim(lambda k: cl[k] >= hi52[k] and cl[k-1] < hi52[k-1], lambda k, ei, ep: cl[k] < e21[k], "J. New 52-week high close, exit close < EMA21")
# K. RDT-style: Stage1 + 1.5xATR stop capped 8%, T1 1.5% -> breakeven, out day 4
atr = pd.concat([yr.h-yr.l, (yr.h-yr.c.shift(1)).abs(), (yr.l-yr.c.shift(1)).abs()], axis=1).max(axis=1).rolling(14).mean().shift(1).values
state = {}
def ex_rdt(k, ei, ep):
    st = state.setdefault(ei, {"stop": max(ep - 1.5*atr[ei], ep*0.92), "t1": False})
    if hi[k] >= ep*1.015: st["t1"] = True; st["stop"] = max(st["stop"], ep)
    return lo[k] <= st["stop"] or (k - ei >= 3)
sim(ent_gaj, ex_rdt, "K. Stage-1, RDT-style ATR stop + breakeven at T1, out day 4")

print("\n=== 5. The two earnings crashes: were you in? ===")
for d in (dt.date(2025,12,3), dt.date(2026,5,28), dt.date(2026,8,27)):
    i = list(yr.index).index(d); prev = yr.c.iloc[i-1]
    print(f"  {d}: prev close {prev:.2f}, open {yr.o.iloc[i]:.2f} ({yr.o.iloc[i]/prev-1:+.1%} gap), close {yr.c.iloc[i]:.2f} ({yr.c.iloc[i]/prev-1:+.1%}); above EMA21 the day before: {yr.c.iloc[i-1] > yr.ema21.iloc[i-1]}; Stage-1 qualified day before: {ent_gaj(i-1)}")
yr.to_csv("out/P_daily_1y.csv")
