"""$100k through swing + trend books together, with and without the earnings collar on the trend book."""
import sys, io, contextlib, math, datetime as dt, numpy as np, pandas as pd; sys.path.insert(0,'.')
from engine import Dataset, Params, run
from run import ALL
import portfolio as P
import data as D
ds=Dataset(); P.init(ds)
# --- swing book (tuned, 5-min entries) ---
C=Params(mode="orb",orb_bars=3,vol_mult=1.5,stop_mode="pct",stop_pct=5,targets=(),trail="none",hold="overnight",max_hold_days=3,earliest="09:45",max_off_high=10)
sw=run(ds,C,*ALL)
# --- trend book (B3 daily) ---
src=open('capture_portfolio.py').read().split('print(f"SPY:')[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
tr=sets["B3 breakout+vol, Stage-1, exit <EMA21"].copy()
tr["in_px"]=[F[s].o.get(d,np.nan) for s,d in zip(tr.symbol,tr.entry)]; tr["out_px"]=tr.in_px*(1+tr.ret)
# --- collar adjustment on trend trades: clip earnings-sized gap days inside the hold to [-10%,+15%] ---
G=pd.read_csv('out/gap_events.csv',parse_dates=['date']); G['date']=G.date.dt.date
adj=tr.copy(); hits=0; delta=[]
for i,r in adj.iterrows():
    ev=G[(G.symbol==r.symbol)&(G.date>r.entry)&(G.date<=r.exit)]
    d=0.0
    for _,e in ev.iterrows():
        d+=min(max(e.day,-0.10),0.15)-e.day; hits+=1
    delta.append(d)
adj["ret"]=adj.ret+np.array(delta); adj["out_px"]=adj.in_px*(1+adj.ret)
print(f"trend trades {len(tr)}, earnings-sized gap days inside a hold: {hits}; collar adds {np.sum(delta)*100:+.1f} pct-points of trade return in total")
def trend_curve(t,mp,sz,start_eq):
    m,eq=portfolio(t,mp,sz,5e-4,start_eq); return eq,m
def swing_curve(t,mp,sz,start_eq):
    with contextlib.redirect_stdout(io.StringIO()): eq=P.portfolio(t,mp,sz,5,start_eq=start_eq,label="")
    return eq
def stats(eq,label):
    ret=eq.pct_change().dropna(); yrs=(eq.index[-1]-eq.index[0]).days/365.25
    y25=eq[eq.index<=dt.date(2025,12,31)]; y26=eq[eq.index>dt.date(2025,12,31)]
    print(f"{label:52s} final ${eq.iloc[-1]:,.0f}  total {eq.iloc[-1]/1e5-1:+.1%}  CAGR {(eq.iloc[-1]/1e5)**(1/yrs)-1:+.1%}  maxDD {(eq/eq.cummax()-1).min():.1%}  Sharpe {ret.mean()/ret.std()*math.sqrt(252):.2f}  2025 {y25.iloc[-1]/1e5-1:+.1%}  2026 {eq.iloc[-1]/y25.iloc[-1]-1:+.1%}")
spy=P.spy_d['c'].reindex(sorted(set(ds.sessions)&set(sw.session.unique())|set(sessions))).dropna()
sessions_all=sorted(set(sessions))
spy=P.spy_d['c'].reindex(sessions_all); spy=spy/spy.iloc[0]*1e5
print("\n$100,000, Jan 2 2025 -> Oct 9 2026 (21.3 months), 5 bps slippage per side:")
stats(spy,"SPY buy and hold")
s100=swing_curve(sw,10,0.10,1e5); stats(s100,"Swing book only, 10 slots x 10%")
t100,_=trend_curve(tr,10,0.10,1e5); stats(t100,"Trend book only, 10 slots x 10%, no collar")
t100c,_=trend_curve(adj,10,0.10,1e5); stats(t100c,"Trend book only, 10 slots x 10%, with collar")
s50=swing_curve(sw,5,0.20,5e4); t50,_=trend_curve(tr,5,0.20,5e4); t50c,_=trend_curve(adj,5,0.20,5e4)
s50b=swing_curve(sw,10,0.10,5e4); t50b,_=trend_curve(tr,10,0.10,5e4); t50bc,_=trend_curve(adj,10,0.10,5e4)
comb=(s50.reindex(sessions_all).ffill()+t50.reindex(sessions_all).ffill()); stats(comb,"50/50: swing 5x20% + trend 5x20%, no collar")
combc=(s50.reindex(sessions_all).ffill()+t50c.reindex(sessions_all).ffill()); stats(combc,"50/50: swing 5x20% + trend 5x20%, with collar")
comb2=(s50b.reindex(sessions_all).ffill()+t50bc.reindex(sessions_all).ffill()); stats(comb2,"50/50: swing 10x10% + trend 10x10% (half-size slots), collar")
pd.DataFrame({"spy":spy,"swing_100k":s100.reindex(sessions_all).ffill(),"trend_100k":t100.reindex(sessions_all).ffill(),"trend_100k_collar":t100c.reindex(sessions_all).ffill(),"combined_50_50":comb,"combined_50_50_collar":combc}).to_csv("out/combined_100k_curves.csv")
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(11,5.5)); x=pd.to_datetime(pd.Series(sessions_all))
for ser,lab,lw in ((combc,'50/50 swing + trend, with collar',2.2),(s100.reindex(sessions_all).ffill(),'Swing book only',1.3),(t100c.reindex(sessions_all).ffill(),'Trend book only (collar)',1.3),(spy,'SPY',1.2)):
    ax.plot(x,ser.values,lw=lw,label=lab,ls='--' if lab=='SPY' else '-',color='gray' if lab=='SPY' else None)
ax.set_title('$100,000 from Jan 2 2025 to Oct 9 2026'); ax.set_ylabel('USD'); ax.grid(alpha=.3); ax.legend(); fig.tight_layout(); fig.savefig('out/combined_100k.png',dpi=130)
print("\nmonthly P&L of the 50/50 + collar portfolio:")
m=combc.groupby(pd.to_datetime(pd.Series(combc.index)).dt.to_period('M').values).agg(['first','last']); print(((m['last']/m['first']-1)*100).round(1).to_string())
