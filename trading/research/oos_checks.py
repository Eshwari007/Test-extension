"""Two pre-registered checks on both windows: (1) trend slot filling by Stage-1 rank instead of first-come;
(2) swing book with the SPY>EMA50 regime switch that is already in the project plan. Not a re-tuning."""
import os, sys, io, math, contextlib, datetime as dt, numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
win=sys.argv[1]
if win=="2324":
    os.environ["MOM_CACHE"]=os.path.join(HERE,"cache_2324"); os.environ["MOM_DAILY_START"]="2022-01-01"; os.environ["MOM_BT_START"]="2023-01-03"; os.environ["MOM_BT_END"]="2024-12-31"
import data as D
from engine import Dataset, Params, run, stats
import portfolio as P
START,END=D.BT_START,D.BT_END; P.ALL=(START,END); ET=D.g.ET
ds=Dataset(); P.init(ds); spy_d=D.load("spy_daily.pkl"); spy_d.index=spy_d.index.tz_convert(ET).date
sessions=sorted(d for d in ds.sessions if START<=d<=END); spy=spy_d.c.reindex(sessions)
spy_e50=spy_d.c.ewm(span=50,adjust=False).mean(); regime_ok={d:bool(spy_d.c.get(d,np.nan)>spy_e50.get(d,np.nan)) for d in spy_d.index}
def pstats(eq,label,base=1e5):
    ret=eq.pct_change().dropna(); yrs=(eq.index[-1]-eq.index[0]).days/365.25
    print(f"  {label:58s} total {eq.iloc[-1]/base-1:+6.1%}  CAGR {(eq.iloc[-1]/base)**(1/yrs)-1:+6.1%}  maxDD {(eq/eq.cummax()-1).min():6.1%}  Sharpe {ret.mean()/ret.std()*math.sqrt(252):.2f}")
print(f"=== window {START} -> {END}; SPY {spy.iloc[-1]/spy.iloc[0]-1:+.1%} ===")
# ---- swing: base vs regime switch (no entries when SPY < EMA50 at prior close)
C=Params(mode="orb",orb_bars=3,vol_mult=1.5,stop_mode="pct",stop_pct=5,targets=(),trail="none",hold="overnight",max_hold_days=3,earliest="09:45",max_off_high=10)
sw=run(ds,C,START,END)
prev={d:sessions[i-1] if i>0 else None for i,d in enumerate(sessions)}
sw_reg=sw[[regime_ok.get(prev[d],True) if prev.get(d) else True for d in sw.session]]
def swing_port(t,mp,sz,eq0=1e5):
    with contextlib.redirect_stdout(io.StringIO()): eq=P.portfolio(t,mp,sz,5,start_eq=eq0,label="")
    return eq.reindex(sessions).ffill()
s=stats(sw); r=stats(sw_reg)
print(f"SWING per-trade: base n={s['n']} PF={s['pf']} avgR={s['avgR']} | with SPY>EMA50 switch n={r['n']} PF={r['pf']} avgR={r['avgR']}")
pstats(swing_port(sw,10,0.10),"swing 10x10% base"); pstats(swing_port(sw_reg,10,0.10),"swing 10x10% with regime switch")
# ---- trend: first-come vs ranked slot filling
daily=D.load("daily.pkl"); spy21=spy_d.c/spy_d.c.shift(21)-1
def feats(df):
    d=df.copy(); d.index=d.index.tz_convert(ET).date
    d["e21"]=d.c.ewm(span=21,adjust=False).mean(); d["e50"]=d.c.ewm(span=50,adjust=False).mean(); d["s50"]=d.c.rolling(50).mean()
    d["hi20"]=d.h.rolling(20).max().shift(1); d["hi52"]=d.h.rolling(252,min_periods=120).max().shift(1)
    d["r21"]=d.c/d.c.shift(21)-1; d["dvol"]=(d.c*d.v).rolling(20).mean(); d["rvol"]=d.v/d.v.rolling(20).mean().shift(1); d["spy21"]=spy21.reindex(d.index).values
    return d
F={s:feats(df) for s,df in daily.items()}; trades=[]
for s,d in F.items():
    d=d[(d.index>=START-dt.timedelta(days=5))&(d.index<=END)]
    if len(d)<30: continue
    cl,op=d.c.values,d.o.values; idx=list(d.index); pos=None; c={k:d[k].values for k in ["e21","e50","s50","hi20","hi52","r21","dvol","rvol","spy21"]}
    for k in range(1,len(idx)-1):
        if idx[k]<START: continue
        if pos is None:
            if np.isnan(c["hi52"][k]) or np.isnan(c["e50"][k]): continue
            if c["r21"][k]>c["spy21"][k] and cl[k]>c["s50"][k] and cl[k]>10 and c["dvol"][k]>25e6 and cl[k]/c["hi52"][k]-1>=-0.10 and cl[k]>c["hi20"][k] and cl[k]>c["e50"][k] and c["rvol"][k]>=1.5:
                pos=(k+1,op[k+1],c["r21"][k]-c["spy21"][k])
        else:
            ei,ep,rs=pos
            if cl[k]<c["e21"][k]: trades.append((s,idx[ei],idx[k+1],ep,op[k+1],rs)); pos=None
    if pos: trades.append((s,idx[pos[0]],idx[-1],pos[1],cl[-1],pos[2]))
tr=pd.DataFrame(trades,columns=["symbol","entry","exit","in_px","out_px","rs"]); tr["ret"]=tr.out_px/tr.in_px-1
closes={s:F[s].c for s in F}
def trend_port(t,mp,size,ranked,slip=5e-4,eq0=1e5,regime=False):
    t=t.sort_values(["entry","rs" if ranked else "symbol"],ascending=[True,not ranked]).reset_index(drop=True); by=t.groupby("entry"); cash=eq0; open_pos={}; eq=[]
    for d in sessions:
        for k in [k for k,p in open_pos.items() if p["exit"]==d]:
            p=open_pos.pop(k); cash+=p["qty"]*p["out_px"]*(1-slip)
        if d in by.groups and (not regime or regime_ok.get(prev.get(d),True)):
            for k,r in by.get_group(d).iterrows():
                if len(open_pos)>=mp: continue
                mv=sum(p["qty"]*closes[p["sym"]].get(d,p["in_px"]) for p in open_pos.values()); px=r.in_px*(1+slip); qty=math.floor((cash+mv)*size/px)
                if qty<=0 or qty*px>cash: continue
                cash-=qty*px; open_pos[k]=dict(sym=r.symbol,qty=qty,in_px=px,exit=r.exit,out_px=r.out_px)
        mv=0.0
        for p in open_pos.values():
            cc=closes[p["sym"]].get(d,np.nan); mv+=p["qty"]*(cc if not np.isnan(cc) else p["in_px"])
        eq.append(cash+mv)
    return pd.Series(eq,index=sessions)
w=tr.ret>0; print(f"TREND per-trade: n={len(tr)} win={w.mean():.0%} avg={tr.ret.mean()*100:+.2f}% PF={tr.ret[w].sum()/max(1e-9,-tr.ret[~w].sum()):.2f}")
pstats(trend_port(tr,10,0.10,False),"trend 10x10% first-come (as before)")
pstats(trend_port(tr,10,0.10,True),"trend 10x10% ranked by RS")
pstats(trend_port(tr,10,0.10,True,regime=True),"trend 10x10% ranked + regime switch")
pstats(trend_port(tr,5,0.20,True),"trend 5x20% ranked by RS")
pstats(trend_port(tr,20,0.05,True),"trend 20x5% ranked by RS")
# ---- combined, recommended config with both fixes
comb=swing_port(sw_reg,10,0.10,5e4)+trend_port(tr,10,0.10,True,eq0=5e4,regime=True)
pstats(comb,"50/50 swing(regime) + trend(ranked, regime), 10x10%")
comb5=swing_port(sw_reg,5,0.20,5e4)+trend_port(tr,5,0.20,True,eq0=5e4,regime=True)
pstats(comb5,"50/50 swing(regime) + trend(ranked, regime), 5x20%")
pstats(spy/spy.iloc[0]*1e5,"SPY")
