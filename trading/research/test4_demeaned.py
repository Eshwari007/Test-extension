"""Test 4: day-demeaned forward excess return of trend-book entry signals at 5/10/20 sessions, both caches."""
import os, sys, datetime as dt, numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
win=sys.argv[1]
if win=="2324":
    os.environ["MOM_CACHE"]=os.path.join(HERE,"cache_2324"); os.environ["MOM_DAILY_START"]="2022-01-01"; os.environ["MOM_BT_START"]="2023-01-03"; os.environ["MOM_BT_END"]="2024-12-31"
import data as D
ET=D.g.ET; START,END=D.BT_START,D.BT_END
daily=D.load("daily.pkl"); spy=D.load("spy_daily.pkl"); spy.index=spy.index.tz_convert(ET).date
spy21=spy.c/spy.c.shift(21)-1; spy_fwd={h:(spy.c.shift(-h)/spy.c-1) for h in (1,5,10,20)}
rows=[]; base=[]
for s,df in daily.items():
    d=df.copy(); d.index=d.index.tz_convert(ET).date
    d["e21"]=d.c.ewm(span=21,adjust=False).mean(); d["e50"]=d.c.ewm(span=50,adjust=False).mean(); d["s50"]=d.c.rolling(50).mean()
    d["hi20"]=d.h.rolling(20).max().shift(1); d["hi52"]=d.h.rolling(252,min_periods=120).max().shift(1); d["r21"]=d.c/d.c.shift(21)-1
    d["dvol"]=(d.c*d.v).rolling(20).mean(); d["rvol"]=d.v/d.v.rolling(20).mean().shift(1); d["spy21"]=spy21.reindex(d.index).values
    fwd={h:(d.o.shift(-1-h)/d.o.shift(-1)-1) for h in (1,5,10,20)}   # next-open entry to open h sessions later
    sfwd={h:(spy.o.shift(-1-h)/spy.o.shift(-1)-1).reindex(d.index) for h in (1,5,10,20)}
    w=(d.index>=START)&(d.index<=END)
    st1=(d.r21>d.spy21)&(d.c>d.s50)&(d.c>10)&(d.dvol>25e6)&(d.c/d.hi52-1>=-0.10)
    sig=st1&(d.c>d.hi20)&(d.c>d.e50)&(d.rvol>=1.5)&w
    for dte in d.index[sig.values]:
        rows.append(dict(symbol=s,date=dte,**{f"ex{h}":fwd[h].get(dte)-sfwd[h].get(dte) for h in (1,5,10,20)},**{f"raw{h}":fwd[h].get(dte) for h in (1,5,10,20)}))
    # baseline: all Stage-1 days without the breakout (same stocks, no entry rule)
    for dte in d.index[(st1&~sig&w).values][::5]:
        base.append(dict(symbol=s,date=dte,**{f"ex{h}":fwd[h].get(dte)-sfwd[h].get(dte) for h in (1,5,10,20)}))
R=pd.DataFrame(rows).dropna(); B=pd.DataFrame(base).dropna()
print(f"=== TEST 4, {START} -> {END}: {len(R)} trend entry signals; baseline = Stage-1 days without a breakout ({len(B)} sampled) ===")
print("horizon | mean excess vs SPY (entry-to-exit, next-open fills) | t-stat | hit rate | raw mean | baseline (Stage-1, no breakout) excess")
for h in (1,5,10,20):
    x=R[f"ex{h}"]; b=B[f"ex{h}"]; t=x.mean()/(x.std()/np.sqrt(len(x)))
    print(f"  {h:2d}d    {x.mean()*100:+.2f}%   t={t:5.2f}   hit {(x>0).mean():.0%}   raw {R[f'raw{h}'].mean()*100:+.2f}%   baseline {b.mean()*100:+.2f}% (t={b.mean()/(b.std()/np.sqrt(len(b))):.2f})")
# by year and by month-cluster robustness
R["year"]=pd.to_datetime(R.date).dt.year
print("\nby year, 20d excess:"); print(R.groupby("year").ex20.agg(["size","mean"]).assign(mean=lambda x:(x["mean"]*100).round(2)).to_string())
R["month"]=pd.to_datetime(R.date).dt.to_period("M")
m=R.groupby("month").ex20.mean(); print(f"\nmonths with positive 20d excess: {(m>0).sum()} of {len(m)}; median month {m.median()*100:+.2f}%")
R.to_csv(f"out/test4_{win}.csv",index=False)
