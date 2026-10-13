"""Test 1: plan's exact rules over 2026-06-23 -> 2026-10-09, next-open fills + 5 bps, ranked slot filling, regime switch.
Trade list for the trend book (20x5% and 10x10%) and the swing book (10x10%), plus the diagnostics asked for."""
import os, sys, io, math, contextlib, datetime as dt, numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import data as D
from engine import Dataset, Params, run, stats
import portfolio as P
START,END=dt.date(2026,6,23),dt.date(2026,10,9); P.ALL=(START,END); ET=D.g.ET
ds=Dataset(); P.init(ds); spy_d=D.load("spy_daily.pkl"); spy_d.index=spy_d.index.tz_convert(ET).date
sessions=sorted(d for d in ds.sessions if START<=d<=END); spy=spy_d.c.reindex(sessions)
spy_e50=spy_d.c.ewm(span=50,adjust=False).mean(); regime_ok={d:bool(spy_d.c.get(d)>spy_e50.get(d)) for d in spy_d.index}
prev={d:sessions[i-1] if i>0 else sorted(spy_d.index)[sorted(spy_d.index).index(d)-1] for i,d in enumerate(sessions)}
names=pd.read_csv(os.path.join(HERE,'..','data','sp500.csv')).set_index('Symbol')['Security'].to_dict()
print(f"=== TEST 1: {START} -> {END}, {len(sessions)} sessions, SPY {spy.iloc[-1]/spy.iloc[0]-1:+.1%}; regime switch off on {sum(not regime_ok.get(prev[d],True) for d in sessions)} sessions ===")
daily=D.load("daily.pkl"); spy21=spy_d.c/spy_d.c.shift(21)-1
def feats(df):
    d=df.copy(); d.index=d.index.tz_convert(ET).date
    d["e21"]=d.c.ewm(span=21,adjust=False).mean(); d["e50"]=d.c.ewm(span=50,adjust=False).mean(); d["s50"]=d.c.rolling(50).mean()
    d["hi20"]=d.h.rolling(20).max().shift(1); d["hi52"]=d.h.rolling(252,min_periods=120).max().shift(1)
    d["r21"]=d.c/d.c.shift(21)-1; d["dvol"]=(d.c*d.v).rolling(20).mean(); d["rvol"]=d.v/d.v.rolling(20).mean().shift(1); d["spy21"]=spy21.reindex(d.index).values
    return d
F={s:feats(df) for s,df in daily.items()}
cands=[]; diag={}
for s,d in F.items():
    d=d[(d.index>=START-dt.timedelta(days=5))&(d.index<=END)]
    if len(d)<10: continue
    cl,op=d.c.values,d.o.values; idx=list(d.index); pos=None; c={k:d[k].values for k in ["e21","e50","s50","hi20","hi52","r21","dvol","rvol","spy21"]}
    for k in range(1,len(idx)-1):
        if idx[k]<START: continue
        st1=c["r21"][k]>c["spy21"][k] and cl[k]>c["s50"][k] and cl[k]>10 and c["dvol"][k]>25e6
        near=cl[k]/c["hi52"][k]-1>=-0.10 if not np.isnan(c["hi52"][k]) else False
        brk=cl[k]>c["hi20"][k] and cl[k]>c["e50"][k] and c["rvol"][k]>=1.5
        if s in ("MRNA","MPC","PSX","VLO","P","MU","SNDK"):
            diag.setdefault(s,[]).append((idx[k],round(c["r21"][k]*100,1),round((cl[k]/c["hi52"][k]-1)*100,1) if not np.isnan(c["hi52"][k]) else None,st1,near,brk))
        if pos is None:
            if st1 and near and brk: pos=(k+1,op[k+1],c["r21"][k]-c["spy21"][k],idx[k])
        else:
            ei,ep,rs,sd=pos
            if cl[k]<c["e21"][k]: cands.append((s,sd,idx[ei],idx[k+1],ep,op[k+1],rs,"ema21")); pos=None
    if pos: cands.append((s,pos[3],idx[pos[0]],idx[-1],pos[1],cl[-1],pos[2],"open"))
tr=pd.DataFrame(cands,columns=["symbol","signal_date","entry","exit","in_px","out_px","rs","reason"]); tr["ret"]=tr.out_px/tr.in_px-1
print(f"\ncandidate-days (Stage1 + near-high + breakout, before slots/regime): {len(tr)} signals in {tr.symbol.nunique()} names; per-trade avg {tr.ret.mean()*100:+.2f}%, win {(tr.ret>0).mean():.0%}, PF {tr.ret[tr.ret>0].sum()/max(1e-9,-tr.ret[tr.ret<=0].sum()):.2f}")
closes={s:F[s].c for s in F}
def trend_book(t,mp,size,slip=5e-4,eq0=1e5):
    t=t.sort_values(["entry","rs"],ascending=[True,False]).reset_index(drop=True); by=t.groupby("entry"); cash=eq0; open_pos={}; eq=[]; taken=[]
    for d in sessions:
        for k in [k for k,p in open_pos.items() if p["exit"]==d]:
            p=open_pos.pop(k); cash+=p["qty"]*p["out_px"]*(1-slip)
        if d in by.groups and regime_ok.get(prev[d],True):
            for k,r in by.get_group(d).iterrows():
                if len(open_pos)>=mp or r.symbol in {p["sym"] for p in open_pos.values()}: continue
                mv=sum(p["qty"]*closes[p["sym"]].get(d,p["in_px"]) for p in open_pos.values()); px=r.in_px*(1+slip); qty=math.floor((cash+mv)*size/px)
                if qty<=0 or qty*px>cash: continue
                cash-=qty*px; open_pos[k]=dict(sym=r.symbol,qty=qty,in_px=px,exit=r.exit,out_px=r.out_px)
                taken.append(dict(symbol=r.symbol,company=names.get(r.symbol,""),signal=r.signal_date,entry=r.entry,exit=r.exit,entry_px=round(px,2),exit_px=round(r.out_px*(1-slip),2),shares=qty,pnl=round(qty*(r.out_px*(1-slip)-px),0),ret=round(r.out_px*(1-slip)/px-1,4),reason=r.reason,rs=round(r.rs*100,1)))
        mv=sum(p["qty"]*(closes[p["sym"]].get(d,np.nan) if not np.isnan(closes[p["sym"]].get(d,np.nan)) else p["in_px"]) for p in open_pos.values()); eq.append(cash+mv)
    return pd.Series(eq,index=sessions),pd.DataFrame(taken)
for mp,sz in ((20,0.05),(10,0.10)):
    eq,tk=trend_book(tr,mp,sz)
    print(f"\n--- TREND BOOK {mp} x {sz:.0%}, ranked, regime switch, next-open + 5 bps: ${eq.iloc[-1]:,.0f} ({eq.iloc[-1]/1e5-1:+.1%}), maxDD {(eq/eq.cummax()-1).min():.1%}, {len(tk)} trades, win {(tk.pnl>0).mean():.0%}, PF {tk.pnl[tk.pnl>0].sum()/max(1,-tk.pnl[tk.pnl<=0].sum()):.2f} ---")
    print(tk.sort_values("entry").to_string(index=False)); tk.to_csv(f"out/test1_trend_{mp}x{int(sz*100)}.csv",index=False)
C=Params(mode="orb",orb_bars=3,vol_mult=1.5,stop_mode="pct",stop_pct=5,targets=(),trail="none",hold="overnight",max_hold_days=3,earliest="09:45",max_off_high=10)
sw=run(ds,C,START,END); sw=sw[[regime_ok.get(prev.get(d),True) for d in sw.session]]
with contextlib.redirect_stdout(io.StringIO()): eqs=P.portfolio(sw,10,0.10,5,start_eq=1e5,label="")
s=stats(sw); print(f"\n--- SWING BOOK 10 x 10%, regime switch: ${eqs.iloc[-1]:,.0f} ({eqs.iloc[-1]/1e5-1:+.1%}); {s['n']} trades, win {s['win']}, PF {s['pf']} ---")
print(sw[["session","symbol","entry","stop","exit_time","exits","R","pnl"]].to_string(index=False)); sw.to_csv("out/test1_swing.csv",index=False)
print("\n--- DIAGNOSTICS: why named stocks were or were not bought (date, 21d ret %, % off 52w high, stage1, within10%, breakout) ---")
for s_,rows in diag.items():
    rows=[r for r in rows if r[3]]  # days Stage 1 passed
    if not rows: print(f"{s_}: never passed Stage 1 in the window"); continue
    near_days=sum(r[4] for r in rows); brk_days=sum(r[5] and r[4] for r in rows)
    print(f"{s_}: Stage1 on {len(rows)} days; within 10% of 52w high on {near_days}; eligible breakout days {brk_days}; first/last: {rows[0][:3]} .. {rows[-1][:3]}")
