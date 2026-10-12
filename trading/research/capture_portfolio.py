"""Portfolio view of the universe-wide capture methods: 10 slots x 10% of equity, 5 bps slippage, daily marks."""
import sys, datetime as dt, math; sys.path.insert(0,'.')
import numpy as np, pandas as pd
src=open('capture_universe.py').read().split('print("=== Universe-wide')[0]
exec(src)
import io, contextlib
def get(label, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()): return run(label,*a,**k)
brk=lambda k,cl,hi,lo,c: cl[k]>c["hi20"][k] and cl[k]>c["e50"][k]
sets={
 "B3 breakout+vol, Stage-1, exit <EMA21": get("B3", lambda k,cl,hi,lo,c: brk(k,cl,hi,lo,c) and c["rvol"][k]>=1.5, lambda k,ei,ep,cl,hi,lo,c: cl[k]<c["e21"][k], stage1=True),
 "B6 breakout, Stage-1, exit <EMA50": get("B6", brk, lambda k,ei,ep,cl,hi,lo,c: cl[k]<c["e50"][k], stage1=True),
 "B5 breakout, Stage-1, exit <10d low": get("B5", brk, lambda k,ei,ep,cl,hi,lo,c: cl[k]<c["lo10"][k], stage1=True),
 "A  Stage-1 any day, 3d hold, 5% stop": get("A", lambda k,cl,hi,lo,c: True, lambda k,ei,ep,cl,hi,lo,c: lo[k]<=ep*0.95, stage1=True, max_hold=3),
}
closes={s:F[s].c for s in F}
sessions=[d for d in S.index if start<=d<=end]
spy=S.c.reindex(sessions)
def portfolio(t, max_pos=10, size=0.10, slip=5e-4, start_eq=1e5):
    t=t.sort_values(["entry","symbol"]).reset_index(drop=True)
    by_day=t.groupby("entry")
    cash=start_eq; open_pos={}; eq=[]; taken=0; skipped=0
    for d in sessions:
        # exits at today's open (trade exit date == d)
        for k in [k for k,p in open_pos.items() if p["exit"]==d]:
            p=open_pos.pop(k); cash+=p["qty"]*p["out_px"]*(1-slip)
        if d in by_day.groups:
            for k,r in by_day.get_group(d).iterrows():
                if len(open_pos)>=max_pos: skipped+=1; continue
                mv=sum(p["qty"]*closes[p["sym"]].get(d,p["in_px"]) for p in open_pos.values())
                px=r.in_px*(1+slip); qty=math.floor((cash+mv)*size/px)
                if qty<=0 or qty*px>cash: skipped+=1; continue
                cash-=qty*px; taken+=1
                open_pos[k]=dict(sym=r.symbol,qty=qty,in_px=px,exit=r.exit,out_px=r.out_px)
        mv=sum(p["qty"]*closes[p["sym"]].get(d,np.nan) if not np.isnan(closes[p["sym"]].get(d,np.nan)) else p["qty"]*p["in_px"] for p in open_pos.values())
        eq.append(cash+mv)
    eq=pd.Series(eq,index=sessions); ret=eq.pct_change().dropna(); yrs=(sessions[-1]-sessions[0]).days/365.25
    return dict(taken=taken,skipped=skipped,final=eq.iloc[-1],total=eq.iloc[-1]/start_eq-1,cagr=(eq.iloc[-1]/start_eq)**(1/yrs)-1,
                maxdd=(eq/eq.cummax()-1).min(),sharpe=ret.mean()/ret.std()*math.sqrt(252), y2025=eq[eq.index<=dt.date(2025,12,31)].iloc[-1]/start_eq-1,
                y2026=eq.iloc[-1]/eq[eq.index<=dt.date(2025,12,31)].iloc[-1]-1), eq
print(f"SPY: total {spy.iloc[-1]/spy.iloc[0]-1:+.1%}, maxDD {(spy/spy.cummax()-1).min():.1%}")
curves={}
for name,t in sets.items():
    # need entry/exit prices: recompute from closes/opens
    t=t.copy()
    t["in_px"]=[F[s].o.get(d,np.nan) for s,d in zip(t.symbol,t.entry)]
    t["out_px"]=t.in_px*(1+t.ret)
    for mp,sz in ((10,0.10),(5,0.20)):
        m,eq=portfolio(t,mp,sz); curves[(name,mp)]=eq
        print(f"{name:40s} {mp:2d}x{sz:.0%}: taken={m['taken']:4d} skipped={m['skipped']:4d} final=${m['final']:,.0f} total={m['total']:+.1%} CAGR={m['cagr']:+.1%} maxDD={m['maxdd']:.1%} Sharpe={m['sharpe']:.2f} 2025={m['y2025']:+.1%} 2026={m['y2026']:+.1%}",flush=True)
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(11,5.5)); x=pd.to_datetime(pd.Series(sessions))
for (name,mp),eq in curves.items():
    if mp==10: ax.plot(x,eq.values,lw=1.4,label=f"{name} (10x10%)")
ax.plot(x,(spy/spy.iloc[0]*1e5).values,color='gray',ls='--',label='SPY'); ax.legend(fontsize=8); ax.grid(alpha=.3); ax.set_title('Capture methods on the S&P 500 universe, $100k, Jan 2025 - Oct 9 2026'); fig.tight_layout(); fig.savefig('out/capture_curves.png',dpi=130)
