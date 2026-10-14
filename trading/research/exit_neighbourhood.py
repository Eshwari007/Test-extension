import sys, os, io, contextlib
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
src=open('exit_grid_pit.py').read().split('spy_total=S.c')[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
import numpy as np, pandas as pd, datetime as dt
yrs_w=[("2021",dt.date(2021,1,4),dt.date(2021,12,31)),("2022",dt.date(2022,1,3),dt.date(2022,12,30)),("2023",dt.date(2023,1,3),dt.date(2023,12,29)),("2024",dt.date(2024,1,2),dt.date(2024,12,31)),("2025",dt.date(2025,1,2),dt.date(2025,12,31)),("2026",dt.date(2026,1,2),dt.date(2026,10,9))]
spy_total=S.c[ses[-1]]/S.c[ses[0]]-1
spy_y={n:S.c[[d for d in ses if a<=d<=b][-1]]/S.c[[d for d in ses if a<=d<=b][0]]-1 for n,a,b in yrs_w}
def sim_years(t,mp=10,size=0.10,slip=5e-4,eq0=1e5):
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
    ys={n:eq[(eq.index>=a)&(eq.index<=b)].iloc[-1]/eq[(eq.index>=a)&(eq.index<=b)].iloc[0]-1 for n,a,b in yrs_w}
    return eq.iloc[-1]/eq0-1,(eq/eq.cummax()-1).min(),len(tk),tk[tk>0].sum()/max(1e-9,-tk[tk<=0].sum()),ys
print("NEIGHBOURHOOD: hold N sessions then sell at close, hard stop only (no trail), ranked, regime, 10x10%")
print(f"{'hold':>5s} {'stop':>6s} | {'total':>7s} {'maxDD':>6s} {'PF':>5s} {'n':>4s} | "+" ".join(f"{n:>7s}" for n,_,_ in yrs_w)+" | beats SPY")
print(f"{'SPY':>12s} | {spy_total:+7.1%} {'':>6s} {'':>5s} {'':>4s} | "+" ".join(f"{spy_y[n]:+7.1%}" for n,_,_ in yrs_w))
rows=[]
for hold in (10,15,20,25,30,40,60):
    for stop in (0,0.06,0.08,0.10,0.12):
        t=trades_for(None,stop,0,0,hold); tot,dd,n,pf,ys=sim_years(t); beat=sum(ys[k]>spy_y[k] for k in ys)
        print(f"{hold:5d} {('-'+format(stop,'.0%')) if stop else 'none':>6s} | {tot:+7.1%} {dd:6.1%} {pf:5.2f} {n:4d} | "+" ".join(f"{ys[n_]:+7.1%}" for n_,_,_ in yrs_w)+f" | {beat} of 6",flush=True)
        rows.append(dict(hold=hold,stop=stop,total=tot,maxdd=dd,pf=pf,n=n,beat=beat,**ys))
pd.DataFrame(rows).to_csv("out/exit_neighbourhood.csv",index=False)
print("\nfor comparison, EMA21 trail (the plan) by year:")
t=trades_for("e21",0,0,0,0); tot,dd,n,pf,ys=sim_years(t); print(f"{'e21':>12s} | {tot:+7.1%} {dd:6.1%} {pf:5.2f} {n:4d} | "+" ".join(f"{ys[n_]:+7.1%}" for n_,_,_ in yrs_w)+f" | {sum(ys[k]>spy_y[k] for k in ys)} of 6")
