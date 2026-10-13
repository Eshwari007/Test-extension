"""Tests 2 and 3: trend book on six calendar windows 2021..2026 with point-in-time S&P 500 membership.
Rules frozen: Stage 1 (21d ret > SPY, >SMA50, >$10, $25M ADV, within 10% of 52w high) + 20d-high breakout on 1.5x vol + >EMA50;
entry next open +5 bps; exit next open after close < EMA21; -8% disaster stop; ranked slot filling by RS; regime switch SPY>EMA50."""
import os, sys, pickle, math, datetime as dt, numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(HERE,".."))
import gajjala_scanner_us as g
ET=g.ET; C=os.path.join(HERE,"cache_pit"); USE_STOP=os.environ.get("USE_STOP","1")=="1"; print("disaster stop:",USE_STOP)
daily=pickle.load(open(f"{C}/daily.pkl","rb")); spy=pickle.load(open(f"{C}/spy_daily.pkl","rb")); members=pickle.load(open(f"{C}/members.pkl","rb"))
mdates=sorted(members)
def member_set(d):
    i=np.searchsorted(mdates,d,side="right")-1
    return members[mdates[max(i,0)]]
S=spy.copy(); S.index=S.index.tz_convert(ET).date; spy21=S.c/S.c.shift(21)-1; spy_e50=S.c.ewm(span=50,adjust=False).mean()
regime_ok={d:bool(S.c[d]>spy_e50[d]) for d in S.index}
all_sessions=list(S.index)
def feats(df):
    d=df.copy(); d.index=d.index.tz_convert(ET).date
    d["e21"]=d.c.ewm(span=21,adjust=False).mean(); d["e50"]=d.c.ewm(span=50,adjust=False).mean(); d["s50"]=d.c.rolling(50).mean()
    d["hi20"]=d.h.rolling(20).max().shift(1); d["hi52"]=d.h.rolling(252,min_periods=120).max().shift(1)
    d["r21"]=d.c/d.c.shift(21)-1; d["dvol"]=(d.c*d.v).rolling(20).mean(); d["rvol"]=d.v/d.v.rolling(20).mean().shift(1); d["spy21"]=spy21.reindex(d.index).values
    return d
F={s:feats(df) for s,df in daily.items() if len(df)>60}
closes={s:F[s].c for s in F}; opens={s:F[s].o for s in F}
# all candidate signals once (membership checked on the signal date)
cands=[]; sig_rows=[]
for s,d in F.items():
    cl,op,lo=d.c.values,d.o.values,d.l.values; idx=list(d.index); c={k:d[k].values for k in ["e21","e50","s50","hi20","hi52","r21","dvol","rvol","spy21"]}
    pos=None
    for k in range(1,len(idx)-1):
        if pos is None:
            if np.isnan(c["hi52"][k]) or np.isnan(c["e50"][k]) or np.isnan(c["rvol"][k]): continue
            if s not in member_set(idx[k]): continue
            if c["r21"][k]>c["spy21"][k] and cl[k]>c["s50"][k] and cl[k]>10 and c["dvol"][k]>25e6 and cl[k]/c["hi52"][k]-1>=-0.10 and cl[k]>c["hi20"][k] and cl[k]>c["e50"][k] and c["rvol"][k]>=1.5:
                pos=(k+1,op[k+1],c["r21"][k]-c["spy21"][k],idx[k])
                # demeaned forward excess for test 4 (next open to open 20 sessions later)
                if k+21<len(idx):
                    so=S.o; sd0,sd1=idx[k+1],idx[min(k+21,len(idx)-1)]
                    if sd0 in so.index and sd1 in so.index: sig_rows.append((s,idx[k],op[k+21]/op[k+1]-1-(so[sd1]/so[sd0]-1)))
        else:
            ei,ep,rs,sd=pos
            stopped=USE_STOP and lo[k]<=ep*0.92
            if stopped or cl[k]<c["e21"][k]:
                out=min(op[k+1],ep*0.92) if stopped else op[k+1]
                cands.append((s,sd,idx[ei],idx[k+1],ep,out,rs,"stop" if stopped else "ema21")); pos=None
    if pos: cands.append((s,pos[3],idx[pos[0]],idx[-1],pos[1],cl[-1],pos[2],"open"))
T=pd.DataFrame(cands,columns=["symbol","signal","entry","exit","in_px","out_px","rs","reason"]); T["ret"]=T.out_px/T.in_px-1
SIG=pd.DataFrame(sig_rows,columns=["symbol","date","ex20"])
print(f"candidate trades 2020-2026 (PIT universe): {len(T)}")
def sim(t,sessions,mp,size,regime,slip=5e-4,eq0=1e5):
    t=t[(t.entry>=sessions[0])&(t.entry<=sessions[-1])].sort_values(["entry","rs"],ascending=[True,False]).reset_index(drop=True); by=t.groupby("entry")
    cash=eq0; open_pos={}; eq=[]; taken=[]
    for d in sessions:
        for k in [k for k,p in open_pos.items() if p["exit"]<=d]:
            p=open_pos.pop(k); cash+=p["qty"]*p["out_px"]*(1-slip)
        prev=all_sessions[all_sessions.index(d)-1]
        if d in by.groups and (not regime or regime_ok.get(prev,True)):
            for k,r in by.get_group(d).iterrows():
                if len(open_pos)>=mp or r.symbol in {p["sym"] for p in open_pos.values()}: continue
                mv=sum(p["qty"]*closes[p["sym"]].get(d,p["in_px"]) for p in open_pos.values()); px=r.in_px*(1+slip); qty=math.floor((cash+mv)*size/px)
                if qty<=0 or qty*px>cash: continue
                cash-=qty*px; open_pos[k]=dict(sym=r.symbol,qty=qty,in_px=px,exit=r.exit,out_px=r.out_px); taken.append(r.out_px*(1-slip)/px-1)
        mv=0.0
        for p in open_pos.values():
            cc=closes[p["sym"]].get(d,np.nan); mv+=p["qty"]*(cc if not np.isnan(cc) else p["in_px"])
        eq.append(cash+mv)
    # liquidate at window end for a clean comparison
    eq=pd.Series(eq,index=sessions); tk=np.array(taken)
    pf=tk[tk>0].sum()/max(1e-9,-tk[tk<=0].sum()) if len(tk) else np.nan
    return dict(total=eq.iloc[-1]/eq0-1,maxdd=(eq/eq.cummax()-1).min(),n=len(tk),win=(tk>0).mean() if len(tk) else np.nan,pf=pf,eq=eq)
windows=[("2021",dt.date(2021,1,4),dt.date(2021,12,31)),("2022",dt.date(2022,1,3),dt.date(2022,12,30)),("2023",dt.date(2023,1,3),dt.date(2023,12,29)),("2024",dt.date(2024,1,2),dt.date(2024,12,31)),("2025",dt.date(2025,1,2),dt.date(2025,12,31)),("2026 YTD",dt.date(2026,1,2),dt.date(2026,10,9))]
print("\n=== TEST 3: trend book by calendar window, PIT universe, next-open + 5 bps ===")
print(f"{'window':9s} {'SPY':>7s} | {'20x5 rk+reg':>11s} {'excess':>7s} {'maxDD':>6s} {'PF':>5s} {'n':>4s} | {'10x10 rk+reg':>12s} {'excess':>7s} {'maxDD':>6s} {'PF':>5s} | {'20x5 no regime':>14s} {'excess':>7s} {'maxDD':>6s} | {'20d entry excess':>16s} {'n':>5s} {'regime-off days':>15s}")
rows=[]
for name,a,b in windows:
    ses=[d for d in all_sessions if a<=d<=b]; spyr=S.c[ses[-1]]/S.c[ses[0]]-1
    r1=sim(T,ses,20,0.05,True); r2=sim(T,ses,10,0.10,True); r3=sim(T,ses,20,0.05,False)
    sg=SIG[(SIG.date>=a)&(SIG.date<=b)]; off=sum(not regime_ok.get(all_sessions[all_sessions.index(d)-1],True) for d in ses)
    print(f"{name:9s} {spyr:+7.1%} | {r1['total']:+11.1%} {r1['total']-spyr:+7.1%} {r1['maxdd']:6.1%} {r1['pf']:5.2f} {r1['n']:4d} | {r2['total']:+12.1%} {r2['total']-spyr:+7.1%} {r2['maxdd']:6.1%} {r2['pf']:5.2f} | {r3['total']:+14.1%} {r3['total']-spyr:+7.1%} {r3['maxdd']:6.1%} | {sg.ex20.mean()*100:+15.2f}% {len(sg):5d} {off:15d}")
    rows.append(dict(window=name,spy=spyr,t20_reg=r1['total'],t20_reg_dd=r1['maxdd'],t20_reg_pf=r1['pf'],t20_reg_n=r1['n'],t10_reg=r2['total'],t10_reg_dd=r2['maxdd'],t10_reg_pf=r2['pf'],t20_noreg=r3['total'],t20_noreg_dd=r3['maxdd'],ex20=sg.ex20.mean(),n_sig=len(sg),regime_off_days=off))
    pd.DataFrame({"eq_20x5_reg":r1["eq"],"eq_10x10_reg":r2["eq"],"eq_20x5_noreg":r3["eq"],"spy":S.c.reindex(ses)/S.c[ses[0]]*1e5}).to_csv(f"out/test3_{name.replace(chr(32),chr(95))}_{'stop' if USE_STOP else 'nostop'}.csv")
R=pd.DataFrame(rows); R.to_csv("out/test3_summary_%s.csv"%("stop" if USE_STOP else "nostop")+"",index=False)
print("\n=== TEST 2: 2022 bear market detail (20x5%, ranked) ===")
ses=[d for d in all_sessions if dt.date(2022,1,3)<=d<=dt.date(2022,12,30)]
for lab,reg in (("regime switch ON",True),("regime switch OFF",False)):
    r=sim(T,ses,20,0.05,reg); m=r["eq"].groupby(pd.to_datetime(pd.Series(r["eq"].index)).dt.to_period("M").values).agg(["first","last"])
    print(f"  {lab}: total {r['total']:+.1%}, maxDD {r['maxdd']:.1%}, PF {r['pf']:.2f}, n {r['n']}, win {r['win']:.0%}; monthly: "+" ".join(f"{str(i)[-2:]}:{(v['last']/v['first']-1)*100:+.0f}" for i,v in m.iterrows()))
spy22=S.c.reindex(ses); print(f"  SPY 2022: {spy22.iloc[-1]/spy22.iloc[0]-1:+.1%}, maxDD {(spy22/spy22.cummax()-1).min():.1%}; regime switch blocked entries on {sum(not regime_ok.get(all_sessions[all_sessions.index(d)-1],True) for d in ses)} of {len(ses)} sessions")
print("\n=== worst-window summary (the bar: positive excess in >=4 of 6, worst DD <= 25%, PF >= 1.2 in every window) ===")
for col,lab in (("t20_reg","20x5% ranked+regime"),("t10_reg","10x10% ranked+regime")):
    ex=(R[col]-R.spy); print(f"  {lab}: excess positive in {(ex>0).sum()} of 6; worst DD {R[col+'_dd'].min():.1%}; min PF {R[col+'_pf'].min():.2f}; mean excess {ex.mean()*100:+.1f} pp/yr; median {ex.median()*100:+.1f}")
