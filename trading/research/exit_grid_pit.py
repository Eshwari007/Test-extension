"""Exit grid for the trend book on the point-in-time universe, 2021-01-04 -> 2026-10-09.
Same entry (Stage 1 + 20d-high breakout on 1.5x vol, > EMA50), ranked fill, regime switch, 10 slots x 10%, next-open + 5 bps.
Exits: trail rule x hard stop x profit-taking. Reports 6-year total, worst-year, min per-window PF, worst DD, win rate."""
import os, sys, pickle, math, datetime as dt, numpy as np, pandas as pd, itertools
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(HERE,".."))
import gajjala_scanner_us as g
ET=g.ET; C=os.path.join(HERE,"cache_pit")
daily=pickle.load(open(f"{C}/daily.pkl","rb")); spy=pickle.load(open(f"{C}/spy_daily.pkl","rb")); members=pickle.load(open(f"{C}/members.pkl","rb")); mdates=sorted(members)
def member_set(d): return members[mdates[max(np.searchsorted(mdates,d,side="right")-1,0)]]
S=spy.copy(); S.index=S.index.tz_convert(ET).date; spy21=S.c/S.c.shift(21)-1; spy_e50=S.c.ewm(span=50,adjust=False).mean(); regime_ok={d:bool(S.c[d]>spy_e50[d]) for d in S.index}; all_sessions=list(S.index)
A,B=dt.date(2021,1,4),dt.date(2026,10,9); ses=[d for d in all_sessions if A<=d<=B]
def feats(df):
    d=df.copy(); d.index=d.index.tz_convert(ET).date
    for n in (10,21,50): d[f"e{n}"]=d.c.ewm(span=n,adjust=False).mean()
    d["s50"]=d.c.rolling(50).mean(); d["hi20"]=d.h.rolling(20).max().shift(1); d["hi52"]=d.h.rolling(252,min_periods=120).max().shift(1)
    d["lo10"]=d.l.rolling(10).min().shift(1); d["lo20"]=d.l.rolling(20).min().shift(1)
    d["r21"]=d.c/d.c.shift(21)-1; d["dvol"]=(d.c*d.v).rolling(20).mean(); d["rvol"]=d.v/d.v.rolling(20).mean().shift(1); d["spy21"]=spy21.reindex(d.index).values
    pc=d.c.shift(1); d["atr"]=pd.concat([d.h-d.l,(d.h-pc).abs(),(d.l-pc).abs()],axis=1).max(axis=1).rolling(14).mean()
    return d
F={s:feats(df) for s,df in daily.items() if len(df)>60}; closes={s:F[s].c for s in F}
# entry signals once
sigs=[]
for s,d in F.items():
    cl=d.c.values; idx=list(d.index); c={k:d[k].values for k in ["e50","s50","hi20","hi52","r21","dvol","rvol","spy21"]}
    for k in range(1,len(idx)-1):
        if idx[k]<A-dt.timedelta(days=3) or idx[k]>B or np.isnan(c["hi52"][k]) or np.isnan(c["rvol"][k]): continue
        if s not in member_set(idx[k]): continue
        if c["r21"][k]>c["spy21"][k] and cl[k]>c["s50"][k] and cl[k]>10 and c["dvol"][k]>25e6 and cl[k]/c["hi52"][k]-1>=-0.10 and cl[k]>c["hi20"][k] and cl[k]>c["e50"][k] and c["rvol"][k]>=1.5:
            sigs.append((s,k,c["r21"][k]-c["spy21"][k]))
print(f"{len(sigs)} entry signals")
def trades_for(trail,stop_pct,target_pct,atr_mult,time_stop):
    out=[]; busy={}
    for s,k,rs in sorted(sigs,key=lambda x:(x[0],x[1])):
        d=F[s]; idx=d.index; n=len(d)
        if k+1>=n: continue
        if s in busy and k<=busy[s]: continue
        cl,op,lo,hi=d.c.values,d.o.values,d.l.values,d.h.values; tr=d[trail].values if trail in d else None; atr=d["atr"].values
        ep=op[k+1]; stop=ep*(1-stop_pct) if stop_pct else -1; peak=ep; exit_i=None; px=None
        for j in range(k+1,n):
            peak=max(peak,hi[j])
            if atr_mult: stop=max(stop,peak-atr_mult*atr[j])          # chandelier trail from the high
            if lo[j]<=stop and stop>0: exit_i=j; px=min(op[j],stop) if j>k+1 else stop; break
            if target_pct and hi[j]>=ep*(1+target_pct): exit_i=j; px=max(op[j],ep*(1+target_pct)); break
            if j>k+1 and time_stop and j-(k+1)>=time_stop: exit_i=j; px=cl[j]; break
            if tr is not None and j>k+1 and cl[j-1]<tr[j-1]: exit_i=j; px=op[j]; break   # close below trail -> next open
        if exit_i is None: exit_i=n-1; px=cl[-1]
        out.append((s,idx[k+1],idx[exit_i],ep,px,rs)); busy[s]=exit_i
    t=pd.DataFrame(out,columns=["symbol","entry","exit","in_px","out_px","rs"]); t["ret"]=t.out_px/t.in_px-1; return t
def sim(t,mp=10,size=0.10,slip=5e-4,eq0=1e5):
    t=t[(t.entry>=A)&(t.entry<=B)].sort_values(["entry","rs"],ascending=[True,False]).reset_index(drop=True); by=t.groupby("entry"); cash=eq0; open_pos={}; eq=[]; tk=[]
    for d in ses:
        for k in [k for k,p in open_pos.items() if p["exit"]<=d]: p=open_pos.pop(k); cash+=p["qty"]*p["out_px"]*(1-slip)
        prev=all_sessions[all_sessions.index(d)-1]
        if d in by.groups and regime_ok.get(prev,True):
            for k,r in by.get_group(d).iterrows():
                if len(open_pos)>=mp or r.symbol in {p["sym"] for p in open_pos.values()}: continue
                mv=sum(p["qty"]*closes[p["sym"]].get(d,p["in_px"]) for p in open_pos.values()); px=r.in_px*(1+slip); qty=math.floor((cash+mv)*size/px)
                if qty<=0 or qty*px>cash: continue
                cash-=qty*px; open_pos[k]=dict(sym=r.symbol,qty=qty,in_px=px,exit=r.exit,out_px=r.out_px); tk.append(r.out_px*(1-slip)/px-1)
        mv=sum(p["qty"]*(closes[p["sym"]].get(d,np.nan) if not np.isnan(closes[p["sym"]].get(d,np.nan)) else p["in_px"]) for p in open_pos.values()); eq.append(cash+mv)
    eq=pd.Series(eq,index=ses); tk=np.array(tk)
    yrs=eq.groupby(pd.to_datetime(pd.Series(eq.index)).dt.year.values).agg(["first","last"]); yr=(yrs["last"]/yrs["first"]-1)
    return dict(total=eq.iloc[-1]/eq0-1,worst_year=yr.min(),best_year=yr.max(),maxdd=(eq/eq.cummax()-1).min(),n=len(tk),win=(tk>0).mean(),pf=tk[tk>0].sum()/max(1e-9,-tk[tk<=0].sum()),avg=tk.mean(),avg_loss=tk[tk<=0].mean(),avg_win=tk[tk>0].mean())
spy_total=S.c[ses[-1]]/S.c[ses[0]]-1
print(f"SPY 2021-01-04 -> 2026-10-09: {spy_total:+.1%}\n")
grid=[]
for trail,stop_pct,target,atrm,tstop in [
    ("e21",0,0,0,0),("e21",0.05,0,0,0),("e21",0.08,0,0,0),("e21",0.12,0,0,0),
    ("e10",0,0,0,0),("e10",0.05,0,0,0),("e50",0,0,0,0),("e50",0.08,0,0,0),
    ("lo10",0,0,0,0),("lo20",0,0,0,0),("lo20",0.08,0,0,0),
    (None,0,0,2.0,0),(None,0,0,3.0,0),(None,0,0,4.0,0),(None,0.08,0,3.0,0),
    ("e21",0,0.15,0,0),("e21",0,0.25,0,0),("e21",0.08,0.15,0,0),("e50",0,0.25,0,0),
    (None,0.05,0,0,3),(None,0.05,0,0,10),(None,0.08,0,0,20),(None,0.10,0,0,40),
    ("e21",0.03,0,0,0),(None,0.03,0,0,5),(None,0.03,0.06,0,0),(None,0.05,0.10,0,0)]:
    t=trades_for(trail,stop_pct,target,atrm,tstop); r=sim(t)
    lab=(f"trail {trail}" if trail else (f"chandelier {atrm}xATR" if atrm else "no trail"))+(f", stop -{stop_pct:.0%}" if stop_pct else ", no stop")+(f", target +{target:.0%}" if target else "")+(f", time {tstop}d" if tstop else "")
    grid.append(dict(exit=lab,total=r["total"],worst_year=r["worst_year"],best_year=r["best_year"],maxdd=r["maxdd"],n=r["n"],win=r["win"],pf=r["pf"],avg_win=r["avg_win"],avg_loss=r["avg_loss"]))
    print(f"{lab:48s} total {r['total']:+7.1%}  worst yr {r['worst_year']:+6.1%}  best yr {r['best_year']:+6.1%}  maxDD {r['maxdd']:6.1%}  n {r['n']:4d}  win {r['win']:.0%}  PF {r['pf']:.2f}  avg win {r['avg_win']*100:+5.1f}%  avg loss {r['avg_loss']*100:+5.1f}%",flush=True)
pd.DataFrame(grid).to_csv("out/exit_grid_pit.csv",index=False)
