"""Robustness of the hold-N exit: (1) sizing/path dependence, (2) per-window PF for the bar, (3) IS/OOS selection split,
(4) per-signal 25-session demeaned excess for top-ranked signals only, by year."""
import sys, os, io, contextlib
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
src=open('exit_neighbourhood.py').read().split('print("NEIGHBOURHOOD')[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
import numpy as np, pandas as pd, datetime as dt
def sim_full(t,mp,size,slip=5e-4,eq0=1e5):
    t=t[(t.entry>=A)&(t.entry<=B)].sort_values(["entry","rs"],ascending=[True,False]).reset_index(drop=True); by=t.groupby("entry"); cash=eq0; open_pos={}; eq=[]; tk=[]
    for d in ses:
        for k in [k for k,p in open_pos.items() if p["exit"]<=d]: p=open_pos.pop(k); cash+=p["qty"]*p["out_px"]*(1-slip)
        prev=all_sessions[all_sessions.index(d)-1]
        if d in by.groups and regime_ok.get(prev,True):
            for k,r in by.get_group(d).iterrows():
                if len(open_pos)>=mp or r.symbol in {p["sym"] for p in open_pos.values()}: continue
                mv=sum(p["qty"]*closes[p["sym"]].get(d,p["in_px"]) for p in open_pos.values()); px=r.in_px*(1+slip); qty=math.floor((cash+mv)*size/px)
                if qty<=0 or qty*px>cash: continue
                cash-=qty*px; open_pos[k]=dict(sym=r.symbol,qty=qty,in_px=px,exit=r.exit,out_px=r.out_px,entry_d=d); tk.append((d,r.out_px*(1-slip)/px-1))
        mv=sum(p["qty"]*(closes[p["sym"]].get(d,np.nan) if not np.isnan(closes[p["sym"]].get(d,np.nan)) else p["in_px"]) for p in open_pos.values()); eq.append(cash+mv)
    eq=pd.Series(eq,index=ses); tk=pd.DataFrame(tk,columns=["d","r"])
    ys={n:eq[(eq.index>=a)&(eq.index<=b)].iloc[-1]/eq[(eq.index>=a)&(eq.index<=b)].iloc[0]-1 for n,a,b in yrs_w}
    pfs={n:(lambda x:x[x>0].sum()/max(1e-9,-x[x<=0].sum()))(tk[(tk.d>=a)&(tk.d<=b)].r) for n,a,b in yrs_w}
    return eq,ys,pfs
print("=== (1) sizing / path dependence: hold-N with stop, three sizings ===")
print(f"{'cell':14s} "+" ".join(f"{s:>22s}" for s in ("5x20%","10x10%","20x5%")))
for hold,stop in ((20,0.08),(20,0.10),(25,0.08),(25,0.10),(25,0.12),(30,0.08)):
    t=trades_for(None,stop,0,0,hold); cells=[]
    for mp,sz in ((5,0.20),(10,0.10),(20,0.05)):
        eq,ys,pfs=sim_full(t,mp,sz); cells.append(f"{eq.iloc[-1]/1e5-1:+7.1%} dd{(eq/eq.cummax()-1).min():6.1%} {sum(ys[k]>spy_y[k] for k in ys)}/6")
    print(f"{hold:2d}d -{stop:.0%}       "+" ".join(f"{c:>22s}" for c in cells),flush=True)
t=trades_for("e21",0,0,0,0); cells=[]
for mp,sz in ((5,0.20),(10,0.10),(20,0.05)):
    eq,ys,pfs=sim_full(t,mp,sz); cells.append(f"{eq.iloc[-1]/1e5-1:+7.1%} dd{(eq/eq.cummax()-1).min():6.1%} {sum(ys[k]>spy_y[k] for k in ys)}/6")
print(f"{'EMA21 trail':14s} "+" ".join(f"{c:>22s}" for c in cells))
print("\n=== (2) the bar, per window, 10x10%: excess vs SPY and PF ===")
for hold,stop in ((25,0.08),(25,0.10),(20,0.10)):
    t=trades_for(None,stop,0,0,hold); eq,ys,pfs=sim_full(t,10,0.10)
    print(f"{hold}d -{stop:.0%}: "+"  ".join(f"{k}: {ys[k]-spy_y[k]:+5.1%} PF {pfs[k]:.2f}" for k in ys)+f"  | excess>0 in {sum(ys[k]>spy_y[k] for k in ys)}/6, min PF {min(pfs.values()):.2f}, maxDD {(eq/eq.cummax()-1).min():.1%}")
print("\n=== (3) selection split: choose (hold,stop) on 2021-23 only, report 2024-26 ===")
R=pd.read_csv("out/exit_neighbourhood.csv")
R["is_tot"]=(1+R["2021"])*(1+R["2022"])*(1+R["2023"])-1; R["oos_tot"]=(1+R["2024"])*(1+R["2025"])*(1+R["2026"])-1
spy_is=(1+spy_y["2021"])*(1+spy_y["2022"])*(1+spy_y["2023"])-1; spy_oos=(1+spy_y["2024"])*(1+spy_y["2025"])*(1+spy_y["2026"])-1
top=R.sort_values("is_tot",ascending=False).head(5)
print(f"SPY: 2021-23 {spy_is:+.1%}, 2024-26 {spy_oos:+.1%}")
for _,r in top.iterrows(): print(f"  hold {int(r.hold)} stop {r.stop:.0%}: IS {r.is_tot:+.1%} -> OOS {r.oos_tot:+.1%} (beats SPY OOS: {r.oos_tot>spy_oos})")
top2=R.sort_values("oos_tot",ascending=False).head(5); print("reverse: choose on 2024-26, report 2021-23")
for _,r in top2.iterrows(): print(f"  hold {int(r.hold)} stop {r.stop:.0%}: OOS-chosen {r.oos_tot:+.1%} -> 2021-23 {r.is_tot:+.1%} (beats SPY: {r.is_tot>spy_is})")
print("\n=== (4) per-signal 25-session demeaned excess (next open -> open 25 sessions later), top-3 RS signals of each day vs all signals, by year ===")
rows=[]
so=S.o
for s,k,rs in sigs:
    d=F[s]; idx=d.index
    if k+26>=len(idx): continue
    e0,e1=idx[k+1],idx[k+26]
    if e0 not in so.index or e1 not in so.index: continue
    rows.append(dict(symbol=s,date=idx[k],rs=rs,ex=d.o.values[k+26]/d.o.values[k+1]-1-(so[e1]/so[e0]-1),regime=regime_ok.get(idx[k],True)))
X=pd.DataFrame(rows); X["year"]=pd.to_datetime(X.date).dt.year; X["rank"]=X.groupby("date").rs.rank(ascending=False)
for lab,sub in (("all signals",X),("regime on",X[X.regime]),("regime on, top-3 RS of the day",X[X.regime&(X["rank"]<=3)]),("regime on, top-1 RS of the day",X[X.regime&(X["rank"]<=1)])):
    g_=sub.groupby("year").ex.agg(["size","mean"]); print(f"{lab:34s} n={len(sub):5d} mean {sub.ex.mean()*100:+.2f}% t={sub.ex.mean()/(sub.ex.std()/np.sqrt(len(sub))):.2f} | "+" ".join(f"{y}:{m*100:+.1f}%({n})" for y,(n,m) in g_.iterrows()))
