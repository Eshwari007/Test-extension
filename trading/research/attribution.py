"""Why do the PIT results differ from the earlier ones? 2025-01-02 -> 2026-10-09, trend book 20x5% ranked+regime,
2x2: universe {point-in-time S&P 500, today's list + NDX extras} x {with -8% disaster stop, without}."""
import os, sys, pickle, math, datetime as dt, numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(HERE,".."))
import gajjala_scanner_us as g
ET=g.ET; C=os.path.join(HERE,"cache_pit")
daily=pickle.load(open(f"{C}/daily.pkl","rb")); spy=pickle.load(open(f"{C}/spy_daily.pkl","rb")); members=pickle.load(open(f"{C}/members.pkl","rb")); mdates=sorted(members)
cur=pickle.load(open(os.path.join(HERE,"cache","daily.pkl"),"rb"))   # today's list + NDX extras, from 2024-01
for s,df in cur.items():
    if s not in daily: daily[s]=df
today_list=set(cur)
def member_set(d): return members[mdates[max(np.searchsorted(mdates,d,side="right")-1,0)]]
S=spy.copy(); S.index=S.index.tz_convert(ET).date; spy21=S.c/S.c.shift(21)-1; spy_e50=S.c.ewm(span=50,adjust=False).mean(); regime_ok={d:bool(S.c[d]>spy_e50[d]) for d in S.index}; all_sessions=list(S.index)
def feats(df):
    d=df.copy(); d.index=d.index.tz_convert(ET).date
    d["e21"]=d.c.ewm(span=21,adjust=False).mean(); d["e50"]=d.c.ewm(span=50,adjust=False).mean(); d["s50"]=d.c.rolling(50).mean()
    d["hi20"]=d.h.rolling(20).max().shift(1); d["hi52"]=d.h.rolling(252,min_periods=120).max().shift(1)
    d["r21"]=d.c/d.c.shift(21)-1; d["dvol"]=(d.c*d.v).rolling(20).mean(); d["rvol"]=d.v/d.v.rolling(20).mean().shift(1); d["spy21"]=spy21.reindex(d.index).values
    return d
F={s:feats(df) for s,df in daily.items() if len(df)>60}; closes={s:F[s].c for s in F}
A,B=dt.date(2025,1,2),dt.date(2026,10,9); ses=[d for d in all_sessions if A<=d<=B]
def cands(universe_pit,stop):
    out=[]
    for s,d in F.items():
        if not universe_pit and s not in today_list: continue
        cl,op,lo=d.c.values,d.o.values,d.l.values; idx=list(d.index); c={k:d[k].values for k in ["e21","e50","s50","hi20","hi52","r21","dvol","rvol","spy21"]}; pos=None
        for k in range(1,len(idx)-1):
            if idx[k]<A-dt.timedelta(days=3) or idx[k]>B: continue
            if pos is None:
                if np.isnan(c["hi52"][k]) or np.isnan(c["e50"][k]) or np.isnan(c["rvol"][k]): continue
                if universe_pit and s not in member_set(idx[k]): continue
                if c["r21"][k]>c["spy21"][k] and cl[k]>c["s50"][k] and cl[k]>10 and c["dvol"][k]>25e6 and cl[k]/c["hi52"][k]-1>=-0.10 and cl[k]>c["hi20"][k] and cl[k]>c["e50"][k] and c["rvol"][k]>=1.5:
                    pos=(k+1,op[k+1],c["r21"][k]-c["spy21"][k])
            else:
                ei,ep,rs=pos; stopped=stop and lo[k]<=ep*0.92
                if stopped or cl[k]<c["e21"][k]: out.append((s,idx[ei],idx[k+1],ep,min(op[k+1],ep*0.92) if stopped else op[k+1],rs)); pos=None
        if pos: out.append((s,idx[pos[0]],idx[-1],pos[1],cl[-1],pos[2]))
    t=pd.DataFrame(out,columns=["symbol","entry","exit","in_px","out_px","rs"]); t["ret"]=t.out_px/t.in_px-1; return t
def sim(t,mp,size,slip=5e-4,eq0=1e5):
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
    eq=pd.Series(eq,index=ses); tk=np.array(tk); return eq.iloc[-1]/eq0-1,(eq/eq.cummax()-1).min(),len(tk),tk[tk>0].sum()/max(1e-9,-tk[tk<=0].sum()),tk.mean()
print(f"2025-01-02 -> 2026-10-09, SPY {S.c[ses[-1]]/S.c[ses[0]]-1:+.1%}; trend book 20x5% ranked + regime switch, next-open + 5 bps")
print(f"{'universe':34s} {'stop':8s} {'cands':>6s} {'cand avg':>9s} {'cand PF':>8s} | {'total':>7s} {'maxDD':>7s} {'taken':>6s} {'PF':>5s} {'avg':>7s}")
for upit,ulab in ((True,"point-in-time S&P 500"),(False,"today's S&P 500 + NDX extras")):
    for stop in (True,False):
        t=cands(upit,stop); tot,dd,n,pf,avg=sim(t,20,0.05); w=t.ret>0
        print(f"{ulab:34s} {'-8% stop' if stop else 'none':8s} {len(t):6d} {t.ret.mean()*100:+8.2f}% {t.ret[w].sum()/max(1e-9,-t.ret[~w].sum()):8.2f} | {tot:+7.1%} {dd:7.1%} {n:6d} {pf:5.2f} {avg*100:+6.2f}%")
# which names drive the difference: top contributors present only in today's list
t_today=cands(False,False); t_pit=cands(True,False)
only=set(t_today.symbol)-set(t_pit.symbol); print(f"\nnames tradeable only with today's list (not S&P members at signal time): {len(only)}: {sorted(only)[:40]}")
g1=t_today[t_today.symbol.isin(only)]; print(f"their candidate trades: {len(g1)}, avg {g1.ret.mean()*100:+.2f}%, sum of returns {g1.ret.sum()*100:+.0f} pct-points (vs {t_today.ret.sum()*100:+.0f} for all)")
