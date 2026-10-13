"""Up/down asymmetry of earnings-sized gaps (7%+ open gap on 2x+ volume), Jan 2025 - Oct 9 2026, all 516 names,
and the effect of a free -10%/+15% collar on the events a trend-hold position would have been in. Output: out/gap_asymmetry.log."""
import sys, os, datetime as dt, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data as D
ET = D.g.ET; daily = D.load("daily.pkl"); spyd = D.load("spy_daily.pkl")
S = spyd.copy(); S.index = S.index.tz_convert(ET).date; spy21 = S.c / S.c.shift(21) - 1
rows = []
for s, df in daily.items():
    full = df.copy(); full.index = full.index.tz_convert(ET).date
    d = full[full.index >= dt.date(2025, 1, 2)]
    if len(d) < 60: continue
    r21 = full.c / full.c.shift(21) - 1; hi52 = full.h.rolling(252, min_periods=120).max(); s50 = full.c.rolling(50).mean()
    e21 = full.c.ewm(span=21, adjust=False).mean(); pc = full.c.shift(1); gap = full.o / pc - 1; day = full.c / pc - 1
    vol_ratio = full.v / full.v.rolling(20).mean().shift(1)
    for dte in d.index:
        g = gap.get(dte)
        if g is None or np.isnan(g) or abs(g) < 0.07: continue
        prev = pc.index[pc.index.get_loc(dte) - 1]
        leader = (r21.get(prev, np.nan) > spy21.get(prev, np.nan)) and full.c.get(prev) > s50.get(prev) and (full.c.get(prev) / hi52.get(prev) - 1 >= -0.10)
        rows.append(dict(symbol=s, date=dte, gap=g, day=day.get(dte), leader=bool(leader), above_e21=bool(full.c.get(prev) > e21.get(prev)), vol=vol_ratio.get(dte)))
G = pd.DataFrame(rows); G = G[G.vol >= 2.0]
def summ(x, label):
    up = x[x.gap > 0]; dn = x[x.gap < 0]
    print(f"{label:55s} n={len(x):4d}  up {len(up)/len(x):.0%} avg {up.day.mean()*100:+.1f}%  |  down {len(dn)/len(x):.0%} avg {dn.day.mean()*100:+.1f}%  |  mean {x.day.mean()*100:+.2f}%  |  beyond -11%: {(x.day<-0.11).mean():.0%}, beyond +15%: {(x.day>0.15).mean():.0%}")
summ(G, "all names"); summ(G[G.leader], "Stage-1 leader the day before"); summ(G[~G.leader], "not a leader"); summ(G[G.leader & G.above_e21], "leader AND above EMA21 (trend-hold)")
L = G[G.leader & G.above_e21].copy(); L["collar"] = L.day.clip(lower=-0.10, upper=0.15)
print(f"\n{len(L)} trend-hold events: mean unhedged {L.day.mean()*100:+.2f}%, collared {L.collar.mean()*100:+.2f}%; std {L.day.std()*100:.1f}% -> {L.collar.std()*100:.1f}%; worst {L.day.min()*100:+.0f}% -> {L.collar.min()*100:+.0f}%")
print(f"cap bit on {(L.day>0.15).sum()} events (avg {(L.day[L.day>0.15]-0.15).mean()*100:.1f}pp), floor saved on {(L.day<-0.10).sum()} (avg {(-0.10-L.day[L.day<-0.10]).mean()*100:.1f}pp)")
G.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "gap_events.csv"), index=False)
